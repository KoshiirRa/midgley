"""
Greenville Regional Master Execution Script (greenville_main.py)
Standalone 6-Step Pipeline tailored to the Greenville, North Carolina metropolitan area (PADD 1C):
1. Market Data Ingestion & Live Pump Price Anchoring ($3.25/gal base)
2. Unstructured Regional News, Finlight.me REST API, Colonial Pipeline Selma/Apex Hubs & NCZ081 NOAA Weather Processing
3. Selma Rack Crack Spread Feature Engineering & Exponential Memory Decay
4. Quantitative Model Training & Ablation Evaluation
5. Real-Time Greenville Shock Scenario Simulations (Colonial Pipeline Outage, Atlantic Hurricane Landfall, Selma Tank Farm Power Blackout, NC Gas Tax Update)
6. MLOps Prediction Logging & Rolling Performance Tracking
"""

import os
import sys
import logging
import pandas as pd
import numpy as np

from src.greenville_regional import fetch_greenville_market_data, get_greenville_regional_events
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models
from src.prediction_logger import log_predictions, generate_performance_report, backfill_new_region_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.live_fuel_feed import fetch_live_metro_retail_price

def run_greenville_pipeline(live_pump_price: float = None, use_llm_api: bool = False, model_type: str = "ridge"):
    if live_pump_price is None:
        live_pump_price = fetch_live_metro_retail_price("Greenville_NC")["price"]

    print("=" * 80)
    print("  GREENVILLE, NORTH CAROLINA METRO GAS PRICE PREDICTION PIPELINE")
    print(f"  LIVE PUMP PRICE ANCHOR: ${live_pump_price:.2f}/gal (PADD 1C South Atlantic)")
    print("=" * 80)

    # Step 1: Ingest Market Data for Greenville Region & Anchor Live Pump Price
    print("\n[Step 1/6] Ingesting Market Data & Calibrating Live Greenville Pump Price...")
    market_df = fetch_greenville_market_data(start_date="2022-01-01", live_current_price=live_pump_price)
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Live Calibrated Greenville Pump Price Anchor: ${live_pump_price:.2f}/gal")

    # Step 2: Extract Features from Localized News, NOAA Weather, Maritime & Social Feeds
    print("\n[Step 2/6] Extracting LLM Factor Metrics from Finlight, NCZ081 NOAA, Colonial Pipeline & Selma Hub Feeds...")
    events_raw = get_greenville_regional_events()
    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api)
    
    print("  Sample Scored Events:")
    for _, r in events_df.iloc[:3].iterrows():
        print(f"    - [{r['date'].strftime('%Y-%m-%d')}] '{r['headline'][:65]}...'")
        print(f"       -> GeoRisk: {r['geopolitical_risk']}, SupplyDisruption: {r['supply_disruption']}, NetPressure: {r['overall_price_pressure']}")

    # Step 3: Feature Engineering & Decayed Memory Fusion
    print("\n[Step 3/6] Engineering Selma Rack Crack Spread & Fusing Decayed Event Memory...")
    features_df = create_feature_matrix(market_df, events_df, forecast_horizon=5)
    splits = prepare_chronological_splits(features_df, train_ratio=0.8, forecast_horizon=5)
    
    print(f"  -> Chronological Train Split: {len(splits['X_train_hybrid'])} rows")
    print(f"  -> Chronological Out-of-Time Test Split: {len(splits['X_test_hybrid'])} rows")

    # Step 4: Model Training & Evaluation
    print("\n[Step 4/6] Training Models & Running Ablation Experiment...")
    results = train_and_compare_models(splits, model_type=model_type)

    print("\n" + "=" * 65)
    print("     GREENVILLE REGIONAL MODEL EVALUATION & METRICS SUMMARY")
    print("=" * 65)
    print(f" Target Location: Greenville, NC Metropolitan Area (Live Base: ${live_pump_price:.2f}/gal)")
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
    print("\n[Step 5/6] Real-Time Greenville Regional & Pipeline Shock Scenario Simulations...")
    scenarios = [
        {
            "name": "Scenario 1: Colonial Pipeline Mainline Outage / Cyberattack Shock",
            "headline": "Colonial Pipeline Line 1 emergency shutdown halts batch shipments into Selma NC breakout tank farms."
        },
        {
            "name": "Scenario 2: Category 3 Atlantic Hurricane Landfall & Tar River Flooding",
            "headline": "Major Hurricane landfall inundates Eastern NC coastal distribution highways and Tar River transport routes."
        },
        {
            "name": "Scenario 3: Selma NC Tank Farm Power Grid Outage Shock",
            "headline": "Severe convective microburst knocks out Duke Energy substation at Selma breakout hub, suspending rack loading."
        },
        {
            "name": "Scenario 4: NC State Motor Fuel Tax Formula Adjustment",
            "headline": "North Carolina Department of Revenue enacts annual fuel tax formula rate increase on wholesale rack gasoline."
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
    greenville_baseline_forecast = live_pump_price * (1.0 + baseline_return)
    
    print(f"\n Baseline Greenville 5-Day Forecast (No Shock): ${greenville_baseline_forecast:.3f}/gal (Base: ${live_pump_price:.2f}/gal)")
    print("-" * 75)
    
    scenario_results = []
    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        
        supply_impact = scores['supply_disruption'] * 0.045
        pressure_impact = scores['overall_price_pressure'] * 0.035
        geo_impact = scores['geopolitical_risk'] * 0.020
        net_shock_pct = supply_impact + pressure_impact + geo_impact
        
        multiplier = 1.42 if ("Weekend" in sc["name"] or "WEEKEND" in sc["headline"]) else 1.0
        adjusted_shock_pct = net_shock_pct * multiplier
        
        sim_greenville_price = greenville_baseline_forecast * (1.0 + adjusted_shock_pct)
        dollar_change = sim_greenville_price - greenville_baseline_forecast
        pct_change = (dollar_change / greenville_baseline_forecast) * 100
        
        scenario_results.append({
            "Scenario": sc["name"],
            "Adjusted 5D Price": f"${sim_greenville_price:.3f}/gal",
            "Impact ($)": f"{dollar_change:+.3f}/gal",
            "Impact (%)": f"{pct_change:+.2f}%"
        })
        print(f"  {sc['name']:<56} -> ${sim_greenville_price:.3f}/gal ({dollar_change:+.3f} | {pct_change:+.2f}%)")
    print("=" * 75)

    # Step 6: MLOps Prediction Logging & Backfilling
    print("\n[Step 6/6] Logging Predictions to MLOps Store (data/prediction_history.csv)...")
    test_dates = splits['test_df']['date']
    preds_hybrid = results['predictions_hybrid']
    
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    dynamic_margin = live_pump_price - latest_rbob
    hist_greenville_base = splits['test_df']['greenville_retail_gasoline'] if 'greenville_retail_gasoline' in splits['test_df'].columns else splits['test_df']['gasoline_rbob'] + dynamic_margin
    hist_greenville_pred = preds_hybrid + dynamic_margin

    n_logged = backfill_new_region_history(
        test_dates=test_dates,
        base_prices=hist_greenville_base,
        predicted_prices=hist_greenville_pred,
        region="Greenville_NC",
        model_version=f"v1.4-Finlight-Greenville-{model_type.capitalize()}"
    )

    last_date = market_df['date'].iloc[-1]
    today_df = pd.DataFrame([{
        'date': last_date,
        'current_price': live_pump_price,
        'predicted_5d_price': greenville_baseline_forecast
    }])
    log_predictions(today_df, region="Greenville_NC", model_version=f"v1.4-Finlight-Greenville-{model_type.capitalize()}")
    print(f"  -> Logged & evaluated {n_logged} historical out-of-time test predictions for Greenville_NC.")

    return {
        "results": results,
        "baseline_forecast": greenville_baseline_forecast,
        "live_pump_price": live_pump_price,
        "scenarios": scenario_results
    }


if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    model_choice = "ridge"
    for arg in sys.argv:
        if arg.startswith("--model="):
            model_choice = arg.split("=")[1].lower()
            
    run_greenville_pipeline(use_llm_api=use_api, model_type=model_choice)
