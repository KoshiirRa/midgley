"""
Unit tests for DatabaseClient and schema initialization (src/db/client.py).
"""

import os
import tempfile
import pytest
from src.db.client import DatabaseClient


@pytest.fixture
def temp_db():
    """Creates an isolated temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    client = DatabaseClient(sqlite_path=db_path)
    yield client
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_db_schema_initialization(temp_db):
    """Verifies that all normalized tables are created upon initialization."""
    tables = temp_db.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = {t["name"] for t in tables}
    
    expected_tables = {
        "forecasts",
        "intraday_revisions",
        "intraday_events",
        "evaluated_headlines",
        "data_vintages",
        "ground_truth",
        "evaluations",
        "sync_watermarks"
    }
    for tbl in expected_tables:
        assert tbl in table_names, f"Expected table {tbl} was not created"


def test_forecast_insert_and_query(temp_db):
    """Verifies forecast insert, idempotent upsert, and query."""
    sql = """
    INSERT INTO forecasts (
        forecast_id, region, model_version, origin_date, horizon, target_date,
        predicted_price, ci_lower_95, ci_upper_95, run_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    temp_db.execute(sql, (
        "test_f_001", "National", "v1.6-Ridge", "2026-09-29", 5, "2026-10-06",
        2.4500, 2.3800, 2.5200, "LIVE_PROSPECTIVE"
    ))

    rows = temp_db.execute("SELECT * FROM forecasts WHERE forecast_id = ?;", ("test_f_001",))
    assert len(rows) == 1
    assert rows[0]["region"] == "National"
    assert rows[0]["predicted_price"] == 2.4500

    # Idempotent upsert
    upsert_sql = """
    INSERT INTO forecasts (
        forecast_id, region, model_version, origin_date, horizon, target_date,
        predicted_price, ci_lower_95, ci_upper_95, run_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(forecast_id) DO UPDATE SET predicted_price = excluded.predicted_price;
    """
    temp_db.execute(upsert_sql, (
        "test_f_001", "National", "v1.6-Ridge", "2026-09-29", 5, "2026-10-06",
        2.4650, 2.3800, 2.5200, "LIVE_PROSPECTIVE"
    ))
    updated_rows = temp_db.execute("SELECT * FROM forecasts WHERE forecast_id = ?;", ("test_f_001",))
    assert len(updated_rows) == 1
    assert updated_rows[0]["predicted_price"] == 2.4650


def test_turso_circuit_breaker_fallback_initializes_sqlite():
    """Verifies that tripping circuit breaker to local SQLite initializes schema and succeeds (Issue #614 T-34)."""
    from unittest.mock import patch
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Client initialized with fake Turso URL
        client = DatabaseClient(db_url="https://mock-turso.turso.io", auth_token="mock_token", sqlite_path=db_path)
        client.is_turso = True

        with patch("urllib.request.urlopen", side_effect=Exception("503 Service Unavailable")):
            res = client.execute("SELECT * FROM forecasts;")
            assert res == []
            assert client.is_turso is False

            # Verify write succeeds on fallen-back local SQLite without "no such table" errors
            client.execute("""
                INSERT INTO forecasts (forecast_id, region, model_version, origin_date, horizon, target_date, predicted_price, ci_lower_95, ci_upper_95, run_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, ("fb_001", "National", "v1.0", "2026-10-01", 1, "2026-10-02", 2.5, 2.4, 2.6, "TEST"))
            rows = client.execute("SELECT * FROM forecasts WHERE forecast_id = 'fb_001';")
            assert len(rows) == 1
            assert rows[0]["forecast_id"] == "fb_001"
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

