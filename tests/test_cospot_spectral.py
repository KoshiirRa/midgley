"""
Unit & Integration Tests for CoSPOT Compositional Spectral & Wavelet Feature Prompting (Issue #215)
Reference: arXiv:2609.02093v1
"""

import unittest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from src.cospot_spectral_engine import (
    compute_dft_spectral_features,
    compute_dwt_wavelet_features,
    generate_spectral_prompt_context,
    compute_rolling_spectral_features,
    CoSPOTOnlineAdapter
)
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import evaluate_cospot_spectral_benchmarks
from src.event_analyzer import extract_event_features_llm, extract_batch_event_features_llm, extract_event_features_rule_based


class TestCoSPOTSpectralEngine(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        # 50 days of synthetic price data with a 10-day cyclical wave + upward trend + noise
        t = np.linspace(0, 50, 50)
        trend = 2.50 + 0.01 * t
        cycle = 0.15 * np.sin(2 * np.pi * t / 10.0)
        noise = np.random.normal(0, 0.02, 50)
        self.prices = trend + cycle + noise
        
        self.df = pd.DataFrame({
            'date': pd.date_range(start='2026-01-01', periods=50, freq='B'),
            'gasoline_rbob': self.prices,
            'wti_crude': self.prices * 30.0,
            'brent_crude': self.prices * 31.0
        })

    def test_dft_spectral_features_basic(self):
        res = compute_dft_spectral_features(self.prices, lookback=21, low_pass_gamma=0.4)
        self.assertIn("dominant_cycle_period_days", res)
        self.assertIn("low_freq_energy_ratio", res)
        self.assertIn("spectral_entropy", res)
        self.assertIn("spectral_trend_slope", res)
        
        self.assertGreater(res["dominant_cycle_period_days"], 0)
        self.assertGreaterEqual(res["low_freq_energy_ratio"], 0.0)
        self.assertLessEqual(res["low_freq_energy_ratio"], 1.0)
        self.assertGreaterEqual(res["spectral_entropy"], 0.0)
        self.assertLessEqual(res["spectral_entropy"], 1.0)

    def test_dft_short_series_safety(self):
        res = compute_dft_spectral_features([2.5, 2.6], lookback=21)
        self.assertEqual(res["dominant_cycle_period_days"], 21.0)
        self.assertEqual(res["low_freq_energy_ratio"], 1.0)

    def test_dwt_wavelet_features_basic(self):
        res = compute_dwt_wavelet_features(self.prices, level=2)
        self.assertIn("dwt_detail_energy_ratio", res)
        self.assertIn("dwt_detail_shock_mag", res)
        self.assertIn("dwt_approx_momentum", res)
        self.assertIn("dwt_d1_norm", res)
        self.assertIn("dwt_d2_norm", res)
        
        self.assertGreaterEqual(res["dwt_detail_energy_ratio"], 0.0)
        self.assertGreaterEqual(res["dwt_detail_shock_mag"], 0.0)

    def test_dwt_short_series_safety(self):
        res = compute_dwt_wavelet_features([2.5, 2.6, 2.7])
        self.assertEqual(res["dwt_detail_energy_ratio"], 0.0)
        self.assertEqual(res["dwt_detail_shock_mag"], 0.0)

    def test_generate_spectral_prompt_context(self):
        ctx = generate_spectral_prompt_context(self.prices, lookback=21)
        self.assertIsInstance(ctx, str)
        self.assertIn("[MARKET FREQUENCY & SPECTRAL REGIME (CoSPOT arXiv:2609.02093)]", ctx)
        self.assertIn("Dominant Cycle:", ctx)
        self.assertIn("Spectral Regime:", ctx)
        self.assertIn("Wavelet Noise & Shock State:", ctx)

    def test_compute_rolling_spectral_features(self):
        df_spec = compute_rolling_spectral_features(self.df, price_col='gasoline_rbob', lookback=21)
        expected_cols = [
            'cospot_dft_dominant_period', 'cospot_dft_low_freq_energy_ratio',
            'cospot_dft_spectral_entropy', 'cospot_dwt_detail_energy_ratio',
            'cospot_dwt_detail_shock_mag', 'cospot_dwt_approx_momentum'
        ]
        for col in expected_cols:
            self.assertIn(col, df_spec.columns)
            self.assertEqual(len(df_spec[col]), len(self.df))
            self.assertFalse(df_spec[col].isna().any())

    def test_cospot_online_adapter(self):
        adapter = CoSPOTOnlineAdapter(delta=0.90, learning_rate=0.05)
        x_vec = np.array([1.0, 0.5, -0.2])
        
        # Initial prediction is 0.0
        self.assertEqual(adapter.predict_residual(x_vec), 0.0)
        
        # Train on a step with error +0.10
        adapter.fit_online_step(x_vec, y_true=2.60, y_pred_base=2.50)
        
        # Next residual prediction should be positive and non-zero
        pred_res = adapter.predict_residual(x_vec)
        self.assertGreater(pred_res, 0.0)
        
        # Check geometric decay application
        weights_norm_step1 = np.linalg.norm(adapter.weights)
        adapter.fit_online_step(x_vec, y_true=2.50, y_pred_base=2.50)
        # When error is 0, weights decay by delta factor
        self.assertLess(np.linalg.norm(adapter.weights), weights_norm_step1 + 0.01)

    def test_feature_engineering_matrix_integration(self):
        feature_matrix = create_feature_matrix(self.df, forecast_horizon=5)
        expected_cospot_cols = [
            'cospot_dft_dominant_period', 'cospot_dft_low_freq_energy_ratio',
            'cospot_dft_spectral_entropy', 'cospot_dwt_detail_energy_ratio',
            'cospot_dwt_detail_shock_mag', 'cospot_dwt_approx_momentum'
        ]
        for col in expected_cospot_cols:
            self.assertIn(col, feature_matrix.columns)

        splits = prepare_chronological_splits(feature_matrix, train_ratio=0.7, forecast_horizon=5)
        for col in expected_cospot_cols:
            self.assertIn(col, splits['quant_feature_names'])
            self.assertIn(col, splits['hybrid_feature_names'])

    def test_models_evaluate_cospot_spectral_benchmarks(self):
        feature_matrix = create_feature_matrix(self.df, forecast_horizon=5)
        splits = prepare_chronological_splits(feature_matrix, train_ratio=0.7, forecast_horizon=5)
        
        benchmarks = evaluate_cospot_spectral_benchmarks(splits)
        self.assertEqual(benchmarks["status"], "success")
        self.assertGreater(benchmarks["cospot_feature_count"], 0)
        self.assertIn("metrics_base_without_spectral", benchmarks)
        self.assertIn("metrics_cospot_spectral_quant", benchmarks)
        self.assertIn("metrics_cospot_spectral_hybrid", benchmarks)
        self.assertIn("metrics_cospot_online_adapted", benchmarks)
        self.assertIn("MAE", benchmarks["metrics_cospot_spectral_quant"])

    def test_event_analyzer_with_spectral_context(self):
        headline = "OPEC+ agrees to unexpected 1.5 million barrel crude production cut"
        spectral_ctx = generate_spectral_prompt_context(self.prices)
        
        # Test rule-based extraction fallback with spectral context
        scores = extract_event_features_llm(headline, tier="basic", spectral_context=spectral_ctx)
        self.assertIn("geopolitical_risk", scores)
        self.assertIn("supply_disruption", scores)
        self.assertIn("overall_price_pressure", scores)
        
        # Test batch extraction
        batch_scores = extract_batch_event_features_llm([headline, "Refinery fire halts Midwest fuel output"], spectral_context=spectral_ctx)
        self.assertEqual(len(batch_scores), 2)
        self.assertIn("supply_disruption", batch_scores[1])


if __name__ == '__main__':
    unittest.main()
