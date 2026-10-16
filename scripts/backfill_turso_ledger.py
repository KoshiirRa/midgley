#!/usr/bin/env python3
"""
Turso Cloud Database Backfill Utility (scripts/backfill_turso_ledger.py)

Uploads historical prediction and backtest records from data/prediction_history.csv
directly into the remote Turso libSQL Cloud Database using fast multi-row batch inserts.

Enables cloud environments (like GitHub Actions runners) to skip redundant 
historical backfill computation without having to commit or merge massive CSV diffs.

Usage:
    python scripts/backfill_turso_ledger.py [--csv data/prediction_history.csv] [--batch-size 50]
"""

import os
import sys
import json
import time
import uuid
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import pandas as pd


def get_turso_endpoint_and_headers() -> tuple[str, dict]:
    turso_url = os.environ.get("TURSO_DATABASE_URL", "").strip()
    turso_token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()

    if not turso_url or not turso_token:
        raise ValueError("Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN environment variables.")

    if turso_url.startswith("turso://"):
        turso_url = "https://" + turso_url[8:]
    elif turso_url.startswith("libsql://"):
        turso_url = "https://" + turso_url[9:]

    endpoint = f"{turso_url.rstrip('/')}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {turso_token}",
        "Content-Type": "application/json",
    }
    return endpoint, headers


def ensure_turso_tables(endpoint: str, headers: dict) -> None:
    """Ensures prediction_history and forecasts tables exist in Turso."""
    create_pred_history_sql = """CREATE TABLE IF NOT EXISTS prediction_history (
        forecast_id TEXT PRIMARY KEY,
        issued_at_utc TEXT,
        log_timestamp TEXT,
        forecast_target_date TEXT,
        forecast_horizon_days INTEGER,
        region TEXT,
        model_version TEXT,
        run_type TEXT,
        headline_trigger TEXT,
        current_base_price REAL,
        predicted_5d_price REAL,
        predicted_direction TEXT,
        actual_5d_price REAL,
        actual_direction TEXT,
        error_dollars REAL,
        directional_hit REAL,
        llm_price_pressure REAL,
        llm_supply_disruption REAL,
        quant_baseline_5d_price REAL,
        llm_augmentation_delta REAL,
        prediction_lower_95ci REAL,
        prediction_upper_95ci REAL,
        within_95ci_hit REAL,
        data_source_provenance TEXT,
        is_retroactive_backtest INTEGER
    );"""

    create_forecasts_sql = """CREATE TABLE IF NOT EXISTS forecasts (
        forecast_id TEXT PRIMARY KEY,
        region TEXT NOT NULL,
        model_version TEXT NOT NULL,
        origin_date TEXT NOT NULL,
        horizon INTEGER NOT NULL,
        target_date TEXT NOT NULL,
        predicted_price REAL NOT NULL,
        ci_lower_95 REAL,
        ci_upper_95 REAL,
        ci_lower_80 REAL,
        ci_upper_80 REAL,
        llm_price_pressure REAL DEFAULT 0.0,
        llm_supply_disruption REAL DEFAULT 0.0,
        point_in_time_features TEXT,
        run_type TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );"""

    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": create_pred_history_sql}},
            {"type": "execute", "stmt": {"sql": create_forecasts_sql}},
            {"type": "close"}
        ]
    }
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15.0) as resp:
        pass
    print("[Turso Init] Ensured prediction_history and forecasts tables exist in Turso.")


