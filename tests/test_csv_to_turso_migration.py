"""
Unit tests for CSV to Database migration and deduplication (scripts/migrate_csv_to_turso.py).
"""

import os
import tempfile
import pandas as pd
import pytest
from src.db.client import DatabaseClient
from scripts.migrate_csv_to_turso import migrate_csv_to_database, generate_deterministic_forecast_id


def test_deterministic_forecast_id():
    """Verifies that identical forecast parameters yield identical deterministic hashes."""
    id1 = generate_deterministic_forecast_id("National", "v1.6-Ridge", "2026-09-29", 5, "LIVE_PROSPECTIVE")
    id2 = generate_deterministic_forecast_id("National", "v1.6-Ridge", "2026-09-29", 5, "LIVE_PROSPECTIVE")
    id3 = generate_deterministic_forecast_id("Tulsa_OK", "v1.6-Ridge", "2026-09-29", 5, "LIVE_PROSPECTIVE")

    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 32


def test_migration_deduplication(tmp_path):
    """Verifies that duplicate CSV rows are collapsed into unique forecast records."""
    sample_rows = []
    # 5 identical duplicate backtest runs for the same forecast
    for i in range(5):
        sample_rows.append({
            "region": "National",
            "model_version": "v1.6-Ridge",
            "forecast_target_date": "2026-10-05",
            "forecast_horizon_days": 5,
            "run_type": "RETROSPECTIVE_BACKTEST",
            "predicted_5d_price": 2.4500,
            "prediction_lower_95ci": 2.3800,
            "prediction_upper_95ci": 2.5200,
            "actual_5d_price": 2.4600,
            "error_dollars": 0.0100,
            "within_95ci_hit": 1.0,
            "directional_hit": 1.0,
            "log_timestamp": f"2026-09-2{i} 12:00:00"
        })

    df = pd.DataFrame(sample_rows)
    csv_path = str(tmp_path / "test_dedup.csv")
    db_path = str(tmp_path / "test_dedup.db")

    df.to_csv(csv_path, index=False)
    db = DatabaseClient(sqlite_path=db_path)

    res = migrate_csv_to_database(csv_path, db=db)
    assert res["status"] == "SUCCESS"
    assert res["raw_csv_rows"] == 5
    assert res["unique_forecasts"] == 1
    assert res["duplicates_removed"] == 4

    # Check DB rows
    forecasts = db.execute("SELECT * FROM forecasts;")
    assert len(forecasts) == 1
    evals = db.execute("SELECT * FROM evaluations;")
    assert len(evals) == 1
