"""
Newark Regional Master Execution Script (src/locations/newark/main.py)
Standalone 6-Step Pipeline tailored to the Newark, Delaware metropolitan area (PADD 1B):
1. Market Data Ingestion & Live Pump Price Anchoring ($3.35/gal base)
2. Unstructured Regional News, Finlight.me REST API, Delaware Bay Lightering, C&D Canal Detours & DEZ001 NOAA Weather Processing
3. Delaware City Crack Spread Feature Engineering & Exponential Memory Decay
4. Quantitative Model Training & Ablation Evaluation
5. Real-Time Newark Shock Scenario Simulations (Delaware City Refinery Outage, Nor'easter Surge, C&D Canal Detour, Delaware Bay Freeze)
6. MLOps Prediction Logging & Rolling Performance Tracking
"""

import os
import sys
import logging
import pandas as pd
import numpy as np

from src.locations.newark.regional import fetch_newark_market_data, get_newark_regional_events
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models, train_multi_horizon_models
from src.prediction_logger import log_predictions, generate_performance_report, backfill_new_region_history, resolve_model_tag, backfill_actual_prices_and_evaluate
from src.live_fuel_feed import fetch_live_metro_retail_price

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_newark_pipeline(live_pump_price: float = None, use_llm_api: bool = False, model_type: str = "ridge"):
    if live_pump_price is None:
        live_pump_price = fetch_live_metro_retail_price("Newark_DE")["price"]

    print("=" * 80)
    print("  NEWARK, DELAWARE METRO GAS PRICE PREDICTION PIPELINE")
    print(f"  LIVE PUMP PRICE ANCHOR: ${live_pump_price:.2f}/gal (PADD 1B Central Atlantic)")
    print("=" * 80)

    # Step 1: Ingest Market Data for Newark Region & Anchor Live Pump Price
    print("\n[Step 1/6] Ingesting Market Data & Calibrating Live Newark Pump Price...")
    market_df = fetch_newark_market_data(start_date="2022-01-01", live_current_price=live_pump_price)
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Live Calibrated Newark Pump Price Anchor: ${live_pump_price:.2f}/gal")

    # Step 2: Extract Features from Localized News, NOAA Weather, Maritime & Social Feeds
    print("\n[Step 2/6] Extracting LLM Factor Metrics from Finlight, DEZ001 NOAA, Delaware Bay & C&D Canal Feeds...")
    events_raw = get_newark_regional_events()
    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api)
    
    print("  Sample Scored Events:")
    for _, r in events_df.iloc[:3].iterrows():
        print(f"    - [{r['date'].strftime('%Y-%m-%d')}] '{r['headline'][:65]}...'")
        print(f"       -> GeoRisk: {r['geopolitical_risk']}, SupplyDisruption: {r['supply_disruption']}, NetPressure: {r['overall_price_pressure']}")

    # Step 3 & 4: Multi-Horizon Feature Engineering & Model Training (1D-5D)
    print("\n[Step 3/6] Engineering Delaware City Crack Spread & Fusing Decayed Event Memory (Multi-Horizon 1D-5D)...")
    multi_horizon_results = train_multi_horizon_models(
        market_df, 
        events_df, 
        horizons=[1, 2, 3, 4, 5], 
        model_type=model_type
    )
    results = multi_horizon_results[5]
    splits = results['splits']
    results['multi_horizon_results'] = multi_horizon_results

    print("\n[Step 4/6] Training Models & Running Ablation Experiment (5-Day Horizon Primary Baseline)...")
    print("\n" + "=" * 65)
    print("        NEWARK REGIONAL MODEL EVALUATION & METRICS SUMMARY (5-DAY)")
    print("=" * 65)
    print(f" Target Location: Newark, DE Metropolitan Area (Live Base: ${live_pump_price:.2f}/gal)")
    print(f" Algorithm: {model_type.upper()}")
    print("-" * 65)
    print(f" {'Metric':<27} {'Baseline (Quant)':<18} {'Hybrid (LLM-Augmented)'}")
    print("-" * 65)
    print(f" {'MAE':<27} {results['metrics_quant']['MAE']:<18.4f} {results['metrics_hybrid']['MAE']:.4f}")
    print(f" {'RMSE':<27} {results['metrics_quant']['RMSE']:<18.4f} {results['metrics_hybrid']['RMSE']:.4f}")
    print(f" {'MAPE (%)':<27} {results['metrics_quant']['MAPE (%)']:<18.2f} {results['metrics_hybrid']['MAPE (%)']:.2f}")
    print(f" {'Directional Accuracy (%)':<27} {results['metrics_quant']['Directional Accuracy (%)']:<18.2f} {results['metrics_hybrid']['Directional Accuracy (%)']:.2f}")
    print("-" * 65)
    mae_diff = (results['metrics_quant']['MAE'] - results['metrics_hybrid']['MAE']) / results['metrics_quant']['MAE'] * 100
    rmse_diff = (results['metrics_quant']['RMSE'] - results['metrics_hybrid']['RMSE']) / results['metrics_quant']['RMSE'] * 100
    print(f" MAE Improvement with LLM Event Features:  {mae_diff:+.2f}% reduction in error")
    print(f" RMSE Improvement with LLM Event Features: {rmse_diff:+.2f}% reduction in error")
    print("=" * 65)

    # Step 5: Real-Time Scenario Simulations
    print("\n[Step 5/6] Real-Time Newark Regional & Maritime Shock Scenario Simulations...")
    scenarios = [
        {
            "name": "Scenario 1: PBF Delaware City Refinery FCC Outage",
            "headline": "Unplanned fluid catalytic cracker shutdown at 180,000 bpd Delaware City Refinery halts regional rack loading."
        },
        {
            "name": "Scenario 2: Delaware River Nor'easter Storm Surge",
            "headline": "Bomb Cyclone Nor'easter brings 14-inch snow blizzard & coastal storm surge, freezing Delaware Bay ship channel."
        },
        {
            "name": "Scenario 3: C&D Canal Shoaling Emergency Detour",
            "headline": "C&D Canal closed for maintenance dredging; tank barges detoured 300 nm around Delmarva Peninsula (+35% freight surge)."
        },
        {
            "name": "Scenario 4: Delaware Bay Ice Lockout & Lightering Freeze",
            "headline": "Sub-zero hard freeze halts deepwater tanker lightering at Big Stone Anchorage in Delaware Bay."
        },
        {
            "name": "Scenario 5: Weekend Executive OPEC Talkdown Post",
            "headline": "TRUMP WEEKEND SOCIAL POST: 'OPEC is pushing oil prices artificially High! Must increase production by 2.0M bpd immediately!'"
        },
        {
            "name": "Scenario 6: Weekend Foreign Crude Tariff Declaration",
            "headline": "TRUMP WEEKEND SOCIAL POST: 'Starting Monday morning, 25% Tariffs will take effect on ALL foreign crude oil imports!'"
        }
    ]
    
    base_row = splits.get('X_live_hybrid', splits['X_test_hybrid'].iloc[-1:]).copy()
    raw_pred_price = results.get('live_pred_price', results['model_hybrid'].predict(base_row)[0])
    last_hist_price = float(splits.get('live_current_price', splits['test_df']['gasoline_rbob'].iloc[-1]))
    
    baseline_return = results.get('live_pred_return', (raw_pred_price - last_hist_price) / last_hist_price if last_hist_price > 0 else 0.0)
    newark_baseline_forecast = live_pump_price * (1.0 + baseline_return)
    
    print(f"\n  CURRENT NEWARK LIVE PUMP PRICE:     ${live_pump_price:.3f}/gal")
    print(f"  BASELINE 5-DAY NEWARK FORECAST:      ${newark_baseline_forecast:.3f}/gal ({baseline_return*100:+.2f}%)")
    print("-" * 80)
    
    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        
        supply_impact = scores['supply_disruption'] * 0.045
        pressure_impact = scores['overall_price_pressure'] * 0.035
        geo_impact = scores['geopolitical_risk'] * 0.020
        net_shock_pct = supply_impact + pressure_impact + geo_impact
        
        shocked_forecast = newark_baseline_forecast * (1.0 + net_shock_pct)
        delta_dollars = shocked_forecast - newark_baseline_forecast
        
        print(f"\n  [{sc['name']}]")
        print(f"  Headline: \"{headline}\"")
        print(f"  LLM Extraction -> Supply Disruption: {scores['supply_disruption']:+.2f}, Price Pressure: {scores['overall_price_pressure']:+.2f}")
        print(f"  -> Shocked 5-Day Forecast:  ${shocked_forecast:.3f}/gal")
        print(f"  -> Estimated Price Shock:   {delta_dollars:+.3f}/gal ({net_shock_pct*100:+.2f}%)")
        
    # Step 6: Log Predictions to Historical Store & Report Model Performance across 1D-5D (Issue #314)
    print("\n[Step 6/6] Logging Forecasts & Backtesting Historical Prediction Accuracy (Multi-Horizon 1D-5D)...")
    newark_version = resolve_model_tag("Newark_DE", model_type=model_type)
    last_date = market_df['date'].iloc[-1]
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    dynamic_margin = live_pump_price - latest_rbob

    for h in [1, 2, 3, 4, 5]:
        h_res = multi_horizon_results.get(h)
        if not h_res:
            continue
        h_splits = h_res['splits']
        h_test_dates = h_splits['test_df']['date']
        h_preds_hybrid = h_res['predictions_hybrid']
        h_preds_quant = h_res['predictions_quant']
        
        hist_newark_base = h_splits['test_df']['newark_retail_gasoline'] if 'newark_retail_gasoline' in h_splits['test_df'].columns else h_splits['test_df']['gasoline_rbob'] + dynamic_margin
        hist_newark_pred = h_preds_hybrid + dynamic_margin
        hist_newark_quant = h_preds_quant + dynamic_margin

        backfill_new_region_history(
            test_dates=h_test_dates,
            base_prices=hist_newark_base,
            predicted_prices=hist_newark_pred,
            region="Newark_DE",
            model_version=newark_version,
            forecast_horizon_days=h,
            quant_baseline_prices=hist_newark_quant
        )

        # Log active out-of-time h-day horizon forecast
        raw_pred_h = float(h_res['live_pred_price'])
        raw_quant_h = float(h_res.get('live_pred_quant_price', raw_pred_h))
        last_hist_price_h = float(h_splits['test_df']['gasoline_rbob'].iloc[-1])
        baseline_return_h = (raw_pred_h - last_hist_price_h) / last_hist_price_h
        quant_return_h = (raw_quant_h - last_hist_price_h) / last_hist_price_h
        newark_h_forecast = live_pump_price * (1.0 + baseline_return_h)
        newark_h_quant = live_pump_price * (1.0 + quant_return_h)

        today_df = pd.DataFrame([{
            'date': last_date,
            'current_price': live_pump_price,
            'predicted_5d_price': newark_h_forecast,
            'quant_baseline_5d_price': newark_h_quant,
            'forecast_horizon_days': h
        }])
        log_predictions(today_df, region="Newark_DE", model_version=newark_version, forecast_horizon_days=h)

    backfill_actual_prices_and_evaluate(target_region="Newark_DE")
    print(f"  -> Logged & backfilled discrete 1D-5D predictions to store (data/prediction_history.csv)")
    
    perf_report = generate_performance_report()
    if not perf_report.empty:
        print("\n" + "=" * 65)
        print("         HISTORICAL PREDICTION TRACKER & MODEL ITERATION SUMMARY")
        print("=" * 65)
        print(perf_report.to_string(index=False))
        print("=" * 65)
        
    print("\nNewark Regional Pipeline Execution Complete!\n")
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_newark_pipeline(use_llm_api=use_api, model_type="ridge")
