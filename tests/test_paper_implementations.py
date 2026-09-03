"""
Unit tests for implemented research paper algorithms (Issue #142):
- Paper 2608.25128v1 (Context Routing Diagnostic & RBU Theorem)
- Paper 2608.25871v1 (CEDAR Two-Stage Residual Decomposition)
"""

import unittest
import pandas as pd
import numpy as np
from src.feature_engineering import compute_context_routing_diagnostic, create_feature_matrix
from src.event_analyzer import extract_event_residual_cedar_two_stage
from src.models import predict_with_cedar_residual_decomposition

class TestPaperImplementations(unittest.TestCase):
    
    def setUp(self):
        dates = pd.date_range('2026-01-01', periods=30, freq='B')
        prices = 2.50 + np.cumsum(np.random.normal(0, 0.02, 30))
        self.market_df = pd.DataFrame({
            'date': dates,
            'gasoline_rbob': prices,
            'wti_crude': prices * 30
        })
        
    def test_context_routing_diagnostic_high_autocorrelation(self):
        # Create perfectly persistent sticky prices (rho_h ~ 1.0)
        df_sticky = self.market_df.copy()
        diag = compute_context_routing_diagnostic(df_sticky, target_col='gasoline_rbob', horizon=5, threshold=0.95)
        
        self.assertIn('rho_h', diag)
        self.assertIn('recommendation', diag)
        self.assertIn(diag['recommendation'], ['SKIP_FUSION', 'TRY_FUSION'])
        self.assertGreaterEqual(diag['rbu_bound'], 0.0)
        
    def test_cedar_two_stage_residual_extraction(self):
        headlines = [
            "Refinery explosion in West Tulsa causes production halt",
            "OPEC announces surprise voluntary output cuts of 1M bpd"
        ]
        result = extract_event_residual_cedar_two_stage(headlines, regional_context="Tulsa_OK")
        
        self.assertIn('residual_delta_gal', result)
        self.assertIn('extracted_tags', result)
        self.assertIn('market_summary', result)
        self.assertIsInstance(result['residual_delta_gal'], float)
        self.assertGreater(len(result['extracted_tags']), 0)
        self.assertIn('refinery', result['extracted_tags'])
        
    def test_cedar_prediction_formula(self):
        class DummyModel:
            def predict(self, X):
                return np.array([3.50, 3.55])
                
        model = DummyModel()
        X_test = pd.DataFrame({'a': [1, 2]})
        residual_delta = 0.125
        
        preds = predict_with_cedar_residual_decomposition(model, X_test, residual_event_delta=residual_delta)
        np.testing.assert_array_almost_equal(preds, np.array([3.625, 3.675]))


if __name__ == '__main__':
    unittest.main()
