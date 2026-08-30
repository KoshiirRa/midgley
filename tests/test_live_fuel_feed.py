"""
Unit tests for Live Fuel Price API Feed Module (src/live_fuel_feed.py)
Verifies multi-locale GasBuddy GraphQL queries, AAA web scraper fallbacks, prediction_history.csv lookup, and static anchor fallbacks.
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

from src.live_fuel_feed import (
    fetch_gasbuddy_prices_by_zip,
    fetch_aaa_metro_price,
    fetch_history_last_known_price,
    fetch_live_metro_retail_price,
    fetch_live_metro_retail_prices,
    REGION_METADATA
)
from src.lookup_cache import global_cache


class TestLiveFuelFeed(unittest.TestCase):

    def test_region_metadata_keys(self):
        """Verify all expected regions are present in REGION_METADATA with required attributes."""
        expected_regions = ["National", "Tulsa_OK", "Newark_DE", "Cincinnati_OH", "Cincinnati_KY", "Oakland_CA", "BayArea_CA"]
        for reg in expected_regions:
            self.assertIn(reg, REGION_METADATA)
            self.assertIn("zip", REGION_METADATA[reg])
            self.assertIn("state", REGION_METADATA[reg])
            self.assertIn("static_anchor", REGION_METADATA[reg])

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_fetch_gasbuddy_prices_by_zip_success(self, mock_urlopen):
        """Verify GasBuddy GraphQL response parsing calculates average regular gas price."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_data = {
            "data": {
                "locationBySearchTerm": {
                    "stations": {
                        "results": [
                            {
                                "id": "1",
                                "name": "QuikTrip #1",
                                "prices": [
                                    {"fuelProduct": "regular", "credit": {"price": 3.85}}
                                ]
                            },
                            {
                                "id": "2",
                                "name": "Casey's #2",
                                "prices": [
                                    {"fuelProduct": "regular", "credit": {"price": 3.95}}
                                ]
                            }
                        ]
                    }
                }
            }
        }
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = fetch_gasbuddy_prices_by_zip("74103")
        self.assertIsNotNone(res)
        self.assertEqual(res["average_price"], 3.90)
        self.assertEqual(len(res["stations"]), 2)
        self.assertIn("GasBuddy GraphQL", res["source"])

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_fetch_aaa_metro_price_success(self, mock_urlopen):
        """Verify AAA web scraper html regex parsing extracts valid price."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_html = "<html><body><h3>Tulsa Metro</h3><table><tr><td>Current Avg.</td><td>$3.890</td></tr></table></body></html>"
        mock_response.read.return_value = mock_html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = fetch_aaa_metro_price("Tulsa_OK")
        self.assertIsNotNone(res)
        self.assertEqual(res["average_price"], 3.89)
        self.assertIn("AAA Web Scraper", res["source"])

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_fetch_aaa_metro_price_no_match_returns_none(self, mock_urlopen):
        """Verify AAA web scraper returns None when header banner National Average is present but no metro table match exists."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_html = "<html><body><header>National Average: $4.099</header></body></html>"
        mock_response.read.return_value = mock_html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = fetch_aaa_metro_price("Oakland_CA")
        self.assertIsNone(res)

    @patch("pandas.read_csv")
    @patch("os.path.exists")
    def test_fetch_history_last_known_price(self, mock_exists, mock_read_csv):
        """Verify prediction_history.csv lookup extracts latest logged price for region."""
        mock_exists.return_value = True
        import pandas as pd
        mock_df = pd.DataFrame([
            {"region": "Tulsa_OK", "current_base_price": 3.85},
            {"region": "Oakland_CA", "current_base_price": 5.62}
        ])
        mock_read_csv.return_value = mock_df

        res = fetch_history_last_known_price("Oakland_CA")
        self.assertIsNotNone(res)
        self.assertEqual(res["average_price"], 5.62)
        self.assertEqual(res["source"], "prediction_history.csv History")

    @patch("src.live_fuel_feed.fetch_history_last_known_price")
    @patch("src.live_fuel_feed.fetch_eia_or_yfinance_price")
    @patch("src.live_fuel_feed.fetch_aaa_metro_price")
    @patch("src.live_fuel_feed.fetch_gasbuddy_prices_by_zip")
    def test_fetch_live_metro_retail_price_fallback_chain(self, mock_gb, mock_aaa, mock_eia, mock_hist):
        """Verify full fallback chain execution: GasBuddy -> AAA -> EIA -> History -> Static Anchor."""
        global_cache.clear()
        # 1. When GasBuddy succeeds, return GasBuddy
        mock_gb.return_value = {"average_price": 3.99, "source": "GasBuddy GraphQL (Zip 74103)"}
        res1 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res1["price"], 3.99)
        self.assertIn("GasBuddy", res1["source"])

        # 2. When GasBuddy fails but AAA succeeds, return AAA
        global_cache.clear()
        mock_gb.return_value = None
        mock_aaa.return_value = {"average_price": 3.95, "source": "AAA Web Scraper (OK)"}
        res2 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res2["price"], 3.95)
        self.assertIn("AAA", res2["source"])

        # 3. When GasBuddy & AAA fail but EIA succeeds, return EIA
        global_cache.clear()
        mock_aaa.return_value = None
        mock_eia.return_value = {"average_price": 3.92, "source": "EIA/yfinance RBOB Benchmark"}
        res3 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res3["price"], 3.92)
        self.assertIn("EIA", res3["source"])

        # 4. When network feeds fail, fallback to history
        global_cache.clear()
        mock_eia.return_value = None
        mock_hist.return_value = {"average_price": 3.88, "source": "prediction_history.csv History"}
        res4 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res4["price"], 3.88)
        self.assertIn("prediction_history.csv", res4["source"])

        # 5. When all fail, fallback to static anchor constant ($3.890 for Tulsa)
        global_cache.clear()
        mock_hist.return_value = None
        res5 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res5["price"], 3.890)
        self.assertIn("Static Anchor", res5["source"])

    def test_fetch_live_metro_retail_prices_all_regions(self):
        """Verify fetch_live_metro_retail_prices returns non-empty dict for all regions."""
        prices = fetch_live_metro_retail_prices()
        self.assertIsInstance(prices, dict)
        self.assertEqual(len(prices), len(REGION_METADATA))
        for reg in REGION_METADATA:
            self.assertIn(reg, prices)
            self.assertIsInstance(prices[reg], float)
            self.assertGreater(prices[reg], 0.0)


if __name__ == "__main__":
    unittest.main()
