"""
Unit tests for SHAP Feature Attribution Engine for Model Interpretability (Issue #114).
Verifies:
1. compute_shap_feature_attributions calculates sorted feature impact values.
2. train_and_compare_models outputs shap_feature_attributions dictionary.
"""

import unittest
import pandas as pd
import numpy as np
from src.data_ingestion import _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import compute_shap_feature_attributions, train_and_compare_models

class TestSHAPAttribution(unittest.TestCase):

    def setUp(self):
        self.market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')
        self.feature_df = create_feature_matrix(self.market_df, forecast_horizon=5)
        self.split_data = prepare_chronological_splits(self.feature_df, train_ratio=0.8, forecast_horizon=5)

    def test_compute_shap_feature_attributions(self):
        """Verify compute_shap_feature_attributions returns non-empty sorted feature attributions."""
        res = train_and_compare_models(self.split_data, model_type="ridge")
        model_hybrid = res["model_hybrid"]
        X_test_hybrid = self.split_data["X_test_hybrid"]
        feature_names = self.split_data["hybrid_feature_names"]
        
        attributions = compute_shap_feature_attributions(model_hybrid, X_test_hybrid, feature_names)
        
        self.assertIsInstance(attributions, dict)
        self.assertGreater(len(attributions), 0)
        
        # Verify non-increasing attribution values order
        vals = list(attributions.values())
        for i in range(len(vals) - 1):
            self.assertGreaterEqual(vals[i], vals[i+1])

    def test_train_and_compare_models_contains_shap_key(self):
        """Verify train_and_compare_models return dictionary contains shap_feature_attributions key."""
        res = train_and_compare_models(self.split_data, model_type="ridge")
        self.assertIn("shap_feature_attributions", res)
        self.assertIsInstance(res["shap_feature_attributions"], dict)

if __name__ == '__main__':
    unittest.main()
