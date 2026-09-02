"""
Unit tests for Open-Meteo High-Resolution Regional Temperature & Freeze Shocks Connector (Issue #72).
Verifies:
1. OpenMeteoDegreeDaysConnector returns degree days (HDD, CDD) and freeze warning flags.
2. Degree days formulas: HDD = max(0, 65 - T_mean), CDD = max(0, T_mean - 65).
3. Feature engineering matrix creates hdd_5d_rolling and cdd_5d_rolling columns.
"""

import unittest
import pandas as pd
from src.noaa_weather import OpenMeteoDegreeDaysConnector
from src.data_ingestion import _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits

class TestOpenMeteoWeather(unittest.TestCase):

    def setUp(self):
        self.connector = OpenMeteoDegreeDaysConnector()

    def test_fetch_hub_degree_days_tulsa(self):
        """Verify fetch_hub_degree_days returns structured temperature and degree days dictionary for Tulsa."""
        res = self.connector.fetch_hub_degree_days("Tulsa_OK")
        
        self.assertEqual(res["hub_code"], "Tulsa_OK")
        self.assertIn("mean_temp_f", res)
        self.assertIn("heating_degree_days_hdd", res)
        self.assertIn("cooling_degree_days_cdd", res)
        self.assertIn("freeze_warning", res)
        
        # Verify HDD and CDD math
        mean_t = res["mean_temp_f"]
        expected_hdd = max(0.0, 65.0 - mean_t)
        expected_cdd = max(0.0, mean_t - 65.0)
        self.assertAlmostEqual(res["heating_degree_days_hdd"], expected_hdd, places=1)
        self.assertAlmostEqual(res["cooling_degree_days_cdd"], expected_cdd, places=1)

    def test_fetch_all_hubs_degree_days(self):
        """Verify fetch_all_hubs_degree_days returns all 6 refining hubs."""
        all_res = self.connector.fetch_all_hubs_degree_days()
        self.assertIn("hubs", all_res)
        self.assertIn("Tulsa_OK", all_res["hubs"])
        self.assertIn("Newark_DE", all_res["hubs"])
        self.assertIn("Cincinnati_OH", all_res["hubs"])
        self.assertIn("Oakland_CA", all_res["hubs"])
        self.assertIn("Greenville_NC", all_res["hubs"])
        self.assertIn("Charlotte_NC", all_res["hubs"])

    def test_feature_matrix_open_meteo_columns(self):
        """Verify create_feature_matrix creates hdd_5d_rolling and cdd_5d_rolling feature columns."""
        market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')
        feature_df = create_feature_matrix(market_df, forecast_horizon=5)
        
        self.assertIn("hdd_daily", feature_df.columns)
        self.assertIn("cdd_daily", feature_df.columns)
        self.assertIn("hdd_5d_rolling", feature_df.columns)
        self.assertIn("cdd_5d_rolling", feature_df.columns)
        self.assertIn("freeze_warning_flag", feature_df.columns)
        
        splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
        self.assertIn("hdd_5d_rolling", splits["quant_feature_names"])
        self.assertIn("cdd_5d_rolling", splits["quant_feature_names"])

if __name__ == '__main__':
    unittest.main()
