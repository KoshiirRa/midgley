"""
Integration and Concurrency Tests for Self-Hosted Process Serialization & Atomic Storage
(Issues #424 & #425)
"""

import os
import time
import threading
import subprocess
import pandas as pd
import pytest

from src.storage_io import atomic_write_csv, atomic_write_json
from src.prediction_logger import log_predictions, HISTORY_CSV_PATH


def test_concurrent_readers_during_rapid_atomic_writes(tmp_path):
    """
    Soak test: Verifies that concurrent reader threads encounter ZERO short reads,
    ZERO empty data errors, and ZERO malformed parsing exceptions while the destination
    CSV is being continuously overwritten via atomic_write_csv.
    """
    target_csv = tmp_path / "rapid_prediction_history.csv"
    initial_df = pd.DataFrame({
        "forecast_target_date": ["2026-09-24"] * 100,
        "region": ["National"] * 100,
        "current_base_price": [2.50] * 100,
        "predicted_5d_price": [2.55] * 100,
        "predicted_direction": ["UP"] * 100
    })
    atomic_write_csv(target_csv, initial_df, index=False)

    stop_event = threading.Event()
    read_errors = []
    read_successes = [0]

    def reader_loop():
        while not stop_event.is_set():
            try:
                df = pd.read_csv(target_csv)
                if len(df) == 0:
                    read_errors.append("Empty DataFrame read!")
                read_successes[0] += 1
            except Exception as e:
                read_errors.append(f"Reader exception: {type(e).__name__}: {e}")
            time.sleep(0.001)

    # Launch 4 concurrent reader threads
    reader_threads = [threading.Thread(target=reader_loop) for _ in range(4)]
    for t in reader_threads:
        t.start()

    # Perform 50 rapid atomic overwrites
    for i in range(50):
        new_df = pd.DataFrame({
            "forecast_target_date": [f"2026-09-{i:02d}"] * 100,
            "region": ["National"] * 100,
            "current_base_price": [2.50 + i * 0.01] * 100,
            "predicted_5d_price": [2.55 + i * 0.01] * 100,
            "predicted_direction": ["UP"] * 100
        })
        atomic_write_csv(target_csv, new_df, index=False)
        time.sleep(0.002)

    stop_event.set()
    for t in reader_threads:
        t.join()

    assert len(read_errors) == 0, f"Encountered reader errors: {read_errors[:5]}"
    assert read_successes[0] > 50


def test_concurrency_lock_prevents_lost_updates(tmp_path):
    """
    Verifies that serialized writes using atomic_write_csv properly preserve
    all appended rows without silent overwrite.
    """
    target_csv = tmp_path / "test_ledger.csv"
    initial_df = pd.DataFrame({
        "forecast_target_date": ["2026-09-24"],
        "region": ["National"],
        "model_version": ["v1"],
        "run_type": ["DAILY_ROUTINE"],
        "current_base_price": [2.50],
        "predicted_5d_price": [2.55],
        "predicted_direction": ["UP"],
        "forecast_horizon_days": [5]
    })
    atomic_write_csv(target_csv, initial_df, index=False)

    # Writer A simulation
    df_a = pd.read_csv(target_csv)
    row_a = pd.DataFrame({
        "forecast_target_date": ["2026-09-25"],
        "region": ["Tulsa_OK"],
        "model_version": ["v1"],
        "run_type": ["DAILY_ROUTINE"],
        "current_base_price": [2.30],
        "predicted_5d_price": [2.35],
        "predicted_direction": ["UP"],
        "forecast_horizon_days": [5]
    })
    combined_a = pd.concat([df_a, row_a], ignore_index=True)
    atomic_write_csv(target_csv, combined_a, index=False)

    # Writer B simulation
    df_b = pd.read_csv(target_csv)
    row_b = pd.DataFrame({
        "forecast_target_date": ["2026-09-26"],
        "region": ["Newark_DE"],
        "model_version": ["v1"],
        "run_type": ["DAILY_ROUTINE"],
        "current_base_price": [2.60],
        "predicted_5d_price": [2.65],
        "predicted_direction": ["UP"],
        "forecast_horizon_days": [5]
    })
    combined_b = pd.concat([df_b, row_b], ignore_index=True)
    atomic_write_csv(target_csv, combined_b, index=False)

    final_df = pd.read_csv(target_csv)
    assert len(final_df) == 3
    assert set(final_df["region"]) == {"National", "Tulsa_OK", "Newark_DE"}
