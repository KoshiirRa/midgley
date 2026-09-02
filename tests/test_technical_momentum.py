"""
Unit tests for Technical Momentum Indicators for RBOB & WTI Futures (Issue #92).
Verifies:
1. compute_technical_momentum_indicators calculates RSI-14, MACD, Bollinger %B, and ATR-14 without nulls.
2. create_feature_matrix includes technical momentum feature columns in feature matrices and chronological splits.
"""

import unittest
from src.data_ingestion import _generate_synthetic_market_data
from src.feature_engineering import compute_technical_momentum_indicators, create_feature_matrix, prepare_chronological_splits

class TestTechnicalMomentum(unittest.TestCase):

    def setUp(self):
        self.market_df = _generate_synthetic_market_data('2026-01-01', '2026-03-30')

    def test_compute_technical_momentum_indicators(self):
        """Verify compute_technical_momentum_indicators adds technical columns without NaN values."""
        df_tech = compute_technical_momentum_indicators(self.market_df)
        
        self.assertIn("rbob_rsi_14", df_tech.columns)
        self.assertIn("rbob_macd_line", df_tech.columns)
        self.assertIn("rbob_macd_signal", df_tech.columns)
        self.assertIn("rbob_bollinger_band_pct_b", df_tech.columns)
        self.assertIn("rbob_atr_14", df_tech.columns)
        
        self.assertEqual(df_tech["rbob_rsi_14"].isna().sum(), 0)
        self.assertEqual(df_tech["rbob_macd_line"].isna().sum(), 0)

    def test_feature_matrix_technical_columns(self):
        """Verify create_feature_matrix merges technical momentum columns into chronological splits."""
        feature_df = create_feature_matrix(self.market_df, forecast_horizon=5)
        
        self.assertIn("rbob_rsi_14", feature_df.columns)
        self.assertIn("rbob_atr_14", feature_df.columns)
        
        splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
        self.assertIn("rbob_rsi_14", splits["quant_feature_names"])
        self.assertIn("rbob_macd_line", splits["quant_feature_names"])

if __name__ == '__main__':
    unittest.main()
