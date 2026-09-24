"""
Unified Regional Metro Execution Pipeline Runner (src/locations/runner.py)
Provides a single, parameterized entry point for executing localized 6-step forecasting pipelines
across all registered metropolitan calibration hubs (Issue #433).
"""

from __future__ import annotations

import os
import sys
import logging
import importlib
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from src.regional_metadata import get_regional_metadata
from src.event_analyzer import process_event_dataset
from src.models import train_multi_horizon_models
from src.prediction_logger import (
    log_predictions,
    backfill_new_region_history,
    resolve_model_tag,
    backfill_actual_prices_and_evaluate
)
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)

# Regional module mapping
REGION_MODULE_MAP = {
    "tulsa": ("src.locations.tulsa.regional", "fetch_tulsa_market_data", "get_tulsa_regional_events", "Tulsa_OK"),
    "tulsa_ok": ("src.locations.tulsa.regional", "fetch_tulsa_market_data", "get_tulsa_regional_events", "Tulsa_OK"),
    "newark": ("src.locations.newark.regional", "fetch_newark_market_data", "get_newark_regional_events", "Newark_NJ"),
    "newark_de": ("src.locations.newark.regional", "fetch_newark_market_data", "get_newark_regional_events", "Newark_NJ"),
    "cincinnati": ("src.locations.cincinnati.regional", "fetch_cincinnati_market_data", "get_cincinnati_regional_events", "Cincinnati_OH"),
    "cincinnati_oh": ("src.locations.cincinnati.regional", "fetch_cincinnati_market_data", "get_cincinnati_regional_events", "Cincinnati_OH"),
    "greenville": ("src.locations.greenville.regional", "fetch_greenville_market_data", "get_greenville_regional_events", "Greenville_NC"),
    "greenville_nc": ("src.locations.greenville.regional", "fetch_greenville_market_data", "get_greenville_regional_events", "Greenville_NC"),
    "charlotte": ("src.locations.charlotte.regional", "fetch_charlotte_market_data", "get_charlotte_regional_events", "Charlotte_NC"),
    "charlotte_nc": ("src.locations.charlotte.regional", "fetch_charlotte_market_data", "get_charlotte_regional_events", "Charlotte_NC"),
    "oakland": ("src.locations.oakland.regional", "fetch_oakland_market_data", "get_oakland_regional_events", "Oakland_CA"),
    "oakland_ca": ("src.locations.oakland.regional", "fetch_oakland_market_data", "get_oakland_regional_events", "Oakland_CA"),
    "port_st_lucie": ("src.locations.port_st_lucie.regional", "fetch_port_st_lucie_market_data", "get_port_st_lucie_regional_events", "Port_St_Lucie_FL"),
    "port_st_lucie_fl": ("src.locations.port_st_lucie.regional", "fetch_port_st_lucie_market_data", "get_port_st_lucie_regional_events", "Port_St_Lucie_FL"),
}


