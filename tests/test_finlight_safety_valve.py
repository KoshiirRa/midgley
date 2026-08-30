"""
Unit & Integration Tests for Finlight API Quota Safety Valve (tests/test_finlight_safety_valve.py)
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

from src.finlight_feed import (
    _check_and_increment_quota,
    get_finlight_quota_status,
    fetch_finlight_articles,
    MAX_MONTHLY_CALLS,
    MAX_DAILY_CALLS,
    QUOTA_FILE
)


from src.lookup_cache import global_cache


class TestFinlightSafetyValve(unittest.TestCase):
    def setUp(self):
        global_cache.clear()
        if os.path.exists(QUOTA_FILE):
            try:
                os.remove(QUOTA_FILE)
            except Exception:
                pass

    def tearDown(self):
        global_cache.clear()
        if os.path.exists(QUOTA_FILE):
            try:
                os.remove(QUOTA_FILE)
            except Exception:
                pass

    @patch("src.lookup_cache.global_cache.get_quota_ledger", return_value=None)
    def test_quota_ledger_increment(self, mock_edge):
        allowed, status = _check_and_increment_quota()
        self.assertTrue(allowed)
        self.assertEqual(status["monthly_calls"], 1)

        status_info = get_finlight_quota_status()
        self.assertEqual(status_info["monthly_calls"], 1)
        self.assertFalse(status_info["safety_valve_active"])

    def test_safety_valve_tripped_at_max_daily(self):
        # Simulate reaching MAX_DAILY_CALLS
        os.makedirs("data", exist_ok=True)
        from datetime import datetime
        now = datetime.now()
        day_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")

        quota_data = {
            "current_month": month_key,
            "monthly_calls": 10,
            "daily_calls": {day_key: MAX_DAILY_CALLS}
        }
        with open(QUOTA_FILE, "w", encoding="utf-8") as f:
            json.dump(quota_data, f)

        allowed, status = _check_and_increment_quota()
        self.assertFalse(allowed)

        status_info = get_finlight_quota_status()
        self.assertTrue(status_info["safety_valve_active"])

    @patch("src.finlight_feed.requests.post")
    def test_fetch_finlight_articles_intercepted_when_safety_valve_active(self, mock_post):
        # Set quota data to max monthly
        os.makedirs("data", exist_ok=True)
        from datetime import datetime
        month_key = datetime.now().strftime("%Y-%m")

        quota_data = {
            "current_month": month_key,
            "monthly_calls": MAX_MONTHLY_CALLS,
            "daily_calls": {}
        }
        with open(QUOTA_FILE, "w", encoding="utf-8") as f:
            json.dump(quota_data, f)

        with patch.dict("os.environ", {"FINLIGHT_API_KEY": "test_key"}):
            articles = fetch_finlight_articles(force_refresh=True)
            # mock_post should NEVER be called when safety valve is active
            mock_post.assert_not_called()
            self.assertIsInstance(articles, list)


if __name__ == "__main__":
    unittest.main()
