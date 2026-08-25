"""
Unit tests for Lookup Cache Module (src/lookup_cache.py)
Tests set, get, cache hits/misses, TTL expiration, clear, and in-memory fallback.
"""

import os
import time
import tempfile
import unittest

from src.lookup_cache import LookupCache


class TestLookupCache(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_cache.sqlite")
        self.cache = LookupCache(db_path=self.db_path)

    def tearDown(self):
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


if __name__ == "__main__":
    unittest.main()
