"""
Unit tests for Multi-Model Stacking Ensemble Regressor & Quantile Uncertainty Bands (Issue #170).
Verifies:
1. build_stacking_ensemble_pipeline creates a valid StackingRegressor.
2. compute_quantile_uncertainty_bands computes P10 <= P50 <= P90 bounds.
3. train_and_compare_models(model_type="stacking") fits ensemble and outputs predictions_p10, predictions_p50, predictions_p90.
"""

import unittest
import numpy as np
from sklearn.ensemble import StackingRegressor
from src.data_ingestion import _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import (
    build_stacking_ensemble_pipeline,
    compute_quantile_uncertainty_bands,
    train_and_compare_models
)

class TestStackingEnsemble(unittest.TestCase):

    def setUp(self):
        self.market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')
        self.feature_df = create_feature_matrix(self.market_df, forecast_horizon=5)
        self.split_data = prepare_chronological_splits(self.feature_df, train_ratio=0.8, forecast_horizon=5)

    def test_build_stacking_ensemble_pipeline(self):
        """Verify build_stacking_ensemble_pipeline builds a scikit-learn StackingRegressor."""
        ensemble = build_stacking_ensemble_pipeline()
        self.assertIsInstance(ensemble, StackingRegressor)
        self.assertGreaterEqual(len(ensemble.estimators), 3)

    def test_compute_quantile_uncertainty_bands(self):
        """Verify compute_quantile_uncertainty_bands computes P10 <= P50 <= P90 order."""
        y_pred = np.array([2.50, 2.60, 2.70])
        bands = compute_quantile_uncertainty_bands(y_pred, residual_std=0.10)
        
        self.assertIn("p10", bands)
        self.assertIn("p50", bands)
        self.assertIn("p90", bands)
        
        np.testing.assert_array_less(bands["p10"], bands["p50"])
        np.testing.assert_array_less(bands["p50"], bands["p90"])

    def test_train_and_compare_models_stacking(self):
        """Verify train_and_compare_models with model_type='stacking' outputs quantile prediction arrays."""
        res = train_and_compare_models(self.split_data, model_type="stacking")
        
        self.assertIn("predictions_p10", res)
        self.assertIn("predictions_p50", res)
        self.assertIn("predictions_p90", res)
        
        self.assertEqual(len(res["predictions_p10"]), len(res["y_test"]))
        np.testing.assert_array_less(res["predictions_p10"], res["predictions_p90"])

if __name__ == '__main__':
    unittest.main()
