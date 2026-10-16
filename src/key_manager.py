"""
Key Manager & Access Control Engine (src/key_manager.py)
Provides SQLite-backed API key provisioning, salted PBKDF2 SHA-256 token hashing,
tier-based access validation (privileged vs basic), sliding-window rate limiting,
and revocation management for Midgley REST API Gateway & MCP Server.
"""

import os
import re
import math
import sqlite3
import secrets
import hashlib
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger(__name__)

# Secret Redaction Patterns (Issue #570, #614)
SECRET_PATTERNS = [
    re.compile(r"gh[opusr]_[A-Za-z0-9_]{20,}", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}", re.IGNORECASE),
    re.compile(r"mg_(?:prod|dev)_[A-Za-z0-9_]{16,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"https?://(?:[a-zA-Z0-9-]+\.)?hc-ping\.com/[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", re.IGNORECASE),
]


def redact_secrets(text: Optional[str]) -> str:
    """Masks secret tokens and sensitive API keys with [REDACTED] (Issue #570, #614)."""
    if not text:
        return ""
    redacted = str(text)
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


class RedactingLoggingFilter(logging.Filter):
    """Logging filter that sanitizes secret tokens, webhooks, and ping URLs from log messages (Issue #614)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (redact_secrets(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            elif isinstance(record.args, (tuple, list)):
                record.args = tuple(redact_secrets(a) if isinstance(a, str) else a for a in record.args)
        return True


def setup_logging_redaction(root_logger: Optional[logging.Logger] = None) -> None:
    """Attaches RedactingLoggingFilter to root and configured handlers (Issue #614)."""
    target = root_logger or logging.getLogger()
    filt = RedactingLoggingFilter()
    for handler in target.handlers:
        handler.addFilter(filt)
    target.addFilter(filt)


# Default Database Path
DEFAULT_DB_PATH = os.path.join("data", "security.db")
DEFAULT_RPM = 30


class KeyManager:
    """
    SQLite-backed key registry and rate limiting manager.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # In-memory token verification cache: token_hash -> (cached_at_epoch, is_valid, key_info, err) (Issue #614)
        self._verification_cache: Dict[str, Tuple[float, bool, Optional[Dict[str, Any]], Optional[str]]] = {}
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes SQLite schema for api_keys and rate_limits if not exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_prefix TEXT UNIQUE NOT NULL,
                    key_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    tier TEXT NOT NULL DEFAULT 'basic',
                    rate_limit_rpm INTEGER NOT NULL DEFAULT 30,
                    environment TEXT NOT NULL DEFAULT 'dev',
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    key_prefix TEXT NOT NULL,
                    minute_timestamp INTEGER NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (key_prefix, minute_timestamp)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_prefix TEXT NOT NULL,
                    timestamp_sec REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rate_limit_events_prefix_ts ON rate_limit_events(key_prefix, timestamp_sec)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)
            """)
            conn.commit()

    @staticmethod
    def _hash_token(token: str, salt: str) -> str:
        """Computes salted PBKDF2 SHA-256 hash for a raw token."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            token.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()

    def create_key(
        self,
        user_id: str,
        tier: str = "basic",
        rate_limit_rpm: int = DEFAULT_RPM,
        environment: str = "dev",
        expires_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Provisions a new API key.
        Returns dict containing the raw plaintext token (shown ONLY once) and key metadata.
        """
        tier = tier.lower()
        if tier not in ("privileged", "basic"):
            tier = "basic"
        
        env_code = "prod" if environment.lower() in ("prod", "production") else "dev"
        raw_hex = secrets.token_hex(24)
        prefix = f"mg_{env_code}_{raw_hex[:8]}"
        token = f"{prefix}_{raw_hex[8:]}"

        salt = secrets.token_hex(16)
        key_hash = self._hash_token(token, salt)

        now_dt = datetime.now(timezone.utc)
        created_at = now_dt.isoformat()
        
        expires_at = None
        if expires_days and expires_days > 0:
            expires_at = (now_dt + timedelta(days=expires_days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO api_keys (
                    key_prefix, key_hash, salt, user_id, tier,
                    rate_limit_rpm, environment, created_at, expires_at, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (prefix, key_hash, salt, user_id, tier, rate_limit_rpm, env_code, created_at, expires_at)
            )
            conn.commit()

        logger.info(f"Created API key [{prefix}] for user '{user_id}' ({tier} tier, {env_code} env)")

        return {
            "token": token,
            "key_prefix": prefix,
            "user_id": user_id,
            "tier": tier,
            "rate_limit_rpm": rate_limit_rpm,
            "environment": env_code,
            "created_at": created_at,
            "expires_at": expires_at,
            "active": True
        }

    def verify_key(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validates an incoming plaintext token against SQLite registry with 60-second in-memory caching (Issue #614).
        Returns (is_valid, key_info_dict, error_message).
        """
        if not token or not isinstance(token, str):
            return False, None, "Missing or invalid token string."

        # Check in-memory 60s verification cache
        cache_key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.time()
        cached = self._verification_cache.get(cache_key)
        if cached and (now - cached[0] < 60.0):
            return cached[1], cached[2], cached[3]

        parts = token.split("_")
        if len(parts) < 3:
            return False, None, "Invalid API key format."

        prefix = f"{parts[0]}_{parts[1]}_{parts[2]}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT key_prefix, key_hash, salt, user_id, tier, rate_limit_rpm, environment, created_at, expires_at, active
                FROM api_keys
                WHERE key_prefix = ?
                """,
                (prefix,)
            )
            row = cursor.fetchone()

        if not row:
            return False, None, "API key prefix not found."

        if not row["active"]:
            return False, None, "API key has been revoked."

        if row["expires_at"]:
            try:
                exp_dt = datetime.fromisoformat(row["expires_at"])
                if datetime.now(timezone.utc) > exp_dt:
                    return False, None, "API key has expired."
            except Exception:
                pass

        # Verify PBKDF2 hash match
        expected_hash = row["key_hash"]
        salt = row["salt"]
        computed_hash = self._hash_token(token, salt)

        if not secrets.compare_digest(computed_hash, expected_hash):
            return False, None, "Invalid API key token signature."

        key_info = {
            "key_prefix": row["key_prefix"],
            "user_id": row["user_id"],
            "tier": row["tier"],
            "rate_limit_rpm": row["rate_limit_rpm"],
            "environment": row["environment"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"]
        }

        # Cache successful verification for 60 seconds
        self._verification_cache[cache_key] = (now, True, key_info, None)
        return True, key_info, None

    def check_rate_limit(self, key_prefix: str, rate_limit_rpm: int = DEFAULT_RPM) -> Tuple[bool, int, int, int]:
        """
        Enforces true continuous 60-second sliding-window rate limiting using SQLite rate_limit_events (Issue #614 T-26).
        Returns (allowed, retry_after_seconds, remaining_requests, reset_seconds).
        Eliminates 2x boundary bursts across calendar minutes.
        """
        now = time.time()
        window_start = now - 60.0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Prune events older than 60 seconds
            cursor.execute("DELETE FROM rate_limit_events WHERE timestamp_sec < ?", (window_start,))

            # 2. Count requests in active 60-second trailing window
            cursor.execute(
                """
                SELECT COUNT(*), MIN(timestamp_sec)
                FROM rate_limit_events
                WHERE key_prefix = ? AND timestamp_sec >= ?
                """,
                (key_prefix, window_start)
            )
            row = cursor.fetchone()
            count = row[0] if row else 0
            oldest_ts = row[1] if (row and row[1]) else now

            if count >= rate_limit_rpm:
                retry_after = max(1, int(math.ceil(60.0 - (now - oldest_ts))))
                conn.commit()
                return False, retry_after, 0, retry_after

            # 3. Insert current request event into sliding window ledger
            cursor.execute(
                "INSERT INTO rate_limit_events (key_prefix, timestamp_sec) VALUES (?, ?)",
                (key_prefix, now)
            )

            # 4. Backward-compatible aggregate update in rate_limits table
            current_minute = int(now // 60)
            cursor.execute(
                """
                INSERT INTO rate_limits (key_prefix, minute_timestamp, request_count)
                VALUES (?, ?, 1)
                ON CONFLICT(key_prefix, minute_timestamp)
                DO UPDATE SET request_count = request_count + 1
                """,
                (key_prefix, current_minute)
            )
            conn.commit()

            remaining = max(0, rate_limit_rpm - (count + 1))
            return True, 0, remaining, 60

    def list_keys(self, environment: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists metadata for registered API keys (excluding secret hashes/salts)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if environment:
                env_code = "prod" if environment.lower() in ("prod", "production") else "dev"
                cursor.execute(
                    """
                    SELECT key_prefix, user_id, tier, rate_limit_rpm, environment, created_at, expires_at, active
                    FROM api_keys WHERE environment = ? ORDER BY id DESC
                    """,
                    (env_code,)
                )
            else:
                cursor.execute(
                    """
                    SELECT key_prefix, user_id, tier, rate_limit_rpm, environment, created_at, expires_at, active
                    FROM api_keys ORDER BY id DESC
                    """
                )
            rows = cursor.fetchall()

        return [
            {
                "key_prefix": r["key_prefix"],
                "user_id": r["user_id"],
                "tier": r["tier"],
                "rate_limit_rpm": r["rate_limit_rpm"],
                "environment": r["environment"],
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
                "active": bool(r["active"])
            }
            for r in rows
        ]

    def revoke_key(self, key_prefix: str) -> bool:
        """Revokes an API key by prefix and clears verification cache (Issue #614)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE api_keys SET active = 0 WHERE key_prefix = ?",
                (key_prefix,)
            )
            conn.commit()
            updated = cursor.rowcount > 0

        if updated:
            self._verification_cache.clear()
            logger.info(f"Revoked API key prefix [{key_prefix}]")
        return updated

    async def verify_key_async(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Non-blocking asynchronous wrapper for verify_key (offloads PBKDF2 to worker thread)."""
        return await asyncio.to_thread(self.verify_key, token)

    async def check_rate_limit_async(self, key_prefix: str, rate_limit_rpm: int = DEFAULT_RPM) -> Tuple[bool, int, int, int]:
        """Non-blocking asynchronous wrapper for check_rate_limit (offloads SQLite I/O to worker thread)."""
        return await asyncio.to_thread(self.check_rate_limit, key_prefix, rate_limit_rpm)


# Default singleton instance
global_key_manager = KeyManager()
