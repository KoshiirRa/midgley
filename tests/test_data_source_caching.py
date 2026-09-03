"""
Unit tests for Data Source Caching Integration (Issue #108 / src/lookup_cache.py).
Verifies FRED, EIA, USDA, AlphaVantage, and Socrata State Open Data connectors query & populate global_cache.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from src.lookup_cache import global_cache
from src.data_ingestion import (
    FREDDataConnector,
    EIADataConnector,
    USDABiofuelConnector,
    EIAStateMetroRetailConnector,
    AlphaVantageDataConnector,
)
from src.state_open_data import UniversalStateOpenDataConnector


class TestDataSourceCaching(unittest.TestCase):

    def setUp(self):
        global_cache.clear()

    def tearDown(self):
        global_cache.clear()

    def test_fred_connector_caching(self):
        connector = FREDDataConnector()
        res = connector.fetch_series("GASREGW")
        self.assertIsNotNone(res)
        
        # Verify stored in global_cache under fred_GASREGW key
        cached = global_cache.get("fred_GASREGW")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.get("series_id"), "GASREGW")
        self.assertTrue(cached.get("_cache_hit"))

    def test_eia_padd_connector_caching(self):
        connector = EIADataConnector()
        res = connector.fetch_padd_inventory_and_refinery_data()
        self.assertIsNotNone(res)
        
        cached = global_cache.get("eia_padd_refinery_inventory")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.get("status"), "SUCCESS")
        self.assertTrue(cached.get("_cache_hit"))

    def test_usda_biofuel_connector_caching(self):
        connector = USDABiofuelConnector()
        res = connector.fetch_ethanol_blendstock_costs()
        self.assertIsNotNone(res)

        cached = global_cache.get("usda_ethanol_blendstock")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.get("status"), "SUCCESS")
        self.assertTrue(cached.get("_cache_hit"))

    def test_eia_state_metro_connector_caching(self):
        connector = EIAStateMetroRetailConnector()
        res_state = connector.fetch_state_retail_price("CA")
        res_metro = connector.fetch_metro_retail_price("SanFrancisco")

        cached_state = global_cache.get("eia_state_retail_CA")
        cached_metro = global_cache.get("eia_metro_retail_SanFrancisco")

        self.assertIsNotNone(cached_state)
        self.assertEqual(cached_state.get("state_code"), "CA")
        self.assertIsNotNone(cached_metro)
        self.assertEqual(cached_metro.get("metro_name"), "SanFrancisco")

    def test_alpha_vantage_connector_caching(self):
        connector = AlphaVantageDataConnector(api_key="TEST_KEY")
        test_payload = {"symbol": "WTI", "price": 75.50}
        connector._save_cache_response("test_commodity", test_payload)

        cached = global_cache.get("alphavant_test_commodity")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.get("symbol"), "WTI")

        cached_res = connector._get_cached_response("test_commodity")
        self.assertIsNotNone(cached_res)
        self.assertEqual(cached_res.get("symbol"), "WTI")

    def test_socrata_state_open_data_caching(self):
        connector = UniversalStateOpenDataConnector()
        res = connector.get_state_fuel_tax("OK")
        self.assertIsNotNone(res)

        cached = global_cache.get("socrata_fuel_tax_OK")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.get("state_code"), "OK")
        self.assertTrue(cached.get("_cache_hit"))


if __name__ == "__main__":
    unittest.main()
