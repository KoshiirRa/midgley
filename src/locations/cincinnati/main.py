"""
Cincinnati Regional Master Execution Script (src/locations/cincinnati/main.py)
Standalone 6-Step Pipeline tailored to the Cincinnati, OH & Northern Kentucky tri-state metropolitan area:
1. Market Data Ingestion & Dual-State Live Pump Price Anchoring (OH: $3.450/gal, KY: $3.325/gal base)
2. Unstructured Regional News, Finlight.me REST API, Catlettsburg Refinery, Ohio & Lower Mississippi River Barge Logistics & Tri-State NOAA Weather Processing
3. Ohio Valley & Catlettsburg Crack Spread Feature Engineering & Decayed Event Memory Fusion
4. Quantitative Model Training & Ablation Evaluation
5. Real-Time Cincinnati Regional & River Maritime Shock Scenario Simulations
6. MLOps Prediction Logging & Rolling Performance Tracking
"""

import os
import sys
import logging
import pandas as pd
import numpy as np

from src.locations.cincinnati.regional import fetch_cincinnati_market_data, get_cincinnati_regional_events
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models, train_multi_horizon_models
from src.prediction_logger import log_predictions, generate_performance_report, backfill_new_region_history, resolve_model_tag, backfill_actual_prices_and_evaluate
from src.live_fuel_feed import fetch_live_metro_retail_price

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_cincinnati_pipeline(
    live_oh_price: float = None, 
    live_ky_price: float = None, 
    use_llm_api: bool = False, 
    model_type: str = "ridge"
):
    if live_oh_price is None:
        live_oh_price = fetch_live_metro_retail_price("Cincinnati_OH")["price"]
    if live_ky_price is None:
        live_ky_price = fetch_live_metro_retail_price("Cincinnati_KY")["price"]

    tax_delta = live_oh_price - live_ky_price
    print("=" * 80)
    print("  CINCINNATI, OH / NORTHERN KY METRO GAS PRICE PREDICTION PIPELINE")
    print(f"  LIVE PUMP PRICE ANCHORS: Ohio (OH): ${live_oh_price:.3f}/gal | Kentucky (KY): ${live_ky_price:.3f}/gal")
    print(f"  CROSS-RIVER STATE FUEL TAX & RETAIL DIFFERENTIAL: ${tax_delta:.3f}/gal")
    print("=" * 80)

    # Step 1: Ingest Market Data for Cincinnati Region & Anchor Dual-State Pump Prices
    print("\n[Step 1/6] Ingesting Market Data & Calibrating Dual-State Pump Prices...")
    market_df = fetch_cincinnati_market_data(
        start_date="2022-01-01", 
        live_oh_price=live_oh_price, 
        live_ky_price=live_ky_price
    )
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Ohio Retail Base (OH):     ${live_oh_price:.3f}/gal (State Tax: 38.5¢/gal)")
    print(f"  -> Kentucky Retail Base (KY): ${live_ky_price:.3f}/gal (State Tax: 26.0¢/gal)")

    # Step 2: Extract Features from Localized News, NOAA Weather, River & Social Feeds
    print("\n[Step 2/6] Extracting LLM Factor Metrics from Finlight, Tri-State NOAA & River Feeds...")
    events_raw = get_cincinnati_regional_events()
    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api)
    
    print("  Sample Scored Events:")
    for _, r in events_df.iloc[:3].iterrows():
        print(f"    - [{r['date'].strftime('%Y-%m-%d')}] '{r['headline'][:65]}...'")
        print(f"       -> GeoRisk: {r['geopolitical_risk']}, SupplyDisruption: {r['supply_disruption']}, NetPressure: {r['overall_price_pressure']}")

    # Step 3 & 4: Multi-Horizon Feature Engineering & Model Training (1D-5D)
    print("\n[Step 3/6] Engineering Ohio Valley Crack Spread & Fusing Decayed Event Memory (Multi-Horizon 1D-5D)...")
    multi_horizon_results = train_multi_horizon_models(
        market_df, 
        events_df, 
        horizons=[1, 2, 3, 4, 5], 
        model_type=model_type
    )
    results = multi_horizon_results[5]
    splits = results['splits']
    results['multi_horizon_results'] = multi_horizon_results

    print("\n[Step 4/6] Model Evaluation & Metrics Summary (5-Day Horizon Primary Baseline)...")
    print("\n" + "=" * 65)
    print("      CINCINNATI REGIONAL MODEL EVALUATION & METRICS SUMMARY (5-DAY)")
    print("=" * 65)
    print(f" Target Location: Cincinnati OH / NKY Metro (OH Base: ${live_oh_price:.3f}/gal | KY Base: ${live_ky_price:.3f}/gal)")
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
    print("\n[Step 5/6] Real-Time Cincinnati Regional & Maritime Shock Scenario Simulations...")
    scenarios = [
        {
            "name": "Scenario 1: Lower Mississippi Low-Water Barge Grounding Crisis",
            "headline": "Historic drought drops Lower Mississippi River gage below -10ft at Memphis, halting petroleum barge tows into Ohio Valley."
        },
        {
            "name": "Scenario 2: Catlettsburg Refinery Hydrocracker Explosion",
            "headline": "Catlettsburg 290,000 bpd refinery declares force majeure following hydrocracker unit explosion, cutting tri-state supply."
        },
        {
            "name": "Scenario 3: Ohio River Ice Gorge / Lock 52 Freeze Bottleneck",
            "headline": "Polar vortex causes catastrophic ice gorge at Markland Locks on Ohio River, halting tank barge traffic into Cincinnati."
        },
        {
            "name": "Scenario 4: Kentucky State Fuel Tax Rate Hike Enacted",
            "headline": "Kentucky General Assembly passes motor fuel excise tax increase of +$0.045/gal, narrowing Ohio-Kentucky price spread."
        },
        {
            "name": "Scenario 5: Weekend Executive OPEC Talkdown Post",
            "headline": "TRUMP WEEKEND SOCIAL POST: 'OPEC is pushing oil prices artificially High! Must increase production by 2.0M bpd immediately!'"
        },
        {
            "name": "Scenario 6: Weekend Foreign Energy Tariff Declaration",
            "headline": "TRUMP WEEKEND SOCIAL POST: 'Starting Monday morning, 25% Tariffs will take effect on ALL foreign energy imports!'"
        }
    ]
    
    base_row = splits['X_test_hybrid'].iloc[-1:].copy()
    raw_pred_price = results['model_hybrid'].predict(base_row)[0]
    last_hist_price = splits['test_df']['gasoline_rbob'].iloc[-1]
    
    baseline_return = (raw_pred_price - last_hist_price) / last_hist_price
    cin_oh_baseline_forecast = live_oh_price * (1.0 + baseline_return)
    cin_ky_baseline_forecast = live_ky_price * (1.0 + baseline_return)
    
    print(f"\n  CURRENT BASE PRICES: Ohio (OH): ${live_oh_price:.3f}/gal | Kentucky (KY): ${live_ky_price:.3f}/gal")
    print(f"  BASELINE 5-DAY FORECAST (OH): ${cin_oh_baseline_forecast:.3f}/gal ({baseline_return*100:+.2f}%)")
    print(f"  BASELINE 5-DAY FORECAST (KY): ${cin_ky_baseline_forecast:.3f}/gal ({baseline_return*100:+.2f}%)")
    print("-" * 80)
    
    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        
        supply_impact = scores['supply_disruption'] * 0.045
        pressure_impact = scores['overall_price_pressure'] * 0.035
        geo_impact = scores['geopolitical_risk'] * 0.020
        net_shock_pct = supply_impact + pressure_impact + geo_impact
        
        shocked_forecast_oh = cin_oh_baseline_forecast * (1.0 + net_shock_pct)
        shocked_forecast_ky = cin_ky_baseline_forecast * (1.0 + net_shock_pct)
        delta_dollars = shocked_forecast_oh - cin_oh_baseline_forecast
        
        print(f"\n  [{sc['name']}]")
        print(f"  Headline: \"{headline}\"")
        print(f"  LLM Extraction -> Supply Disruption: {scores['supply_disruption']:+.2f}, Price Pressure: {scores['overall_price_pressure']:+.2f}")
        print(f"  -> Shocked Ohio 5-Day Forecast:     ${shocked_forecast_oh:.3f}/gal")
        print(f"  -> Shocked Kentucky 5-Day Forecast: ${shocked_forecast_ky:.3f}/gal")
        print(f"  -> Estimated Price Shock:          {delta_dollars:+.3f}/gal ({net_shock_pct*100:+.2f}%)")
        
    # Step 6: Log Predictions to Historical Store & Report Model Performance across 1D-5D (Issue #314)
    print("\n[Step 6/6] Logging Forecasts & Backtesting Historical Prediction Accuracy (Multi-Horizon 1D-5D)...")
    oh_version = resolve_model_tag("Cincinnati_OH", model_type=model_type)
    ky_version = resolve_model_tag("Cincinnati_KY", model_type=model_type)
    last_date = market_df['date'].iloc[-1]
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    margin_oh = live_oh_price - latest_rbob
    margin_ky = live_ky_price - latest_rbob

    for h in [1, 2, 3, 4, 5]:
        h_res = multi_horizon_results.get(h)
        if not h_res:
            continue
        h_splits = h_res['splits']
        h_test_dates = h_splits['test_df']['date']
        h_preds_hybrid = h_res['predictions_hybrid']
        h_preds_quant = h_res['predictions_quant']
        
        hist_oh_base = h_splits['test_df']['cincinnati_oh_retail_gasoline'] if 'cincinnati_oh_retail_gasoline' in h_splits['test_df'].columns else h_splits['test_df']['gasoline_rbob'] + margin_oh
        hist_oh_pred = h_preds_hybrid + margin_oh
        hist_oh_quant = h_preds_quant + margin_oh
        hist_ky_base = h_splits['test_df']['cincinnati_ky_retail_gasoline'] if 'cincinnati_ky_retail_gasoline' in h_splits['test_df'].columns else h_splits['test_df']['gasoline_rbob'] + margin_ky
        hist_ky_pred = h_preds_hybrid + margin_ky
        hist_ky_quant = h_preds_quant + margin_ky

        backfill_new_region_history(
            test_dates=h_test_dates,
            base_prices=hist_oh_base,
            predicted_prices=hist_oh_pred,
            region="Cincinnati_OH",
            model_version=oh_version,
            forecast_horizon_days=h,
            quant_baseline_prices=hist_oh_quant
        )
        backfill_new_region_history(
            test_dates=h_test_dates,
            base_prices=hist_ky_base,
            predicted_prices=hist_ky_pred,
            region="Cincinnati_KY",
            model_version=ky_version,
            forecast_horizon_days=h,
            quant_baseline_prices=hist_ky_quant
        )

        raw_pred_h = float(h_res['live_pred_price'])
        raw_quant_h = float(h_res.get('live_pred_quant_price', raw_pred_h))
        last_hist_price_h = float(h_splits['test_df']['gasoline_rbob'].iloc[-1])
        baseline_return_h = (raw_pred_h - last_hist_price_h) / last_hist_price_h
        quant_return_h = (raw_quant_h - last_hist_price_h) / last_hist_price_h
        cin_oh_h_forecast = live_oh_price * (1.0 + baseline_return_h)
        cin_oh_h_quant = live_oh_price * (1.0 + quant_return_h)
        cin_ky_h_forecast = live_ky_price * (1.0 + baseline_return_h)
        cin_ky_h_quant = live_ky_price * (1.0 + quant_return_h)

        today_oh = pd.DataFrame([{
            'date': last_date,
            'current_price': live_oh_price,
            'predicted_5d_price': cin_oh_h_forecast,
            'quant_baseline_5d_price': cin_oh_h_quant,
            'forecast_horizon_days': h
        }])
        today_ky = pd.DataFrame([{
            'date': last_date,
            'current_price': live_ky_price,
            'predicted_5d_price': cin_ky_h_forecast,
            'quant_baseline_5d_price': cin_ky_h_quant,
            'forecast_horizon_days': h
        }])
        
        log_predictions(today_oh, region="Cincinnati_OH", model_version=oh_version, forecast_horizon_days=h)
        log_predictions(today_ky, region="Cincinnati_KY", model_version=ky_version, forecast_horizon_days=h)

    backfill_actual_prices_and_evaluate(target_region="Cincinnati_OH")
    backfill_actual_prices_and_evaluate(target_region="Cincinnati_KY")
    print(f"  -> Logged & backfilled discrete 1D-5D predictions for Cincinnati_OH and Cincinnati_KY")
    
    perf_report = generate_performance_report()
    if not perf_report.empty:
        print("\n" + "=" * 65)
        print("         HISTORICAL PREDICTION TRACKER & MODEL ITERATION SUMMARY")
        print("=" * 65)
        print(perf_report.to_string(index=False))
        print("=" * 65)
        
    print("\nCincinnati Regional Pipeline Execution Complete!\n")
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_cincinnati_pipeline(use_llm_api=use_api, model_type="ridge")
