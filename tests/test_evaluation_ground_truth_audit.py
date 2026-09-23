"""Unit tests for Evaluation Ground Truth Audit (Issue #352).

Verifies that evaluation routines strictly distinguish observed retail ground truth
from proxy reconstructions and eliminate retrospective margin application:
1. Ground truth for regional predictions comes strictly from EIARetailFeed (official weekly EIA series).
2. Zero retrospective static margin addition (e.g., wholesale + $0.55 or +$0.425).
3. Missing dates remain un-evaluated (NaN) rather than filled with synthetic proxy values.
4. Data source provenance correctly records official EIA series identifiers.
"""

import numpy as np
import pandas as pd
import pytest

from src.eia_retail_feed import EIARetailFeed
from src.prediction_logger import (
    backfill_actual_prices_and_evaluate,
    validate_price_plausibility,
)


class MockEIARetailFeed:
    """Mock EIA Retail Feed supplying distinct state and PADD price series."""
    def __init__(self):
        self.prices = {
            ("National", "2024-05-06"): 3.65,
            ("Tulsa_OK", "2024-05-06"): 3.12,
            ("Newark_DE", "2024-05-06"): 3.58,
            ("Cincinnati_OH", "2024-05-06"): 3.45,
            ("Oakland_CA", "2024-05-06"): 5.15,
        }

    def get_retail_price_for_date(self, region: str, date_str: str):
        return self.prices.get((region, date_str), None)


def test_no_synthetic_margin_in_regional_evaluation(tmp_path):
    """Ensure regional actuals match official EIA ground truth without synthetic margin shifts."""
    test_csv = tmp_path / "test_prediction_history.csv"
    
    # Create test prediction history with unevaluated rows
    df = pd.DataFrame([
        {
            "log_timestamp": "2024-05-01 08:00:00",
            "forecast_target_date": "2024-05-06",
            "forecast_horizon_days": 5,
            "region": "Tulsa_OK",
            "model_version": "v1.7.0-Boudouard",
            "run_type": "PRODUCTION_LIVE",
            "headline_trigger": "None",
            "current_base_price": 3.05,
            "predicted_5d_price": 3.10,
            "predicted_direction": "UP",
            "actual_5d_price": np.nan,
            "actual_direction": np.nan,
            "error_dollars": np.nan,
            "directional_hit": np.nan,
            "prediction_lower_95ci": 2.95,
            "prediction_upper_95ci": 3.25,
        },
        {
            "log_timestamp": "2024-05-01 08:00:00",
            "forecast_target_date": "2024-05-06",
            "forecast_horizon_days": 5,
            "region": "Oakland_CA",
            "model_version": "v1.7.0-Boudouard",
            "run_type": "PRODUCTION_LIVE",
            "headline_trigger": "None",
            "current_base_price": 5.05,
            "predicted_5d_price": 5.20,
            "predicted_direction": "UP",
            "actual_5d_price": np.nan,
            "actual_direction": np.nan,
            "error_dollars": np.nan,
            "directional_hit": np.nan,
            "prediction_lower_95ci": 4.90,
            "prediction_upper_95ci": 5.40,
        }
    ])
    df.to_csv(test_csv, index=False)

    mock_eia = MockEIARetailFeed()
    evaluated_df = backfill_actual_prices_and_evaluate(
        csv_path=str(test_csv),
        eia_feed_override=mock_eia,
        force_eval=True,
    )

    tulsa_row = evaluated_df[evaluated_df["region"] == "Tulsa_OK"].iloc[0]
    oakland_row = evaluated_df[evaluated_df["region"] == "Oakland_CA"].iloc[0]

    # Verify exact match with EIA ground truth
    assert tulsa_row["actual_5d_price"] == 3.12
    assert tulsa_row["directional_hit"] == 1
    assert tulsa_row["data_source_provenance"] == "eia_retail_feed:Tulsa_OK"

    assert oakland_row["actual_5d_price"] == 5.15
    assert oakland_row["directional_hit"] == 1
    assert oakland_row["data_source_provenance"] == "eia_retail_feed:Oakland_CA"


def test_missing_date_remains_unevaluated_nan(tmp_path):
    """Ensure dates without official EIA observations remain NaN rather than filled with fallback proxies."""
    test_csv = tmp_path / "test_prediction_history.csv"
    
    df = pd.DataFrame([
        {
            "log_timestamp": "2024-05-01 08:00:00",
            "forecast_target_date": "2024-05-15",  # Not in mock EIA feed
            "forecast_horizon_days": 5,
            "region": "Tulsa_OK",
            "model_version": "v1.7.0-Boudouard",
            "run_type": "PRODUCTION_LIVE",
            "headline_trigger": "None",
            "current_base_price": 3.05,
            "predicted_5d_price": 3.10,
            "predicted_direction": "UP",
            "actual_5d_price": np.nan,
            "actual_direction": np.nan,
            "error_dollars": np.nan,
            "directional_hit": np.nan,
            "prediction_lower_95ci": 2.95,
            "prediction_upper_95ci": 3.25,
        }
    ])
    df.to_csv(test_csv, index=False)

    mock_eia = MockEIARetailFeed()
    evaluated_df = backfill_actual_prices_and_evaluate(
        csv_path=str(test_csv),
        eia_feed_override=mock_eia,
        force_eval=True,
    )

    row = evaluated_df.iloc[0]
    assert pd.isna(row["actual_5d_price"])
    assert pd.isna(row["directional_hit"])
    assert pd.isna(row["error_dollars"])


def test_validate_price_plausibility_bounds():
    """Test price plausibility filters for retail and wholesale boundaries."""
    # Plausible retail prices
    assert validate_price_plausibility(3.25, "Tulsa_OK", is_retail=True)
    assert validate_price_plausibility(5.80, "Oakland_CA", is_retail=True)

    # Implausible retail prices
    assert not validate_price_plausibility(0.45, "Tulsa_OK", is_retail=True)
    assert not validate_price_plausibility(15.0, "Oakland_CA", is_retail=True)
    assert not validate_price_plausibility(None, "National", is_retail=True)
    assert not validate_price_plausibility(np.nan, "National", is_retail=True)

    # Plausible wholesale prices (RBOB spot)
    assert validate_price_plausibility(2.15, "National", is_retail=False)
    assert not validate_price_plausibility(0.20, "National", is_retail=False)
    assert not validate_price_plausibility(9.50, "National", is_retail=False)
