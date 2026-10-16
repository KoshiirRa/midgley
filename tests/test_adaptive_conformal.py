"""
Unit Tests for Adaptive Conformal Inference & Quantile Generation (Issue #449).
"""

import unittest
import numpy as np
from src.models import (
    compute_conformal_prediction_intervals,
    evaluate_prediction_interval_quality,
    AdaptiveConformalInference,
    compute_calibrated_quantiles
)


class TestAdaptiveConformal(unittest.TestCase):
    def test_adaptive_conformal_updates_on_misses(self):
        aci = AdaptiveConformalInference(target_alpha=0.05, gamma=0.02, initial_alpha=0.05)

        # Simulation 1: Hits (actual inside interval) -> alpha should increase (narrow interval)
        for _ in range(5):
            new_alpha = aci.update(y_true=3.0, lower_bound=2.8, upper_bound=3.2)
        self.assertGreater(new_alpha, 0.05)

        # Simulation 2: Misses (actual outside interval) -> alpha should decrease (widen interval)
        for _ in range(10):
            new_alpha = aci.update(y_true=3.5, lower_bound=2.8, upper_bound=3.2)
        self.assertLess(new_alpha, 0.05)

    def test_adaptive_conformal_bounds_computation(self):
        aci = AdaptiveConformalInference(target_alpha=0.05)
        resids = np.random.normal(0, 0.05, 60)
        low, high = aci.compute_interval(3.50, resids)
        self.assertLess(float(np.asarray(low).flat[0]), 3.50)
        self.assertGreater(float(np.asarray(high).flat[0]), 3.50)

    def test_compute_calibrated_quantiles(self):
        y_pred = 3.25
        resids = np.random.normal(0, 0.06, 50)
        quantiles = compute_calibrated_quantiles(y_pred, resids, quantiles=[0.10, 0.50, 0.90])

        self.assertIn(0.10, quantiles)
        self.assertIn(0.50, quantiles)
        self.assertIn(0.90, quantiles)

        # Quantile ordering: P10 <= P50 <= P90
        p10 = float(np.asarray(quantiles[0.10]).flat[0])
        p50 = float(np.asarray(quantiles[0.50]).flat[0])
        p90 = float(np.asarray(quantiles[0.90]).flat[0])
        self.assertLess(p10, p50)
        self.assertLess(p50, p90)


if __name__ == "__main__":
    unittest.main()