def backfill_to_turso(csv_path: str = "data/prediction_history.csv", batch_size: int = 50, only_backtests: bool = False) -> int:
    if not os.path.exists(csv_path):
        print(f"[Error] CSV not found at {csv_path}", file=sys.stderr)
        return 0

    print(f"[Turso Backfill] Reading {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    if df.empty:
        print("[Turso Backfill] CSV is empty.")
        return 0

    if only_backtests:
        if 'is_retroactive_backtest' in df.columns:
            df = df[df['is_retroactive_backtest'].fillna(False).astype(bool)]
        elif 'run_type' in df.columns:
            df = df[df['run_type'].astype(str).str.upper() == 'RETROSPECTIVE_BACKTEST']

    total_records = len(df)
    print(f"[Turso Backfill] Preparing to sync {total_records:,} records in multi-row batches of {batch_size}...")

    endpoint, headers = get_turso_endpoint_and_headers()
    ensure_turso_tables(endpoint, headers)

    total_synced = 0
    start_time = time.time()

    for i in range(0, total_records, batch_size):
        chunk = df.iloc[i:i + batch_size]
        pred_args = []
        fc_args = []

        for _, row in chunk.iterrows():
            f_id = str(row.get("forecast_id")) if pd.notna(row.get("forecast_id")) and str(row.get("forecast_id")).strip() else str(uuid.uuid4())
            issued_utc = str(row.get("issued_at_utc")) if pd.notna(row.get("issued_at_utc")) and str(row.get("issued_at_utc")).strip() else datetime.now(timezone.utc).isoformat()
            is_retro = 1 if bool(row.get("is_retroactive_backtest", False)) else 0
            horizon = int(float(row.get("forecast_horizon_days", 5))) if pd.notna(row.get("forecast_horizon_days")) else 5
            origin_date = str(row.get("log_timestamp", ""))[:10] if pd.notna(row.get("log_timestamp")) else ""
            target_date = str(row.get("forecast_target_date", "")) if pd.notna(row.get("forecast_target_date")) else ""
            region = str(row.get("region", ""))
            model_ver = str(row.get("model_version", ""))
            run_type = str(row.get("run_type", "RETROSPECTIVE_BACKTEST" if is_retro else "LIVE_PROSPECTIVE"))

            pred_price = float(row.get("predicted_5d_price", 0.0)) if pd.notna(row.get("predicted_5d_price")) else 0.0
            low_95 = float(row.get("prediction_lower_95ci", 0.0)) if pd.notna(row.get("prediction_lower_95ci")) else None
            high_95 = float(row.get("prediction_upper_95ci", 0.0)) if pd.notna(row.get("prediction_upper_95ci")) else None
            llm_pressure = float(row.get("llm_price_pressure", 0.0)) if pd.notna(row.get("llm_price_pressure")) else 0.0
            llm_supply = float(row.get("llm_supply_disruption", 0.0)) if pd.notna(row.get("llm_supply_disruption")) else 0.0

            # Args for prediction_history
            pred_args.extend([
                {"type": "text", "value": f_id},
                {"type": "text", "value": issued_utc},
                {"type": "text", "value": str(row.get("log_timestamp", ""))},
                {"type": "text", "value": target_date},
                {"type": "integer", "value": str(horizon)},
                {"type": "text", "value": region},
                {"type": "text", "value": model_ver},
                {"type": "text", "value": run_type},
                {"type": "text", "value": str(row.get("headline_trigger", ""))},
                {"type": "float", "value": float(row.get("current_base_price", 0.0)) if pd.notna(row.get("current_base_price")) else 0.0},
                {"type": "float", "value": pred_price},
                {"type": "text", "value": str(row.get("predicted_direction", ""))},
                {"type": "float", "value": float(row.get("actual_5d_price", 0.0)) if pd.notna(row.get("actual_5d_price")) else 0.0},
                {"type": "text", "value": str(row.get("actual_direction", ""))},
                {"type": "float", "value": float(row.get("error_dollars", 0.0)) if pd.notna(row.get("error_dollars")) else 0.0},
                {"type": "float", "value": float(row.get("directional_hit", 0.0)) if pd.notna(row.get("directional_hit")) else 0.0},
                {"type": "float", "value": llm_pressure},
                {"type": "float", "value": llm_supply},
                {"type": "float", "value": float(row.get("quant_baseline_5d_price", 0.0)) if pd.notna(row.get("quant_baseline_5d_price")) else 0.0},
                {"type": "float", "value": float(row.get("llm_augmentation_delta", 0.0)) if pd.notna(row.get("llm_augmentation_delta")) else 0.0},
                {"type": "float", "value": low_95} if low_95 is not None else {"type": "null"},
                {"type": "float", "value": high_95} if high_95 is not None else {"type": "null"},
                {"type": "float", "value": float(row.get("within_95ci_hit", 0.0)) if pd.notna(row.get("within_95ci_hit")) else 0.0},
                {"type": "text", "value": str(row.get("data_source_provenance", "yfinance"))},
                {"type": "integer", "value": str(is_retro)}
            ])

            # Args for forecasts
            fc_args.extend([
                {"type": "text", "value": f_id},
                {"type": "text", "value": region},
                {"type": "text", "value": model_ver},
                {"type": "text", "value": origin_date},
                {"type": "integer", "value": str(horizon)},
                {"type": "text", "value": target_date},
                {"type": "float", "value": pred_price},
                {"type": "float", "value": low_95} if low_95 is not None else {"type": "null"},
                {"type": "float", "value": high_95} if high_95 is not None else {"type": "null"},
                {"type": "float", "value": llm_pressure},
                {"type": "float", "value": llm_supply},
                {"type": "text", "value": run_type}
            ])

        # Multi-row statements
        n_rows = len(chunk)
        ph_row_placeholder = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        sql_pred = f"""INSERT OR REPLACE INTO prediction_history (
            forecast_id, issued_at_utc, log_timestamp, forecast_target_date, forecast_horizon_days, region, model_version, run_type,
            headline_trigger, current_base_price, predicted_5d_price, predicted_direction,
            actual_5d_price, actual_direction, error_dollars, directional_hit,
            llm_price_pressure, llm_supply_disruption, quant_baseline_5d_price,
            llm_augmentation_delta, prediction_lower_95ci, prediction_upper_95ci,
            within_95ci_hit, data_source_provenance, is_retroactive_backtest
        ) VALUES {', '.join([ph_row_placeholder] * n_rows)}"""

        fc_row_placeholder = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        sql_fc = f"""INSERT INTO forecasts (
            forecast_id, region, model_version, origin_date, horizon, target_date,
            predicted_price, ci_lower_95, ci_upper_95, llm_price_pressure, llm_supply_disruption, run_type
        ) VALUES {', '.join([fc_row_placeholder] * n_rows)}
        ON CONFLICT(forecast_id) DO UPDATE SET
            predicted_price = excluded.predicted_price,
            ci_lower_95 = excluded.ci_lower_95,
            ci_upper_95 = excluded.ci_upper_95;"""

        requests = [
            {"type": "execute", "stmt": {"sql": sql_pred, "args": pred_args}},
            {"type": "execute", "stmt": {"sql": sql_fc, "args": fc_args}},
            {"type": "close"}
        ]

        payload = {"requests": requests}
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=30.0) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    for res in resp_data.get("results", []):
                        if res.get("type") == "error":
                            raise RuntimeError(f"Turso batch execution error: {res.get('error')}")
                break
            except Exception as e:
                if attempt == 3:
                    raise
                print(f"  [Notice] Attempt {attempt} failed ({e}). Retrying in {attempt * 2}s...")
                time.sleep(attempt * 2)

        total_synced += n_rows
        elapsed = time.time() - start_time
        rate = total_synced / elapsed if elapsed > 0 else 0
        if total_synced % 500 == 0 or total_synced == total_records:
            print(f"  -> Synced {total_synced:,}/{total_records:,} records ({total_synced / total_records * 100:.1f}%) | {rate:.0f} rows/s")

    elapsed_total = time.time() - start_time
    print(f"\n[Turso Backfill Complete] Successfully synced {total_synced:,} records to Turso in {elapsed_total:.1f}s.")
    return total_synced


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill prediction history records into Turso libSQL Cloud Database.")
    parser.add_argument("--csv", default="data/prediction_history.csv", help="Path to prediction_history.csv")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for pipeline requests")
    parser.add_argument("--only-backtests", action="store_true", help="Only backfill retrospective backtest records")
    args = parser.parse_args()

    backfill_to_turso(csv_path=args.csv, batch_size=args.batch_size, only_backtests=args.only_backtests)
