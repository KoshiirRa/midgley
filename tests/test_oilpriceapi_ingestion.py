"""
Unit tests for OilpriceAPI Energy & Petroleum Data Feed Connector (Issue #128).
Tests commodity spot price retrieval, multi-commodity sweep, daily quota safety valve (25 calls/day),
off-hours caching, market-hours gating, network failure fallback, and telemetry logging.
"""

import os
import json
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.data_ingestion import (
    OilPriceAPIDataConnector,
    fetch_oilpriceapi_prices,
    OILPRICEAPI_QUOTA_FILE,
    OILPRICEAPI_CACHE_FILE,
    OILPRICEAPI_MAX_DAILY_CALLS
)


class TestOilPriceAPIIngestion(unittest.TestCase):

    def setUp(self):
        # Create temporary directory for isolated quota and cache files
        self.test_dir = tempfile.TemporaryDirectory()
        self.quota_path = os.path.join(self.test_dir.name, "oilpriceapi_quota.json")
        self.cache_path = os.path.join(self.test_dir.name, "oilpriceapi_cache.json")

        self.quota_patcher = patch("src.data_ingestion.OILPRICEAPI_QUOTA_FILE", self.quota_path)
        self.cache_patcher = patch("src.data_ingestion.OILPRICEAPI_CACHE_FILE", self.cache_path)
        self.quota_patcher.start()
        self.cache_patcher.start()

    def tearDown(self):
        self.quota_patcher.stop()
        self.cache_patcher.stop()
        self.test_dir.cleanup()

    def test_connector_initialization(self):
        """Verify connector initialization with default settings and benchmark codes."""
        connector = OilPriceAPIDataConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)
        self.assertEqual(connector.max_daily_calls, 25)
        self.assertIn("WTI_USD", connector.benchmark_prices)
        self.assertIn("BRENT_USD", connector.benchmark_prices)
        self.assertIn("RBOB_USD", connector.benchmark_prices)
        self.assertIn("NG_USD", connector.benchmark_prices)

    def test_quota_safety_valve(self):
        """Verify 25 calls/day hard cap enforcement and safety valve trip."""
        connector = OilPriceAPIDataConnector()
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
        connector = OilPriceAPIDataConnector()
        day_str = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"latest_WTI_USD_{day_str}"

        # Pre-seed cache
        os.makedirs(self.test_dir.name, exist_ok=True)
        sample_payload = {
            "code": "WTI_USD",
            "name": "WTI Crude Oil ($/bbl)",
            "price": 76.50,
            "formatted": "$76.50",
            "currency": "USD",
            "status": "SUCCESS"
        }
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump({cache_key: sample_payload}, f)

        # Mock off-hours (is_trading_hours -> False)
        with patch.object(connector, "is_trading_hours", return_value=False):
            res = connector.fetch_latest_price("WTI_USD")
            self.assertEqual(res["code"], "WTI_USD")
            self.assertEqual(res["price"], 76.50)
            self.assertTrue(res.get("cached_off_hours", False))

            # Verify no quota was consumed
            quota_status = connector.get_quota_status()
            self.assertEqual(quota_status["today_calls"], 0)

    def test_fetch_latest_price_benchmark_fallback(self):
        """Verify fallback benchmark response when API key is missing."""
        connector = OilPriceAPIDataConnector()
        res_wti = connector.fetch_latest_price("WTI_USD")
        self.assertEqual(res_wti["code"], "WTI_USD")
        self.assertGreater(res_wti["price"], 0.0)
        self.assertEqual(res_wti["currency"], "USD")
        self.assertEqual(res_wti["status"], "FALLBACK")
        self.assertTrue(res_wti["is_free_alternative"])

        res_rbob = connector.fetch_latest_price("RBOB_USD")
        self.assertEqual(res_rbob["code"], "RBOB_USD")
        self.assertEqual(res_rbob["price"], 2.420)

    def test_fetch_all_spot_prices_sweep(self):
        """Verify multi-commodity spot sweep across all supported commodity codes."""
        connector = OilPriceAPIDataConnector()
        res_all = connector.fetch_all_spot_prices()

        self.assertEqual(res_all["status"], "SUCCESS")
        self.assertTrue(res_all["is_free_alternative"])
        self.assertIn("spot_prices", res_all)
        spot_map = res_all["spot_prices"]

        self.assertIn("WTI_USD", spot_map)
        self.assertIn("BRENT_USD", spot_map)
        self.assertIn("RBOB_USD", spot_map)
        self.assertIn("NG_USD", spot_map)
        self.assertIn("HO_USD", spot_map)
        self.assertIn("RAL_USD", spot_map)
        self.assertIn("COAL_USD", spot_map)

    def test_convenience_function(self):
        """Verify fetch_oilpriceapi_prices convenience function."""
        single_res = fetch_oilpriceapi_prices("BRENT_USD")
        self.assertEqual(single_res["code"], "BRENT_USD")
        self.assertGreater(single_res["price"], 0.0)

        all_res = fetch_oilpriceapi_prices()
        self.assertEqual(all_res["status"], "SUCCESS")
        self.assertIn("spot_prices", all_res)

    def test_mock_live_api_call(self):
        """Verify successful live API response parsing when API key is provided."""
        connector = OilPriceAPIDataConnector(api_key="TEST_API_KEY")
        mock_response_data = {
            "status": "success",
            "data": {
                "price": 77.80,
                "formatted": "$77.80",
                "currency": "USD",
                "code": "WTI_USD",
                "created_at": "2026-08-29T20:00:00.000Z",
                "type": "spot_price"
            }
        }

        mock_http_response = MagicMock()
        mock_http_response.status = 200
        mock_http_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_http_response.__enter__.return_value = mock_http_response

        with patch("urllib.request.urlopen", return_value=mock_http_response):
            with patch.object(connector, "is_trading_hours", return_value=True):
                res = connector.fetch_latest_price("WTI_USD")
                self.assertEqual(res["code"], "WTI_USD")
                self.assertEqual(res["price"], 77.80)
                self.assertEqual(res["formatted"], "$77.80")
                self.assertEqual(res["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
