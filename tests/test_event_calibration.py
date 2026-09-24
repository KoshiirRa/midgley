"""
Unit Test Suite for Empirical Event Econometric Calibration & Decoupled PRAXIST (tests/test_event_calibration.py)
Tests EventEconometricCalibrator, decay half-life optimization, and decoupled PRAXIST benchmark. (Issue #361)
"""

import pytest
import pandas as pd
from src.event_calibration import EventEconometricCalibrator
from src.praxist_engine import PRAXISTResearchEngine


def test_event_econometric_calibrator_loading():
    calibrator = EventEconometricCalibrator()
    events_df = calibrator.load_historical_events()
    assert not events_df.empty
    assert len(events_df) >= 5
    assert "event_id" in events_df.columns
    assert "category" in events_df.columns
    assert "shock_score" in events_df.columns
    assert "realized_5d_return" in events_df.columns


def test_event_decay_half_life_calibration():
    calibrator = EventEconometricCalibrator()
    params = calibrator.calibrate_category_parameters()
    assert isinstance(params, dict)
    assert "supply_disruption" in params
    assert "geopolitical_risk" in params
    assert "opec_action" in params

    # Check realistic physical half-life bounds (between 1 and 30 days)
    for cat, p in params.items():
        assert 1.0 <= p["half_life_days"] <= 30.0
        assert 0.01 <= p["impact_weight_beta"] <= 0.30

    half_lives_dict = calibrator.get_calibrated_half_lives_dict()
    assert isinstance(half_lives_dict, dict)
    assert half_lives_dict["supply_disruption"] > 0.0


def test_decoupled_praxist_historical_evaluation():
    praxist = PRAXISTResearchEngine()
    candidate_params = {
        "half_life_days": 4.8,
        "geopolitical_weight": 0.38,
        "supply_disruption_weight": 0.42,
        "opec_action_weight": 0.20,
        "weekend_gap_multiplier": 1.45
    }
    res = praxist.evaluate_hypothesis(
        hypothesis_name="Test_Decoupled_Historical_Decay",
        candidate_params=candidate_params,
        use_synthetic_benchmark=False
    )
    assert res is not None
    assert "mae_delta" in res
    assert "directional_accuracy_delta" in res
    assert "status" in res
    assert res["status"] in ["ACCEPTED", "REJECTED", "INCONCLUSIVE"]
