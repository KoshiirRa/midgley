"""
Unit Tests for NASA POWER Data Ingestion & Climatology Feature Extraction (Issues #420 & #370)
"""

import os
import tempfile
import json
import unittest
from unittest.mock import patch, MagicMock

from src.nasa_power import (
    celsius_to_fahrenheit,
    calculate_hdd,
    calculate_cdd,
    calculate_gdd,
    NASAPowerClient,
    DISTILLATE_TERMINAL_HUBS,
    BIOFUEL_CORN_HUBS
)


class TestNASAPowerModule(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = os.path.join(self.temp_dir.name, "nasa_power_cache.json")
        self.client = NASAPowerClient(cache_file=self.cache_file)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_temperature_conversion(self):
        self.assertAlmostEqual(celsius_to_fahrenheit(0.0), 32.0, places=2)
        self.assertAlmostEqual(celsius_to_fahrenheit(100.0), 212.0, places=2)
        self.assertAlmostEqual(celsius_to_fahrenheit(20.0), 68.0, places=2)
        self.assertAlmostEqual(celsius_to_fahrenheit(-10.0), 14.0, places=2)

    def test_hdd_and_cdd_calculations(self):
        # Cold day (40 F): HDD = 25, CDD = 0
        self.assertEqual(calculate_hdd(40.0), 25.0)
        self.assertEqual(calculate_cdd(40.0), 0.0)

        # Mild day (65 F): HDD = 0, CDD = 0
        self.assertEqual(calculate_hdd(65.0), 0.0)
        self.assertEqual(calculate_cdd(65.0), 0.0)

        # Hot day (85 F): HDD = 0, CDD = 20
        self.assertEqual(calculate_hdd(85.0), 0.0)
        self.assertEqual(calculate_cdd(85.0), 20.0)

    def test_gdd_calculation(self):
        # T_max = 80 F, T_min = 60 F -> T_mean = 70 F -> GDD = 20
        self.assertEqual(calculate_gdd(t_max_f=80.0, t_min_f=60.0), 20.0)

        # Capped T_max (95 F -> capped to 86), Floor T_min (45 F -> floored to 50)
        # T_adj = (86 + 50) / 2 = 68 -> GDD = 18
        self.assertEqual(calculate_gdd(t_max_f=95.0, t_min_f=45.0), 18.0)

        # Cold day (45 F max, 30 F min) -> (50 + 50) / 2 = 50 -> GDD = 0
        self.assertEqual(calculate_gdd(t_max_f=45.0, t_min_f=30.0), 0.0)

    def test_fetch_point_daily_mock_testing_mode(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            data = self.client.fetch_point_daily(
                lat=40.7357,
                lon=-74.1724,
                start_date="20260915",
                end_date="20260920",
                parameters=["T2M", "T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]
            )
            self.assertIn("T2M", data)
            self.assertIn("T2M_MAX", data)
            self.assertIn("T2M_MIN", data)
            self.assertIn("ALLSKY_SFC_SW_DWN", data)
            self.assertIn("PRECTOTCORR", data)
            self.assertTrue(len(data["T2M"]) >= 5)

    def test_get_distillate_weather_features(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            feats = self.client.get_distillate_weather_features(days_back=5, end_date_str="20260920")
            self.assertEqual(feats["hubs_evaluated"], len(DISTILLATE_TERMINAL_HUBS))
            self.assertIn("padd1_distillate_avg_hdd", feats)
            self.assertIn("padd1_distillate_avg_cdd", feats)
            self.assertIn("padd1_distillate_demand_draw_index", feats)
            self.assertIn("terminal_breakdown", feats)
            self.assertIn("NewYorkHarbor", feats["terminal_breakdown"])

    def test_get_ethanol_agro_features(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            feats = self.client.get_ethanol_agro_features(days_back=5, end_date_str="20260920")
            self.assertEqual(feats["hubs_evaluated"], len(BIOFUEL_CORN_HUBS))
            self.assertIn("padd2_corn_avg_gdd", feats)
            self.assertIn("padd2_corn_avg_solar_mj_m2", feats)
            self.assertIn("padd2_corn_avg_precip_mm", feats)
            self.assertIn("ethanol_feedstock_yield_pressure", feats)
            self.assertIn("corn_belt_breakdown", feats)
            self.assertIn("DesMoines_IA", feats["corn_belt_breakdown"])

    def test_get_combined_nasa_power_features(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            combined = self.client.get_combined_nasa_power_features()
            self.assertIn("distillate_features", combined)
            self.assertIn("ethanol_features", combined)
            self.assertIn("padd1_distillate_avg_hdd", combined)
            self.assertIn("padd2_corn_avg_gdd", combined)

    @patch.dict(os.environ, {"TEST_NASA_POWER_FORCE": "1"})
    @patch("src.nasa_power.urllib.request.urlopen")
    def test_live_network_handling_and_caching(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "properties": {
                "parameter": {
                    "T2M": {"20260915": 18.5, "20260916": 19.2}
                }
            }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.client.fetch_point_daily(
            lat=40.7357,
            lon=-74.1724,
            start_date="20260915",
            end_date="20260916",
            parameters=["T2M"]
        )
        self.assertIn("T2M", res)
        self.assertEqual(res["T2M"]["20260915"], 18.5)


if __name__ == "__main__":
    unittest.main()
