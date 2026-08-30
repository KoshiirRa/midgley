"""
Lookup Cache Module (src/lookup_cache.py)
Provides 3-tier response caching & quota ledger synchronization:
- Tier 1 (Primary): Turso Edge SQLite HTTP REST API (TURSO_DATABASE_URL & TURSO_AUTH_TOKEN)
- Tier 2 (Backup): Cloudflare D1/R2 Edge Worker (CLOUDFLARE_CACHE_URL & CLOUDFLARE_AUTH_TOKEN)
- Tier 3 (Fallback): Local SQLite Datastore (data/lookup_cache.sqlite) + In-Memory Fast Dict
"""

import os
import json
import sqlite3
import time
import sys
import urllib.request
import urllib.error
import logging
from typing import Optional, Dict, Any, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _load_env_fallback():
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_fallback()

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DB = os.path.join("data", "lookup_cache.sqlite")
DEFAULT_TTL_SECONDS = 900  # 15 minutes
HTTP_TIMEOUT_SECONDS = 2.0


class LookupCache:
    """
    3-Tier Thread-safe Lookup Cache with edge fallbacks & shared quota ledger sync.
    """

    def __init__(self, db_path: str = DEFAULT_CACHE_DB):
        self.db_path = db_path
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._use_sqlite = True
        self.stats = {
            "hits_in_memory": 0,
            "hits_turso": 0,
            "hits_cloudflare": 0,
            "hits_local_sqlite": 0,
            "misses": 0,
            "writes": 0,
            "errors": 0,
        }
        self._init_db()

    def _init_db(self):
        """Initializes local SQLite database schema if possible."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS lookup_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL
                    )
                """)
                conn.commit()
            logger.info(f"Initialized local SQLite lookup cache at: {self.db_path}")
        except Exception as e:
            logger.warning(f"Could not initialize SQLite database at {self.db_path}: {e}. Falling back to in-memory.")
            self._use_sqlite = False

    def _get_edge_credentials(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        turso_url = os.environ.get("TURSO_DATABASE_URL")
        turso_token = os.environ.get("TURSO_AUTH_TOKEN")
        cf_url = os.environ.get("CLOUDFLARE_CACHE_URL")
        cf_token = os.environ.get("CLOUDFLARE_AUTH_TOKEN")
        if turso_url and turso_url.startswith("turso://"):
            turso_url = "https://" + turso_url[8:]
        if cf_url and cf_url.startswith("http://"):
            cf_url = "https://" + cf_url[7:]
        return turso_url, turso_token, cf_url, cf_token

    def _turso_ensure_table(self, turso_url: str, turso_token: str):
        """Ensures the lookup_cache table exists on remote Turso Edge SQLite."""
        if getattr(self, "_turso_table_initialized", False):
            return
        try:
            endpoint = f"{turso_url.rstrip('/')}/v2/pipeline"
            headers = {
                "Authorization": f"Bearer {turso_token}",
                "Content-Type": "application/json",
            }
            body = json.dumps({
                "requests": [
                    {
                        "type": "execute",
                        "stmt": {
                            "sql": "CREATE TABLE IF NOT EXISTS lookup_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL)"
                        },
                    },
                    {"type": "close"}
                ]
            }).encode("utf-8")
            req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    self._turso_table_initialized = True
        except Exception as e:
            logger.warning(f"Turso table initialization notice: {e}")

    def _turso_get(self, key: str, turso_url: str, turso_token: str) -> Optional[Tuple[str, float, float]]:
        """Queries Tier 1 Turso Edge SQLite via HTTPS REST API."""
        try:
            self._turso_ensure_table(turso_url, turso_token)
            endpoint = f"{turso_url.rstrip('/')}/v2/pipeline"
            headers = {
                "Authorization": f"Bearer {turso_token}",
                "Content-Type": "application/json",
            }
            body = json.dumps({
                "requests": [
                    {
                        "type": "execute",
                        "stmt": {
                            "sql": "SELECT value, created_at, expires_at FROM lookup_cache WHERE key = ?",
                            "args": [{"type": "text", "value": key}],
                        },
                    },
                    {"type": "close"}
                ]
            }).encode("utf-8")

            req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results", [])
                    if results and results[0].get("type") == "ok":
                        rows = results[0].get("response", {}).get("result", {}).get("rows", [])
                        if rows:
                            row = rows[0]
                            val_str = row[0].get("value")
                            created_at = float(row[1].get("value", 0))
                            expires_at = float(row[2].get("value", 0))
                            return val_str, created_at, expires_at
        except Exception as e:
            logger.warning(f"Turso Edge cache fetch notice: {e}")
            self.stats["errors"] += 1
        return None

    def _turso_set(self, key: str, val_str: str, created_at: float, expires_at: float, turso_url: str, turso_token: str):
        """Writes entry to Tier 1 Turso Edge SQLite via HTTPS REST API."""
        try:
            self._turso_ensure_table(turso_url, turso_token)
            endpoint = f"{turso_url.rstrip('/')}/v2/pipeline"
            headers = {
                "Authorization": f"Bearer {turso_token}",
                "Content-Type": "application/json",
            }
            body = json.dumps({
                "requests": [
                    {
                        "type": "execute",
                        "stmt": {
                            "sql": "INSERT OR REPLACE INTO lookup_cache (key, value, created_at, expires_at) VALUES (?, ?, ?, ?)",
                            "args": [
                                {"type": "text", "value": key},
                                {"type": "text", "value": val_str},
                                {"type": "float", "value": float(created_at)},
                                {"type": "float", "value": float(expires_at)},
                            ],
                        },
                    },
                    {"type": "close"}
                ]
            }).encode("utf-8")

            req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                pass
        except Exception as e:
            logger.warning(f"Turso Edge cache write notice: {e}")
            self.stats["errors"] += 1

    def _cloudflare_get(self, key: str, cf_url: str, cf_token: str = None) -> Optional[Tuple[str, float, float]]:
        """Queries Tier 2 Cloudflare D1/R2 Worker REST API."""
        try:
            endpoint = f"{cf_url.rstrip('/')}/api/v1/cache/{urllib.parse.quote(key)}"
            headers = {"User-Agent": "MidgleyCacheGateway/1.0"}
            if cf_token:
                headers["Authorization"] = f"Bearer {cf_token}"
            req = urllib.request.Request(endpoint, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    val_str = json.dumps(data.get("value", {}))
                    created_at = float(data.get("created_at", time.time()))
                    expires_at = float(data.get("expires_at", time.time() + DEFAULT_TTL_SECONDS))
                    return val_str, created_at, expires_at
        except Exception as e:
            logger.warning(f"Cloudflare Edge cache fetch notice: {e}")
            self.stats["errors"] += 1
        return None

    def _cloudflare_set(self, key: str, val_str: str, created_at: float, expires_at: float, cf_url: str, cf_token: str = None):
        """Writes entry to Tier 2 Cloudflare D1/R2 Worker REST API."""
        try:
            endpoint = f"{cf_url.rstrip('/')}/api/v1/cache"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "MidgleyCacheGateway/1.0"
            }
            if cf_token:
                headers["Authorization"] = f"Bearer {cf_token}"
            payload = {
                "key": key,
                "value": json.loads(val_str),
                "created_at": created_at,
                "expires_at": expires_at,
            }
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                pass
        except Exception as e:
            logger.warning(f"Cloudflare Edge cache write notice: {e}")
            self.stats["errors"] += 1

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a cached value using 3-tier cascading evaluation.
        Returns None if cache miss or expired.
        """
        now = time.time()

        # In-memory fast dictionary check
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if now < entry["expires_at"]:
                self.stats["hits_in_memory"] += 1
                val_dict = dict(entry["value"])
                val_dict["_cache_hit"] = True
                val_dict["_cache_tier"] = "in-memory"
                val_dict["_cache_age_seconds"] = round(now - entry["created_at"], 1)
                return val_dict
            else:
                del self._memory_cache[key]

        turso_url, turso_token, cf_url, cf_token = self._get_edge_credentials()

        # Tier 1: Turso Edge SQLite
        if turso_url and turso_token:
            res = self._turso_get(key, turso_url, turso_token)
            if res:
                val_str, created_at, expires_at = res
                if now < expires_at:
                    self.stats["hits_turso"] += 1
                    val_dict = json.loads(val_str)
                    val_dict["_cache_hit"] = True
                    val_dict["_cache_tier"] = "turso-edge"
                    val_dict["_cache_age_seconds"] = round(now - created_at, 1)
                    # Cache back to in-memory
                    self._memory_cache[key] = {"value": val_dict, "created_at": created_at, "expires_at": expires_at}
                    return val_dict

        # Tier 2: Cloudflare D1/R2 Worker
        if cf_url:
            res = self._cloudflare_get(key, cf_url, cf_token)
            if res:
                val_str, created_at, expires_at = res
                if now < expires_at:
                    self.stats["hits_cloudflare"] += 1
                    val_dict = json.loads(val_str)
                    val_dict["_cache_hit"] = True
                    val_dict["_cache_tier"] = "cloudflare-edge"
                    val_dict["_cache_age_seconds"] = round(now - created_at, 1)
                    self._memory_cache[key] = {"value": val_dict, "created_at": created_at, "expires_at": expires_at}
                    return val_dict

        # Tier 3: Local SQLite
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT value, created_at, expires_at FROM lookup_cache WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    if row:
                        val_str, created_at, expires_at = row
                        if now < expires_at:
                            self.stats["hits_local_sqlite"] += 1
                            val_dict = json.loads(val_str)
                            val_dict["_cache_hit"] = True
                            val_dict["_cache_tier"] = "local-sqlite"
                            val_dict["_cache_age_seconds"] = round(now - created_at, 1)
                            self._memory_cache[key] = {"value": val_dict, "created_at": created_at, "expires_at": expires_at}
                            return val_dict
                        else:
                            cursor.execute("DELETE FROM lookup_cache WHERE key = ?", (key,))
                            conn.commit()
            except Exception as e:
                logger.warning(f"Error reading local SQLite cache for key '{key}': {e}")
                self.stats["errors"] += 1

        self.stats["misses"] += 1
        return None

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Stores a dictionary value across active cache tiers.
        """
        now = time.time()
        expires_at = now + ttl_seconds
        clean_val = {k: v for k, v in value.items() if not k.startswith("_")}
        val_str = json.dumps(clean_val)

        self.stats["writes"] += 1

        # Always update in-memory
        self._memory_cache[key] = {
            "value": clean_val,
            "created_at": now,
            "expires_at": expires_at
        }

        # Tier 3: Local SQLite
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO lookup_cache (key, value, created_at, expires_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (key, val_str, now, expires_at)
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Error setting local SQLite cache for key '{key}': {e}")
                self.stats["errors"] += 1

        turso_url, turso_token, cf_url, cf_token = self._get_edge_credentials()

        # Tier 1: Turso Edge SQLite
        if turso_url and turso_token:
            self._turso_set(key, val_str, now, expires_at, turso_url, turso_token)

        # Tier 2: Cloudflare Worker
        if cf_url:
            self._cloudflare_set(key, val_str, now, expires_at, cf_url, cf_token)

    def get_quota_ledger(self, service: str) -> dict:
        """
        Retrieves the shared multi-tier quota ledger for a specific service.
        """
        cache_key = f"quota:{service}:current"
        data = self.get(cache_key)
        if data:
            return data
        return {}

    def update_quota_ledger(self, service: str, monthly_calls: int, today_calls: int, month_key: str, day_key: str) -> dict:
        """
        Updates the shared multi-tier quota ledger for a specific service.
        """
        cache_key = f"quota:{service}:current"
        payload = {
            "service": service,
            "current_month": month_key,
            "monthly_calls": monthly_calls,
            "daily_calls": {day_key: today_calls},
            "last_updated": time.time(),
        }
        # Quota ledger persisted for 60 days
        self.set(cache_key, payload, ttl_seconds=86400 * 60)
        return payload

    def clear(self):
        """Clears all cached entries from local storage and remote edge tiers."""
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM lookup_cache")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Error clearing SQLite cache: {e}")
        self._memory_cache.clear()

        turso_url, turso_token, cf_url, cf_token = self._get_edge_credentials()
        if turso_url and turso_token:
            try:
                endpoint = f"{turso_url.rstrip('/')}/v2/pipeline"
                headers = {
                    "Authorization": f"Bearer {turso_token}",
                    "Content-Type": "application/json",
                }
                body = json.dumps({
                    "requests": [
                        {"type": "execute", "stmt": {"sql": "DELETE FROM lookup_cache"}},
                        {"type": "close"}
                    ]
                }).encode("utf-8")
                req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                    pass
            except Exception as e:
                logger.warning(f"Turso clear notice: {e}")

        if cf_url:
            try:
                endpoint = f"{cf_url.rstrip('/')}/api/v1/cache"
                headers = {"User-Agent": "MidgleyCacheGateway/1.0"}
                if cf_token:
                    headers["Authorization"] = f"Bearer {cf_token}"
                req = urllib.request.Request(endpoint, headers=headers, method="DELETE")
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                    pass
            except urllib.error.HTTPError as e:
                if e.code == 405:
                    # If Worker does not support DELETE method yet, overwrite in-memory state
                    logger.debug("Cloudflare Worker DELETE method not configured.")
                else:
                    logger.warning(f"Cloudflare clear notice: {e}")
            except Exception as e:
                logger.warning(f"Cloudflare clear notice: {e}")

    def purge_expired(self):
        """Purges expired items from cache."""
        now = time.time()
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM lookup_cache WHERE expires_at <= ?", (now,))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Error purging expired SQLite cache: {e}")

        expired_keys = [k for k, v in self._memory_cache.items() if now >= v["expires_at"]]
        for k in expired_keys:
            del self._memory_cache[k]

    def get_stats(self) -> dict:
        """Returns statistics on cache activity and tier configuration."""
        turso_url, turso_token, cf_url, cf_token = self._get_edge_credentials()
        return {
            "stats": self.stats,
            "in_memory_keys": len(self._memory_cache),
            "use_local_sqlite": self._use_sqlite,
            "db_path": self.db_path,
            "turso_configured": bool(turso_url and turso_token),
            "cloudflare_configured": bool(cf_url),
        }


# Global singleton cache instance
global_cache = LookupCache()


def clear_lookup_cache():
    """Clears the global lookup cache instance."""
    global_cache.clear()


if __name__ == "__main__":
    if "--stats" in sys.argv:
        stats = global_cache.get_stats()
        print("==================================================")
        print("   MIDGLEY MULTI-TIER LOOKUP CACHE GATEWAY STATS  ")
        print("==================================================")
        print(json.dumps(stats, indent=2))
        sys.exit(0)
