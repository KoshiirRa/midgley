"""
CSV Prediction History to Database Migration Script (scripts/migrate_csv_to_turso.py)

Ingests legacy monolithic data/prediction_history.csv, deduplicates redundant backtest runs (Item E-1),
generates deterministic SHA-256 primary keys, and batch-populates normalized database tables:
- forecasts
- ground_truth
- evaluations
"""

import os
import sys
import hashlib
import pandas as pd
import numpy as np
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.db.client import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def generate_deterministic_forecast_id(
    region: str,
    model_version: str,
    target_date: str,
    horizon: int,
    run_type: str
) -> str:
    """Computes deterministic 32-character SHA-256 identifier for a forecast."""
    raw = f"{region.strip().lower()}_{model_version.strip().lower()}_{str(target_date)[:10]}_{int(horizon)}_{run_type.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def migrate_csv_to_database(csv_path: str = "data/prediction_history.csv", db=None) -> dict:
    """Migrates and deduplicates prediction_history.csv into normalized database tables."""
    if not os.path.exists(csv_path):
        logger.warning(f"CSV file not found at {csv_path}. Skipping migration.")
        return {"status": "NO_FILE", "rows_migrated": 0}

    logger.info(f"Reading legacy prediction ledger from {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    total_raw_rows = len(df)
    logger.info(f"Total raw CSV rows: {total_raw_rows}")

    if db is None:
        db = get_db(reset=True)
    db.init_schema()

    forecast_stmts = []
    ground_truth_stmts = []
    eval_stmts = []

    seen_forecast_ids = set()
    seen_gt_keys = set()
    seen_eval_ids = set()

    for _, row in df.iterrows():
        region = str(row.get("region", "National")).strip()
        model_version = str(row.get("model_version", "v0.7.2")).strip()
        
        target_val = row.get("forecast_target_date") if pd.notna(row.get("forecast_target_date")) else row.get("target_date")
        target_date = str(target_val)[:10] if pd.notna(target_val) else ""
        if not target_date or target_date in ("nan", "None", ""):
            continue

        horizon_val = row.get("forecast_horizon_days") if pd.notna(row.get("forecast_horizon_days")) else row.get("horizon_step", 5)
        try:
            horizon = int(float(horizon_val))
        except Exception:
            horizon = 5

        # Origin date
        origin_val = row.get("log_timestamp") if pd.notna(row.get("log_timestamp")) else row.get("issued_at_utc")
        if pd.notna(origin_val) and str(origin_val) not in ("nan", "None", ""):
            origin_date = str(origin_val)[:10]
        else:
            try:
                origin_date = (pd.to_datetime(target_date) - pd.tseries.offsets.BDay(horizon)).strftime("%Y-%m-%d")
            except Exception:
                origin_date = target_date

        run_type_val = row.get("run_type") if pd.notna(row.get("run_type")) else "BACKTEST"
        run_type = str(run_type_val).strip().upper()

        forecast_id = generate_deterministic_forecast_id(region, model_version, target_date, horizon, run_type)
        
        pred_val = row.get("predicted_5d_price") if pd.notna(row.get("predicted_5d_price")) else row.get("predicted_wholesale_price", 0.0)
        try:
            pred_price = float(pred_val)
        except Exception:
            pred_price = 0.0

        ci_low_95 = float(row["prediction_lower_95ci"]) if "prediction_lower_95ci" in row and pd.notna(row["prediction_lower_95ci"]) else None
        ci_high_95 = float(row["prediction_upper_95ci"]) if "prediction_upper_95ci" in row and pd.notna(row["prediction_upper_95ci"]) else None
        ci_low_80 = float(row["prediction_lower_80ci"]) if "prediction_lower_80ci" in row and pd.notna(row["prediction_lower_80ci"]) else None
        ci_high_80 = float(row["prediction_upper_80ci"]) if "prediction_upper_80ci" in row and pd.notna(row["prediction_upper_80ci"]) else None
        
        llm_press = float(row["llm_price_pressure"]) if "llm_price_pressure" in row and pd.notna(row["llm_price_pressure"]) else 0.0
        llm_disrup = float(row["llm_supply_disruption"]) if "llm_supply_disruption" in row and pd.notna(row["llm_supply_disruption"]) else 0.0

        if forecast_id not in seen_forecast_ids:
            seen_forecast_ids.add(forecast_id)
            forecast_sql = """
            INSERT INTO forecasts (
                forecast_id, region, model_version, origin_date, horizon, target_date,
                predicted_price, ci_lower_95, ci_upper_95, ci_lower_80, ci_upper_80,
                llm_price_pressure, llm_supply_disruption, run_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(forecast_id) DO NOTHING;
            """
            forecast_stmts.append((forecast_sql, (
                forecast_id, region, model_version, origin_date, horizon, target_date,
                pred_price, ci_low_95, ci_high_95, ci_low_80, ci_high_80,
                llm_press, llm_disrup, run_type
            )))

        # Actual price & evaluation
        actual_val = row.get("actual_5d_price") if pd.notna(row.get("actual_5d_price")) else row.get("actual_wholesale_price")
        if pd.notna(actual_val):
            try:
                actual_price = float(actual_val)
                if actual_price > 0:
                    series_id = f"ACTUAL_{region.upper()}"
                    gt_key = (series_id, target_date)
                    if gt_key not in seen_gt_keys:
                        seen_gt_keys.add(gt_key)
                        gt_sql = """
                        INSERT INTO ground_truth (series_id, obs_date, actual_price, settled_at, source)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(series_id, obs_date) DO UPDATE SET actual_price = excluded.actual_price;
                        """
                        ground_truth_stmts.append((gt_sql, (series_id, target_date, actual_price, target_date, "legacy_ledger")))

                    eval_id = hashlib.sha256(f"{forecast_id}_{target_date}".encode("utf-8")).hexdigest()[:32]
                    if eval_id not in seen_eval_ids:
                        seen_eval_ids.add(eval_id)
                        abs_err = abs(pred_price - actual_price)
                        pct_err = (abs_err / actual_price * 100.0) if actual_price > 0 else 0.0
                        dir_correct = int(row.get("directional_hit", 1)) if pd.notna(row.get("directional_hit")) else (
                            1 if (pred_price >= actual_price) == (pred_price >= 0) else 0
                        )
                        within_95 = int(row.get("within_95ci_hit", 1)) if pd.notna(row.get("within_95ci_hit")) else (
                            1 if (ci_low_95 is not None and ci_high_95 is not None and ci_low_95 <= actual_price <= ci_high_95) else 0
                        )

                        eval_sql = """
                        INSERT INTO evaluations (
                            evaluation_id, forecast_id, series_id, actual_price, absolute_error,
                            percentage_error, directional_correct, within_95ci
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(evaluation_id) DO NOTHING;
                        """
                        eval_stmts.append((eval_sql, (
                            eval_id, forecast_id, series_id, actual_price, round(abs_err, 4),
                            round(pct_err, 4), dir_correct, within_95
                        )))
            except Exception:
                pass

    logger.info(f"Executing batch inserts into database...")
    db.execute_batch(forecast_stmts)
    db.execute_batch(ground_truth_stmts)
    db.execute_batch(eval_stmts)

    unique_forecasts_count = len(forecast_stmts)
    dedup_ratio = (1.0 - unique_forecasts_count / total_raw_rows) * 100.0 if total_raw_rows > 0 else 0.0

    logger.info(f"=== Migration Summary ===")
    logger.info(f"Raw CSV rows:             {total_raw_rows}")
    logger.info(f"Unique Forecasts Created: {unique_forecasts_count}")
    logger.info(f"Duplicate Rows Removed:   {total_raw_rows - unique_forecasts_count} ({dedup_ratio:.1f}% deduplication)")
    logger.info(f"Ground Truth Observations:{len(ground_truth_stmts)}")
    logger.info(f"Evaluations Logged:       {len(eval_stmts)}")

    return {
        "status": "SUCCESS",
        "raw_csv_rows": total_raw_rows,
        "unique_forecasts": unique_forecasts_count,
        "duplicates_removed": total_raw_rows - unique_forecasts_count,
        "ground_truth_count": len(ground_truth_stmts),
        "evaluations_count": len(eval_stmts)
    }


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/prediction_history.csv"
    res = migrate_csv_to_database(csv_file)
    print(res)
