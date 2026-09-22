"""
Unit tests for Temporal Lookahead Leakage Prevention (Issue #354).
Verifies:
1. Feature NaN imputation does not propagate future values backward (bfill elimination).
2. Chronological train/test split boundary enforces an h-step purging gap with zero target label overlap.
3. Context routing autocorrelation diagnostic computes strictly on training partitions.
4. Stacking ensemble cross-validation uses chronological TimeSeriesSplit without future lookahead.
5. PurgedGroupTimeSeriesSplit enforces temporal boundaries in chronological_only mode.
"""

import unittest
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from src.feature_engineering import (
    create_feature_matrix,
    prepare_chronological_splits,
    compute_context_routing_diagnostic
)
from src.models import (
    build_stacking_ensemble_pipeline,
    PurgedGroupTimeSeriesSplit
)


class TestTemporalLeakage(unittest.TestCase):

    def test_feature_dataset_no_backward_fill(self):
        """Verifies that missing feature values are forward-filled and never backward-filled."""
        dates = pd.date_range("2026-01-01", periods=20, freq="D")
        wti = [np.nan, np.nan, np.nan] + [70.0 + i for i in range(17)]
        gas = [2.50 + 0.01 * i for i in range(20)]

        df = pd.DataFrame({
            "date": dates,
            "gasoline_rbob": gas,
            "wti_crude": wti,
            "crack_spread": [15.0] * 20
        })

        res_df = create_feature_matrix(df, forecast_horizon=5)

        # In index 0, wti_crude should be 0.0 (constant fill) NOT 70.0 (backward fill)
        self.assertEqual(res_df["wti_crude"].iloc[0], 0.0)
        self.assertEqual(res_df["wti_crude"].iloc[1], 0.0)
        self.assertEqual(res_df["wti_crude"].iloc[2], 0.0)
        self.assertEqual(res_df["wti_crude"].iloc[3], 70.0)

    def test_chronological_split_purges_boundary_overlap(self):
        """Verifies that the chronological train/test split purges the h-step boundary overlap."""
        n = 100
        dates = pd.date_range("2026-01-01", periods=n, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "gasoline_rbob": [2.50 + i * 0.01 for i in range(n)],
            "wti_crude": [70.0] * n,
            "crack_spread": [15.0] * n,
            "target_price_5d": [2.50 + (i + 5) * 0.01 for i in range(n)]
        })

        train_ratio = 0.8
        forecast_horizon = 5
        splits = prepare_chronological_splits(df, train_ratio=train_ratio, forecast_horizon=forecast_horizon, purge_overlap=True)

        test_df = splits["test_df"]
        y_train = splits["y_train"]

        split_idx = int(n * train_ratio)  # 80

        # Test slice starts at index 80
        self.assertEqual(test_df.index[0], split_idx)

        # The last training index must be <= split_idx - forecast_horizon
        last_train_idx = y_train.index[-1]
        self.assertLessEqual(last_train_idx, split_idx - forecast_horizon)

        # Target value of the last training observation must correspond to a date BEFORE the first test observation
        last_train_target = splits["y_train_price"].iloc[-1]
        expected_target_at_boundary = df["gasoline_rbob"].iloc[last_train_idx + forecast_horizon]
        self.assertEqual(last_train_target, expected_target_at_boundary)
        self.assertLess(last_train_idx + forecast_horizon, split_idx)

    def test_context_routing_diagnostic_respects_train_ratio(self):
        """Verifies that context routing diagnostic can be calculated strictly on the training partition."""
        dates = pd.date_range("2026-01-01", periods=100, freq="D")
        train_prices = [2.0 + np.sin(i / 2.0) * 0.1 for i in range(80)]
        test_prices = [2.0 + i * 0.05 for i in range(20)]

        df = pd.DataFrame({
            "date": dates,
            "gasoline_rbob": train_prices + test_prices
        })

        diag_full = compute_context_routing_diagnostic(df, horizon=5, train_ratio=None)
        diag_train_only = compute_context_routing_diagnostic(df, horizon=5, train_ratio=0.8)

        self.assertIn("rho_h", diag_train_only)
        self.assertIn("recommendation", diag_train_only)
        self.assertNotEqual(diag_train_only["rho_h"], diag_full["rho_h"])

    def test_stacking_ensemble_uses_chronological_cv(self):
        """Verifies that build_stacking_ensemble_pipeline defaults to PurgedGroupTimeSeriesSplit."""
        stacking_model = build_stacking_ensemble_pipeline()
        self.assertIsInstance(stacking_model.cv, PurgedGroupTimeSeriesSplit)
        self.assertEqual(stacking_model.cv.n_splits, 5)

    def test_purged_group_time_series_split_chronological_mode(self):
        """Verifies that PurgedGroupTimeSeriesSplit in chronological_only mode never trains on future folds."""
        n_samples = 100
        X = np.random.randn(n_samples, 4)
        y = np.random.randn(n_samples)

        splitter = PurgedGroupTimeSeriesSplit(n_splits=5, label_horizon_steps=5, embargo_steps=5, chronological_only=True)
        splits = list(splitter.split(X, y))

        for train_idx, test_idx in splits:
            test_start = min(test_idx)
            for t_idx in train_idx:
                self.assertLess(t_idx, test_start, f"Train index {t_idx} occurred after or during test starting at {test_start}")


if __name__ == "__main__":
    unittest.main()
