"""
Prediction Logger & Model Performance Tracking Engine (src/prediction_logger.py)
Logs model predictions over time, backfills actual historical prices, evaluates rolling error metrics
(MAE, RMSE, Directional Hit Rate), and enables continuous iterative improvement.
"""

import os
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

HISTORY_CSV_PATH = os.path.join("data", "prediction_history.csv")

def ensure_history_store():
    """Ensures data directory and prediction_history.csv file exist with standard and extended MLOps schema."""
    os.makedirs("data", exist_ok=True)
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
        "directional_hit",
        "llm_price_pressure",
        "llm_supply_disruption",
        "quant_baseline_5d_price",
        "llm_augmentation_delta",
        "prediction_lower_95ci",
        "prediction_upper_95ci",
        "within_95ci_hit",
        "data_source_provenance",
        "forecast_horizon_days"
    ]
    if not os.path.exists(HISTORY_CSV_PATH) or os.path.getsize(HISTORY_CSV_PATH) == 0:
        df = pd.DataFrame(columns=columns)
        df.to_csv(HISTORY_CSV_PATH, index=False)
        logger.info(f"Initialized new prediction history log at {HISTORY_CSV_PATH}")
    else:
        # Migrate existing CSV if missing extended columns
        try:
            df = pd.read_csv(HISTORY_CSV_PATH)
            updated = False
            for col in columns:
                if col not in df.columns:
                    df[col] = np.nan
                    updated = True
            if updated:
                df.to_csv(HISTORY_CSV_PATH, index=False)
                logger.info(f"Migrated existing prediction history log with extended MLOps schema columns.")
        except Exception as e:
            logger.warning(f"Failed to inspect/migrate prediction history CSV: {e}")


