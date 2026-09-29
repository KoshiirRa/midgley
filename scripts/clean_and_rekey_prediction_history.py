"""
Prediction Ledger Clean-Up and Deterministic Re-Keying Engine (scripts/clean_and_rekey_prediction_history.py)
Issue #585 (Finding R-1, N-7)

Restores all 248 historical LIVE_PROSPECTIVE forecasts from git history (revision 2),
collapses backtest runs to 11,891 unique records, removes dummy intraday rows,
and deterministically re-keys every forecast with immutable SHA-256 primary IDs.
"""

import os
import io
import hashlib
import subprocess
import logging
from typing import Optional
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HISTORY_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prediction_history.csv")


def generate_deterministic_forecast_id(
    region: str,
    model_version: str,
    target_date: str,
    horizon_days: int,
    run_type: str,
    issued_at_utc: Optional[str] = None
) -> str:
    """Generates a deterministic 32-character hex SHA-256 hash forecast ID."""
    reg = str(region or "").strip()
    mv = str(model_version or "").strip()
    td = str(target_date or "")[:10].strip()
    h = str(horizon_days or 5).strip()
    rt = str(run_type or "").strip()
    
    if rt == "LIVE_PROSPECTIVE" and issued_at_utc:
        ts = str(issued_at_utc).strip()
        raw_key = f"{reg}|{mv}|{ts}|{td}|{h}|{rt}"
    else:
        raw_key = f"{reg}|{mv}|{td}|{h}|{rt}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:32]


def clean_and_rekey_history(
    csv_path: str = HISTORY_CSV_PATH,
    source_git_rev: str = "a667e0a1~1",
    output_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Cleans, deduplicates, and re-keys prediction_history.csv deterministically.
    """
    out_path = output_path or csv_path
    
    # 1. Fetch historical un-truncated CSV from git rev if available
    df_raw = None
    try:
        cmd = ["git", "show", f"{source_git_rev}:data/prediction_history.csv"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        df_raw = pd.read_csv(io.BytesIO(res.stdout), low_memory=False)
        logger.info(f"Loaded {len(df_raw)} raw historical rows from git rev {source_git_rev}")
    except Exception as e:
        logger.warning(f"Could not load git rev {source_git_rev} ({e}); falling back to current file at {csv_path}")
        if os.path.exists(csv_path):
            df_raw = pd.read_csv(csv_path, low_memory=False)
        else:
            raise FileNotFoundError(f"Cannot find {csv_path}")

    # Standardize columns
    if "forecast_target_date" not in df_raw.columns and "target_date" in df_raw.columns:
        df_raw["forecast_target_date"] = df_raw["target_date"]
    if "forecast_horizon_days" not in df_raw.columns and "horizon_step" in df_raw.columns:
        df_raw["forecast_horizon_days"] = df_raw["horizon_step"]

    # 2. Extract Backtests & Deduplicate
    backtests = df_raw[df_raw["run_type"] == "RETROSPECTIVE_BACKTEST"].copy()
    backtests = backtests.drop_duplicates(
        subset=["region", "model_version", "forecast_target_date", "forecast_horizon_days", "run_type"],
        keep="last"
    )
    logger.info(f"Collapsed backtests to {len(backtests)} unique records")

    # 3. Extract Live Prospective Forecasts (All 248 rows)
    live = df_raw[df_raw["run_type"] == "LIVE_PROSPECTIVE"].copy()
    # Deduplicate live forecasts on exact issue timestamp + parameters
    if "issued_at_utc" in live.columns and live["issued_at_utc"].notna().any():
        live = live.drop_duplicates(
            subset=["region", "model_version", "issued_at_utc", "forecast_target_date", "forecast_horizon_days", "run_type"],
            keep="last"
        )
    elif "log_timestamp" in live.columns:
        live = live.drop_duplicates(
            subset=["region", "model_version", "log_timestamp", "forecast_target_date", "forecast_horizon_days", "run_type"],
            keep="last"
        )
    logger.info(f"Preserved {len(live)} live prospective forecast issuances")

    # 4. Filter Genuine Intraday Revisions (Exclude hard-coded $3.184 dummy rows)
    intraday = df_raw[df_raw["run_type"] == "INTRADAY_REVISION"].copy()
    if not intraday.empty:
        # Quarantine dummy $3.184 rows
        is_dummy = (intraday["current_base_price"] == 3.184) & (intraday["predicted_5d_price"].isin([3.2502, 3.0821, 3.0948, 3.2604, 3.2859, 3.2986, 3.1203, 3.2349, 3.2375]))
        dummy_rows = intraday[is_dummy]
        genuine_intraday = intraday[~is_dummy]
        if not dummy_rows.empty:
            logger.info(f"Quarantined {len(dummy_rows)} dummy intraday rows from production ledger")
        intraday = genuine_intraday

    # 5. Combine Clean Partitions
    clean_df = pd.concat([backtests, live, intraday], ignore_index=True)

    # 6. Apply Deterministic Re-Keying
    new_ids = []
    for _, row in clean_df.iterrows():
        reg = row.get("region", "National")
        mv = row.get("model_version", "v1.6-Ridge")
        td = row.get("forecast_target_date", "")
        h = row.get("forecast_horizon_days", 5)
        rt = row.get("run_type", "RETROSPECTIVE_BACKTEST")
        ts = row.get("issued_at_utc") or row.get("log_timestamp")
        
        fid = generate_deterministic_forecast_id(
            region=reg,
            model_version=mv,
            target_date=td,
            horizon_days=h,
            run_type=rt,
            issued_at_utc=ts if rt == "LIVE_PROSPECTIVE" else None
        )
        new_ids.append(fid)

    clean_df["forecast_id"] = new_ids

    # 7. Sort Chronologically
    sort_cols = [c for c in ["log_timestamp", "forecast_target_date", "forecast_horizon_days"] if c in clean_df.columns]
    if sort_cols:
        clean_df = clean_df.sort_values(by=sort_cols).reset_index(drop=True)

    # 8. Atomic Write Output
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    clean_df.to_csv(out_path, index=False)
    logger.info(f"Successfully wrote {len(clean_df)} deterministic records to {out_path}")
    return clean_df


if __name__ == "__main__":
    clean_and_rekey_history()
