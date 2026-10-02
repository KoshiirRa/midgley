"""
Unit tests for Mixed-Frequency Kalman Filter Metro Nowcasting Engine (Issue #445).
"""

import unittest
import numpy as np
import pandas as pd
from src.metro_nowcast import MetroNowcastEngine, nowcast_metro_price


class TestMetroNowcastEngine(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        n = 60
        dates = pd.date_range("2026-01-01", periods=n, freq="D")
        
        # True latent price (random walk)
        true_price = 3.50 + np.cumsum(np.random.normal(0, 0.015, n))
        
        # Source 1: AAA (daily, noise ~ 0.04)
        price_aaa = true_price + np.random.normal(0, 0.04, n)
        
        # Source 2: GasBuddy (daily with some missing days, bias = -0.02)
        price_gb = true_price - 0.02 + np.random.normal(0, 0.05, n)
        # Introduce 20% missing values
        mask_gb = np.random.rand(n) < 0.2
        price_gb[mask_gb] = np.nan
        
        # Source 3: EIA (weekly on Mondays, noise ~ 0.02)
        price_eia = np.full(n, np.nan)
        for i, d in enumerate(dates):
            if d.weekday() == 0:  # Monday
                price_eia[i] = true_price[i] + np.random.normal(0, 0.02)
        
        self.df = pd.DataFrame({
            "date": dates,
            "true_price": true_price,
            "price_aaa": price_aaa,
            "price_gasbuddy": price_gb,
            "price_eia": price_eia
        })

    def test_kalman_filter_execution_and_convergence(self):
        engine = MetroNowcastEngine()
        engine.fit_parameters(self.df, aaa_col="price_aaa", gasbuddy_col="price_gasbuddy", eia_col="price_eia")
        
        self.assertTrue(engine.is_fitted)
        self.assertIn("GasBuddy", engine.biases)
        
        result_df = engine.run_filter(
            self.df,
            aaa_col="price_aaa",
            gasbuddy_col="price_gasbuddy",
            eia_col="price_eia"
        )
        
        self.assertIn("filtered_nowcast", result_df.columns)
        self.assertIn("smoothed_price", result_df.columns)
        self.assertIn("nowcast_std_err", result_df.columns)
        self.assertIn("smoothed_std_err", result_df.columns)
        
        # Verify filtered nowcast tracks true price accurately (MAE < $0.06)
        mae = np.mean(np.abs(result_df["filtered_nowcast"] - result_df["true_price"]))
        self.assertLess(mae, 0.06)
        
        # Verify smoothing variance is less than or equal to filtered variance
        self.assertTrue(np.all(result_df["smoothed_std_err"] <= result_df["nowcast_std_err"] + 1e-4))

    def test_nowcast_metro_price_helper(self):
        res = nowcast_metro_price("Tulsa_OK", live_price=3.45)
        self.assertEqual(res["region"], "Tulsa_OK")
        self.assertIn("filtered_nowcast", res)
        self.assertIn("confidence_lower_95", res)
        self.assertIn("confidence_upper_95", res)
        self.assertLessEqual(res["confidence_lower_95"], res["filtered_nowcast"])
        self.assertGreaterEqual(res["confidence_upper_95"], res["filtered_nowcast"])


if __name__ == "__main__":
    unittest.main()
