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
    fetch_aaa_csv_prices,
    fetch_aaa_cloudflare_browser_run,
    fetch_aaa_cloudrun_scraper,
    fetch_live_out_of_metro_price,
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

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_fetch_aaa_metro_price_state_average_fallback(self, mock_urlopen):
        """Verify AAA scraper falls back to state average table when no dedicated metro accordion exists."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_html = "<html><body><div class='tblwrap'><table><tr><td>Current Avg.</td><td>$3.970</td></tr></table></div></body></html>"
        mock_response.read.return_value = mock_html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = fetch_aaa_metro_price("Greenville_NC")
        self.assertIsNotNone(res)
        self.assertEqual(res["average_price"], 3.970)
        self.assertIn("State Average", res["source"])

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
    @patch("src.live_fuel_feed.fetch_gasbuddy_prices_by_zip")
    @patch("src.live_fuel_feed.fetch_aaa_cloudflare_browser_run")
    @patch("src.live_fuel_feed.fetch_aaa_csv_prices")
    def test_fetch_live_metro_retail_price_fallback_chain(self, mock_csv, mock_cf, mock_gb, mock_eia, mock_hist):
        """Verify full fallback chain execution: AAA CSV -> Cloudflare Browser Run -> GasBuddy -> EIA -> History -> Static Anchor."""
        global_cache.clear()
        # 1. When AAA CSV succeeds, return AAA CSV
        mock_csv.return_value = {"average_price": 3.96, "source": "AAA Metro Daily CSV (Tulsa, OK)"}
        res1 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res1["price"], 3.96)
        self.assertIn("AAA Metro Daily CSV", res1["source"])

        # 2. When AAA CSV fails but Cloudflare Browser Run succeeds, return Cloudflare Browser Run
        global_cache.clear()
        mock_csv.return_value = None
        mock_cf.return_value = {"average_price": 3.95, "source": "AAA Cloudflare Browser Run (Tulsa_OK)"}
        res2 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res2["price"], 3.95)
        self.assertIn("Cloudflare Browser Run", res2["source"])

        # 3. When AAA CSV & Cloudflare Browser Run fail but GasBuddy succeeds, return GasBuddy
        global_cache.clear()
        mock_cf.return_value = None
        mock_gb.return_value = {"average_price": 3.99, "source": "GasBuddy GraphQL (Zip 74103)"}
        res3 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res3["price"], 3.99)
        self.assertIn("GasBuddy", res3["source"])

        # 4. When GasBuddy fails but EIA succeeds, return EIA
        global_cache.clear()
        mock_gb.return_value = None
        mock_eia.return_value = {"average_price": 3.92, "source": "EIA/yfinance RBOB Benchmark"}
        res4 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res4["price"], 3.92)
        self.assertIn("EIA", res4["source"])

        # 5. When network feeds fail, fallback to history
        global_cache.clear()
        mock_eia.return_value = None
        mock_hist.return_value = {"average_price": 3.88, "source": "prediction_history.csv History"}
        res5 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res5["price"], 3.88)
        self.assertIn("prediction_history.csv", res5["source"])

        # 6. When all fail, fallback to static anchor constant ($3.820 for Tulsa)
        global_cache.clear()
        mock_hist.return_value = None
        res6 = fetch_live_metro_retail_price("Tulsa_OK", use_cache=False)
        self.assertEqual(res6["price"], 3.820)
        self.assertIn("Static Anchor", res6["source"])

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_fetch_aaa_csv_prices_metro_and_state(self, mock_urlopen):
        """Verify fetch_aaa_csv_prices parses lykmapipo metro and state CSVs with multi-grade prices."""
        global_cache.clear()
        mock_metro_csv = (
            "State-Name,State-Abbreviation,Metro-Name,Regular,Mid-Grade,Premium,Diesel,Currency,Unit,Date\n"
            "Oklahoma,OK,Tulsa,3.859,4.159,4.459,4.859,U.S Dollar,US Gallon,2026-10-18\n"
            "California,CA,Oakland,5.850,6.150,6.450,6.750,U.S Dollar,US Gallon,2026-10-18\n"
        )
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = mock_metro_csv.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Test Tulsa Metro lookup
        res_tulsa = fetch_aaa_csv_prices("Tulsa_OK")
        self.assertIsNotNone(res_tulsa)
        self.assertEqual(res_tulsa["average_price"], 3.859)
        self.assertEqual(res_tulsa["grades"]["regular"], 3.859)
        self.assertEqual(res_tulsa["grades"]["diesel"], 4.859)
        self.assertEqual(res_tulsa["granularity"], "METRO")
        self.assertIn("Tulsa", res_tulsa["source"])

        # Test State lookup with state CSV
        global_cache.clear()
        mock_state_csv = (
            "State-Name,State-Abbreviation,Regular,Mid-Grade,Premium,Diesel,Currency,Unit,Date\n"
            "Oklahoma,OK,3.820,4.120,4.420,4.720,U.S Dollar,US Gallon,2026-10-18\n"
            "California,CA,5.750,6.050,6.350,6.650,U.S Dollar,US Gallon,2026-10-18\n"
        )
        mock_response.read.return_value = mock_state_csv.encode("utf-8")
        res_state = fetch_aaa_csv_prices("OK", is_state=True)
        self.assertIsNotNone(res_state)
        self.assertEqual(res_state["average_price"], 3.820)
        self.assertEqual(res_state["granularity"], "STATE")
        self.assertEqual(res_state["grades"]["regular"], 3.820)

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_fetch_aaa_cloudflare_browser_run(self, mock_urlopen):
        """Verify fetch_aaa_cloudflare_browser_run supports Worker endpoints, direct Cloudflare Browser Rendering REST API, and local fallback."""
        # 1. When CLOUDFLARE_BROWSER_RUN_URL is set (Edge Worker Endpoint)
        with patch.dict(os.environ, {"CLOUDFLARE_BROWSER_RUN_URL": "https://midgley-monitor.workers.dev", "CLOUDFLARE_AUTH_TOKEN": "test-cf-token"}):
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({
                "average_price": 3.945,
                "grades": {"regular": 3.945, "midgrade": 4.295, "premium": 4.645, "diesel": 4.945},
                "source": "Tulsa_OK"
            }).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            res = fetch_aaa_cloudflare_browser_run("Tulsa_OK")
            self.assertIsNotNone(res)
            self.assertEqual(res["average_price"], 3.945)
            self.assertIn("Cloudflare Browser Run", res["source"])

        # 2. When CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are set (Direct REST API)
        with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "cf-acc-123", "CLOUDFLARE_API_TOKEN": "cf-api-token"}, clear=True):
            mock_cf_html = "<html><body><h3>Tulsa Metro</h3><table><tr><td>Current Avg.</td><td>$3.885</td></tr></table></body></html>"
            mock_resp2 = MagicMock()
            mock_resp2.status = 200
            mock_resp2.read.return_value = json.dumps({"result": mock_cf_html}).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp2

            res2 = fetch_aaa_cloudflare_browser_run("Tulsa_OK")
            self.assertIsNotNone(res2)
            self.assertEqual(res2["average_price"], 3.885)
            self.assertIn("Cloudflare Browser Run", res2["source"])

        # 3. Backward compatibility alias fetch_aaa_cloudrun_scraper
        res_alias = fetch_aaa_cloudrun_scraper("Tulsa_OK")
        self.assertEqual(res_alias["average_price"], res2["average_price"])

        # 4. When unconfigured, falls back to in-process parser
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.live_fuel_feed.fetch_aaa_metro_price") as mock_local:
                mock_local.return_value = {"average_price": 3.91, "source": "Local AAA"}
                res_local = fetch_aaa_cloudflare_browser_run("Tulsa_OK")
                self.assertEqual(res_local["average_price"], 3.91)

    @patch("src.live_fuel_feed.fetch_aaa_cloudflare_browser_run")
    @patch("src.live_fuel_feed.fetch_aaa_csv_prices")
    @patch("src.live_fuel_feed.fetch_gasbuddy_prices_by_zip")
    def test_fetch_live_out_of_metro_price(self, mock_gb, mock_csv, mock_cf):
        """Verify out-of-metro ZIP routing: GasBuddy station precision primary -> AAA State CSV -> Cloudflare Browser Run."""
        # 1. GasBuddy returns station observations for rural ZIP
        mock_gb.return_value = {
            "average_price": 3.84,
            "stations": [{"station": "Rural Sinclair #4", "regular_price": 3.84}],
            "source": "GasBuddy GraphQL (Zip 74015)"
        }
        res_gb = fetch_live_out_of_metro_price("74015", state_code="OK")
        self.assertIsNotNone(res_gb)
        self.assertEqual(res_gb["price"], 3.84)
        self.assertEqual(res_gb["granularity"], "STATION")
        self.assertIn("GasBuddy", res_gb["source"])

        # 2. GasBuddy returns empty / 0 stations -> falls back to AAA State Daily CSV
        mock_gb.return_value = None
        mock_csv.return_value = {
            "average_price": 3.79,
            "grades": {"regular": 3.79, "midgrade": 4.14, "premium": 4.49, "diesel": 4.89},
            "source": "AAA State Daily CSV (OK)",
            "granularity": "STATE"
        }
        res_fallback = fetch_live_out_of_metro_price("74015", state_code="OK")
        self.assertIsNotNone(res_fallback)
        self.assertEqual(res_fallback["price"], 3.79)
        self.assertEqual(res_fallback["granularity"], "STATE")
        self.assertIn("AAA State Daily CSV", res_fallback["source"])

        # 3. GasBuddy and CSV fail -> falls back to Cloudflare Browser Run
        mock_csv.return_value = None
        mock_cf.return_value = {
            "average_price": 3.81,
            "source": "AAA Cloudflare Browser Run (OK)",
            "granularity": "STATE"
        }
        res_cf = fetch_live_out_of_metro_price("74015", state_code="OK")
        self.assertIsNotNone(res_cf)
        self.assertEqual(res_cf["price"], 3.81)
        self.assertIn("Cloudflare Browser Run", res_cf["source"])

    def test_is_price_outlier_detection(self):
        """Verify is_price_outlier correctly identifies physical bounds and anomalies."""
        from src.live_fuel_feed import is_price_outlier
        # Valid Newark retail gas price ($4.354/gal) is within normal physical bounds
        self.assertFalse(is_price_outlier("Newark_DE", 4.354))
        # Valid lower and upper US prices
        self.assertFalse(is_price_outlier("Newark_DE", 3.377))
        # Extreme impossible low / high prices for non-CA are rejected
        self.assertTrue(is_price_outlier("Newark_DE", 0.95))
        self.assertTrue(is_price_outlier("Newark_DE", 12.50))
        # Oakland_CA $5.827 is valid for CA
        self.assertFalse(is_price_outlier("Oakland_CA", 5.827))
        # $2.00 is an extreme low outlier for Oakland (CA bound is >= 3.50)
        self.assertTrue(is_price_outlier("Oakland_CA", 2.00))
        self.assertTrue(is_price_outlier("Oakland_CA", 10.50))

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
