import unittest
import os
import tempfile
from src.data_ingestion import NOAACOOPSConnector


class TestNOAACOOPSConnector(unittest.TestCase):
    def setUp(self):
        self.connector = NOAACOOPSConnector()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_vintage_file = os.path.join(self.temp_dir.name, "noaa_coops_vintages.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_zero_cost_metadata(self):
        self.assertTrue(self.connector.is_free_alternative)
        self.assertEqual(self.connector.cost_per_query, 0.0)

    def test_fetch_coastal_marine_telemetry_schema(self):
        data = self.connector.fetch_coastal_marine_telemetry()
        self.assertIn("stations", data)
        self.assertIn("marine_terminal_surge_risk", data)
        self.assertIn("marine_terminal_shallow_draft_risk", data)
        self.assertEqual(data["status"], "SUCCESS")

        stations = data["stations"]
        self.assertIn("Houston_TX", stations)
        self.assertIn("Delaware_River_DE", stations)
        self.assertIn("BayArea_CA", stations)
        self.assertIn("Port_St_Lucie_FL", stations)

        for name, st in stations.items():
            self.assertIn("station_id", st)
            self.assertIn("surge_residual_ft", st)
            self.assertIn("surge_risk", st)
            self.assertIn("shallow_draft_risk", st)

    def test_bitemporal_vintage_persistence(self):
        test_record = {
            "source": "NOAA CO-OPS Test",
            "as_of": "2026-08-20 12:00:00",
            "valid_date": "2026-08-20",
            "stations": {
                "Houston_TX": {"station_id": "8770613", "surge_residual_ft": 2.5, "surge_risk": 0.40, "shallow_draft_risk": 0.0}
            },
            "marine_terminal_surge_risk": 0.40,
            "marine_terminal_shallow_draft_risk": 0.0
        }
        self.connector.save_noaa_coops_vintage_record(test_record, filepath=self.temp_vintage_file)

        vintages = self.connector.get_noaa_coops_vintages_as_of("2026-08-21", filepath=self.temp_vintage_file)
        self.assertEqual(len(vintages), 1)
        self.assertEqual(vintages[0]["marine_terminal_surge_risk"], 0.40)

        early_vintages = self.connector.get_noaa_coops_vintages_as_of("2026-08-19", filepath=self.temp_vintage_file)
        self.assertEqual(len(early_vintages), 0)


if __name__ == "__main__":
    unittest.main()
