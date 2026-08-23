"""
Tulsa Regional Master Execution Script (tulsa_main.py)
Standalone 6-Step Pipeline tailored to the Tulsa, OK metropolitan area:
1. Market Data Ingestion & Live Pump Price Anchoring ($3.89/gal)
2. Unstructured Local News, NOAA Weather & Global Maritime Chokepoint Processing
3. Tulsa Crack Spread Feature Engineering & Exponential Memory Decay
4. Quantitative Model Training & Ablation Evaluation
5. Real-Time Tulsa Shock Scenario Simulations (Refinery Tornado, Cushing Spill, Hormuz Blockade)
6. MLOps Prediction Logging & Rolling Performance Tracking
"""

import os
import sys
import logging
import pandas as pd
import numpy as np

from src.tulsa_regional import fetch_tulsa_market_data, get_tulsa_regional_events
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models
from src.prediction_logger import log_predictions, generate_performance_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_tulsa_pipeline(live_pump_price: float = 3.89, use_llm_api: bool = False, model_type: str = "ridge"):
    print("=" * 80)
    print("  TULSA, OKLAHOMA METRO GAS PRICE PREDICTION PIPELINE")
    print(f"  LIVE PUMP PRICE ANCHOR: ${live_pump_price:.2f}/gal")
    print("=" * 80)

    # Step 1: Ingest Market Data for Tulsa Region & Anchor Live Pump Price
    print("\n[Step 1/6] Ingesting Market Data & Calibrating Live Tulsa Pump Price...")
    market_df = fetch_tulsa_market_data(start_date="2022-01-01", live_current_price=live_pump_price)
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Live Calibrated Tulsa Pump Price Anchor: ${live_pump_price:.2f}/gal")

    # Step 2: Extract Features from Localized News, NOAA Weather & Maritime Chokepoints
    print("\n[Step 2/6] Extracting LLM Factor Metrics from Oklahoma, NOAA & Global Maritime Events...")
    events_raw = get_tulsa_regional_events()
    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api)
    
    print("  Sample Scored Regional & Maritime Events:")
    for _, r in events_df.iloc[:3].iterrows():
        print(f"    - [{r['date'].strftime('%Y-%m-%d')}] '{r['headline'][:65]}...'")
        print(f"       -> GeoRisk: {r['geopolitical_risk']}, SupplyDisruption: {r['supply_disruption']}, NetPressure: {r['overall_price_pressure']}")

    # Step 3: Feature Engineering & Decayed Memory Fusion
    print("\n[Step 3/6] Engineering Tulsa Crack Spread & Fusing Decayed Event Memory...")
    features_df = create_feature_matrix(market_df, events_df, forecast_horizon=5)
    splits = prepare_chronological_splits(features_df, train_ratio=0.8, forecast_horizon=5)
    
    print(f"  -> Chronological Train Split: {len(splits['X_train_hybrid'])} rows")
    print(f"  -> Chronological Out-of-Time Test Split: {len(splits['X_test_hybrid'])} rows")

    # Step 4: Model Training & Evaluation
    print("\n[Step 4/6] Training Models & Running Ablation Experiment...")
    results = train_and_compare_models(splits, model_type=model_type)

    print("\n" + "=" * 65)
    print("         TULSA REGIONAL MODEL EVALUATION & METRICS SUMMARY")
    print("=" * 65)
    print(f" Target Location: Tulsa, OK Metropolitan Area (Live Base: ${live_pump_price:.2f}/gal)")
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
    print("\n[Step 5/6] Real-Time Tulsa Regional Shock Scenario Simulations...")
    scenarios = [
        {
            "name": "Scenario 1: West Tulsa Refinery Tornado Shock",
            "headline": "EF-3 Tornado strikes West Tulsa industrial corridor, halting 125,000 bpd HF Sinclair refinery loading racks."
        },
        {
            "name": "Scenario 2: Cushing Keystone Pipeline Spill",
            "headline": "Keystone Pipeline shutdown following major leak near Cushing, OK storage hub, choking Midwest crude flow."
        },
        {
            "name": "Scenario 3: Strait of Hormuz Tanker Blockade",
            "headline": "Iran IRGC Navy threatens total naval closure of Strait of Hormuz following tanker seizure; 21M bpd crude disrupted."
        },
        {
            "name": "Scenario 4: Red Sea Suez Rerouting Crisis",
            "headline": "Houthi missile strikes force 100% of oil tankers to divert around Cape of Good Hope, adding $4.50/bbl freight surge."
        },
        {
            "name": "Scenario 5: Venezuela Sanctions Reinstatement",
            "headline": "US Treasury OFAC revokes Venezuela General License 44; PDVSA heavy crude exports and diluent imports halted."
        }
    ]
    
    base_row = splits['X_test_hybrid'].iloc[-1:].copy()
    raw_pred_price = results['model_hybrid'].predict(base_row)[0]
    last_hist_price = splits['test_df']['gasoline_rbob'].iloc[-1]
    
    baseline_return = (raw_pred_price - last_hist_price) / last_hist_price
    tulsa_baseline_forecast = live_pump_price * (1.0 + baseline_return)
    
    print(f"\n  CURRENT TULSA LIVE PUMP PRICE:      ${live_pump_price:.3f}/gal")
    print(f"  BASELINE 5-DAY TULSA FORECAST:       ${tulsa_baseline_forecast:.3f}/gal ({baseline_return*100:+.2f}%)")
    print("-" * 80)
    
    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        
        supply_impact = scores['supply_disruption'] * 0.045
        pressure_impact = scores['overall_price_pressure'] * 0.035
        geo_impact = scores['geopolitical_risk'] * 0.020
        net_shock_pct = supply_impact + pressure_impact + geo_impact
        
        shocked_forecast = tulsa_baseline_forecast * (1.0 + net_shock_pct)
        delta_dollars = shocked_forecast - tulsa_baseline_forecast
        
        print(f"\n  [{sc['name']}]")
        print(f"  Headline: \"{headline}\"")
        print(f"  LLM Extraction -> Supply Disruption: {scores['supply_disruption']:+.2f}, Price Pressure: {scores['overall_price_pressure']:+.2f}")
        print(f"  -> Shocked 5-Day Forecast:  ${shocked_forecast:.3f}/gal")
        print(f"  -> Estimated Price Shock:   +${delta_dollars:.3f}/gal ({net_shock_pct*100:+.2f}%)")
        
    # Step 6: Log Predictions to Historical Store & Report Model Performance
    print("\n[Step 6/6] Logging Forecasts & Backtesting Historical Prediction Accuracy...")
    test_dates = splits['test_df']['date']
    test_current_prices = splits['test_df']['tulsa_retail_gasoline'] if 'tulsa_retail_gasoline' in splits['test_df'].columns else splits['test_df']['gasoline_rbob']
    preds_hybrid = results['predictions_hybrid']
    
    pred_log_df = pd.DataFrame({
        'date': test_dates.values,
        'current_price': test_current_prices.values,
        'predicted_5d_price': preds_hybrid
    })
    
    n_logged = log_predictions(pred_log_df, region="Tulsa_OK", model_version="v1.2-NOAA-Tulsa-Ridge")
    print(f"  -> Logged predictions to store (data/prediction_history.csv)")
    
    perf_report = generate_performance_report()
    if not perf_report.empty:
        print("\n" + "=" * 65)
        print("         HISTORICAL PREDICTION TRACKER & MODEL ITERATION SUMMARY")
        print("=" * 65)
        print(perf_report.to_string(index=False))
        print("=" * 65)
        
    print("\nTulsa Regional Pipeline Execution Complete!\n")
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_tulsa_pipeline(live_pump_price=3.89, use_llm_api=use_api, model_type="ridge")