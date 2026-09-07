"""
Unit tests for U.S. Treasury Yield Curve & TIPS Inflation Metrics Ingestion (Issue #66).
Verifies:
1. TreasuryYieldConnector zero-cost and free-alternative attributes.
2. fetch_treasury_yield_dataset returns structured yield curve features (10Y, 2Y, 10Y-2Y spread, TIPS real yield).
3. 10Y-2Y spread is properly calculated and non-null.
4. Feature matrix merges Treasury columns into quantitative feature matrix and splits.
5. get_latest_yield_snapshot returns expected payload structure.
"""

import unittest
import pandas as pd
from src.treasury_yield_feed import TreasuryYieldConnector
from src.data_ingestion import _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits


class TestTreasuryYieldFeed(unittest.TestCase):

    def setUp(self):
        self.connector = TreasuryYieldConnector()

    def test_treasury_connector_attributes(self):
        """Verify TreasuryYieldConnector zero-cost and free-alternative attributes."""
        self.assertTrue(self.connector.is_free_source)
        self.assertEqual(self.connector.cost_per_query, 0.0)

    def test_fetch_treasury_yield_dataset(self):
        """Verify fetch_treasury_yield_dataset returns structured yield features."""
        df = self.connector.fetch_treasury_yield_dataset(start_date="2026-01-01", end_date="2026-03-01")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("date", df.columns)
        self.assertIn("treasury_yield_10y", df.columns)
        self.assertIn("treasury_yield_2y", df.columns)
        self.assertIn("treasury_yield_10y_2y_spread", df.columns)
        self.assertIn("tips_10y_real_yield", df.columns)
        self.assertIn("treasury_spread_delta_5d", df.columns)

        # Ensure values are non-null and numeric
        self.assertFalse(df["treasury_yield_10y"].isna().any())
        self.assertFalse(df["treasury_yield_10y_2y_spread"].isna().any())

    def test_latest_yield_snapshot(self):
        """Verify get_latest_yield_snapshot returns structured dictionary."""
        snapshot = self.connector.get_latest_yield_snapshot()
        self.assertIsInstance(snapshot, dict)
        self.assertIn("treasury_yield_10y", snapshot)
        self.assertIn("treasury_yield_2y", snapshot)
        self.assertIn("treasury_yield_10y_2y_spread", snapshot)
        self.assertIn("tips_10y_real_yield", snapshot)
        self.assertIn("curve_state", snapshot)

    def test_feature_matrix_treasury_columns(self):
        """Verify create_feature_matrix and prepare_chronological_splits incorporate Treasury features."""
        market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')
        feature_df = create_feature_matrix(market_df, forecast_horizon=5)

        self.assertIn("treasury_yield_10y", feature_df.columns)
        self.assertIn("treasury_yield_10y_2y_spread", feature_df.columns)
        self.assertIn("tips_10y_real_yield", feature_df.columns)
        self.assertIn("treasury_spread_delta_5d", feature_df.columns)

        # Verify no NaN values in Treasury columns
        self.assertFalse(feature_df["treasury_yield_10y_2y_spread"].isna().any())
        self.assertFalse(feature_df["tips_10y_real_yield"].isna().any())

        splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
        self.assertIn("treasury_yield_10y", splits["quant_feature_names"])
        self.assertIn("treasury_yield_10y_2y_spread", splits["quant_feature_names"])
        self.assertIn("tips_10y_real_yield", splits["quant_feature_names"])
        self.assertIn("treasury_spread_delta_5d", splits["quant_feature_names"])


if __name__ == '__main__':
    unittest.main()
