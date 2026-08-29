"""
Unit tests for Zero-Cost Energy Feeds & Universal 50-State Open Data Connector (Issue #141).
Tests FRED, EIA v2, Universal 50-State Open Data Portals, USDA Biofuels, and Open-Meteo connectors.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.state_open_data import UniversalStateOpenDataConnector, STATE_METADATA
from src.data_ingestion import FREDDataConnector, EIADataConnector, USDABiofuelConnector
from src.noaa_weather import OpenMeteoDegreeDaysConnector


class TestZeroCostEnergyFeeds(unittest.TestCase):

    def test_universal_state_open_data_50_states_count(self):
        """Verify UniversalStateOpenDataConnector covers all 50 US States + DC (51 total)."""
        connector = UniversalStateOpenDataConnector()
        self.assertEqual(connector.supported_states_count, 51)
        matrix = connector.get_all_states_tax_matrix()
        self.assertEqual(matrix["states_count"], 51)
        self.assertTrue(matrix["is_free_alternative"])
        self.assertEqual(matrix["cost_per_query"], 0.0)

    def test_universal_state_open_data_resolution(self):
        """Verify dynamic state name, postal code, and FIPS code resolution across various states."""
        connector = UniversalStateOpenDataConnector()
        
        # Postal code lookup
        ca_res = connector.get_state_fuel_tax("CA")
        self.assertEqual(ca_res["state_name"], "California")
        self.assertEqual(ca_res["excise_tax_per_gal"], 0.634)
        self.assertTrue(ca_res["is_free_alternative"])

        # State name lookup
        tx_res = connector.get_state_fuel_tax("Texas")
        self.assertEqual(tx_res["state_code"], "TX")
        self.assertEqual(tx_res["excise_tax_per_gal"], 0.200)

        # FIPS code lookup
        ny_res = connector.get_state_fuel_tax("36")
        self.assertEqual(ny_res["state_code"], "NY")

        # Midwest / Ohio River state lookup
        oh_res = connector.get_state_fuel_tax("OH")
        self.assertEqual(oh_res["excise_tax_per_gal"], 0.385)
        
        ky_res = connector.get_state_fuel_tax("KY")
        self.assertEqual(ky_res["excise_tax_per_gal"], 0.260)

    def test_fred_data_connector(self):
        """Verify FREDDataConnector structure and series fetch."""
        connector = FREDDataConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)
        
        res = connector.fetch_series("GASREGW")
        self.assertEqual(res["series_id"], "GASREGW")
        self.assertGreater(res["value"], 0.0)
        self.assertTrue(res["is_free_alternative"])

    def test_eia_data_connector(self):
        """Verify EIADataConnector refinery utilization & stock inventory schema."""
        connector = EIADataConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)

        res = connector.fetch_padd_inventory_and_refinery_data()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("PADD2_Midwest", res["refinery_utilization"])
        self.assertIn("PADD5", res["gasoline_stocks_million_bbl"])

    def test_usda_biofuel_connector(self):
        """Verify USDABiofuelConnector ethanol blendstock and RIN credit calculations."""
        connector = USDABiofuelConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)

        res = connector.fetch_ethanol_blendstock_costs()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreater(res["e100_ethanol_rack_price_per_gal"], 0.0)
        self.assertGreater(res["rin_d6_credit_value_per_gal"], 0.0)

    def test_open_meteo_degree_days_connector(self):
        """Verify OpenMeteoDegreeDaysConnector HDD/CDD calculations for refining hubs."""
        connector = OpenMeteoDegreeDaysConnector()
        self.assertTrue(connector.is_free_alternative)
        self.assertEqual(connector.cost_per_query, 0.0)

        res = connector.fetch_hub_degree_days("Tulsa_OK")
        self.assertEqual(res["hub_code"], "Tulsa_OK")
        self.assertIn("heating_degree_days_hdd", res)
        self.assertIn("cooling_degree_days_cdd", res)

        all_res = connector.fetch_all_hubs_degree_days()
        self.assertEqual(all_res["status"], "SUCCESS")
        self.assertEqual(len(all_res["hubs"]), 6)


if __name__ == "__main__":
    unittest.main()
