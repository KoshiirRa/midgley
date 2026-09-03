"""
Unit tests for Alpha Vantage Energy & Petroleum Data Feed Connector (Issue #130).
Tests secondary market failover, Signal 1 (XLE equity), Signal 2 (RSI/VWAP technicals),
daily quota safety valve (25 calls/day), and market-hours-aware caching.
"""

import os
import json
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.data_ingestion import (
    AlphaVantageDataConnector,
    ALPHA_VANTAGE_QUOTA_FILE,
    ALPHA_VANTAGE_CACHE_FILE,
    ALPHA_VANTAGE_MAX_DAILY_CALLS
)


class TestAlphaVantageIngestion(unittest.TestCase):

    def setUp(self):
        # Create temporary directory for isolated quota and cache files
        self.test_dir = tempfile.TemporaryDirectory()
        self.quota_path = os.path.join(self.test_dir.name, "alpha_vantage_quota.json")
        self.cache_path = os.path.join(self.test_dir.name, "alpha_vantage_cache.json")

        self.quota_patcher = patch("src.data_ingestion.ALPHA_VANTAGE_QUOTA_FILE", self.quota_path)
        self.cache_patcher = patch("src.data_ingestion.ALPHA_VANTAGE_CACHE_FILE", self.cache_path)
        self.quota_patcher.start()
        self.cache_patcher.start()

    def tearDown(self):
        self.quota_patcher.stop()
        self.cache_patcher.stop()
        self.test_dir.cleanup()

    def test_connector_initialization(self):
        """Verify connector initialization with default/custom settings."""
        connector = AlphaVantageDataConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)
        self.assertEqual(connector.max_daily_calls, 25)

    def test_quota_safety_valve(self):
        """Verify 25 calls/day hard cap enforcement and safety valve trip."""
        connector = AlphaVantageDataConnector()
        day_key = datetime.now().strftime("%Y-%m-%d")

        # Pre-fill quota to 25 calls
        os.makedirs(self.test_dir.name, exist_ok=True)
        with open(self.quota_path, "w", encoding="utf-8") as f:
            json.dump({"daily_calls": {day_key: 25}}, f)

        status = connector.get_quota_status()
        self.assertEqual(status["today_calls"], 25)
        self.assertEqual(status["remaining_calls"], 0)
        self.assertTrue(status["safety_valve_active"])

        allowed, info = connector._check_and_increment_quota()
        self.assertFalse(allowed)
        self.assertTrue(info["safety_valve_active"])

    def test_trading_hours_gating_and_off_hours_caching(self):
        """Verify that outside market hours, cached entries are reused without burning quota."""
        connector = AlphaVantageDataConnector()
        day_str = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"equity_XLE_{day_str}"

        # Pre-seed cache
        os.makedirs(self.test_dir.name, exist_ok=True)
        sample_payload = {
            "symbol": "XLE",
            "close_price": 89.50,
            "daily_change_pct": 0.45,
            "status": "SUCCESS"
        }
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump({cache_key: sample_payload}, f)

        # Mock off-hours (is_trading_hours -> False) and bypass global_cache to test local file fixture
        with patch.object(connector, "is_trading_hours", return_value=False), \
             patch("src.lookup_cache.global_cache.get", return_value=None):
            res = connector.fetch_energy_equity_series("XLE")
            self.assertEqual(res["symbol"], "XLE")
            self.assertEqual(res["close_price"], 89.50)
            self.assertTrue(res.get("cached_off_hours", False))

            # Verify no quota was consumed
            quota_status = connector.get_quota_status()
            self.assertEqual(quota_status["today_calls"], 0)

    def test_signal_1_energy_equity_xle(self):
        """Verify Signal 1 (XLE ETF price & return ingestion)."""
        connector = AlphaVantageDataConnector()
        res = connector.fetch_energy_equity_series("XLE")

        self.assertEqual(res["symbol"], "XLE")
        self.assertIn("close_price", res)
        self.assertGreater(res["close_price"], 0.0)
        self.assertIn("daily_change_pct", res)
        self.assertTrue(res["is_free_alternative"])
        self.assertEqual(res["cost_per_query"], 0.0)

    def test_signal_2_technical_indicators(self):
        """Verify Signal 2 (Technical indicators RSI & VWAP)."""
        connector = AlphaVantageDataConnector()
        res_rsi = connector.fetch_technical_indicator("XLE", "RSI", 14)

        self.assertEqual(res_rsi["symbol"], "XLE")
        self.assertEqual(res_rsi["indicator"], "RSI")
        self.assertEqual(res_rsi["time_period"], 14)
        self.assertIn("value", res_rsi)
        self.assertIn("interpretation", res_rsi)
        self.assertTrue(res_rsi["is_free_alternative"])

    def test_commodity_series_failover(self):
        """Verify zero-cost secondary commodity market failover (WTI crude)."""
        connector = AlphaVantageDataConnector()
        res_wti = connector.fetch_commodity_series("WTI")

        self.assertEqual(res_wti["symbol"], "WTI")
        self.assertGreater(res_wti["value"], 0.0)
        self.assertTrue(res_wti["is_free_alternative"])

    def test_market_failover_feed_aggregation(self):
        """Verify full market failover & dual-signal feed aggregation."""
        connector = AlphaVantageDataConnector()
        res_feed = connector.fetch_market_failover_feed()

        self.assertEqual(res_feed["status"], "SUCCESS")
        self.assertIn("WTI", res_feed["commodities"])
        self.assertIn("BRENT", res_feed["commodities"])
        self.assertIn("signal_1_energy_equity", res_feed["signals"])
        self.assertIn("signal_2_technical_rsi", res_feed["signals"])
        self.assertIn("quota_status", res_feed)
        self.assertEqual(res_feed["quota_status"]["max_daily_calls"], 25)

    def test_offline_fallback(self):
        """Verify non-null benchmark responses when API is offline or quota exhausted."""
        connector = AlphaVantageDataConnector(api_key="DEMO_OFFLINE_KEY")

        # Mock urllib error
        with patch("urllib.request.urlopen", side_effect=Exception("Network Offline")):
            res = connector.fetch_commodity_series("BRENT")
            self.assertEqual(res["symbol"], "BRENT")
            self.assertGreater(res["value"], 0.0)
            self.assertEqual(res["status"], "FALLBACK")


if __name__ == "__main__":
    unittest.main()
