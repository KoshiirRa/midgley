"""
Main Orchestration Script for LLM-Augmented Unleaded Gas Price Forecasting
Demonstrates the full pipeline: Data Ingestion -> LLM Event Extraction -> Feature Fusion -> Model Comparison -> Scenario Simulation.
"""

import os
import sys
import pandas as pd
import numpy as np
import logging

from src.data_ingestion import fetch_market_data, get_historical_event_dataset
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_pipeline(use_llm_api: bool = False, model_type: str = "xgboost"):
    print("=" * 80)
    print("  LLM-AUGMENTED UNLEADED GAS PRICE PREDICTION PIPELINE")
    print("=" * 80)
    
    # Step 1: Data Ingestion
    print("\n[Step 1/5] Ingesting Commodity Market Data & Unstructured Event Logs...")
    market_df = fetch_market_data(start_date="2022-01-01")
    raw_events_df = get_historical_event_dataset()
    print(f"  -> Market trading days fetched: {len(market_df)}")
    print(f"  -> Historical news events loaded: {len(raw_events_df)}")
    
    # Step 2: LLM Event Analysis
    print("\n[Step 2/5] Extracting LLM Factor Metrics from Unstructured Event Headlines...")
    events_df = process_event_dataset(raw_events_df, use_llm_api=use_llm_api)
    print("  Sample Scored Events:")
    for idx, row in events_df.head(3).iterrows():
        print(f"    - [{row['date'].strftime('%Y-%m-%d')}] '{row['headline'][:65]}...'")
        print(f"       -> GeoRisk: {row['geopolitical_risk']}, SupplyDisruption: {row['supply_disruption']}, OPEC: {row['opec_action']}, NetPressure: {row['overall_price_pressure']}")
        
    # Step 3: Feature Engineering & Fusion
    print("\n[Step 3/5] Engineering Technical Features & Fusing Decayed Event Memory...")
    feature_df = create_feature_matrix(market_df, events_df, forecast_horizon=5, decay_half_life_days=5.0)
    print(f"  -> Engineered dataset shape: {feature_df.shape}")
    
    splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
    print(f"  -> Chronological Train Split: {len(splits['X_train_quant'])} rows")
    print(f"  -> Chronological Out-of-Time Test Split: {len(splits['X_test_quant'])} rows")
    
    # Step 4: Model Training & Ablation Evaluation
    print("\n[Step 4/5] Training Models & Running Ablation Experiment (Quant-Only vs. LLM Hybrid)...")
    results = train_and_compare_models(splits, model_type=model_type)
    
    print("\n" + "=" * 65)
    print("             MODEL EVALUATION & METRICS SUMMARY")
    print("=" * 65)
    print(f" Algorithm: {model_type.upper()}")
    print("-" * 65)
    print(f" Metric                      Baseline (Quant)   Hybrid (LLM-Augmented)")
    print("-" * 65)
    for metric in ["MAE", "RMSE", "MAPE (%)", "Directional Accuracy (%)"]:
        m_q = results['metrics_quant'][metric]
        m_h = results['metrics_hybrid'][metric]
        print(f" {metric:<27} {m_q:<18} {m_h:<18}")
    print("-" * 65)
    print(f" MAE Improvement with LLM Event Features:  +{results['mae_improvement_pct']}% reduction in error")
    print(f" RMSE Improvement with LLM Event Features: +{results['rmse_improvement_pct']}% reduction in error")
    print("=" * 65)
    
    # Top Feature Importances
    print("\n Top Hybrid Model Feature Importances:")
    top_features = list(results['feature_importance'].items())[:8]
    for feat, val in top_features:
        flag = " [LLM EVENT FEATURE]" if feat.startswith("event_") else ""
        print(f"   - {feat:<30}: {val:.4f}{flag}")
        
    # Step 5: Real-Time Custom Scenario Simulator
    print("\n[Step 5/5] Real-Time Event Scenario Simulation...")
    sample_shock = "Category 5 Hurricane slams into Texas Gulf Coast refining complex, halting 25% of US gasoline output."
    print(f"  Hypothetical Shock Event: \"{sample_shock}\"")
    
    shock_scores = extract_event_features_llm(sample_shock, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
    print(f"  LLM Shock Extraction -> Net Price Pressure: +{shock_scores['overall_price_pressure']}, Supply Disruption: +{shock_scores['supply_disruption']}")
    
    latest_row = splits['X_test_hybrid'].iloc[-1:].copy()
    latest_quant_row = splits['X_test_quant'].iloc[-1:].copy()
    
    normal_pred = results['model_hybrid'].predict(latest_row)[0]
    
    # Apply shock event override
    shocked_row = latest_row.copy()
    shocked_row['event_overall_price_pressure'] += shock_scores['overall_price_pressure']
    shocked_row['event_supply_disruption'] += shock_scores['supply_disruption']
    shocked_pred = results['model_hybrid'].predict(shocked_row)[0]
    
    delta = shocked_pred - normal_pred
    print(f"\n  -> Baseline Forecast (5-day ahead): ${normal_pred:.3f}/gal")
    print(f"  -> Shocked Forecast (5-day ahead):  ${shocked_pred:.3f}/gal")
    print(f"  -> Impact of External Shock:       +${delta:.3f}/gal (+{(delta/normal_pred)*100:.2f}%)")
    print("=" * 80)
    print("Pipeline Execution Complete!\n")
    
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_pipeline(use_llm_api=use_api, model_type="ridge")
