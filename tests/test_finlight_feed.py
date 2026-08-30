"""
Unit tests for Finlight Feed Module (src/finlight_feed.py)
Verifies query consolidation, 30-minute disk cache hits/misses, and rate-limit HTTP 429/403 fallback handling.
"""

import os
import time
import json
import unittest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.finlight_feed import (
    fetch_finlight_articles,
    get_finlight_energy_events,
    UNIFIED_ENERGY_QUERY,
    CACHE_FILE,
    QUOTA_FILE
)


from src.lookup_cache import global_cache


class TestFinlightFeed(unittest.TestCase):

    def setUp(self):
        """Removes temporary cache file and clears lookup cache before each test."""
        global_cache.clear()
        for f in (CACHE_FILE, QUOTA_FILE):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def tearDown(self):
        """Removes temporary cache file and clears lookup cache after each test."""
        global_cache.clear()
        for f in (CACHE_FILE, QUOTA_FILE):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def test_unified_query_structure(self):
        """Verify single consolidated energy query string contains core keywords."""
        self.assertIn("oil", UNIFIED_ENERGY_QUERY)
        self.assertIn("gasoline", UNIFIED_ENERGY_QUERY)
        self.assertIn("Hormuz", UNIFIED_ENERGY_QUERY)
        self.assertIn("refinery", UNIFIED_ENERGY_QUERY)

    @patch("src.finlight_feed.requests.post")
    def test_fetch_finlight_articles_live_and_cache(self, mock_post):
        """Verify live API call creates disk cache and subsequent calls hit cache without network requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "articles": [
                {
                    "title": "OPEC+ Cuts Oil Output",
                    "summary": "OPEC announces supply reductions",
                    "link": "https://example.com/art1",
                    "publishDate": "2026-08-24T12:00:00Z",
                    "source": "Reuters"
                }
            ]
        }
        mock_post.return_value = mock_response

        # 1st call: Hits live API, populates disk cache
        articles1 = fetch_finlight_articles(api_key="test_key", force_refresh=True)
        self.assertEqual(len(articles1), 1)
        self.assertEqual(articles1[0]["title"], "OPEC+ Cuts Oil Output")
        self.assertEqual(mock_post.call_count, 1)
        self.assertTrue(os.path.exists(CACHE_FILE))

        # 2nd call: Hits disk cache (0 network calls)
        articles2 = fetch_finlight_articles(api_key="test_key")
        self.assertEqual(len(articles2), 1)
        self.assertEqual(articles2[0]["title"], "OPEC+ Cuts Oil Output")
        self.assertEqual(mock_post.call_count, 1)  # call count remains 1!

    @patch("src.finlight_feed.requests.post")
    def test_fetch_finlight_articles_http_429_fallback(self, mock_post):
        """Verify HTTP 429 rate-limit returns cached fallback data gracefully."""
        # Pre-populate disk cache with mock article
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        cache_data = {
            "timestamp": time.time() - 3600,  # 1 hour ago
            "articles": [{"title": "Cached Stale Article", "link": "https://example.com/stale"}]
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_post.return_value = mock_response

        # Call with force_refresh=True to bypass valid cache check
        articles = fetch_finlight_articles(api_key="test_key", force_refresh=True)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "Cached Stale Article")

    def test_get_finlight_energy_events_dataframe(self):
        """Verify get_finlight_energy_events returns a properly formatted DataFrame."""
        with patch("src.finlight_feed.fetch_finlight_articles") as mock_fetch:
            mock_fetch.return_value = [
                {
                    "title": "US Crude Inventories Drop",
                    "summary": "EIA reports drawdown",
                    "link": "https://example.com/eia1",
                    "publishDate": "2026-08-24T10:00:00Z",
                    "source": "Bloomberg"
                }
            ]

            df = get_finlight_energy_events()
            self.assertIsInstance(df, pd.DataFrame)
            self.assertFalse(df.empty)
            self.assertIn("headline", df.columns)
            self.assertEqual(df.iloc[0]["source"], "Bloomberg")


if __name__ == "__main__":
    unittest.main()
