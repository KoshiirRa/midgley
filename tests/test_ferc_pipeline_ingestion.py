"""
Unit tests for FERC Form 6 & Open Data API Interstate Oil Pipeline Tariff Ingestion (Issue #123).
Verifies:
1. FERCDataConnector initializes with zero-cost free alternative attributes.
2. fetch_pipeline_tariff_data returns non-null pipeline tariff rates for Colonial, Plantation, Explorer pipelines.
3. create_feature_matrix merges ferc_colonial_line1_tariff_per_bbl and derived FERC columns into feature matrix.
"""

import unittest
from src.data_ingestion import FERCDataConnector, _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits

class TestFERCPipelineIngestion(unittest.TestCase):

    def setUp(self):
        self.connector = FERCDataConnector()

    def test_ferc_connector_attributes(self):
        """Verify FERCDataConnector zero-cost free alternative attributes."""
        self.assertTrue(self.connector.is_free_alternative)
        self.assertEqual(self.connector.cost_per_query, 0.0)

    def test_fetch_pipeline_tariff_data(self):
        """Verify fetch_pipeline_tariff_data returns structured FERC pipeline tariff rates."""
        res = self.connector.fetch_pipeline_tariff_data()
        
        self.assertIn("status", res)
        self.assertIn("ferc_colonial_line1_tariff_per_bbl", res)
        self.assertIn("ferc_plantation_tariff_per_bbl", res)
        self.assertIn("ferc_explorer_tariff_per_bbl", res)
        self.assertIn("ferc_pipeline_tariff_index_5d", res)
        
        self.assertGreater(res["ferc_colonial_line1_tariff_per_bbl"], 0.0)
        self.assertTrue(res["is_free_alternative"])
        self.assertEqual(res["cost_per_query"], 0.0)

    def test_feature_matrix_ferc_columns(self):
        """Verify create_feature_matrix merges ferc_colonial_line1_tariff_per_bbl and derived FERC columns."""
        market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')
        feature_df = create_feature_matrix(market_df, forecast_horizon=5)
        
        self.assertIn("ferc_colonial_line1_tariff_per_bbl", feature_df.columns)
        self.assertIn("ferc_plantation_tariff_per_bbl", feature_df.columns)
        self.assertIn("ferc_explorer_tariff_per_bbl", feature_df.columns)
        self.assertIn("ferc_pipeline_tariff_index_5d", feature_df.columns)
        
        splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
        self.assertIn("ferc_colonial_line1_tariff_per_bbl", splits["quant_feature_names"])
        self.assertIn("ferc_pipeline_tariff_index_5d", splits["quant_feature_names"])

if __name__ == '__main__':
    unittest.main()
