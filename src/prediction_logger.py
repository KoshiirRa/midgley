"""
Prediction Logger & Model Performance Tracking Engine (src/prediction_logger.py)
Logs model predictions over time, backfills actual historical prices, evaluates rolling error metrics
(MAE, RMSE, Directional Hit Rate), and enables continuous iterative improvement.
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

HISTORY_CSV_PATH = os.path.join("data", "prediction_history.csv")

def ensure_history_store():
    """Ensures data directory and prediction_history.csv file exist with standard schema."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(HISTORY_CSV_PATH) or os.path.getsize(HISTORY_CSV_PATH) == 0:
        columns = [
            "log_timestamp",
            "forecast_target_date",
            "region",
            "model_version",
            "run_type",
            "headline_trigger",
            "current_base_price",
            "predicted_5d_price",
            "predicted_direction",
            "actual_5d_price",
            "actual_direction",
            "error_dollars",
            "directional_hit"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_csv(HISTORY_CSV_PATH, index=False)
        logger.info(f"Initialized new prediction history log at {HISTORY_CSV_PATH}")


def log_predictions(
    predictions_df: pd.DataFrame, 
    region: str = "Tulsa_OK", 
    model_version: str = "v1.4-Finlight-Ridge",
    run_type: str = "DAILY_BATCH",
    headline_trigger: str = ""
) -> int:
    """
    Logs a DataFrame of model predictions into prediction_history.csv.
    Expected columns: ['date', 'current_price', 'predicted_5d_price']
    """
    ensure_history_store()
    try:
        history_df = pd.read_csv(HISTORY_CSV_PATH, dtype={"actual_direction": str, "predicted_direction": str})
    except Exception:
        history_df = pd.DataFrame()
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_records = []
    
    for idx, row in predictions_df.iterrows():
        base_price = float(row['current_price'])
        pred_price = float(row['predicted_5d_price'])
        pred_dir = "UP" if pred_price >= base_price else "DOWN"
        if 'forecast_target_date' in row and pd.notna(row['forecast_target_date']):
            target_date = str(row['forecast_target_date'])
        else:
            base_dt = pd.to_datetime(row['date'])
            target_date = pd.bdate_range(start=base_dt, periods=6)[-1].strftime("%Y-%m-%d")
        
        new_records.append({
            "log_timestamp": timestamp_str,
            "forecast_target_date": target_date,
            "region": region,
            "model_version": model_version,
            "run_type": run_type,
            "headline_trigger": headline_trigger,
            "current_base_price": round(base_price, 4),
            "predicted_5d_price": round(pred_price, 4),
            "predicted_direction": pred_dir,
            "actual_5d_price": np.nan,
            "actual_direction": "",
            "error_dollars": np.nan,
            "directional_hit": np.nan
        })
        
    new_df = pd.DataFrame(new_records)
    combined = pd.concat([history_df, new_df], ignore_index=True)
    combined.drop_duplicates(subset=["forecast_target_date", "region", "model_version", "run_type"], keep="last", inplace=True)
    combined.to_csv(HISTORY_CSV_PATH, index=False)
    
    logger.info(f"Logged {len(new_records)} predictions for region '{region}' under version '{model_version}' (Run Type: {run_type}).")
    return len(new_records)



def backfill_actual_prices_and_evaluate() -> pd.DataFrame:
    """
    Fetches actual historical gas prices up to today, matches them against past forecasted target dates,
    updates actual prices, error metrics, and directional hit outcomes in prediction_history.csv.
    """
    ensure_history_store()
    try:
        history_df = pd.read_csv(HISTORY_CSV_PATH)
    except Exception as e:
        logger.warning(f"Could not read prediction history log ({e}). Returning empty DataFrame.")
        return pd.DataFrame()
    
    if history_df.empty:
        logger.warning("Prediction history log is empty. No predictions to evaluate.")
        return history_df
        
    history_df['actual_direction'] = history_df['actual_direction'].astype(object)
    history_df['predicted_direction'] = history_df['predicted_direction'].astype(object)
    
    logger.info("Fetching actual historical market prices to backfill prediction log...")
    
    try:
        data = yf.download("RB=F", start="2022-01-01", progress=False)
        close_series = data['Close']['RB=F'] if isinstance(data.columns, pd.MultiIndex) else data['Close']
        dates_formatted = [d.strftime("%Y-%m-%d") for d in close_series.index]
        actuals_df = pd.DataFrame({'date_str': dates_formatted, 'actual_rbob': close_series.values})
        actuals_map = actuals_df.set_index('date_str')['actual_rbob'].to_dict()
    except Exception as e:
        logger.warning(f"Could not download actuals from yfinance: {e}")
        actuals_map = {}
        
    updated = False
    for idx, row in history_df.iterrows():
        target_date_str = str(row['forecast_target_date'])
        base_price = float(row['current_base_price'])
        pred_price = float(row['predicted_5d_price'])
        pred_dir = str(row['predicted_direction'])
        
        if target_date_str in actuals_map:
            raw_actual = float(actuals_map[target_date_str])
            if row['region'] == "Cincinnati_KY":
                actual_price = raw_actual + 0.425
            elif row['region'] in ["Tulsa_OK", "Newark_DE", "Cincinnati_OH", "Greenville_NC"]:
                actual_price = raw_actual + 0.55
            elif row['region'] == "Oakland_CA":
                actual_price = raw_actual + 2.05
            elif row['region'] == "BayArea_CA":
                actual_price = raw_actual + 2.15
            elif row['region'] == "National":
                actual_price = raw_actual
            else:
                # Dynamic rack margin offset fallback for newly added regional markets
                margin_offset = base_price - raw_actual if base_price > raw_actual else 0.55
                actual_price = raw_actual + margin_offset

            actual_dir = "UP" if actual_price >= base_price else "DOWN"
            err_dollars = abs(actual_price - pred_price)
            hit = 1 if pred_dir == actual_dir else 0
            
            history_df.at[idx, 'actual_5d_price'] = round(actual_price, 4)
            history_df.at[idx, 'actual_direction'] = str(actual_dir)
            history_df.at[idx, 'error_dollars'] = round(err_dollars, 4)
            history_df.at[idx, 'directional_hit'] = hit
            updated = True
            
    if updated:
        history_df.to_csv(HISTORY_CSV_PATH, index=False)
        logger.info("Successfully backfilled actual prices and updated performance metrics.")
        
    return history_df


def backfill_new_region_history(
    test_dates,
    base_prices,
    predicted_prices,
    region: str,
    model_version: str = "v1.4-Ridge"
) -> int:
    """
    Backfills historical test split predictions for a newly added region into prediction_history.csv
    and automatically matches/evaluates mature target dates against ground-truth market prices.
    """
    dates_arr = getattr(test_dates, 'values', test_dates)
    base_arr = getattr(base_prices, 'values', base_prices)
    pred_arr = getattr(predicted_prices, 'values', predicted_prices)

    pred_log_df = pd.DataFrame({
        'date': dates_arr,
        'current_price': base_arr,
        'predicted_5d_price': pred_arr
    })
    
    n_logged = log_predictions(pred_log_df, region=region, model_version=model_version)
    backfill_actual_prices_and_evaluate()
    logger.info(f"Backfilled and evaluated {n_logged} historical prediction records for region '{region}'.")
    return n_logged


def generate_performance_report() -> pd.DataFrame:
    """
    Calculates summary performance metrics aggregated by Model Version and Region.
    """
    df = backfill_actual_prices_and_evaluate()
    if df.empty or df['actual_5d_price'].dropna().empty:
        print("\n[Prediction Tracker] No completed prediction evaluations available yet.")
        return pd.DataFrame()
        
    evaluated_df = df.dropna(subset=['actual_5d_price']).copy()
    
    report_rows = []
    grouped = evaluated_df.groupby(['region', 'model_version'])
    
    for (region, version), group in grouped:
        mae = group['error_dollars'].mean()
        rmse = np.sqrt((group['error_dollars'] ** 2).mean())
        hit_rate = group['directional_hit'].mean() * 100.0
        n_eval = len(group)
        
        report_rows.append({
            "Region": region,
            "Model Version": version,
            "Evaluated Days": n_eval,
            "MAE ($/gal)": round(mae, 4),
            "RMSE ($/gal)": round(rmse, 4),
            "Directional Accuracy (%)": round(hit_rate, 2)
        })
        
    report_df = pd.DataFrame(report_rows)
    return report_df


def filter_evaluated_history_by_window(
    df: pd.DataFrame, window_days: int | str = 30, region: str = None
) -> pd.DataFrame:
    """Filters evaluated prediction history records by rolling window (in days) and region."""
    if df.empty or 'actual_5d_price' not in df.columns:
        return pd.DataFrame()

    eval_df = df.dropna(subset=['actual_5d_price']).copy()
    if eval_df.empty:
        return eval_df

    if region and str(region).lower() not in ["all", "none", ""]:
        reg_target = str(region).lower()
        eval_df = eval_df[eval_df['region'].astype(str).str.lower() == reg_target]

    if eval_df.empty:
        return eval_df

    eval_df['target_dt'] = pd.to_datetime(eval_df['forecast_target_date'], errors='coerce')
    eval_df = eval_df.dropna(subset=['target_dt']).sort_values('target_dt')

    if eval_df.empty:
        return eval_df

    if window_days is not None and str(window_days).lower() != "all":
        try:
            w_int = int(window_days)
            max_dt = eval_df['target_dt'].max()
            cutoff_dt = max_dt - pd.Timedelta(days=w_int)
            eval_df = eval_df[eval_df['target_dt'] >= cutoff_dt]
        except (ValueError, TypeError):
            pass

    return eval_df


def compute_rolling_scoreboard_metrics(
    window_days: int | str = 30, region: str = None
) -> dict:
    """
    Computes rolling performance metrics (MAE, RMSE, MAPE, Directional Hit Rate %,
    Naive Persistence Baseline MAE, and Model MAE Uplift %) over a given rolling day window.
    """
    df = backfill_actual_prices_and_evaluate()
    filtered_df = filter_evaluated_history_by_window(df, window_days=window_days, region=region)

    if filtered_df.empty:
        return {
            "window_days": window_days,
            "region_filter": region or "All",
            "total_evaluations": 0,
            "mae_dollars": 0.0,
            "rmse_dollars": 0.0,
            "mape_pct": 0.0,
            "directional_hit_rate_pct": 0.0,
            "naive_persistence_mae": 0.0,
            "model_uplift_mae_pct": 0.0,
        }

    actuals = filtered_df['actual_5d_price'].astype(float).values
    preds = filtered_df['predicted_5d_price'].astype(float).values
    bases = filtered_df['current_base_price'].astype(float).values
    hits = filtered_df['directional_hit'].astype(float).values

    n_eval = len(filtered_df)
    mae = float(np.mean(np.abs(actuals - preds)))
    rmse = float(np.sqrt(np.mean((actuals - preds) ** 2)))
    mape = float(np.mean(np.abs((actuals - preds) / actuals)) * 100.0)
    hit_rate = float(np.mean(hits) * 100.0)

    naive_errors = np.abs(actuals - bases)
    naive_mae = float(np.mean(naive_errors)) if len(naive_errors) > 0 else 0.0

    if naive_mae > 0:
        model_uplift = float(((naive_mae - mae) / naive_mae) * 100.0)
    else:
        model_uplift = 0.0

    return {
        "window_days": window_days,
        "region_filter": region or "All",
        "total_evaluations": n_eval,
        "mae_dollars": round(mae, 4),
        "rmse_dollars": round(rmse, 4),
        "mape_pct": round(mape, 2),
        "directional_hit_rate_pct": round(hit_rate, 2),
        "naive_persistence_mae": round(naive_mae, 4),
        "model_uplift_mae_pct": round(model_uplift, 2),
    }


def compute_regional_scoreboard_breakdown(window_days: int | str = 30) -> list[dict]:
    """Computes rolling performance metrics for each active region."""
    df = backfill_actual_prices_and_evaluate()
    if df.empty or 'actual_5d_price' not in df.columns:
        return []

    eval_df = df.dropna(subset=['actual_5d_price']).copy()
    if eval_df.empty:
        return []

    regions = eval_df['region'].unique()
    breakdown = []

    for reg in sorted(regions):
        metrics = compute_rolling_scoreboard_metrics(window_days=window_days, region=reg)
        if metrics["total_evaluations"] > 0:
            breakdown.append({
                "region": reg,
                "evaluations": metrics["total_evaluations"],
                "mae_dollars": metrics["mae_dollars"],
                "rmse_dollars": metrics["rmse_dollars"],
                "mape_pct": metrics["mape_pct"],
                "directional_hit_rate_pct": metrics["directional_hit_rate_pct"],
                "naive_persistence_mae": metrics["naive_persistence_mae"],
                "model_uplift_mae_pct": metrics["model_uplift_mae_pct"],
            })

    return breakdown


def get_recent_evaluated_records(region: str = None, limit: int = 50) -> list[dict]:
    """Returns chronologically sorted evaluated forecast records."""
    df = backfill_actual_prices_and_evaluate()
    filtered_df = filter_evaluated_history_by_window(df, window_days="all", region=region)

    if filtered_df.empty:
        return []

    recent_df = filtered_df.tail(limit).copy()
    records = []

    for idx, row in recent_df.iterrows():
        records.append({
            "log_timestamp": str(row.get("log_timestamp", "")),
            "forecast_target_date": str(row.get("forecast_target_date", "")),
            "region": str(row.get("region", "")),
            "model_version": str(row.get("model_version", "")),
            "current_base_price": float(row.get("current_base_price", 0.0)),
            "predicted_5d_price": float(row.get("predicted_5d_price", 0.0)),
            "actual_5d_price": float(row.get("actual_5d_price", 0.0)),
            "predicted_direction": str(row.get("predicted_direction", "")),
            "actual_direction": str(row.get("actual_direction", "")),
            "error_dollars": round(float(row.get("error_dollars", 0.0)), 4),
            "directional_hit": int(row.get("directional_hit", 0)),
        })

    return records

