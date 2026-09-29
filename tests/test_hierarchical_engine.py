"""
Unit Tests for MinT Hierarchical Reconciliation Engine & Empirical Bayes Shrinkage (Issue #450).
"""

import unittest
import numpy as np
from src.hierarchical_engine import (
    build_aggregation_matrix,
    reconcile_mint,
    empirical_bayes_shrinkage_regression,
    MinTHierarchicalEngine,
    BOTTOM_LEVEL_METROS,
    PADD_CLUSTERS
)


class TestHierarchicalEngine(unittest.TestCase):
    def test_aggregation_matrix_structure(self):
        S, node_names = build_aggregation_matrix()
        m = len(BOTTOM_LEVEL_METROS)
        k = len(PADD_CLUSTERS)
        n = 1 + k + m

        self.assertEqual(S.shape, (n, m))
        self.assertEqual(len(node_names), n)
        self.assertEqual(node_names[0], "National")
        self.assertIn("PADD_1B", node_names)
        self.assertIn("Tulsa_OK", node_names)

        # Bottom rows should be identity matrix
        bottom_block = S[1 + k:, :]
        np.testing.assert_array_almost_equal(bottom_block, np.eye(m))

    def test_mint_reconciliation_exact_coherence(self):
        engine = MinTHierarchicalEngine()

        # Incoherent synthetic base forecasts
        base_forecasts = {
            "National": 3.45,
            "PADD_1B": 3.70,
            "PADD_1C": 3.35,
            "PADD_2": 3.20,
            "PADD_5": 5.10,
            "Tulsa_OK": 3.10,
            "Newark_DE": 3.75,
            "Cincinnati_OH": 3.25,
            "Cincinnati_KY": 3.15,
            "Greenville_NC": 3.30,
            "Charlotte_NC": 3.38,
            "Port_St_Lucie_FL": 3.42,
            "Oakland_CA": 5.15,
            "BayArea_CA": 5.18
        }

        reconciled = engine.reconcile_forecast_dict(base_forecasts)

        # Check that reconciled forecasts satisfy exact aggregation constraints S * b_tilde = y_tilde
        # 1. PADD_5 == average of Oakland and BayArea
        padd5_calc = (reconciled["Oakland_CA"] + reconciled["BayArea_CA"]) / 2.0
        self.assertAlmostEqual(reconciled["PADD_5"], padd5_calc, places=3)

        # 2. PADD_2 == average of Tulsa, Cincinnati_OH, Cincinnati_KY
        padd2_calc = (reconciled["Tulsa_OK"] + reconciled["Cincinnati_OH"] + reconciled["Cincinnati_KY"]) / 3.0
        self.assertAlmostEqual(reconciled["PADD_2"], padd2_calc, places=3)

    def test_empirical_bayes_shrinkage_regression(self):
        np.random.seed(42)
        n, p = 25, 4
        X = np.random.normal(0, 1.0, (n, p))
        theta_true = np.array([1.5, -0.8, 0.4, 0.0])
        y = X @ theta_true + np.random.normal(0, 0.1, n)

        theta_prior = np.array([1.0, -0.5, 0.0, 0.0])
        theta_eb = empirical_bayes_shrinkage_regression(X, y, prior_weights=theta_prior, shrinkage_strength=0.20)

        self.assertEqual(len(theta_eb), p)
        # Should be between OLS and prior
        self.assertGreater(theta_eb[0], 0.8)
        self.assertLess(theta_eb[1], -0.4)


if __name__ == "__main__":
    unittest.main()
