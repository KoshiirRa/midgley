"""
Unit tests for Zero-Cost Daily US Fuel Pump Prices Scraper (src/data_ingestion.py & src/live_fuel_feed.py).
Fulfills Issue #134 acceptance criteria by validating non-null zero-cost daily fuel price retrieval.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.data_ingestion import fetch_daily_us_fuel_pump_prices, DailyUSFuelPumpPricesScraper
from src.live_fuel_feed import fetch_aaa_fuel_prices_all_grades


class TestZeroCostFuelScraper(unittest.TestCase):

    def test_daily_us_fuel_pump_prices_scraper_class(self):
        """Verify DailyUSFuelPumpPricesScraper class connector instantiation and properties."""
        scraper = DailyUSFuelPumpPricesScraper()
        self.assertTrue(scraper.is_free_alternative)
        self.assertEqual(scraper.cost_per_query, 0.0)

    @patch("src.live_fuel_feed.fetch_aaa_fuel_prices_all_grades")
    @patch("src.live_fuel_feed.fetch_live_metro_retail_prices")
    def test_fetch_daily_us_fuel_pump_prices_full_sweep(self, mock_metro, mock_aaa):
        """Verify full multi-region zero-cost sweep returns expected schema."""
        mock_metro.return_value = {
            "Tulsa_OK": 3.890,
            "Newark_DE": 3.350,
            "Oakland_CA": 5.550
        }
        mock_aaa.return_value = {
            "region": "National",
            "source": "AAA Web Scraper (US)",
            "is_free_alternative": True,
            "cost_per_query": 0.0,
            "average_price": 3.184,
            "grades": {"regular": 3.184, "midgrade": 3.584, "premium": 3.984, "diesel": 3.784}
        }

        res = fetch_daily_us_fuel_pump_prices()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["is_free_alternative"])
        self.assertEqual(res["cost_per_query"], 0.0)
        self.assertIn("national_benchmark", res)
        self.assertIn("regional_metros", res)
        self.assertEqual(res["regional_metros"]["Tulsa_OK"], 3.890)

    @patch("src.live_fuel_feed.fetch_aaa_fuel_prices_all_grades")
    def test_fetch_daily_us_fuel_pump_prices_single_region(self, mock_aaa):
        """Verify single region query routes to fetch_aaa_fuel_prices_all_grades."""
        mock_aaa.return_value = {
            "region": "Tulsa_OK",
            "source": "AAA Web Scraper (OK)",
            "is_free_alternative": True,
            "cost_per_query": 0.0,
            "average_price": 3.890,
            "grades": {"regular": 3.890, "midgrade": 4.240, "premium": 4.590, "diesel": 4.390}
        }

        scraper = DailyUSFuelPumpPricesScraper()
        res = scraper.get_prices("Tulsa_OK")
        self.assertEqual(res["region"], "Tulsa_OK")
        self.assertTrue(res["is_free_alternative"])
        self.assertEqual(res["cost_per_query"], 0.0)
        self.assertIn("regular", res["grades"])
        self.assertEqual(res["grades"]["regular"], 3.890)

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_fetch_aaa_fuel_prices_all_grades_html_parsing(self, mock_urlopen):
        """Verify multi-grade HTML parsing extracts Regular, Midgrade, Premium, Diesel prices."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_html = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>Current Avg.</td>
                        <td>$3.184</td>
                        <td>$3.584</td>
                        <td>$3.984</td>
                        <td>$3.784</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        mock_response.read.return_value = mock_html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = fetch_aaa_fuel_prices_all_grades("National")
        self.assertIsNotNone(res)
        self.assertTrue(res["is_free_alternative"])
        self.assertEqual(res["cost_per_query"], 0.0)
        self.assertEqual(res["grades"]["regular"], 3.184)
        self.assertEqual(res["grades"]["midgrade"], 3.584)
        self.assertEqual(res["grades"]["premium"], 3.984)
        self.assertEqual(res["grades"]["diesel"], 3.784)


if __name__ == "__main__":
    unittest.main()
