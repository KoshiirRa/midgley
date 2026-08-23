"""
Tulsa, Oklahoma Gas Price Prediction Execution Script (tulsa_main.py)
Calibrated to Live Pump Prices ($3.89/gal).
"""

import os
import sys
import pandas as pd
import numpy as np
import logging

from src.tulsa_regional import fetch_tulsa_market_data, get_tulsa_regional_events
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_tulsa_pipeline(live_pump_price: float = 3.89, use_llm_api: bool = False, model_type: str = "ridge"):
    print("=" * 80)
    print(f"  TULSA, OKLAHOMA METRO GAS PRICE PREDICTION PIPELINE")
    print(f"  LIVE PUMP PRICE ANCHOR: ${live_pump_price:.2f}/gal")
    print("=" * 80)
    
    print("\n[Step 1/5] Ingesting Market Data & Calibrating Live Tulsa Pump Price...")
    market_df = fetch_tulsa_market_data(start_date="2022-01-01", live_current_price=live_pump_price)
    raw_events_df = get_tulsa_regional_events()
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Latest Calibrated Tulsa Pump Price: ${market_df['tulsa_retail_gasoline'].iloc[-1]:.2f}/gal")
    
    print("\n[Step 2/5] Extracting LLM Factor Metrics from Oklahoma Event Headlines...")
    events_df = process_event_dataset(raw_events_df, use_llm_api=use_llm_api)
    
    print("\n[Step 3/5] Engineering Tulsa Crack Spread & Fusing Decayed Event Memory...")
    feature_df = create_feature_matrix(market_df, events_df, forecast_horizon=5, decay_half_life_days=4.0)
    splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
    print(f"  -> Chronological Train Split: {len(splits['X_train_quant'])} rows")
    print(f"  -> Chronological Out-of-Time Test Split: {len(splits['X_test_quant'])} rows")
    
    print("\n[Step 4/5] Training Models & Running Ablation Experiment...")
    results = train_and_compare_models(splits, model_type=model_type)
    
    print("\n" + "=" * 65)
    print("         TULSA REGIONAL MODEL EVALUATION & METRICS SUMMARY")
    print("=" * 65)
    print(f" Target Location: Tulsa, OK Metropolitan Area (Live Base: ${live_pump_price:.2f}/gal)")
    print(f" Algorithm: {model_type.upper()}")
    print("-" * 65)
    print(" Metric                      Baseline (Quant)   Hybrid (LLM-Augmented)")
    print("-" * 65)
    for metric in ["MAE", "RMSE", "MAPE (%)", "Directional Accuracy (%)"]:
        m_q = results['metrics_quant'][metric]
        m_h = results['metrics_hybrid'][metric]
        print(f" {metric:<27} {m_q:<18} {m_h:<18}")
    print("-" * 65)
    print(f" MAE Improvement with LLM Event Features:  +{results['mae_improvement_pct']}% reduction in error")
    print(f" RMSE Improvement with LLM Event Features: +{results['rmse_improvement_pct']}% reduction in error")
    print("=" * 65)
    
    print("\n[Step 5/5] Real-Time Tulsa Shock Scenario Simulation...")
    scenario_1 = "EF-3 Tornado strikes West Tulsa industrial corridor, halting 125,000 bpd HF Sinclair refinery loading racks."
    print(f"\n  Scenario: '{scenario_1}'")
    shock_1 = extract_event_features_llm(scenario_1, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
    
    latest_row = splits['X_test_hybrid'].iloc[-1:].copy()
    normal_pred = results['model_hybrid'].predict(latest_row)[0]
    
    shocked_row_1 = latest_row.copy()
    shocked_row_1['event_overall_price_pressure'] += shock_1['overall_price_pressure']
    shocked_row_1['event_supply_disruption'] += shock_1['supply_disruption']
    shocked_pred_1 = results['model_hybrid'].predict(shocked_row_1)[0]
    
    delta_1 = shocked_pred_1 - normal_pred
    print(f"  -> Baseline 5-Day Tulsa Retail Forecast: ${normal_pred:.3f}/gal")
    print(f"  -> Shocked 5-Day Tulsa Retail Forecast:  ${shocked_pred_1:.3f}/gal")
    print(f"  -> Estimated Impact of Local Refinery Shock: +${delta_1:.3f}/gal (+{(delta_1/normal_pred)*100:.2f}%)")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_tulsa_pipeline(live_pump_price=3.89, use_llm_api=use_api, model_type="ridge")