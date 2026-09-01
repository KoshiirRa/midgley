"""
Unit tests for Lookup Cache Module (src/lookup_cache.py)
Tests set, get, cache hits/misses, TTL expiration, clear, 3-tier fallbacks, and quota ledger sync.
"""

import os
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.lookup_cache import LookupCache


class TestLookupCache(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_cache.sqlite")
        self.edge_patcher = patch.object(LookupCache, "_get_edge_credentials", return_value=(None, None, None, None))
        self.edge_patcher.start()
        self.cache = LookupCache(db_path=self.db_path)

    def tearDown(self):
        self.edge_patcher.stop()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_set_and_get_hit(self):
        data = {"price": 3.89, "source": "GasBuddy"}
        self.cache.set("test_key", data, ttl_seconds=60)
        
        cached = self.cache.get("test_key")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["price"], 3.89)
        self.assertEqual(cached["source"], "GasBuddy")
        self.assertTrue(cached.get("_cache_hit"))
        self.assertEqual(cached.get("_cache_tier"), "in-memory")
        self.assertGreaterEqual(cached.get("_cache_age_seconds"), 0.0)

    def test_get_miss(self):
        cached = self.cache.get("non_existent_key")
        self.assertIsNone(cached)

    def test_ttl_expiration(self):
        data = {"price": 4.95, "source": "AAA"}
        # Set short TTL
        self.cache.set("expire_key", data, ttl_seconds=1)
        
        # Verify hit immediately
        self.assertIsNotNone(self.cache.get("expire_key"))
        
        # Sleep to allow expiration
        time.sleep(1.2)
        
        # Verify miss after expiration
        self.assertIsNone(self.cache.get("expire_key"))

    def test_clear(self):
        self.cache.set("k1", {"val": 1})
        self.cache.set("k2", {"val": 2})
        self.assertIsNotNone(self.cache.get("k1"))
        self.assertIsNotNone(self.cache.get("k2"))
        
        self.cache.clear()
        self.assertIsNone(self.cache.get("k1"))
        self.assertIsNone(self.cache.get("k2"))

    def test_quota_ledger_sync(self):
        res = self.cache.update_quota_ledger("finlight", monthly_calls=12, today_calls=4, month_key="2026-08", day_key="2026-08-29")
        self.assertEqual(res["monthly_calls"], 12)
        
        fetched = self.cache.get_quota_ledger("finlight")
        self.assertEqual(fetched["monthly_calls"], 12)
        self.assertEqual(fetched["daily_calls"]["2026-08-29"], 4)

    def test_get_stats(self):
        stats = self.cache.get_stats()
        self.assertIn("stats", stats)
        self.assertIn("in_memory_keys", stats)
        self.assertIn("turso_configured", stats)

    def test_cloudflare_get_404_cache_miss(self):
        from urllib.error import HTTPError
        with patch("urllib.request.urlopen", side_effect=HTTPError("http://cf/cache", 404, "Not Found", {}, None)):
            res = self.cache._cloudflare_get("missing_key", "https://cf.example.com")
            self.assertIsNone(res)
            self.assertEqual(self.cache.stats["errors"], 0)


if __name__ == "__main__":
    unittest.main()

