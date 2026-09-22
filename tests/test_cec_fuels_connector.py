import unittest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from src.data_ingestion import CECWeeklyFuelsConnector


class TestCECWeeklyFuelsConnector(unittest.TestCase):
    def setUp(self):
        self.connector = CECWeeklyFuelsConnector()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_vintage_file = os.path.join(self.temp_dir.name, "cec_fuels_vintages.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_zero_cost_metadata(self):
        self.assertTrue(self.connector.is_free_alternative)
        self.assertEqual(self.connector.cost_per_query, 0.0)

    def test_fetch_weekly_fuels_data_schema(self):
        data = self.connector.fetch_weekly_fuels_data()
        self.assertIn("metrics", data)
        self.assertIn("as_of", data)
        self.assertIn("publication_day", data)
        self.assertEqual(data["publication_day"], "Thursday")
        self.assertEqual(data["status"], "SUCCESS")

        metrics = data["metrics"]
        self.assertIn("ca_carbob_stocks_thousand_barrels", metrics)
        self.assertIn("norcal_refinery_utilization_pct", metrics)
        self.assertIn("socal_refinery_utilization_pct", metrics)
        self.assertIn("statewide_refinery_utilization_pct", metrics)
        self.assertGreater(metrics["ca_carbob_stocks_thousand_barrels"], 0.0)

    def test_bitemporal_vintage_persistence(self):
        test_record = {
            "source": "CEC Fuels Watch Test",
            "as_of": "2026-06-11 14:00:00",
            "valid_date": "2026-06-11",
            "publication_day": "Thursday",
            "metrics": {
                "ca_carbob_stocks_thousand_barrels": 5900.0,
                "statewide_refinery_utilization_pct": 88.5
            }
        }
        self.connector.save_cec_fuels_vintage_record(test_record, filepath=self.temp_vintage_file)

        vintages = self.connector.get_cec_fuels_vintages_as_of("2026-06-12", filepath=self.temp_vintage_file)
        self.assertEqual(len(vintages), 1)
        self.assertEqual(vintages[0]["metrics"]["ca_carbob_stocks_thousand_barrels"], 5900.0)

        # Lookahead filtering test
        early_vintages = self.connector.get_cec_fuels_vintages_as_of("2026-06-10", filepath=self.temp_vintage_file)
        self.assertEqual(len(early_vintages), 0)


if __name__ == "__main__":
    unittest.main()
