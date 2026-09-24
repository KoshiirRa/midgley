"""
Global Pytest Fixtures and Sandbox Isolation (tests/conftest.py)
Issue #427: Prevents test artifact pollution in data/prediction_history.csv, docs/, and reports/.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """
    Global autouse fixture that isolates prediction history CSV, test caches,
    and output directories to pytest tmp_path to prevent production ledger pollution.
    """
    monkeypatch.setenv("TESTING", "1")
    
    # 1. Isolate prediction logger HISTORY_CSV_PATH
    test_csv = tmp_path / "prediction_history.csv"
    try:
        import src.prediction_logger as pred_logger
        monkeypatch.setattr(pred_logger, "HISTORY_CSV_PATH", str(test_csv))
    except ImportError:
        pass

    yield tmp_path
