"""
Unit tests for Naive Persistence Baseline & Benchmark Comparisons (Issue #43).
Verifies:
1. evaluate_baseline_comparisons calculates Naive Persistence (P_{t+h} = P_t) metrics.
2. Model uplift (%) over persistence baseline calculation.
3. train_and_compare_models includes metrics_persistence, metrics_moving_avg, and model_uplift_over_persistence_pct.
"""

import unittest
import pandas as pd
import numpy as np
from src.data_ingestion import _generate_synthetic_market_data
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import evaluate_baseline_comparisons, train_and_compare_models

class TestModelBaselines(unittest.TestCase):

    def setUp(self):
        # 60 business days of synthetic market data
        self.market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')
        self.feature_df = create_feature_matrix(self.market_df, forecast_horizon=5)
        self.split_data = prepare_chronological_splits(self.feature_df, train_ratio=0.8, forecast_horizon=5)

    def test_evaluate_baseline_comparisons_persistence(self):
        """Verify evaluate_baseline_comparisons computes Naive Persistence baseline metrics."""
        y_true = pd.Series([2.50, 2.60, 2.70])
        y_current = pd.Series([2.40, 2.50, 2.60])
        
        res = evaluate_baseline_comparisons(y_true, y_current)
        self.assertIn("metrics_persistence", res)
        self.assertIn("MAE", res["metrics_persistence"])
        # Persistence prediction is y_current -> errors: |2.50-2.40|=0.1, |2.60-2.50|=0.1, |2.70-2.60|=0.1 -> MAE = 0.10
        self.assertEqual(res["metrics_persistence"]["MAE"], 0.10)

    def test_train_and_compare_models_baseline_keys(self):
        """Verify train_and_compare_models includes persistence baseline metrics and uplift pct."""
        res = train_and_compare_models(self.split_data, model_type="ridge")
        
        self.assertIn("metrics_persistence", res)
        self.assertIn("metrics_moving_avg", res)
        self.assertIn("model_uplift_over_persistence_pct", res)
        self.assertIn("predictions_persistence", res)
        
        self.assertIsInstance(res["metrics_persistence"]["MAE"], float)
        self.assertIsInstance(res["model_uplift_over_persistence_pct"], float)

if __name__ == '__main__':
    unittest.main()
