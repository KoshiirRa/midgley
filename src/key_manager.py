"""
Key Manager & Access Control Engine (src/key_manager.py)
Provides SQLite-backed API key provisioning, salted PBKDF2 SHA-256 token hashing,
tier-based access validation (privileged vs basic), sliding-window rate limiting,
and revocation management for Midgley REST API Gateway & MCP Server.
"""

import os
import sqlite3
import secrets
import hashlib
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger(__name__)

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
        Validates an incoming plaintext token against SQLite registry.
        Returns (is_valid, key_info_dict, error_message).
        """
        if not token or not isinstance(token, str):
            return False, None, "Missing or invalid token string."

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

        return True, key_info, None

    def check_rate_limit(self, key_prefix: str, rate_limit_rpm: int = DEFAULT_RPM) -> Tuple[bool, int]:
        """
        Enforces 1-minute sliding window rate limiting.
        Returns (allowed, retry_after_seconds).
        """
        current_minute = int(time.time() // 60)
        current_second = int(time.time())
        retry_after = 60 - (current_second % 60)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Fetch request count for current minute
            cursor.execute(
                """
                SELECT request_count FROM rate_limits
                WHERE key_prefix = ? AND minute_timestamp = ?
                """,
                (key_prefix, current_minute)
            )
            row = cursor.fetchone()

            if row:
                count = row["request_count"]
                if count >= rate_limit_rpm:
                    return False, retry_after
                
                cursor.execute(
                    """
                    UPDATE rate_limits SET request_count = request_count + 1
                    WHERE key_prefix = ? AND minute_timestamp = ?
                    """,
                    (key_prefix, current_minute)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO rate_limits (key_prefix, minute_timestamp, request_count)
                    VALUES (?, ?, 1)
                    """,
                    (key_prefix, current_minute)
                )

            # Cleanup older minute records (older than 10 minutes)
            old_cutoff = current_minute - 10
            cursor.execute("DELETE FROM rate_limits WHERE minute_timestamp < ?", (old_cutoff,))
            conn.commit()

        return True, 0

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
        """Revokes an API key by prefix."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE api_keys SET active = 0 WHERE key_prefix = ?",
                (key_prefix,)
            )
            conn.commit()
            updated = cursor.rowcount > 0

        if updated:
            logger.info(f"Revoked API key prefix [{key_prefix}]")
        return updated


# Default singleton instance
global_key_manager = KeyManager()
