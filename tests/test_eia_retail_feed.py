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
    FRED_TO_EIA_V2_SERIES,
    FALLBACK_RETAIL_PRICES,
    validate_eia_ground_truth_coverage
)


class TestEIARetailFeed(unittest.TestCase):

    def setUp(self):
        os.environ["TESTING"] = "1"
        self.feed = EIARetailFeed()

    def test_region_series_mapping_coverage(self):
        """Verify all supported metro regions are mapped to EIA/FRED series."""
        required_regions = [
            "National", "Tulsa_OK", "Newark_DE", "Cincinnati_OH", "Cincinnati_KY", "Chicago_IL",
            "Houston_TX", "Los_Angeles_CA", "Greenville_NC", "Charlotte_NC", "Port_St_Lucie_FL", "Oakland_CA", "BayArea_CA"
        ]
        for reg in required_regions:
            self.assertIn(reg, REGION_TO_EIA_SERIES)
            self.assertGreater(len(REGION_TO_EIA_SERIES[reg]), 0)

    def test_no_cross_geography_national_fallbacks(self):
        """Assert no regional metro falls back to national GASREGW or GASDESW (Issue #608)."""
        national_keys = {"National", "National_ULSD", "National_Diesel"}
        for region, series_list in REGION_TO_EIA_SERIES.items():
            if region not in national_keys:
                for sid, desc in series_list:
                    self.assertNotIn(
                        sid, {"GASREGW", "GASDESW"},
                        f"Regional metro {region} must not use national fallback {sid} ({desc})"
                    )

        # Specifically verify regional series bindings
        self.assertEqual(REGION_TO_EIA_SERIES["Tulsa_OK"][0][0], "GASREGWMW")
        self.assertEqual(REGION_TO_EIA_SERIES["Newark_DE"][0][0], "GASREGW01B")
        self.assertEqual(REGION_TO_EIA_SERIES["Cincinnati_KY"][0][0], "GASREGWMW")
        self.assertEqual(REGION_TO_EIA_SERIES["Chicago_IL"][0][0], "GASREGWCHI")
        self.assertEqual(REGION_TO_EIA_SERIES["Houston_TX"][0][0], "GASREGWHO")
        self.assertEqual(REGION_TO_EIA_SERIES["Los_Angeles_CA"][0][0], "GASREGWLA")
        self.assertEqual(REGION_TO_EIA_SERIES["Greenville_NC"][0][0], "GASREGW01C")
        self.assertEqual(REGION_TO_EIA_SERIES["Charlotte_NC"][0][0], "GASREGW01C")

    def test_validate_eia_ground_truth_coverage(self):
        """Verify that ground truth coverage validation succeeds without exceptions."""
        self.assertTrue(validate_eia_ground_truth_coverage(self.feed))

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
        # Inject known dates into feed's cache for Tulsa's regional benchmark series
        self.feed._series_cache["GASREGWMW"] = {
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

    def test_diesel_series_mapping_and_aliases(self):
        """Verify all regional diesel keys map cleanly to EIA diesel series (Issue #478)."""
        diesel_keys = [
            "National_ULSD", "National_Diesel",
            "Tulsa_ULSD", "Tulsa_Diesel",
            "Newark_ULSD", "Newark_Diesel",
            "Cincinnati_ULSD", "Cincinnati_Diesel",
            "Greenville_ULSD", "Greenville_Diesel",
            "Charlotte_ULSD", "Charlotte_Diesel",
            "Oakland_ULSD", "Oakland_Diesel", "Oakland_CARB_Diesel",
            "Port_St_Lucie_ULSD", "Port_St_Lucie_Diesel"
        ]
        for key in diesel_keys:
            self.assertIn(key, REGION_TO_EIA_SERIES, f"Missing mapping for diesel key: {key}")
            series_tuples = REGION_TO_EIA_SERIES[key]
            self.assertTrue(any("GASDES" in s[0] for s in series_tuples), f"Expected GASDES series in {key}")

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

    def test_eia_dnav_leafhandler_parsing_fallback(self):
        """Verify zero-API-key EIA DNAV LeafHandler HTML parsing and alias resolution."""
        sample_dnav_html = b"""
        <table><tbody>
        <tr><td class='B6'>&nbsp;&nbsp;2026-Oct</td><td class='B5'>10/19&nbsp;</td><td class='B3'>4.145&nbsp;&nbsp;&nbsp;</td><td class='B5'>10/26&nbsp;</td><td class='B3'>4.269&nbsp;&nbsp;&nbsp;</td></tr>
        <tr><td class='B6'>&nbsp;&nbsp;2026-Nov</td><td class='B5'>11/02&nbsp;</td><td class='B3'>4.102&nbsp;&nbsp;&nbsp;</td></tr>
        </tbody></table>
        """
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = sample_dnav_html
        mock_resp.__enter__.return_value = mock_resp

        feed = EIARetailFeed()
        with patch.dict(os.environ, {"TESTING": "1", "TEST_EIA_FORCE": "1", "EIA_API_KEY": ""}), \
             patch("src.lookup_cache.global_cache.get", return_value=None), \
             patch("src.lookup_cache.global_cache.set"), \
             patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
            history = feed.fetch_series_history("GASREGWCHI")
            self.assertEqual(history.get("2026-10-19"), 4.145)
            self.assertEqual(history.get("2026-10-26"), 4.269)
            self.assertEqual(history.get("2026-11-02"), 4.102)
            called_req = mock_url.call_args[0][0]
            # Verify Chicago Y03CH alias resolved to YORD on EIA DNAV
            self.assertIn("EMM_EPMR_PTE_YORD_DPG", called_req.full_url)



if __name__ == "__main__":
    unittest.main()

