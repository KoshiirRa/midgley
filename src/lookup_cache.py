"""
Lookup Cache Module (src/lookup_cache.py)
Provides SQLite-backed response caching with configurable TTL (default 15 minutes)
and fallback to in-memory dictionary storage.
"""

import os
import json
import sqlite3
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DB = os.path.join("data", "lookup_cache.sqlite")
DEFAULT_TTL_SECONDS = 900  # 15 minutes


class LookupCache:
    """
    Thread-safe SQLite/in-memory cache for API responses and feed queries.
    """

    def __init__(self, db_path: str = DEFAULT_CACHE_DB):
        self.db_path = db_path
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._use_sqlite = True
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database schema if possible, else falls back to in-memory."""
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
            logger.info(f"Initialized SQLite lookup cache at: {self.db_path}")
        except Exception as e:
            logger.warning(f"Could not initialize SQLite database at {self.db_path}: {e}. Falling back to in-memory cache.")
            self._use_sqlite = False

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a cached value if present and unexpired.
        Returns None if cache miss or expired.
        """
        now = time.time()
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
                            val_dict = json.loads(val_str)
                            val_dict["_cache_hit"] = True
                            val_dict["_cache_age_seconds"] = round(now - created_at, 1)
                            return val_dict
                        else:
                            # Expired, clean up
                            cursor.execute("DELETE FROM lookup_cache WHERE key = ?", (key,))
                            conn.commit()
            except Exception as e:
                logger.warning(f"Error reading SQLite cache for key '{key}': {e}")

        # In-memory fallback / check
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if now < entry["expires_at"]:
                val_dict = dict(entry["value"])
                val_dict["_cache_hit"] = True
                val_dict["_cache_age_seconds"] = round(now - entry["created_at"], 1)
                return val_dict
            else:
                del self._memory_cache[key]

        return None

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Stores a dictionary value in the cache with specified TTL in seconds.
        """
        now = time.time()
        expires_at = now + ttl_seconds
        # Remove private metadata keys before caching if present
        clean_val = {k: v for k, v in value.items() if not k.startswith("_")}
        val_str = json.dumps(clean_val)

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
                logger.warning(f"Error setting SQLite cache for key '{key}': {e}")

        # Always keep in-memory sync for resilience
        self._memory_cache[key] = {
            "value": clean_val,
            "created_at": now,
            "expires_at": expires_at
        }

    def clear(self):
        """Clears all cached entries."""
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM lookup_cache")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Error clearing SQLite cache: {e}")
        self._memory_cache.clear()

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


# Global singleton cache instance
global_cache = LookupCache()
