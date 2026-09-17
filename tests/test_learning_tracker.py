"""
Unit Tests for Model Learning & Adaptation Tracker (tests/test_learning_tracker.py)
"""

import os
import json
import sqlite3
import pytest
import numpy as np
import pandas as pd

from src.learning_tracker import (
    load_prediction_dataset,
    calculate_longitudinal_learning_curves,
    get_multi_window_performance_summary,
    get_praxist_learning_timeline,
    get_episodic_reflections_summary,
    generate_learning_journal_markdown,
    generate_learning_telemetry_html_snippet,
)


@pytest.fixture
def sample_prediction_df():
    """Generates synthetic prediction history for unit tests."""
    np.random.seed(42)
    n = 60
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="D")
    base_prices = 3.50 + np.cumsum(np.random.normal(0, 0.02, n))
    actual_prices = base_prices + np.random.normal(0.01, 0.03, n)
    predicted_prices = base_prices + np.random.normal(0.005, 0.02, n)
    quant_prices = base_prices + np.random.normal(0.01, 0.04, n)
    hits = (np.sign(predicted_prices - base_prices) == np.sign(actual_prices - base_prices)).astype(int)

    return pd.DataFrame({
        "log_timestamp": [d.strftime("%Y-%m-%d %H:%M:%S") for d in dates],
        "forecast_target_date": [d.strftime("%Y-%m-%d") for d in dates],
        "region": ["Tulsa_OK" if i % 2 == 0 else "National" for i in range(n)],
        "current_base_price": base_prices,
        "predicted_5d_price": predicted_prices,
        "actual_5d_price": actual_prices,
        "quant_baseline_5d_price": quant_prices,
        "directional_hit": hits
    })


@pytest.fixture
def temp_praxist_file(tmp_path):
    """Creates a temporary praxist experiments ledger."""
    file_path = str(tmp_path / "praxist_experiments.json")
    data = {
        "version": "1.0",
        "total_hypotheses_tested": 2,
        "accepted_hypotheses": 1,
        "experiments": [
            {
                "hypothesis_name": "Decay_4.5d_Test",
                "evaluated_at": "2026-09-10T12:00:00",
                "candidate_params": {"half_life_days": 4.5, "weekend_gap_multiplier": 1.42},
                "baseline_mae": 0.0331,
                "candidate_mae": 0.0320,
                "mae_delta": -0.0011,
                "t_statistic": 2.45,
                "p_value": 0.02,
                "status": "ACCEPTED"
            }
        ]
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def temp_sqlite_db(tmp_path):
    """Creates a temporary agent memory SQLite database."""
    db_path = str(tmp_path / "test_memory.sqlite")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE memories (
            id INTEGER PRIMARY KEY,
            memory_id TEXT,
            region TEXT,
            content TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE reflections (
            id INTEGER PRIMARY KEY,
            reflection_id TEXT,
            region TEXT,
            anomaly_type TEXT,
            title TEXT,
            root_cause TEXT,
            historical_analogy TEXT,
            calibration_suggestion TEXT,
            created_at TEXT
        )
    """)
    c.execute("INSERT INTO memories VALUES (1, 'm1', 'Tulsa_OK', 'Memory content', '2026-09-10')")
    c.execute("""
        INSERT INTO reflections VALUES (
            1, 'r1', 'Tulsa_OK', 'SEASONAL_TRANSITION',
            'Tulsa Season Switch Outlier',
            'Winter RVP transition caused prompt refinery blend change.',
            'Similar to 2024 Tulsa seasonal turnaround.',
            'Adjust seasonal RVP calendar weight.',
            '2026-09-10T12:00:00'
        )
    """)
    conn.commit()
    conn.close()
    return db_path


def test_calculate_longitudinal_learning_curves(sample_prediction_df):
    curves = calculate_longitudinal_learning_curves(df=sample_prediction_df, window_days=14, step_days=2)
    assert "dates" in curves
    assert "model_mae" in curves
    assert "naive_mae" in curves
    assert "uplift_pct" in curves
    assert len(curves["dates"]) > 0
    assert len(curves["model_mae"]) == len(curves["dates"])


def test_calculate_longitudinal_learning_curves_empty():
    curves = calculate_longitudinal_learning_curves(df=pd.DataFrame())
    assert curves["total_points"] == 0
    assert curves["dates"] == []


def test_get_multi_window_performance_summary(sample_prediction_df):
    windows = get_multi_window_performance_summary(df=sample_prediction_df)
    assert len(windows) > 0
    window_names = [w["window_name"] for w in windows]
    assert "7-Day Window" in window_names
    assert "All-Time Window" in window_names
    for w in windows:
        assert "model_mae" in w
        assert "uplift_pct" in w
        assert "llm_win_rate_pct" in w


def test_get_praxist_learning_timeline(temp_praxist_file):
    praxist = get_praxist_learning_timeline(experiments_path=temp_praxist_file)
    assert praxist["total_hypotheses"] == 2
    assert praxist["accepted_hypotheses"] == 1
    assert len(praxist["experiments"]) == 1
    assert praxist["experiments"][0]["status"] == "ACCEPTED"


def test_get_episodic_reflections_summary(temp_sqlite_db):
    reflections = get_episodic_reflections_summary(db_path=temp_sqlite_db)
    assert reflections["total_memories"] == 1
    assert reflections["total_reflections"] == 1
    assert len(reflections["categories"]["Seasonal Transition"]) == 1
    assert len(reflections["recent_feed"]) == 1


def test_generate_learning_journal_markdown(sample_prediction_df, tmp_path):
    out_file = str(tmp_path / "TEST_MODEL_LEARNING.md")
    os.environ["TEST_LEARNING_PERSIST"] = "1"
    md = generate_learning_journal_markdown(output_path=out_file, df=sample_prediction_df)
    del os.environ["TEST_LEARNING_PERSIST"]

    assert "# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal" in md
    assert "Longitudinal Performance Evolution" in md
    assert "Sapient PRAXIST Parameter Evolution" in md
    assert os.path.exists(out_file)


def test_generate_learning_telemetry_html_snippet(sample_prediction_df):
    html = generate_learning_telemetry_html_snippet(df=sample_prediction_df, rel_prefix="../")
    assert "model-learning-section" in html
    assert "learningCurveChart" in html
    assert "llmWinRateChart" in html
    assert "Longitudinal Accuracy &amp; Convergence Horizons" in html or "Longitudinal Accuracy & Convergence Horizons" in html
    assert "https://github.com/KoshiirRa/midgley/blob/main/MODEL_LEARNING.md" in html