def run_regional_pipeline(
    region_id: str,
    live_pump_price: Optional[float] = None,
    use_llm_api: bool = False,
    model_type: str = "ridge",
    log_wandb: bool = False
) -> Dict[str, Any]:
    """
    Executes the standardized 6-step localized forecasting pipeline for any regional calibration hub (Issue #433).
    
    1. Ingest Market Data for Region & Calibrate Live Pump Price
    2. Extract Features from Regional News, Weather, Maritime & Social Feeds
    3. Multi-Horizon Feature Engineering (1D-5D) with Region-Specific Routing & RVP
    4. Model Training & Ablation Evaluation
    5. Real-Time Scenario Simulations
    6. MLOps Prediction Logging & Scoreboard Backfilling
    """
    reg_clean = region_id.lower().strip()
    meta = get_regional_metadata(reg_clean)
    display_name = meta.get("display_name", region_id.title())
    
    mod_info = REGION_MODULE_MAP.get(reg_clean)
    if mod_info:
        module_path, fetch_fn_name, events_fn_name, default_logger_key = mod_info
        logger_region_key = meta.get("logger_region_key", default_logger_key)
        reg_module = importlib.import_module(module_path)
        fetch_market_fn = getattr(reg_module, fetch_fn_name)
        get_events_fn = getattr(reg_module, events_fn_name)
    else:
        logger_region_key = meta.get("logger_region_key", display_name.replace(" ", "_"))
        from src.data_ingestion import fetch_market_data
        fetch_market_fn = lambda start_date="2022-01-01", live_current_price=None: fetch_market_data(start_date=start_date)
        get_events_fn = lambda: []

    if live_pump_price is None:
        live_res = fetch_live_metro_retail_price(logger_region_key)
        live_pump_price = live_res["price"]

    logger.info(f"Executing Regional Pipeline for '{display_name}' ({logger_region_key}) | Anchor: ${live_pump_price:.2f}/gal")

    # Step 1: Ingest Market Data for Region
    import inspect
    sig = inspect.signature(fetch_market_fn)
    kwargs = {"start_date": "2022-01-01"}
    if "live_current_price" in sig.parameters:
        kwargs["live_current_price"] = live_pump_price
    elif "live_pump_price" in sig.parameters:
        kwargs["live_pump_price"] = live_pump_price
    elif "live_oakland_price" in sig.parameters:
        kwargs["live_oakland_price"] = live_pump_price
    elif "live_oh_price" in sig.parameters:
        kwargs["live_oh_price"] = live_pump_price

    market_df = fetch_market_fn(**kwargs)

    # Step 2: Extract Features from Localized News & Feeds
    events_raw = get_events_fn()
    has_events = False
    if events_raw is not None:
        if isinstance(events_raw, pd.DataFrame):
            has_events = not events_raw.empty
        elif hasattr(events_raw, '__len__'):
            has_events = len(events_raw) > 0
        else:
            has_events = bool(events_raw)

    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api) if has_events else None

    # Step 3 & 4: Multi-Horizon Feature Engineering & Model Training (1D-5D)
    multi_horizon_results = train_multi_horizon_models(
        market_df=market_df,
        events_df=events_df,
        horizons=[1, 2, 3, 4, 5],
        region=logger_region_key,
        model_type=model_type,
        log_wandb=log_wandb
    )
    results = multi_horizon_results[5]
    splits = results['splits']
    results['multi_horizon_results'] = multi_horizon_results

    # Step 5: Multi-Horizon Prediction Logging
    model_tag = resolve_model_tag(model_type, use_llm=True)
    for h in [1, 2, 3, 4, 5]:
        h_res = multi_horizon_results[h]
        h_splits = h_res['splits']
        live_base = float(h_splits.get('live_current_price', h_splits['test_df']['gasoline_rbob'].iloc[-1]))
        
        # Calculate target delivery date
        log_ts = pd.Timestamp.now(tz="UTC")
        trading_days_ahead = int(h)
        target_date = (log_ts + pd.offsets.BDay(trading_days_ahead)).strftime("%Y-%m-%d")
        
        last_row_hybrid = h_splits.get('X_live_hybrid', h_splits['X_test_hybrid'].iloc[-1:])
        last_row_quant = h_splits.get('X_live_quant', h_splits['X_test_quant'].iloc[-1:])
        
        pred_h = float(h_res['model_hybrid'].predict(last_row_hybrid)[0])
        pred_q = float(h_res['model_quant'].predict(last_row_quant)[0])
        
        if h_res.get('is_return_target', False) or h_splits.get('predict_returns', False):
            pred_h = float(live_base * (1.0 + np.clip(pred_h, -0.25, 0.25)))
            pred_q = float(live_base * (1.0 + np.clip(pred_q, -0.25, 0.25)))

        log_predictions(
            target_date=target_date,
            predicted_price=pred_h,
            quant_baseline_price=pred_q,
            current_base_price=live_base,
            region=logger_region_key,
            forecast_horizon_days=h,
            model_version=model_tag,
            is_retroactive_backtest=False
        )

    # Optional historical backfill if needed
    try:
        backfill_new_region_history(
            region=logger_region_key,
            test_df=splits['test_df'],
            predicted_prices=results['y_pred_hybrid'],
            actual_prices=splits['y_test_hybrid'].values if 'y_test_hybrid' in splits else None,
            forecast_horizon_days=5,
            quant_baseline_prices=results['y_pred_quant'],
            model_version=model_tag
        )
    except Exception as e:
        logger.debug(f"Regional backfill history update skipped: {e}")

    results["region"] = logger_region_key
    results["display_name"] = display_name
    results["live_pump_price"] = live_pump_price
    return results
