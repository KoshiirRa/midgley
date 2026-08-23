"""
Tulsa, Oklahoma Gas Price Prediction Execution Script (tulsa_main.py)
Fully Calibrated to Live Pump Prices ($3.89/gal) with Dynamic Shock Sensitivity.
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
    print("  TULSA, OKLAHOMA METRO GAS PRICE PREDICTION PIPELINE")
    print(f"  LIVE PUMP PRICE ANCHOR: ${live_pump_price:.2f}/gal")
    print("=" * 80)
    
    # Step 1: Data Ingestion & Live Pump Price Anchor
    print("\n[Step 1/5] Ingesting Market Data & Calibrating Live Tulsa Pump Price...")
    market_df = fetch_tulsa_market_data(start_date="2022-01-01", live_current_price=live_pump_price)
    raw_events_df = get_tulsa_regional_events()
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Live Calibrated Tulsa Pump Price Anchor: ${live_pump_price:.2f}/gal")
    
    # Step 2: LLM Regional Event Analysis
    print("\n[Step 2/5] Extracting LLM Factor Metrics from Oklahoma Event Headlines...")
    events_df = process_event_dataset(raw_events_df, use_llm_api=use_llm_api)
    print("  Sample Scored Regional Events:")
    for idx, row in events_df.head(3).iterrows():
        print(f"    - [{row['date'].strftime('%Y-%m-%d')}] '{row['headline'][:65]}...'")
        print(f"       -> GeoRisk: {row['geopolitical_risk']}, SupplyDisruption: {row['supply_disruption']}, NetPressure: {row['overall_price_pressure']}")
        
    # Step 3: Feature Engineering & Decayed Memory Fusion
    print("\n[Step 3/5] Engineering Tulsa Crack Spread & Fusing Decayed Event Memory...")
    feature_df = create_feature_matrix(market_df, events_df, forecast_horizon=5, decay_half_life_days=4.0)
    splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
    print(f"  -> Chronological Train Split: {len(splits['X_train_quant'])} rows")
    print(f"  -> Chronological Out-of-Time Test Split: {len(splits['X_test_quant'])} rows")
    
    # Step 4: Model Training & Ablation Evaluation
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
    
    # Step 5: Enhanced Real-Time Tulsa Shock Scenario Simulations
    print("\n[Step 5/5] Real-Time Tulsa Regional Shock Scenario Simulations...")
    
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
            "name": "Scenario 3: Polar Vortex Oklahoma Power Freeze",
            "headline": "Severe polar vortex freezes water utilities and power grid across Northeast Oklahoma, halting Tulsa refiners."
        }
    ]
    
    base_row = splits['X_test_hybrid'].iloc[-1:].copy()
    raw_pred_price = results['model_hybrid'].predict(base_row)[0]
    
    # Target prices in splits test set
    last_hist_price = splits['test_df']['gasoline_rbob'].iloc[-1]
    
    # Calculate baseline 5-day return % and project onto live pump price ($3.89)
    baseline_return = (raw_pred_price - last_hist_price) / last_hist_price
    tulsa_baseline_forecast = live_pump_price * (1.0 + baseline_return)
    
    print(f"\n  CURRENT TULSA LIVE PUMP PRICE:      ${live_pump_price:.3f}/gal")
    print(f"  BASELINE 5-DAY TULSA FORECAST:       ${tulsa_baseline_forecast:.3f}/gal ({baseline_return*100:+.2f}%)")
    print("-" * 80)
    
    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        
        # Calculate event shock impact on 5-day return
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
        
    print("=" * 80)
    print("Tulsa Regional Pipeline Execution Complete!\n")
    
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_tulsa_pipeline(live_pump_price=3.89, use_llm_api=use_api, model_type="ridge")