"""
Unit tests for Sprint 3:
- Issue #401: 3-2-1 vs 1:1 refining crack spread formulation.
- Issue #397: Return-based target modeling and price level reconstruction.
- Issue #396: Chronological split embargo gap and PurgedGroupTimeSeriesSplit walk-forward CV.
"""

import unittest
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import (
    train_and_compare_models,
    train_multi_horizon_models,
    PurgedGroupTimeSeriesSplit,
    evaluate_predictions
)


class TestModelReturnsAndEmbargo(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 120
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        
        # Synthetic market data with WTI, RBOB, and Heating Oil
        wti = 75.0 + np.cumsum(np.random.normal(0, 0.5, n))
        rbob = 2.40 + np.cumsum(np.random.normal(0, 0.02, n))
        ho = 2.50 + np.cumsum(np.random.normal(0, 0.02, n))
        
        self.market_df = pd.DataFrame({
            "date": dates,
            "gasoline_rbob": np.maximum(rbob, 1.50),
            "wti_crude": np.maximum(wti, 50.0),
            "heating_oil": np.maximum(ho, 1.60),
            "brent_crude": np.maximum(wti + 3.0, 53.0)
        })

    def test_crack_spread_321_and_11_distinction(self):
        """Verify Issue #401: 3-2-1 crack spread is distinct from 1:1 crack spread."""
        feature_df = create_feature_matrix(self.market_df, forecast_horizon=5)
        
        self.assertIn("crack_spread", feature_df.columns)
        self.assertIn("crack_spread_321", feature_df.columns)
        self.assertIn("crack_spread_321_gal", feature_df.columns)
        
        row = feature_df.iloc[10]
        rbob = row["gasoline_rbob"]
        wti = row["wti_crude"]
        ho = row["heating_oil"]
        
        # 1:1 crack ($/gal) = RBOB - WTI / 42
        expected_11 = rbob - (wti / 42.0)
        self.assertAlmostEqual(row["crack_spread"], expected_11, places=3)
        
        # 3-2-1 crack ($/bbl) = (2 * RBOB*42 + 1 * HO*42 - 3 * WTI) / 3
        expected_321_bbl = (2.0 * (rbob * 42.0) + 1.0 * (ho * 42.0) - 3.0 * wti) / 3.0
        self.assertAlmostEqual(row["crack_spread_321"], expected_321_bbl, places=3)
        
        # 3-2-1 crack ($/gal) = (2 * RBOB + 1 * HO - 3 * (WTI/42)) / 3
        expected_321_gal = (2.0 * rbob + 1.0 * ho - 3.0 * (wti / 42.0)) / 3.0
        self.assertAlmostEqual(row["crack_spread_321_gal"], expected_321_gal, places=3)
        self.assertAlmostEqual(row["crack_spread_321_gal"], expected_321_bbl / 42.0, places=3)

    def test_chronological_splits_embargo_gap(self):
        """Verify Issue #396: prepare_chronological_splits enforces purge + embargo gap."""
        feature_df = create_feature_matrix(self.market_df, forecast_horizon=5)
        n_total = len(feature_df)
        train_ratio = 0.8
        horizon = 5
        embargo = 5
        
        splits = prepare_chronological_splits(
            feature_df, 
            train_ratio=train_ratio, 
            forecast_horizon=horizon, 
            purge_overlap=True,
            embargo_steps=embargo
        )
        
        expected_split_idx = int(n_total * train_ratio)
        expected_train_end = expected_split_idx - (horizon + embargo)
        
        self.assertEqual(len(splits["test_df"]), n_total - expected_split_idx)
        self.assertEqual(len(splits["X_train_quant"]), expected_train_end)
        
        # Verify return targets and price targets are present
        self.assertIn("y_train_return", splits)
        self.assertIn("y_train_price", splits)
        self.assertIn("y_test_return", splits)
        self.assertIn("y_test_price", splits)

    def test_return_target_and_price_level_reconstruction(self):
        """Verify Issue #397: Models fit on returns and reconstruct accurate price levels."""
        feature_df = create_feature_matrix(self.market_df, forecast_horizon=5)
        splits = prepare_chronological_splits(
            feature_df, 
            train_ratio=0.8, 
            forecast_horizon=5,
            predict_returns=True
        )
        
        res = train_and_compare_models(splits, model_type="ridge")
        
        # Check predictions are in reasonable dollar/gal level bounds ($1.50 - $4.00)
        pred_hybrid = res["predictions_hybrid"]
        self.assertTrue(np.all(pred_hybrid > 1.0))
        self.assertTrue(np.all(pred_hybrid < 5.0))
        
        # Check that return metrics are tracked
        self.assertIn("metrics_quant_return", res)
        self.assertIn("metrics_hybrid_return", res)
        self.assertIn("predictions_quant_return", res)
        self.assertIn("predictions_hybrid_return", res)
        
        # Check price level reconstruction formula: P_hat = P_curr * (1 + r_hat)
        y_curr = np.array(splits["test_df"]["gasoline_rbob"])
        expected_reconstructed = y_curr * (1.0 + res["predictions_hybrid_return"])
        np.testing.assert_allclose(pred_hybrid, expected_reconstructed, rtol=1e-5)

    def test_purged_group_cv_chronological_walk_forward(self):
        """Verify Issue #396: PurgedGroupTimeSeriesSplit in chronological_only mode with RidgeCV."""
        n_samples = 150
        X = pd.DataFrame(np.random.randn(n_samples, 8), columns=[f"feat_{i}" for i in range(8)])
        y = pd.Series(np.random.normal(0, 0.03, n_samples))
        
        splitter = PurgedGroupTimeSeriesSplit(
            n_splits=4, 
            label_horizon_steps=5, 
            embargo_steps=5, 
            chronological_only=True
        )
        
        splits = list(splitter.split(X, y))
        self.assertGreaterEqual(len(splits), 2)
        
        for train_idx, test_idx in splits:
            self.assertGreater(len(train_idx), 0)
            self.assertGreater(len(test_idx), 0)
            test_start = min(test_idx)
            # All training indices must strictly precede test_start
            for t_idx in train_idx:
                self.assertLess(t_idx, test_start)
                
        # Verify seamless integration with RidgeCV pipeline
        pipe = make_pipeline(StandardScaler(), RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0], cv=splitter))
        pipe.fit(X, y)
        self.assertIn(pipe.named_steps["ridgecv"].alpha_, [0.01, 0.1, 1.0, 10.0])

    def test_multi_horizon_forecasting_level_reconstruction(self):
        """Verify train_multi_horizon_models produces valid live predicted prices."""
        multi_res = train_multi_horizon_models(
            self.market_df, 
            horizons=[1, 3, 5], 
            model_type="ridge"
        )
        
        for h in [1, 3, 5]:
            self.assertIn(h, multi_res)
            res_h = multi_res[h]
            self.assertIn("live_pred_price", res_h)
            self.assertIn("live_base_price", res_h)
            self.assertIn("live_pred_return", res_h)
            self.assertGreater(res_h["live_pred_price"], 1.0)
            self.assertLess(res_h["live_pred_price"], 5.0)


if __name__ == "__main__":
    unittest.main()
