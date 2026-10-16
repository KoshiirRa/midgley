"""
Unit Tests for Statistical Evaluation Harness, Model Confidence Set & Feature Admission Gate (Issue #452).
"""

import unittest
import numpy as np
import pandas as pd
from src.model_evaluation import (
    pesaran_timmermann_test,
    compute_newey_west_hac_standard_error,
    model_confidence_set,
    benjamini_hochberg_fdr_control,
    FeatureAdmissionGate
)


class TestStatisticalEvaluation(unittest.TestCase):
    def test_pesaran_timmermann_directional_hit_rate(self):
        # Perfect directional accuracy
        np.random.seed(42)
        y_true_ret = np.random.normal(0, 0.02, 50)
        y_pred_ret = y_true_ret.copy()

        res = pesaran_timmermann_test(y_true_ret, y_pred_ret)
        self.assertEqual(res["hit_rate_pct"], 100.0)
        self.assertGreater(res["pt_stat"], 5.0)
        self.assertLess(res["p_value"], 0.001)
        self.assertTrue(res["is_significant_at_05"])

        # Random chance directional accuracy
        y_rand = np.random.normal(0, 0.02, 100)
        res_rand = pesaran_timmermann_test(y_true_ret[:20], y_rand[:20])
        self.assertGreaterEqual(res_rand["p_value"], 0.0)

    def test_newey_west_hac_standard_error(self):
        # Autocorrelated AR(1) residuals
        np.random.seed(42)
        e = [np.random.normal(0, 1.0)]
        for _ in range(100):
            e.append(0.7 * e[-1] + np.random.normal(0, 0.5))
        e = np.array(e)

        se_1d = compute_newey_west_hac_standard_error(e, horizon=1)
        se_5d = compute_newey_west_hac_standard_error(e, horizon=5)

        self.assertGreater(se_1d, 0.0)
        self.assertGreater(se_5d, 0.0)
        self.assertGreaterEqual(se_5d, se_1d * 0.9)  # Higher lag bandwidth accounts for persistence

    def test_model_confidence_set(self):
        np.random.seed(42)
        T = 100
        # Model A: Mean loss 0.10
        loss_A = np.random.normal(0.10, 0.02, T)
        # Model B: Mean loss 0.11 (close)
        loss_B = np.random.normal(0.11, 0.02, T)
        # Model C: Mean loss 0.50 (clearly inferior)
        loss_C = np.random.normal(0.50, 0.05, T)

        loss_mat = np.column_stack([loss_A, loss_B, loss_C])
        names = ["Model_A", "Model_B", "Model_C"]

        mcs_res = model_confidence_set(loss_mat, names, alpha=0.10, n_bootstraps=200)
        self.assertIn("Model_A", mcs_res["included_models"])
        self.assertIn("Model_C", mcs_res["eliminated_models"])
        self.assertLess(mcs_res["mcs_pvalues"]["Model_C"], 0.10)

    def test_benjamini_hochberg_fdr_control(self):
        p_vals = {
            "Tulsa_OK": 0.001,
            "Newark_DE": 0.008,
            "Cincinnati_OH": 0.040,
            "Greenville_NC": 0.250,
            "Oakland_CA": 0.850
        }
        fdr_res = benjamini_hochberg_fdr_control(p_vals, q_threshold=0.05)
        self.assertIn("Tulsa_OK", fdr_res["discoveries"])
        self.assertIn("Newark_DE", fdr_res["discoveries"])
        self.assertNotIn("Oakland_CA", fdr_res["discoveries"])

    def test_feature_admission_gate(self):
        gate = FeatureAdmissionGate(mcs_alpha=0.10, fdr_q=0.05)
        np.random.seed(42)
        T = 80
        base_losses = np.random.normal(0.20, 0.03, T)
        # Superior candidate feature reduces loss
        good_cand_losses = base_losses - np.random.uniform(0.02, 0.05, T)
        # Bad candidate feature increases loss
        bad_cand_losses = base_losses + np.random.uniform(0.05, 0.10, T)

        good_res = gate.evaluate_candidate_feature_family(base_losses, good_cand_losses, "good_feature")
        self.assertTrue(good_res["admitted_to_production"])
        self.assertEqual(good_res["decision"], "ADMITTED")

        bad_res = gate.evaluate_candidate_feature_family(base_losses, bad_cand_losses, "bad_feature")
        self.assertFalse(bad_res["admitted_to_production"])
        self.assertEqual(bad_res["decision"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
