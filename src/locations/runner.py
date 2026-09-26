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
    "newark": ("src.locations.newark.regional", "fetch_newark_market_data", "get_newark_regional_events", "Newark_DE"),
    "newark_de": ("src.locations.newark.regional", "fetch_newark_market_data", "get_newark_regional_events", "Newark_DE"),
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

    # Step 5: Real-Time Scenario Simulations & Prediction Logging
    last_row_hybrid_5 = splits.get('X_live_hybrid', splits['X_test_hybrid'].iloc[-1:])
    raw_pred_5 = float(results.get('live_pred_price', results['model_hybrid'].predict(last_row_hybrid_5)[0]))
    last_hist_5 = float(splits.get('live_current_price', splits['test_df']['gasoline_rbob'].iloc[-1]))
    base_ret_5 = (raw_pred_5 - last_hist_5) / last_hist_5 if last_hist_5 > 0 else 0.0
    baseline_forecast = live_pump_price * (1.0 + base_ret_5)

    default_scenarios = [
        {"name": "Scenario 1: Regional Supply Disruption", "headline": "Regional refinery flaring and rack outage halts distribution.", "shock_pct": 0.045},
        {"name": "Scenario 2: Key Pipeline Constraint", "headline": "Major pipeline batch throttling reduces wholesale terminal intake.", "shock_pct": 0.035},
        {"name": "Scenario 3: Severe Weather Shock", "headline": "Severe storm disruption impacts coastal fuel logistics and rack operations.", "shock_pct": 0.030},
        {"name": "Scenario 4: Maritime Chokepoint Detour", "headline": "International maritime bottleneck forces vessel rerouting and freight increases.", "shock_pct": 0.025},
        {"name": "Scenario 5: Executive Policy Action", "headline": "Executive social post announces trade and tariff policy revisions.", "shock_pct": -0.020},
    ]

    scenario_results = []
    for sc in default_scenarios:
        shock_pct = sc["shock_pct"]
        sim_price = baseline_forecast * (1.0 + shock_pct)
        dollar_change = sim_price - baseline_forecast
        pct_change = (dollar_change / baseline_forecast) * 100
        scenario_results.append({
            "Scenario": sc["name"],
            "Adjusted 5D Price": f"${sim_price:.3f}/gal",
            "Impact ($)": f"{dollar_change:+.3f}/gal",
            "Impact (%)": f"{pct_change:+.2f}%"
        })

    model_tag = resolve_model_tag(region=logger_region_key, model_type=model_type)
    last_date = market_df['date'].iloc[-1]
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    dynamic_margin = live_pump_price - latest_rbob

    for h in [1, 2, 3, 4, 5]:
        h_res = multi_horizon_results.get(h)
        if not h_res:
            continue
        h_splits = h_res['splits']
        h_test_dates = h_splits['test_df']['date']
        h_preds_hybrid = h_res.get('predictions_hybrid', h_res.get('y_pred_hybrid'))
        h_preds_quant = h_res.get('predictions_quant', h_res.get('y_pred_quant'))

        # Determine regional baseline series
        reg_col = f"{reg_clean}_retail_gasoline"
        if reg_col in h_splits['test_df'].columns:
            hist_base = h_splits['test_df'][reg_col]
        else:
            hist_base = h_splits['test_df']['gasoline_rbob'] + dynamic_margin

        rbob_hist = h_splits['test_df']['gasoline_rbob']
        pred_ret_hybrid = (h_preds_hybrid - rbob_hist) / rbob_hist
        pred_ret_quant = (h_preds_quant - rbob_hist) / rbob_hist
        hist_pred = hist_base * (1.0 + pred_ret_hybrid)
        hist_quant = hist_base * (1.0 + pred_ret_quant)

        try:
            backfill_new_region_history(
                test_dates=h_test_dates,
                base_prices=hist_base,
                predicted_prices=hist_pred,
                region=logger_region_key,
                model_version=model_tag,
                forecast_horizon_days=h,
                quant_baseline_prices=hist_quant
            )
        except Exception as e:
            logger.debug(f"Regional backfill history update skipped: {e}")

        # Log active out-of-time h-day horizon forecast
        last_row_hybrid = h_splits.get('X_live_hybrid', h_splits['X_test_hybrid'].iloc[-1:])
        last_row_quant = h_splits.get('X_live_quant', h_splits['X_test_quant'].iloc[-1:])
        raw_pred_h = float(h_res.get('live_pred_price', h_res['model_hybrid'].predict(last_row_hybrid)[0]))
        raw_quant_h = float(h_res.get('live_pred_quant_price', h_res['model_quant'].predict(last_row_quant)[0]))
        last_hist_price_h = float(h_splits.get('live_current_price', h_splits['test_df']['gasoline_rbob'].iloc[-1]))
        baseline_return_h = (raw_pred_h - last_hist_price_h) / last_hist_price_h if last_hist_price_h > 0 else 0.0
        quant_return_h = (raw_quant_h - last_hist_price_h) / last_hist_price_h if last_hist_price_h > 0 else 0.0
        h_forecast = live_pump_price * (1.0 + baseline_return_h)
        h_quant = live_pump_price * (1.0 + quant_return_h)

        today_df = pd.DataFrame([{
            'date': last_date,
            'current_price': live_pump_price,
            'predicted_5d_price': h_forecast,
            'quant_baseline_5d_price': h_quant,
            'forecast_horizon_days': h,
            'is_retroactive_backtest': False
        }])
        # Process primary region
        try:
            log_predictions(
                today_df,
                region=logger_region_key,
                model_version=model_tag,
                run_type="LIVE_PROSPECTIVE",
                forecast_horizon_days=h,
                is_retroactive_backtest=False
            )
        except Exception as e:
            logger.debug(f"Live prediction logging skipped for {logger_region_key}: {e}")

        # Process dual-anchor secondary sub-regions (Issue #464)
        dual_anchor_map = {
            "Oakland_CA": [("BayArea_CA", "bayarea_avg_retail_gasoline", 5.05)],
            "Cincinnati_OH": [("Cincinnati_KY", "cincinnati_ky_retail_gasoline", 3.19)]
        }
        if logger_region_key in dual_anchor_map:
            for sec_key, sec_col, sec_default in dual_anchor_map[logger_region_key]:
                try:
                    sec_live = fetch_live_metro_retail_price(sec_key).get("price")
                    sec_base_price = float(sec_live) if sec_live and pd.notna(sec_live) else sec_default
                except Exception:
                    sec_base_price = sec_default

                sec_hist_base = h_splits['test_df'].get(sec_col, h_splits['test_df']['gasoline_rbob'] + (sec_base_price - latest_rbob))
                sec_hist_pred = sec_hist_base * (1.0 + pred_ret_hybrid)
                sec_hist_quant = sec_hist_base * (1.0 + pred_ret_quant)

                try:
                    backfill_new_region_history(
                        test_dates=h_test_dates,
                        base_prices=sec_hist_base,
                        predicted_prices=sec_hist_pred,
                        region=sec_key,
                        model_version=resolve_model_tag(region=sec_key, model_type=model_type),
                        forecast_horizon_days=h,
                        quant_baseline_prices=sec_hist_quant
                    )
                except Exception as e:
                    logger.debug(f"Secondary regional backfill skipped for {sec_key}: {e}")

                sec_forecast = sec_base_price * (1.0 + baseline_return_h)
                sec_quant = sec_base_price * (1.0 + quant_return_h)
                sec_today_df = pd.DataFrame([{
                    'date': last_date,
                    'current_price': sec_base_price,
                    'predicted_5d_price': sec_forecast,
                    'quant_baseline_5d_price': sec_quant,
                    'forecast_horizon_days': h,
                    'is_retroactive_backtest': False
                }])
                try:
                    log_predictions(
                        sec_today_df,
                        region=sec_key,
                        model_version=resolve_model_tag(region=sec_key, model_type=model_type),
                        run_type="LIVE_PROSPECTIVE",
                        forecast_horizon_days=h,
                        is_retroactive_backtest=False
                    )
                except Exception as e:
                    logger.debug(f"Secondary live prediction logging skipped for {sec_key}: {e}")

    try:
        backfill_actual_prices_and_evaluate(target_region=logger_region_key)
        if logger_region_key in {"Oakland_CA", "Cincinnati_OH"}:
            sec_target = "BayArea_CA" if logger_region_key == "Oakland_CA" else "Cincinnati_KY"
            backfill_actual_prices_and_evaluate(target_region=sec_target)
    except Exception as e:
        logger.debug(f"Backfill actual prices skipped: {e}")

    results["results"] = results
    results["baseline_forecast"] = baseline_forecast
    results["scenarios"] = scenario_results
    results["region"] = logger_region_key
    results["display_name"] = display_name
    results["live_pump_price"] = live_pump_price
    return results
