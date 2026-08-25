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
    if not os.path.exists(HISTORY_CSV_PATH):
        columns = [
            "log_timestamp",
            "forecast_target_date",
            "region",
            "model_version",
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
    model_version: str = "v1.4-Finlight-Ridge"
) -> int:
    """
    Logs a DataFrame of model predictions into prediction_history.csv.
    Expected columns: ['date', 'current_price', 'predicted_5d_price']
    """
    ensure_history_store()
    history_df = pd.read_csv(HISTORY_CSV_PATH, dtype={"actual_direction": str, "predicted_direction": str})
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_records = []
    
    for idx, row in predictions_df.iterrows():
        base_price = float(row['current_price'])
        pred_price = float(row['predicted_5d_price'])
        pred_dir = "UP" if pred_price >= base_price else "DOWN"
        target_date = (pd.to_datetime(row['date']) + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
        
        new_records.append({
            "log_timestamp": timestamp_str,
            "forecast_target_date": target_date,
            "region": region,
            "model_version": model_version,
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
    combined.drop_duplicates(subset=["forecast_target_date", "region", "model_version"], keep="last", inplace=True)
    combined.to_csv(HISTORY_CSV_PATH, index=False)
    
    logger.info(f"Logged {len(new_records)} predictions for region '{region}' under version '{model_version}'.")
    return len(new_records)


def backfill_actual_prices_and_evaluate() -> pd.DataFrame:
    """
    Fetches actual historical gas prices up to today, matches them against past forecasted target dates,
    updates actual prices, error metrics, and directional hit outcomes in prediction_history.csv.
    """
    ensure_history_store()
    history_df = pd.read_csv(HISTORY_CSV_PATH)
    
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