def sync_predictions_to_cloud(df: Optional[pd.DataFrame] = None) -> dict:
    """
    Synchronizes prediction history records to Cloud DB (Turso Edge / Cloudflare D1 / Neon Postgres).
    Provides automatic fallback to local CSV datastore if offline or if credentials are missing.
    """
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    cf_url = os.environ.get("CLOUDFLARE_CACHE_URL")
    cf_token = os.environ.get("CLOUDFLARE_AUTH_TOKEN")

    if df is None:
        ensure_history_store()
        try:
            df = pd.read_csv(HISTORY_CSV_PATH)
        except Exception as e:
            logger.warning(f"Could not read prediction history CSV for cloud sync: {e}")
            return {"status": "offline_fallback", "synced_rows": 0, "provider": "local_csv", "reason": str(e)}

    if df is None or df.empty:
        return {"status": "synced", "synced_rows": 0, "provider": "local_csv"}

    # 1. Attempt Turso Edge SQLite sync if credentials present
    if turso_url and turso_token:
        try:
            if turso_url.startswith("turso://"):
                turso_url = "https://" + turso_url[8:]
            elif turso_url.startswith("libsql://"):
                turso_url = "https://" + turso_url[9:]
            endpoint = f"{turso_url.rstrip('/')}/v2/pipeline"
            headers = {
                "Authorization": f"Bearer {turso_token}",
                "Content-Type": "application/json",
            }
            create_stmt = {
                "type": "execute",
                "stmt": {
                    "sql": """CREATE TABLE IF NOT EXISTS prediction_history (
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
                        PRIMARY KEY (log_timestamp, forecast_target_date, region)
                    )"""
                }
            }
            requests = [create_stmt]
            recent_df = df.tail(50)
            for _, row in recent_df.iterrows():
                requests.append({
                    "type": "execute",
                    "stmt": {
                        "sql": """INSERT OR REPLACE INTO prediction_history (
                            log_timestamp, forecast_target_date, forecast_horizon_days, region, model_version, run_type,
                            headline_trigger, current_base_price, predicted_5d_price, predicted_direction,
                            actual_5d_price, actual_direction, error_dollars, directional_hit,
                            llm_price_pressure, llm_supply_disruption, quant_baseline_5d_price,
                            llm_augmentation_delta, prediction_lower_95ci, prediction_upper_95ci,
                            within_95ci_hit, data_source_provenance
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        "args": [
                            {"type": "text", "value": str(row.get("log_timestamp", ""))},
                            {"type": "text", "value": str(row.get("forecast_target_date", ""))},
                            {"type": "integer", "value": str(int(float(row.get("forecast_horizon_days", 5)))) if pd.notna(row.get("forecast_horizon_days")) else "5"},
                            {"type": "text", "value": str(row.get("region", ""))},
                            {"type": "text", "value": str(row.get("model_version", ""))},
                            {"type": "text", "value": str(row.get("run_type", ""))},
                            {"type": "text", "value": str(row.get("headline_trigger", ""))},
                            {"type": "float", "value": float(row.get("current_base_price", 0.0)) if pd.notna(row.get("current_base_price")) else 0.0},
                            {"type": "float", "value": float(row.get("predicted_5d_price", 0.0)) if pd.notna(row.get("predicted_5d_price")) else 0.0},
                            {"type": "text", "value": str(row.get("predicted_direction", ""))},
                            {"type": "float", "value": float(row.get("actual_5d_price", 0.0)) if pd.notna(row.get("actual_5d_price")) else 0.0},
                            {"type": "text", "value": str(row.get("actual_direction", ""))},
                            {"type": "float", "value": float(row.get("error_dollars", 0.0)) if pd.notna(row.get("error_dollars")) else 0.0},
                            {"type": "float", "value": float(row.get("directional_hit", 0.0)) if pd.notna(row.get("directional_hit")) else 0.0},
                            {"type": "float", "value": float(row.get("llm_price_pressure", 0.0)) if pd.notna(row.get("llm_price_pressure")) else 0.0},
                            {"type": "float", "value": float(row.get("llm_supply_disruption", 0.0)) if pd.notna(row.get("llm_supply_disruption")) else 0.0},
                            {"type": "float", "value": float(row.get("quant_baseline_5d_price", 0.0)) if pd.notna(row.get("quant_baseline_5d_price")) else 0.0},
                            {"type": "float", "value": float(row.get("llm_augmentation_delta", 0.0)) if pd.notna(row.get("llm_augmentation_delta")) else 0.0},
                            {"type": "float", "value": float(row.get("prediction_lower_95ci", 0.0)) if pd.notna(row.get("prediction_lower_95ci")) else 0.0},
                            {"type": "float", "value": float(row.get("prediction_upper_95ci", 0.0)) if pd.notna(row.get("prediction_upper_95ci")) else 0.0},
                            {"type": "float", "value": float(row.get("within_95ci_hit", 0.0)) if pd.notna(row.get("within_95ci_hit")) else 0.0},
                            {"type": "text", "value": str(row.get("data_source_provenance", "yfinance"))}
                        ]
                    }
                })
            requests.append({"type": "close"})
            body = json.dumps({"requests": requests}).encode("utf-8")
            req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    logger.info(f"Successfully synced {len(recent_df)} prediction records to Turso Edge database.")
                    return {"status": "synced", "synced_rows": len(recent_df), "provider": "turso_edge"}
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            logger.warning(f"Turso prediction cloud sync notice: HTTP Error {e.code}: {e.reason} - {err_body}")
        except Exception as e:
            logger.warning(f"Turso prediction cloud sync notice: {e}")

    # 2. Attempt Cloudflare D1 / Edge Worker sync if credentials present
    if cf_url:
        try:
            if cf_url.startswith("http://"):
                cf_url = "https://" + cf_url[7:]
            endpoint = f"{cf_url.rstrip('/')}/api/v1/sync/predictions"
            headers = {"Content-Type": "application/json", "User-Agent": "MidgleyPredictionSync/1.0"}
            if cf_token:
                headers["Authorization"] = f"Bearer {cf_token}"
            clean_df = df.tail(50).astype(object).where(pd.notna(df), None)
            recent_records = clean_df.to_dict(orient="records")
            body = json.dumps({"predictions": recent_records}).encode("utf-8")
            req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Successfully synced {len(recent_records)} prediction records to Cloudflare D1 Edge Worker.")
                    return {"status": "synced", "synced_rows": len(recent_records), "provider": "cloudflare_d1"}
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            logger.warning(f"Cloudflare D1 prediction sync notice: HTTP Error {e.code}: {e.reason} - {err_body}")
        except Exception as e:
            logger.warning(f"Cloudflare D1 prediction sync notice: {e}")

    return {"status": "offline_fallback", "synced_rows": len(df), "provider": "local_csv"}


def get_cloud_sync_status() -> dict:
    """Returns active cloud database sync providers and local CSV store status."""
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    cf_url = os.environ.get("CLOUDFLARE_CACHE_URL")
    neon_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("POSTGRES_URL")

    active_providers = []
    if turso_url:
        active_providers.append("turso_edge_sqlite")
    if cf_url:
        active_providers.append("cloudflare_d1")
    if neon_url:
        active_providers.append("neon_serverless_postgres")

    ensure_history_store()
    total_local_rows = 0
    if os.path.exists(HISTORY_CSV_PATH):
        try:
            df = pd.read_csv(HISTORY_CSV_PATH)
            total_local_rows = len(df)
        except Exception:
            pass

    return {
        "cloud_sync_enabled": len(active_providers) > 0,
        "active_providers": active_providers,
        "primary_store": active_providers[0] if active_providers else "local_csv",
        "fallback_store": "local_csv",
        "total_local_records": total_local_rows,
        "history_file_path": HISTORY_CSV_PATH
    }


def compute_regional_residual_std(
    region: str = None, 
    window_days: int = 30, 
    default_std: float = 0.0612,
    horizon_days: Optional[int] = None
) -> float:
    """
    Computes rolling 30-day standard error of regional prediction residuals (Issue #214, #394).
    sigma_residual = std(actual_5d_price - predicted_5d_price)
    Optionally scales by sqrt(horizon_days / 5) for multi-horizon forecast bounds.
    Returns default_std (0.0612 $/gal) scaled by horizon if evaluated history has < 3 records.
    """
    base_std = default_std
    try:
        if os.path.exists(HISTORY_CSV_PATH):
            df = pd.read_csv(HISTORY_CSV_PATH)
            filtered = filter_evaluated_history_by_window(df, window_days=window_days, region=region, horizon_days=horizon_days)
            if not filtered.empty and 'actual_5d_price' in filtered.columns:
                actuals = filtered['actual_5d_price'].astype(float).values
                preds = filtered['predicted_5d_price'].astype(float).values
                residuals = actuals - preds
                if len(residuals) >= 3:
                    res_std = float(np.std(residuals, ddof=1))
                    return max(0.01, round(res_std, 4))
            
            # If not enough records for specific horizon, compute over all horizons for region
            if horizon_days is not None:
                all_h_filtered = filter_evaluated_history_by_window(df, window_days=window_days, region=region)
                if not all_h_filtered.empty and 'actual_5d_price' in all_h_filtered.columns:
                    actuals = all_h_filtered['actual_5d_price'].astype(float).values
                    preds = all_h_filtered['predicted_5d_price'].astype(float).values
                    residuals = actuals - preds
                    if len(residuals) >= 3:
                        base_std = float(np.std(residuals, ddof=1))
    except Exception as e:
        logger.debug(f"Notice computing regional residual std for {region}: {e}")

    if horizon_days is not None and horizon_days > 0:
        scaled_std = base_std * np.sqrt(horizon_days / 5.0)
        return max(0.01, round(scaled_std, 4))

    return base_std


def resolve_model_tag(
    region: str = "National", 
    model_type: str = "Ridge", 
    custom_version: Optional[str] = None
) -> str:
    """
    Standardizes model version tag generation across national and regional prediction loggers.
    Dynamically resolves active model version (e.g. 'v1.6-Ipatieff') and attaches region and model type.
    Example: 'v1.6-Ipatieff-Tulsa-Ridge' or 'v1.6-Ipatieff-National-Ridge'
    """
    if custom_version:
        return custom_version
    try:
        from src.version import get_model_version
        base_version = get_model_version().replace(" ", "-")
    except Exception:
        base_version = "v1.6-Ipatieff"
    
    clean_region = region.replace("_", "").replace(" ", "")
    clean_model_type = model_type.capitalize()
    return f"{base_version}-{clean_region}-{clean_model_type}"


def log_predictions(
    predictions_df: pd.DataFrame, 
    region: str = "Tulsa_OK", 
    model_version: Optional[str] = None,
    run_type: str = "DAILY_BATCH",
    headline_trigger: str = "",
    forecast_horizon_days: int = 5
) -> int:
    """
    Logs a DataFrame of model predictions into prediction_history.csv.
    Expected columns: ['date', 'current_price', 'predicted_5d_price']
    Optional extended columns: ['forecast_horizon_days', 'llm_price_pressure', 'llm_supply_disruption', 'quant_baseline_5d_price',
                               'llm_augmentation_delta', 'prediction_lower_95ci', 'prediction_upper_95ci',
                               'data_source_provenance']
    """
    if model_version is None:
        model_version = resolve_model_tag(region=region, model_type="Ridge")
    ensure_history_store()
    try:
        history_df = pd.read_csv(HISTORY_CSV_PATH, dtype={"actual_direction": str, "predicted_direction": str})
    except Exception:
        history_df = pd.DataFrame()
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_records = []

    res_std = compute_regional_residual_std(region=region, window_days=30)
    
    for idx, row in predictions_df.iterrows():
        base_price = float(row['current_price'])
        pred_price = float(row['predicted_5d_price'])
        pred_dir = "UP" if pred_price >= base_price else "DOWN"
        
        # Determine forecast horizon
        row_h = row.get('forecast_horizon_days', row.get('horizon_days', row.get('horizon', forecast_horizon_days)))
        try:
            h_days = int(float(row_h)) if pd.notna(row_h) else int(forecast_horizon_days)
        except (ValueError, TypeError):
            h_days = int(forecast_horizon_days)

        if 'forecast_target_date' in row and pd.notna(row['forecast_target_date']):
            target_date = str(row['forecast_target_date'])
        else:
            base_dt = pd.to_datetime(row['date'])
            target_date = pd.bdate_range(start=base_dt, periods=h_days + 1)[-1].strftime("%Y-%m-%d")
        
        quant_base = float(row.get('quant_baseline_5d_price')) if 'quant_baseline_5d_price' in row and pd.notna(row['quant_baseline_5d_price']) else np.nan
        aug_delta = float(row.get('llm_augmentation_delta')) if 'llm_augmentation_delta' in row and pd.notna(row['llm_augmentation_delta']) else (round(pred_price - quant_base, 4) if pd.notna(quant_base) else 0.0)

        lower_ci = float(row.get('prediction_lower_95ci')) if 'prediction_lower_95ci' in row and pd.notna(row['prediction_lower_95ci']) else round(pred_price - (1.96 * res_std), 4)
        upper_ci = float(row.get('prediction_upper_95ci')) if 'prediction_upper_95ci' in row and pd.notna(row['prediction_upper_95ci']) else round(pred_price + (1.96 * res_std), 4)

        
        new_records.append({
            "log_timestamp": timestamp_str,
            "forecast_target_date": target_date,
            "forecast_horizon_days": h_days,
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
            "directional_hit": np.nan,
            "llm_price_pressure": float(row.get('llm_price_pressure')) if 'llm_price_pressure' in row and pd.notna(row['llm_price_pressure']) else 0.0,
            "llm_supply_disruption": float(row.get('llm_supply_disruption')) if 'llm_supply_disruption' in row and pd.notna(row['llm_supply_disruption']) else 0.0,
            "quant_baseline_5d_price": round(quant_base, 4) if pd.notna(quant_base) else round(base_price, 4),
            "llm_augmentation_delta": round(aug_delta, 4),
            "prediction_lower_95ci": round(lower_ci, 4),
            "prediction_upper_95ci": round(upper_ci, 4),
            "within_95ci_hit": np.nan,
            "data_source_provenance": str(row.get('data_source_provenance', 'yfinance'))
        })
        
    new_df = pd.DataFrame(new_records)
    combined = pd.concat([history_df, new_df], ignore_index=True)
    combined.drop_duplicates(subset=["forecast_target_date", "forecast_horizon_days", "region", "model_version", "run_type"], keep="last", inplace=True)
    combined.to_csv(HISTORY_CSV_PATH, index=False)
    try:
        sync_predictions_to_cloud(combined)
    except Exception as e:
        logger.warning(f"Background prediction cloud sync notice: {e}")
    
    logger.info(f"Logged {len(new_records)} predictions ({forecast_horizon_days}d horizon) for region '{region}' under version '{model_version}' (Run Type: {run_type}).")
    try:
        from src.healthcheck_monitor import ping_healthcheck_success
        ping_healthcheck_success(
            log_message=f"Logged {len(new_records)} predictions for {region} ({model_version}, {run_type})"
        )
    except Exception as e:
        logger.debug(f"Healthcheck heartbeat notice: {e}")
    return len(new_records)



RBOB_ACTUALS_CACHE_FILE = "data/rbob_actuals_cache.json"
_GLOBAL_RBOB_ACTUALS_CACHE: Dict[str, float] = {}


def validate_price_plausibility(price: Optional[float], region: str = "National", is_retail: bool = True) -> bool:
    """
    Validates whether a price observation falls within economically plausible bands (Issue #399).
    Retail gasoline plausibility band: [$1.00, $10.00]/gal.
    Wholesale RBOB futures plausibility band: [$0.50, $7.00]/gal.
    """
    if price is None:
        return False
    try:
        val = float(price)
        if np.isnan(val) or np.isinf(val):
            return False
        if is_retail and region != "National":
            return 1.00 <= val <= 10.00
        elif region == "National" and not is_retail:
            return 0.50 <= val <= 7.00
        return 0.50 <= val <= 10.00
    except (ValueError, TypeError):
        return False


def cleanse_prediction_history(csv_path: Optional[str] = None) -> int:
    """
    Cleanses Test_Region, Test_*, and corrupted test fixture rows from prediction_history.csv (Issue #399).
    Returns the number of rows purged.
    """
    path = csv_path or HISTORY_CSV_PATH
    if not os.path.exists(path):
        return 0
    try:
        df = pd.read_csv(path)
        initial_len = len(df)
        if initial_len == 0:
            return 0
        # Filter out Test_Region and test artifacts
        valid_mask = ~df['region'].astype(str).str.startswith("Test_") & ~df['region'].astype(str).str.contains("Test", case=False)
        # Filter out NaN or completely invalid base prices
        valid_mask = valid_mask & df['current_base_price'].notna() & (df['current_base_price'] > 0.10)
        cleansed_df = df[valid_mask].copy()
        purged = initial_len - len(cleansed_df)
        if purged > 0:
            cleansed_df.to_csv(path, index=False)
            logger.info(f"Cleanse: Purged {purged} invalid/test fixture rows from {path}.")
        return purged
    except Exception as e:
        logger.warning(f"Failed to cleanse prediction history at {path}: {e}")
        return 0


def backfill_actual_prices_and_evaluate(
    target_region: Optional[str] = None,
    actuals_map_override: Optional[dict] = None,
    eia_feed_override: Optional[Any] = None,
    csv_path: Optional[str] = None,
    force_eval: bool = False
) -> pd.DataFrame:
    """
    Fetches actual historical gas prices up to today, matches them against past forecasted target dates,
    updates actual prices, error metrics, and directional hit outcomes in prediction_history.csv.
    Uses official observed U.S. EIA weekly retail prices by PADD/State (Issue #403, #391, #392) as ground truth.
    Eliminates synthetic offset ladders and identity fallbacks.
    Allows dependency injection for testing without network calls (Issue #395).
    """
    global _GLOBAL_RBOB_ACTUALS_CACHE
    target_csv = csv_path or HISTORY_CSV_PATH
    if not csv_path:
        ensure_history_store()
    try:
        history_df = pd.read_csv(target_csv)
    except Exception as e:
        logger.warning(f"Could not read prediction history log ({e}). Returning empty DataFrame.")
        return pd.DataFrame()
    
    if history_df.empty:
        logger.warning("Prediction history log is empty. No predictions to evaluate.")
        return history_df

    # If dependency injection or force_eval is active, proceed even under TESTING=1 (Issue #395)
    is_injected = (actuals_map_override is not None) or (eia_feed_override is not None) or (csv_path is not None) or force_eval
    if not is_injected and os.environ.get("TESTING") == "1" and os.environ.get("TEST_YFINANCE_FORCE") != "1":
        logger.debug("TESTING=1: Returning cached prediction history without online yfinance download.")
        return history_df
        
    history_df['actual_direction'] = history_df['actual_direction'].astype(object)
    history_df['predicted_direction'] = history_df['predicted_direction'].astype(object)
    
    logger.info("Fetching actual historical market prices to backfill prediction log...")
    
    if actuals_map_override is not None:
        actuals_map = actuals_map_override
    else:
        actuals_map = _GLOBAL_RBOB_ACTUALS_CACHE
        if not actuals_map and os.path.exists(RBOB_ACTUALS_CACHE_FILE):
            try:
                with open(RBOB_ACTUALS_CACHE_FILE, "r", encoding="utf-8") as f:
                    actuals_map = json.load(f)
                    _GLOBAL_RBOB_ACTUALS_CACHE = actuals_map
            except Exception:
                actuals_map = {}

        if not actuals_map and (not is_injected or force_eval):
            try:
                data = yf.download("RB=F", start="2022-01-01", progress=False)
                close_series = data['Close']['RB=F'] if isinstance(data.columns, pd.MultiIndex) else data['Close']
                dates_formatted = [d.strftime("%Y-%m-%d") for d in close_series.index]
                actuals_df = pd.DataFrame({'date_str': dates_formatted, 'actual_rbob': close_series.values})
                actuals_map = actuals_df.set_index('date_str')['actual_rbob'].to_dict()
                _GLOBAL_RBOB_ACTUALS_CACHE = actuals_map
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(RBOB_ACTUALS_CACHE_FILE)), exist_ok=True)
                    with open(RBOB_ACTUALS_CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(actuals_map, f, indent=2)
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Could not download actuals from yfinance: {e}")
                actuals_map = {}
        
    if eia_feed_override is not None:
        eia_feed = eia_feed_override
    else:
        try:
            from src.eia_retail_feed import EIARetailFeed
            eia_feed = EIARetailFeed()
        except Exception as e:
            logger.debug(f"EIARetailFeed unavailable, fallback to basis: {e}")
            eia_feed = None

    unevaluated_mask = history_df['actual_5d_price'].isna()
    if target_region:
        unevaluated_mask = unevaluated_mask & (history_df['region'] == target_region)
    target_indices = history_df[unevaluated_mask].index
    if len(target_indices) == 0:
        return history_df

    updated = False
    for idx in target_indices:
        row = history_df.loc[idx]
        target_date_str = str(row['forecast_target_date'])
        base_price = float(row['current_base_price'])
        pred_price = float(row['predicted_5d_price'])
        pred_dir = str(row['predicted_direction'])
        reg = str(row['region'])
        
        actual_price = None
        source_prov = None

        if reg == "National":
            if actuals_map and target_date_str in actuals_map:
                candidate_price = float(actuals_map[target_date_str])
                if validate_price_plausibility(candidate_price, "National", is_retail=False):
                    actual_price = candidate_price
                    source_prov = "yfinance:RB=F"
            elif eia_feed:
                candidate_price = eia_feed.get_retail_price_for_date("National", target_date_str)
                if validate_price_plausibility(candidate_price, "National", is_retail=True):
                    actual_price = candidate_price
                    source_prov = "eia_retail_feed:GASREGW"
        else:
            # Regional metro ground-truth lookup via EIA weekly retail feed (Issue #403, #391, #392)
            if eia_feed:
                candidate_price = eia_feed.get_retail_price_for_date(reg, target_date_str)
                if validate_price_plausibility(candidate_price, reg, is_retail=True):
                    actual_price = candidate_price
                    source_prov = f"eia_retail_feed:{reg}"

        if actual_price is not None:
            actual_dir = "UP" if actual_price >= base_price else "DOWN"
            err_dollars = abs(actual_price - pred_price)
            hit = 1 if pred_dir == actual_dir else 0

            # 95% Confidence Interval Coverage Hit Evaluation (Issue #394)
            lower_ci = row.get('prediction_lower_95ci')
            upper_ci = row.get('prediction_upper_95ci')
            if pd.isna(lower_ci) or pd.isna(upper_ci):
                h_days = _infer_horizon_days(row)
                r_std = compute_regional_residual_std(reg, window_days=30, horizon_days=h_days)
                half_width = 1.96 * r_std
                lower_ci = pred_price - half_width
                upper_ci = pred_price + half_width
                history_df.at[idx, 'prediction_lower_95ci'] = round(lower_ci, 4)
                history_df.at[idx, 'prediction_upper_95ci'] = round(upper_ci, 4)

            ci_hit = 1 if (float(lower_ci) <= actual_price <= float(upper_ci)) else 0

            history_df.at[idx, 'actual_5d_price'] = round(actual_price, 4)
            history_df.at[idx, 'actual_direction'] = str(actual_dir)
            history_df.at[idx, 'error_dollars'] = round(err_dollars, 4)
            history_df.at[idx, 'directional_hit'] = hit
            history_df.at[idx, 'within_95ci_hit'] = ci_hit
            if source_prov:
                history_df.at[idx, 'data_source_provenance'] = source_prov
            updated = True
            
    if updated:
        history_df.to_csv(target_csv, index=False)
        if target_csv == HISTORY_CSV_PATH and os.environ.get("TESTING") != "1":
            try:
                sync_predictions_to_cloud(history_df)
            except Exception as e:
                logger.warning(f"Background prediction cloud sync notice: {e}")
        logger.info("Successfully backfilled actual prices and updated performance metrics.")
        
        # Ingest evaluated memories/anomalies into AgentMemoryManager (Retain - Issue #230, #326)
        if target_csv == HISTORY_CSV_PATH and os.environ.get("TESTING") != "1":
            try:
                from src.agent_memory import AgentMemoryManager
                mem_mgr = AgentMemoryManager()
                eval_candidates = history_df[history_df['actual_5d_price'].notna()]
                if target_region:
                    eval_candidates = eval_candidates[eval_candidates['region'] == target_region]
                for _, row in eval_candidates.tail(10).iterrows():
                    err = float(row.get('error_dollars', 0.0))
                    reg = str(row.get('region', target_region or 'National'))
                    pred = float(row.get('predicted_5d_price', 0.0))
                    act = float(row.get('actual_5d_price', 0.0))
                    target_d = str(row.get('forecast_target_date', ''))
                    anom_type = "LARGE_OVERESTIMATE" if (pred - act) >= 0.25 else ("LARGE_UNDERESTIMATE" if (act - pred) >= 0.25 else ("DIRECTIONAL_FLIP" if row.get('directional_hit') == 0.0 and abs(pred - act) >= 0.05 else "NORMAL"))
                    # Only retain genuine prediction anomaly shocks into episodic memory to protect token spend
                    if anom_type != "NORMAL":
                        mem_mgr.retain(
                            content=f"Evaluated forecast for {reg} on {target_d}: Predicted ${pred:.4f}, Actual ${act:.4f}, Error ${err:+.4f}/gal ({anom_type})",
                            region=reg,
                            memory_type="anomaly_shock",
                            anomaly_type=anom_type,
                            error_dollars=err,
                            predicted_price=pred,
                        actual_price=act,
                        forecast_target_date=target_d,
                        metadata={"provenance_source": str(row.get("provenance_source", "yfinance"))}
                    )
        except Exception as e:
            logger.debug(f"Agent memory retention notice: {e}")
            
    return history_df


def backfill_new_region_history(
    test_dates,
    base_prices,
    predicted_prices,
    region: str,
    model_version: Optional[str] = None,
    forecast_horizon_days: int = 5
) -> int:
    """
    Backfills historical test split predictions for a newly added region into prediction_history.csv
    and automatically matches/evaluates mature target dates against ground-truth market prices (Issue #314).
    """
    if model_version is None:
        try:
            from src.version import get_model_version
            model_version = get_model_version().replace(" ", "-")
        except Exception:
            model_version = "v1.6-Ipatieff"
    dates_arr = getattr(test_dates, 'values', test_dates)
    base_arr = getattr(base_prices, 'values', base_prices)
    pred_arr = getattr(predicted_prices, 'values', predicted_prices)

    pred_log_df = pd.DataFrame({
        'date': dates_arr,
        'current_price': base_arr,
        'predicted_5d_price': pred_arr,
        'forecast_horizon_days': forecast_horizon_days
    })
    
    n_logged = log_predictions(pred_log_df, region=region, model_version=model_version, forecast_horizon_days=forecast_horizon_days)
    backfill_actual_prices_and_evaluate()
    logger.info(f"Backfilled and evaluated {n_logged} historical prediction records for region '{region}' ({forecast_horizon_days}d horizon).")
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


def _infer_horizon_days(row) -> int:
    """Infers the forecast horizon in trading/business days from record or date difference."""
    if 'forecast_horizon_days' in row and pd.notna(row['forecast_horizon_days']):
        try:
            val = int(float(row['forecast_horizon_days']))
            if 1 <= val <= 30:
                return val
        except (ValueError, TypeError):
            pass
    try:
        if pd.notna(row.get('forecast_target_date')) and pd.notna(row.get('log_timestamp')):
            log_d = str(row['log_timestamp'])[:10]
            tgt_d = str(row['forecast_target_date'])[:10]
            if tgt_d > log_d:
                bdays = int(np.busday_count(log_d, tgt_d))
                return max(1, min(30, bdays))
    except Exception:
        pass
    return 5


def filter_evaluated_history_by_window(
    df: pd.DataFrame, 
    window_days: int | str = 30, 
    region: str = None,
    horizon_days: Optional[int | str] = None
) -> pd.DataFrame:
    """Filters evaluated prediction history records by rolling window (in days), region, and forecast horizon."""
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
            cutoff_dt = max_dt - pd.to_timedelta(w_int, unit='D')
            eval_df = eval_df[eval_df['target_dt'] >= cutoff_dt]
        except (ValueError, TypeError):
            pass

    if eval_df.empty:
        return eval_df

    if horizon_days is not None and str(horizon_days).lower() not in ["all", "none", ""]:
        try:
            h_int = int(horizon_days)
            inferred = eval_df.apply(_infer_horizon_days, axis=1)
            eval_df = eval_df[inferred == h_int]
        except (ValueError, TypeError):
            pass

    return eval_df


def compute_rolling_scoreboard_metrics(
    window_days: int | str = 30, 
    region: str = None,
    horizon_days: Optional[int | str] = None
) -> dict:
    """
    Computes rolling performance metrics (MAE, RMSE, MAPE, Directional Hit Rate %,
    Naive Persistence Baseline MAE, and Model MAE Uplift %) over a given rolling day window and horizon.
    """
    df = backfill_actual_prices_and_evaluate()
    filtered_df = filter_evaluated_history_by_window(df, window_days=window_days, region=region, horizon_days=horizon_days)

    h_filter = int(horizon_days) if (horizon_days is not None and str(horizon_days).lower() not in ["all", "none", ""]) else "All"

    if filtered_df.empty:
        return {
            "window_days": window_days,
            "region_filter": region or "All",
            "horizon_filter": h_filter,
            "total_evaluations": 0,
            "mae_dollars": 0.0,
            "rmse_dollars": 0.0,
            "mape_pct": 0.0,
            "directional_hit_rate_pct": 0.0,
            "naive_persistence_mae": 0.0,
            "model_uplift_mae_pct": 0.0,
            "empirical_95ci_coverage_pct": 0.0,
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

    # Empirical 95% Confidence Interval Coverage Hit Rate (Issue #394)
    if 'within_95ci_hit' in filtered_df.columns and filtered_df['within_95ci_hit'].notna().any():
        ci_hits = filtered_df['within_95ci_hit'].dropna().astype(float)
        ci_coverage = float(ci_hits.mean() * 100.0) if len(ci_hits) > 0 else 0.0
    else:
        ci_coverage = 0.0

    naive_errors = np.abs(actuals - bases)
    naive_mae = float(np.mean(naive_errors)) if len(naive_errors) > 0 else 0.0

    if naive_mae > 0:
        model_uplift = float(((naive_mae - mae) / naive_mae) * 100.0)
    else:
        model_uplift = 0.0

    return {
        "window_days": window_days,
        "region_filter": region or "All",
        "horizon_filter": h_filter,
        "total_evaluations": n_eval,
        "mae_dollars": round(mae, 4),
        "rmse_dollars": round(rmse, 4),
        "mape_pct": round(mape, 2),
        "directional_hit_rate_pct": round(hit_rate, 2),
        "naive_persistence_mae": round(naive_mae, 4),
        "model_uplift_mae_pct": round(model_uplift, 2),
        "empirical_95ci_coverage_pct": round(ci_coverage, 2),
    }


def compute_regional_scoreboard_breakdown(
    window_days: int | str = 30,
    horizon_days: Optional[int | str] = None
) -> list[dict]:
    """Computes rolling performance metrics for each active region under optional horizon filter."""
    df = backfill_actual_prices_and_evaluate()
    if df.empty or 'actual_5d_price' not in df.columns:
        return []

    eval_df = df.dropna(subset=['actual_5d_price']).copy()
    if eval_df.empty:
        return []

    regions = eval_df['region'].unique()
    breakdown = []

    for reg in sorted(regions):
        metrics = compute_rolling_scoreboard_metrics(window_days=window_days, region=reg, horizon_days=horizon_days)
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
                "empirical_95ci_coverage_pct": metrics["empirical_95ci_coverage_pct"],
            })

    return breakdown


def compute_horizon_scoreboard_breakdown(
    window_days: int | str = 30, 
    region: str = None,
    horizons: Optional[list[int]] = None
) -> list[dict]:
    """
    Computes rolling performance metrics broken down across discrete forecast horizons (1d through 5d).
    """
    if horizons is None:
        horizons = [1, 2, 3, 4, 5]

    breakdown = []
    horizon_labels = {
        1: "1-Day (24h Ahead)",
        2: "2-Day (48h Ahead)",
        3: "3-Day (72h Ahead)",
        4: "4-Day (96h Ahead)",
        5: "5-Day (1-Week Ahead)"
    }

    for h in horizons:
        metrics = compute_rolling_scoreboard_metrics(window_days=window_days, region=region, horizon_days=h)
        label = horizon_labels.get(h, f"{h}-Day Forward")
        breakdown.append({
            "horizon_days": h,
            "horizon_label": label,
            "evaluations": metrics["total_evaluations"],
            "mae_dollars": metrics["mae_dollars"],
            "rmse_dollars": metrics["rmse_dollars"],
            "mape_pct": metrics["mape_pct"],
            "directional_hit_rate_pct": metrics["directional_hit_rate_pct"],
            "naive_persistence_mae": metrics["naive_persistence_mae"],
            "model_uplift_mae_pct": metrics["model_uplift_mae_pct"],
            "empirical_95ci_coverage_pct": metrics["empirical_95ci_coverage_pct"],
        })

    return breakdown


def get_recent_evaluated_records(
    region: str = None, 
    limit: int = 50,
    horizon_days: Optional[int | str] = None
) -> list[dict]:
    """Returns chronologically sorted evaluated forecast records."""
    df = backfill_actual_prices_and_evaluate()
    filtered_df = filter_evaluated_history_by_window(df, window_days="all", region=region, horizon_days=horizon_days)

    if filtered_df.empty:
        return []

    recent_df = filtered_df.tail(limit).copy()
    records = []

    for idx, row in recent_df.iterrows():
        h_val = int(float(row.get("forecast_horizon_days"))) if pd.notna(row.get("forecast_horizon_days")) else _infer_horizon_days(row)
        records.append({
            "log_timestamp": str(row.get("log_timestamp", "")),
            "forecast_target_date": str(row.get("forecast_target_date", "")),
            "forecast_horizon_days": h_val,
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


def compute_mlops_observability_summary(window_days: int | str = 30) -> dict:
    """
    Computes MLOps observability statistics over evaluated predictions:
    - LLM Intelligence Augmentation Win Rate (vs Pure Quant Baseline)
    - 95% Confidence Interval Coverage Hit Rate %
    - Average LLM Price Pressure & Supply Disruption
    - Performance Breakdown by Data Source Provenance
    """
    df = backfill_actual_prices_and_evaluate()
    filtered_df = filter_evaluated_history_by_window(df, window_days=window_days)

    if filtered_df.empty:
        return {
            "window_days": window_days,
            "total_evaluations": 0,
            "llm_augmentation_win_rate_pct": 0.0,
            "ci_95_coverage_pct": 0.0,
            "avg_llm_price_pressure": 0.0,
            "avg_llm_supply_disruption": 0.0,
            "provenance_breakdown": {}
        }

    n_eval = len(filtered_df)

    # 1. LLM Augmentation Win Rate calculation
    # Quant baseline error vs Hybrid LLM error
    if 'quant_baseline_5d_price' in filtered_df.columns:
        actuals = filtered_df['actual_5d_price'].astype(float)
        preds = filtered_df['predicted_5d_price'].astype(float)
        quant_preds = filtered_df['quant_baseline_5d_price'].astype(float).fillna(filtered_df['current_base_price'].astype(float))
        
        hybrid_errors = (actuals - preds).abs()
        quant_errors = (actuals - quant_preds).abs()
        llm_wins = (hybrid_errors <= quant_errors).sum()
        llm_win_rate = float((llm_wins / n_eval) * 100.0)
    else:
        llm_win_rate = 50.0

    # 2. 95% CI Coverage Hit Rate
    if 'within_95ci_hit' in filtered_df.columns and filtered_df['within_95ci_hit'].notna().any():
        ci_hits = filtered_df['within_95ci_hit'].dropna().astype(float)
        ci_coverage = float(ci_hits.mean() * 100.0) if len(ci_hits) > 0 else 0.0
    else:
        ci_coverage = 0.0

    # 3. Average Feature Attribution Scores
    avg_pressure = float(filtered_df['llm_price_pressure'].dropna().mean()) if 'llm_price_pressure' in filtered_df.columns and filtered_df['llm_price_pressure'].notna().any() else 0.0
    avg_disruption = float(filtered_df['llm_supply_disruption'].dropna().mean()) if 'llm_supply_disruption' in filtered_df.columns and filtered_df['llm_supply_disruption'].notna().any() else 0.0

    # 4. Data Source Provenance Breakdown
    provenance_bdown = {}
    if 'data_source_provenance' in filtered_df.columns:
        for prov, group in filtered_df.groupby('data_source_provenance'):
            if not group.empty and 'error_dollars' in group.columns:
                provenance_bdown[str(prov)] = {
                    "count": len(group),
                    "mae_dollars": round(float(group['error_dollars'].mean()), 4)
                }

    return {
        "window_days": window_days,
        "total_evaluations": n_eval,
        "llm_augmentation_win_rate_pct": round(llm_win_rate, 2),
        "ci_95_coverage_pct": round(ci_coverage, 2),
        "avg_llm_price_pressure": round(avg_pressure, 4),
        "avg_llm_supply_disruption": round(avg_disruption, 4),
        "provenance_breakdown": provenance_bdown
    }


