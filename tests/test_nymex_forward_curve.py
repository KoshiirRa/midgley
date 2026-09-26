"""
Tests for NYMEX Forward Curve, Calendar Spread & Crack Futures Connector (tests/test_nymex_forward_curve.py)
Issue #404: NYMEX forward curve, calendar spreads & crack futures.
"""

import os
import unittest
from unittest.mock import patch
from src.data_ingestion import NYMEXForwardCurveConnector
from src.feature_engineering import create_feature_matrix
import pandas as pd
import numpy as np


class TestNYMEXForwardCurveConnector(unittest.TestCase):

    def setUp(self):
        self.connector = NYMEXForwardCurveConnector()

    def test_fetch_forward_curve_spreads(self):
        """Verify forward curve spreads and crack features structure."""
        res = self.connector.fetch_forward_curve_spreads()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("forward_features", res)
        feats = res["forward_features"]
        
        # Verify required forward curve metrics
        self.assertIn("rbob_m1_price", feats)
        self.assertIn("rbob_m2_price", feats)
        self.assertIn("wti_m1_price", feats)
        self.assertIn("wti_m2_price", feats)
        self.assertIn("ho_m1_price", feats)
        self.assertIn("rbob_calendar_spread_m1_m2", feats)
        self.assertIn("wti_calendar_spread_m1_m2", feats)
        self.assertIn("crack_spread_11", feats)
        self.assertIn("crack_spread_321", feats)
        self.assertIn("curve_backwardation_flag", feats)

        # Verify mathematical consistency
        # Crack spread 1:1 = RBOB - WTI/42
        expected_crack_11 = round(feats["rbob_m1_price"] - (feats["wti_m1_price"] / 42.0), 4)
        self.assertAlmostEqual(feats["crack_spread_11"], expected_crack_11, places=3)

        # 3-2-1 crack spread formula
        expected_crack_321 = round(((2.0 * feats["rbob_m1_price"] + 1.0 * feats["ho_m1_price"]) - (3.0 * (feats["wti_m1_price"] / 42.0))) / 3.0, 4)
        self.assertAlmostEqual(feats["crack_spread_321"], expected_crack_321, places=3)

    def test_nymex_forward_vintage_persistence(self):
        """Verify snapshot saving and retrieval with bitemporal filtering."""
        test_path = "data/test_nymex_forward_vintages_tmp.json"
        test_rec = {
            "source": "Test",
            "as_of": "2026-09-22 00:00:00",
            "valid_date": "2026-09-22",
            "forward_features": {"rbob_calendar_spread_m1_m2": 0.035}
        }
        try:
            with patch.dict(os.environ, {"TESTING": "0"}):
                self.connector.save_nymex_forward_vintage_record(test_rec, filepath=test_path)
                vintages = self.connector.get_nymex_forward_vintages_as_of("2026-09-22", filepath=test_path)
                self.assertGreaterEqual(len(vintages), 1)
                self.assertEqual(vintages[-1]["forward_features"]["rbob_calendar_spread_m1_m2"], 0.035)
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)

    def test_feature_matrix_integration(self):
        """Verify NYMEX forward curve features populate in create_feature_matrix."""
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        mock_df = pd.DataFrame({
            "date": dates,
            "gasoline_rbob": np.linspace(2.30, 2.50, 10),
            "wti_crude": np.linspace(70.0, 75.0, 10),
            "heating_oil": np.linspace(2.40, 2.60, 10),
            "cboe_ovx": np.full(10, 32.0),
            "baker_hughes_rigs": np.full(10, 580.0),
        })

        res_df = create_feature_matrix(mock_df, region="National")
        
        self.assertIn("rbob_calendar_spread_m1_m2", res_df.columns)
        self.assertIn("wti_calendar_spread_m1_m2", res_df.columns)
        self.assertIn("crack_spread_forward_321", res_df.columns)
        self.assertIn("nymex_backwardation_regime", res_df.columns)


if __name__ == "__main__":
    unittest.main()
