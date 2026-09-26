"""
Tests for EIA Weekly Retail Gasoline Price Feed Connector (tests/test_eia_retail_feed.py)
Issue #403: EIA weekly retail prices by PADD/state as evaluation ground truth.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from src.eia_retail_feed import (
    EIARetailFeed,
    REGION_TO_EIA_SERIES,
    FALLBACK_RETAIL_PRICES
)


class TestEIARetailFeed(unittest.TestCase):

    def setUp(self):
        os.environ["TESTING"] = "1"
        self.feed = EIARetailFeed()

    def test_region_series_mapping_coverage(self):
        """Verify all supported metro regions are mapped to EIA/FRED series."""
        required_regions = [
            "National", "Tulsa_OK", "Newark_DE", "Cincinnati_OH", "Cincinnati_KY",
            "Greenville_NC", "Charlotte_NC", "Port_St_Lucie_FL", "Oakland_CA", "BayArea_CA"
        ]
        for reg in required_regions:
            self.assertIn(reg, REGION_TO_EIA_SERIES)
            self.assertGreater(len(REGION_TO_EIA_SERIES[reg]), 0)

    def test_fetch_series_history_mock(self):
        """Verify mock series history generation in testing mode."""
        history = self.feed.fetch_series_history("GASREGW")
        self.assertIsInstance(history, dict)
        self.assertGreater(len(history), 0)
        # Check that values are plausible pump prices ($/gal)
        for d, p in history.items():
            self.assertGreater(p, 1.50)
            self.assertLess(p, 8.00)

    def test_get_retail_price_for_date_exact_and_window(self):
        """Verify get_retail_price_for_date returns accurate price."""
        # Inject known dates into feed's cache
        self.feed._series_cache["GASREGWOK"] = {
            "2026-09-01": 2.95,
            "2026-09-08": 2.98,
            "2026-09-15": 3.02
        }
        # Exact date match
        price = self.feed.get_retail_price_for_date("Tulsa_OK", "2026-09-08")
        self.assertEqual(price, 2.98)

        # Mid-week interpolation / closest lookahead-safe date (2026-09-10 -> 2026-09-08)
        price_midweek = self.feed.get_retail_price_for_date("Tulsa_OK", "2026-09-10")
        self.assertEqual(price_midweek, 2.98)

    def test_fetch_all_retail_series(self):
        """Verify fetch_all_retail_series constructs complete snapshot payload."""
        snapshot = self.feed.fetch_all_retail_series()
        self.assertEqual(snapshot["status"], "SUCCESS")
        self.assertIn("regional_retail_prices", snapshot)
        prices = snapshot["regional_retail_prices"]
        self.assertIn("National", prices)
        self.assertIn("Oakland_CA", prices)
        self.assertIn("Tulsa_OK", prices)
        self.assertGreater(prices["Oakland_CA"], prices["Tulsa_OK"])

    def test_vintage_persistence(self):
        """Verify snapshot saving and loading."""
        test_rec = {
            "source": "Test",
            "timestamp": "2026-09-22 00:00:00",
            "regional_retail_prices": {"National": 3.45}
        }
        test_path = "data/test_eia_retail_vintages_tmp.json"
        try:
            with patch.dict(os.environ, {"TESTING": "0"}):
                self.feed.save_eia_retail_vintage_record(test_rec, filepath=test_path)
                loaded = self.feed.load_eia_retail_vintages(filepath=test_path)
                self.assertGreaterEqual(len(loaded), 1)
                self.assertEqual(loaded[-1]["regional_retail_prices"]["National"], 3.45)
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)


if __name__ == "__main__":
    unittest.main()
