"""
Unit tests for Direct CFTC Commitment of Traders (COT) Energy Positioning Data Ingestion (Issue #143).
Verifies:
1. CFTCDataConnector initializes with zero-cost attributes.
2. fetch_cot_positioning_data returns non-null net speculative, Z-score, commercial hedger ratio, and 1w delta.
3. create_feature_matrix merges CFTC COT positioning features into feature matrix.
"""

import unittest
from src.data_ingestion import CFTCDataConnector, _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits

class TestCFTCCOTIngestion(unittest.TestCase):

    def setUp(self):
        self.connector = CFTCDataConnector()

    def test_cftc_connector_attributes(self):
        """Verify CFTCDataConnector zero-cost free alternative attributes."""
        self.assertTrue(self.connector.is_free_alternative)
        self.assertEqual(self.connector.cost_per_query, 0.0)

    def test_fetch_cot_positioning_data(self):
        """Verify fetch_cot_positioning_data returns structured CFTC positioning metrics."""
        res = self.connector.fetch_cot_positioning_data()
        
        self.assertIn("status", res)
        self.assertIn("cot_rbob_net_speculative", res)
        self.assertIn("cot_rbob_zscore_3y", res)
        self.assertIn("cot_commercial_hedger_ratio", res)
        self.assertIn("cot_net_position_delta_1w", res)
        
        self.assertTrue(res["is_free_alternative"])
        self.assertEqual(res["cost_per_query"], 0.0)

    def test_feature_matrix_cftc_columns(self):
        """Verify create_feature_matrix merges cot_rbob_net_speculative and derived COT features."""
        market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')
        feature_df = create_feature_matrix(market_df, forecast_horizon=5)
        
        self.assertIn("cot_rbob_net_speculative", feature_df.columns)
        self.assertIn("cot_rbob_zscore_3y", feature_df.columns)
        self.assertIn("cot_commercial_hedger_ratio", feature_df.columns)
        self.assertIn("cot_net_position_delta_1w", feature_df.columns)
        
        splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
        self.assertIn("cot_rbob_net_speculative", splits["quant_feature_names"])
        self.assertIn("cot_rbob_zscore_3y", splits["quant_feature_names"])

if __name__ == '__main__':
    unittest.main()
