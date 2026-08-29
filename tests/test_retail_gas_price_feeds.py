"""
Unit tests for Multi-Source Retail Gas Price Feeds (src/data_ingestion.py, src/state_open_data.py & src/live_fuel_feed.py).
Tests EIA State/Metro Survey, State Energy Agency Surveys (CEC/NYSERDA/IDALS), Google Places API, and PyPI Scrapers.
Excludes CollectAPI due to low 100 call/month quota limits.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.data_ingestion import EIAStateMetroRetailConnector
from src.state_open_data import StateEnergyAgencySurveysConnector
from src.live_fuel_feed import fetch_google_maps_fuel_prices, PyPICommunityFuelScraper


class TestRetailGasPriceFeeds(unittest.TestCase):

    def test_eia_state_metro_retail_connector(self):
        """Verify EIAStateMetroRetailConnector returns valid state and metro retail gas prices."""
        connector = EIAStateMetroRetailConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)

        # State retail price query
        ca_res = connector.fetch_state_retail_price("CA")
        self.assertEqual(ca_res["state_code"], "CA")
        self.assertEqual(ca_res["price"], 5.184)
        self.assertTrue(ca_res["is_free_alternative"])

        # Metro retail price query
        sf_res = connector.fetch_metro_retail_price("SanFrancisco")
        self.assertEqual(sf_res["metro_name"], "SanFrancisco")
        self.assertEqual(sf_res["price"], 5.450)

    def test_state_energy_agency_surveys_connector(self):
        """Verify StateEnergyAgencySurveysConnector returns direct CEC, NYSERDA, and IDALS survey breakdowns."""
        connector = StateEnergyAgencySurveysConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)

        # CEC California Survey
        cec_res = connector.fetch_cec_california_fuel_survey()
        self.assertEqual(cec_res["state"], "CA")
        self.assertEqual(cec_res["price_breakdown"]["state_excise_tax"], 0.634)

        # NYSERDA New York Survey
        nyserda_res = connector.fetch_nyserda_new_york_fuel_survey()
        self.assertEqual(nyserda_res["state"], "NY")
        self.assertEqual(nyserda_res["regions"]["NYC_Metropolitan"], 3.550)

        # IDALS Midwest Biofuel Survey
        idals_res = connector.fetch_midwest_biofuel_retail_survey()
        self.assertEqual(idals_res["e10_unleaded_avg"], 3.120)

    def test_pypi_community_fuel_scraper(self):
        """Verify PyPICommunityFuelScraper fallback pricing connector."""
        scraper = PyPICommunityFuelScraper()
        self.assertTrue(scraper.is_free_alternative)
        self.assertEqual(scraper.cost_per_query, 0.0)

        res = scraper.fetch_community_price("Tulsa_OK")
        self.assertEqual(res["region"], "Tulsa_OK")
        self.assertEqual(res["price"], 3.890)

    @patch("src.live_fuel_feed.urllib.request.urlopen")
    def test_google_places_fuel_prices_parsing(self, mock_urlopen):
        """Verify Google Places API station fuelOptions JSON parsing."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_json = {
            "places": [
                {
                    "displayName": {"text": "QuikTrip #1"},
                    "fuelOptions": {
                        "fuelPrices": [
                            {"type": "REGULAR", "price": {"units": "3", "nanos": 890000000}}
                        ]
                    }
                }
            ]
        }
        import json
        mock_response.read.return_value = json.dumps(mock_json).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = fetch_google_maps_fuel_prices(api_key="TEST_MOCK_KEY")
        self.assertIsNotNone(res)
        self.assertEqual(res["average_price"], 3.89)
        self.assertEqual(res["source"], "Google Places API")


if __name__ == "__main__":
    unittest.main()
