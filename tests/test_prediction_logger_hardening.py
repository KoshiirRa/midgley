"""
Unit Tests for Prediction Logger Hardening & Ground Truth Integrity (tests/test_prediction_logger_hardening.py)
Covers Issues #391, #392, #399.
"""

import os
import json
import tempfile
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from src.prediction_logger import (
    validate_price_plausibility,
    cleanse_prediction_history,
    backfill_actual_prices_and_evaluate,
    RBOB_ACTUALS_CACHE_FILE
)


class TestPredictionLoggerHardening:
    """Test suite validating MLOps ground-truth integrity and prediction ledger hardening."""

    def test_validate_price_plausibility(self):
        # Valid retail prices
        assert validate_price_plausibility(3.45, "Tulsa_OK", is_retail=True) is True
        assert validate_price_plausibility(5.25, "Oakland_CA", is_retail=True) is True
        assert validate_price_plausibility(1.00, "Charlotte_NC", is_retail=True) is True
        assert validate_price_plausibility(10.00, "BayArea_CA", is_retail=True) is True

        # Invalid retail prices (below $1.00 or above $10.00)
        assert validate_price_plausibility(0.75, "Tulsa_OK", is_retail=True) is False
        assert validate_price_plausibility(12.50, "Oakland_CA", is_retail=True) is False
        assert validate_price_plausibility(-1.50, "Cincinnati_OH", is_retail=True) is False

        # Valid wholesale futures prices
        assert validate_price_plausibility(2.45, "National", is_retail=False) is True
        assert validate_price_plausibility(0.50, "National", is_retail=False) is True
        assert validate_price_plausibility(6.80, "National", is_retail=False) is True

        # Invalid wholesale prices
        assert validate_price_plausibility(0.20, "National", is_retail=False) is False
        assert validate_price_plausibility(8.50, "National", is_retail=False) is False

        # Non-numeric / NaN / None values
        assert validate_price_plausibility(None) is False
        assert validate_price_plausibility(np.nan) is False
        assert validate_price_plausibility(float('inf')) is False

    def test_cleanse_prediction_history(self):
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            df = pd.DataFrame([
                {'log_timestamp': '2026-09-01T12:00:00', 'forecast_target_date': '2026-09-06', 'region': 'Tulsa_OK', 'current_base_price': 3.45, 'predicted_5d_price': 3.50},
                {'log_timestamp': '2026-09-01T12:00:00', 'forecast_target_date': '2026-09-06', 'region': 'Test_Region', 'current_base_price': 2.45, 'predicted_5d_price': 2.50},
                {'log_timestamp': '2026-09-01T12:00:00', 'forecast_target_date': '2026-09-06', 'region': 'Oakland_CA', 'current_base_price': 5.15, 'predicted_5d_price': 5.20},
                {'log_timestamp': '2026-09-01T12:00:00', 'forecast_target_date': '2026-09-06', 'region': 'Newark_DE', 'current_base_price': np.nan, 'predicted_5d_price': 3.80},
            ])
            df.to_csv(temp_path, index=False)

            purged = cleanse_prediction_history(temp_path)
            assert purged == 2  # 1 Test_Region row + 1 NaN base price row

            cleansed_df = pd.read_csv(temp_path)
            assert len(cleansed_df) == 2
            assert set(cleansed_df['region'].tolist()) == {'Tulsa_OK', 'Oakland_CA'}
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_unmapped_hub_no_forced_up_direction(self):
        """Validates that unmapped regional hubs do NOT trigger synthetic base_price offset fallback (Issue #392)."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            df = pd.DataFrame([ {
                'log_timestamp': '2026-09-01T12:00:00',
                'forecast_target_date': '2026-09-06',
                'region': 'Atlantis_Undersea',
                'model_version': 'v0.7.0',
                'run_type': 'automated_cron',
                'current_base_price': 4.50,
                'predicted_5d_price': 4.20,
                'predicted_direction': 'DOWN',
                'actual_5d_price': np.nan,
                'actual_direction': np.nan,
                'error_dollars': np.nan,
                'directional_hit': np.nan,
                'within_95ci_hit': np.nan,
                'data_source_provenance': 'unmapped'
            } ])
            df.to_csv(temp_path, index=False)

            with patch('src.prediction_logger.HISTORY_CSV_PATH', temp_path), \
                 patch.dict(os.environ, {'TESTING': '0', 'TEST_YFINANCE_FORCE': '1'}):
                
                mock_eia = MagicMock()
                mock_eia.get_retail_price_for_date.return_value = None

                with patch('src.eia_retail_feed.EIARetailFeed', return_value=mock_eia), \
                     patch('src.prediction_logger._GLOBAL_RBOB_ACTUALS_CACHE', {'2026-09-06': 2.45}):
                    
                    res_df = backfill_actual_prices_and_evaluate()
                    row = res_df.iloc[0]
                    assert pd.isna(row['actual_5d_price']) or row['actual_5d_price'] is None
                    assert pd.isna(row['directional_hit']) or row['directional_hit'] is None
                    assert str(row['actual_direction']) != 'UP'
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_regional_ground_truth_uses_eia_retail_feed(self):
        """Validates that regional actuals are sourced from EIARetailFeed and not synthetic +0.55 ladder (Issue #391)."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            df = pd.DataFrame([ {
                'log_timestamp': '2026-09-01T12:00:00',
                'forecast_target_date': '2026-09-06',
                'region': 'Tulsa_OK',
                'model_version': 'v0.7.0',
                'run_type': 'automated_cron',
                'current_base_price': 3.40,
                'predicted_5d_price': 3.55,
                'predicted_direction': 'UP',
                'actual_5d_price': np.nan,
                'actual_direction': np.nan,
                'error_dollars': np.nan,
                'directional_hit': np.nan,
                'within_95ci_hit': np.nan,
                'data_source_provenance': 'eia_retail_feed'
            } ])
            df.to_csv(temp_path, index=False)

            with patch('src.prediction_logger.HISTORY_CSV_PATH', temp_path), \
                 patch.dict(os.environ, {'TESTING': '0', 'TEST_YFINANCE_FORCE': '1'}):
                
                mock_eia = MagicMock()
                mock_eia.get_retail_price_for_date.return_value = 3.6200

                with patch('src.eia_retail_feed.EIARetailFeed', return_value=mock_eia), \
                     patch('src.prediction_logger._GLOBAL_RBOB_ACTUALS_CACHE', {'2026-09-06': 2.40}):
                    
                    res_df = backfill_actual_prices_and_evaluate()
                    row = res_df.iloc[0]
                    assert row['actual_5d_price'] == 3.6200
                    assert row['actual_direction']== 'UP'
                    assert row['directional_hit']== 1
                    assert abs(row['error_dollars'] - 0.07) < 1e-4
                    assert row['data_source_provenance'] == 'eia_retail_feed:Tulsa_OK'
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
