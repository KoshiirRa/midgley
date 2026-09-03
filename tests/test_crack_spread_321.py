"""
Unit tests for 3-2-1 Refining Crack Spread Feature Vector (Issue #169).
Verifies:
1. Synthetic market data includes heating_oil (HO=F).
2. 3-2-1 Crack Spread calculation matches exact mathematical benchmark:
   Crack (3-2-1) = (2 * RBOB*42 + 1 * HO*42 - 3 * WTI) / 3
3. Feature matrix includes crack_spread_321, crack_spread_321_gal, and crack_spread_321_delta_5d.
"""

import unittest
import pandas as pd
import numpy as np
from src.data_ingestion import _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix

class TestCrackSpread321(unittest.TestCase):

    def setUp(self):
        # 60 business days of synthetic data
        self.market_df = _generate_synthetic_market_data(start_date='2026-01-01', end_date='2026-03-30')

    def test_synthetic_data_contains_heating_oil(self):
        """Verify _generate_synthetic_market_data includes heating_oil column."""
        self.assertIn('heating_oil', self.market_df.columns)
        self.assertTrue((self.market_df['heating_oil'] > 0.0).all())

    def test_crack_spread_321_mathematical_benchmark(self):
        """
        Verify exact 3-2-1 Crack Spread math against manual benchmark:
        RBOB = $2.50/gal ($105.00/bbl)
        Heating Oil = $2.70/gal ($113.40/bbl)
        WTI Crude = $75.00/bbl
        
        Expected 3-2-1 Crack = (2 * 105.00 + 1 * 113.40 - 3 * 75.00) / 3
                            = (210.00 + 113.40 - 225.00) / 3
                            = 98.40 / 3 = $32.80/bbl ($0.78095/gal)
        """
        dates = pd.date_range('2026-01-01', periods=60, freq='B')
        df_manual = pd.DataFrame({
            'date': dates,
            'gasoline_rbob': 2.50,
            'heating_oil': 2.70,
            'wti_crude': 75.00
        })

        df_feat = create_feature_matrix(df_manual, forecast_horizon=5)

        self.assertIn('crack_spread_321', df_feat.columns)
        self.assertIn('crack_spread_321_gal', df_feat.columns)
        self.assertIn('crack_spread_321_delta_5d', df_feat.columns)

        expected_bbl = 32.80
        expected_gal = 32.80 / 42.0

        np.testing.assert_almost_equal(df_feat['crack_spread_321'].iloc[0], expected_bbl, decimal=4)
        np.testing.assert_almost_equal(df_feat['crack_spread_321_gal'].iloc[0], expected_gal, decimal=4)

    def test_feature_matrix_pipeline_with_heating_oil(self):
        """Verify feature matrix pipeline generates valid 3-2-1 crack spread series without NaNs."""
        df_feat = create_feature_matrix(self.market_df, forecast_horizon=5)
        self.assertIn('crack_spread_321', df_feat.columns)
        self.assertFalse(df_feat['crack_spread_321'].isnull().any())
        self.assertFalse(df_feat['crack_spread_321_delta_5d'].isnull().any())

if __name__ == '__main__':
    unittest.main()
