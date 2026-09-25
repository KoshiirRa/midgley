"""
Unit & Integration Tests for Zero-Cost EPA Weekly RIN Data Connector (Issue #365).
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import json

from src.data_ingestion import EPARINDataConnector, USDABiofuelConnector


class TestEPARINDataConnector(unittest.TestCase):
    def setUp(self):
        self.connector = EPARINDataConnector()

    def test_fetch_rin_market_data_baseline(self):
        """Verifies default EPA EMTS RIN prices and RVO cost calculation."""
        with patch.dict(os.environ, {"TESTING": "1"}):
            res = self.connector.fetch_rin_market_data()
            self.assertIn(res["status"], ["SUCCESS", "FALLBACK_SYNTHETIC"])
            self.assertIn("rin_prices", res)
            self.assertIn("rin_weekly_volume", res)
            self.assertIn("calculated_rvo_cost_per_gal", res)

            prices = res["rin_prices"]
            self.assertIn("d6_ethanol_per_rin", prices)
            self.assertIn("d4_biodiesel_per_rin", prices)
            self.assertIn("d3_cellulosic_per_rin", prices)
            self.assertGreater(prices["d6_ethanol_per_rin"], 0.10)
            self.assertGreater(prices["d4_biodiesel_per_rin"], 0.20)
            self.assertGreater(prices["d3_cellulosic_per_rin"], 0.50)

            # Check positive RVO obligation cost
            rvo = res["calculated_rvo_cost_per_gal"]
            self.assertGreater(rvo, 0.01)

    def test_usda_biofuel_dynamic_rin_integration(self):
        """Verifies USDABiofuelConnector dynamically incorporates EPA RIN D6 credit."""
        with patch.dict(os.environ, {"TESTING": "1"}):
            usda_conn = USDABiofuelConnector()
            res = usda_conn.fetch_ethanol_blendstock_costs()
            self.assertIn(res["status"], ["SUCCESS", "OBSERVED", "ESTIMATED", "FALLBACK"])
            self.assertIn("rin_d6_credit_value_per_gal", res)
            self.assertIn("calculated_e10_blendstock_offset_per_gal", res)
            self.assertGreater(res["rin_d6_credit_value_per_gal"], 0.0)

    def test_bitemporal_vintage_persistence(self):
        """Verifies EPA RIN bitemporal observation persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_vintage = os.path.join(tmpdir, "epa_rin_vintages.json")

            rec1 = {
                "source": "EPA RIN Test",
                "as_of": "2026-09-01 10:00:00",
                "valid_date": "2026-09-01",
                "rin_prices": {"d6_ethanol_per_rin": 0.50}
            }
            rec2 = {
                "source": "EPA RIN Test",
                "as_of": "2026-09-15 10:00:00",
                "valid_date": "2026-09-15",
                "rin_prices": {"d6_ethanol_per_rin": 0.65}
            }

            EPARINDataConnector.save_epa_rin_vintage_record(rec1, filepath=temp_vintage)
            EPARINDataConnector.save_epa_rin_vintage_record(rec2, filepath=temp_vintage)

            # Query as of Sep 10 -> 1 record
            v_early = EPARINDataConnector.get_epa_rin_vintages_as_of("2026-09-10", filepath=temp_vintage)
            self.assertEqual(len(v_early), 1)
            self.assertEqual(v_early[0]["rin_prices"]["d6_ethanol_per_rin"], 0.50)

            # Query as of Sep 20 -> 2 records
            v_all = EPARINDataConnector.get_epa_rin_vintages_as_of("2026-09-20", filepath=temp_vintage)
            self.assertEqual(len(v_all), 2)


if __name__ == "__main__":
    unittest.main()
