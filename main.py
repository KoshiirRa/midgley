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

def run_pipeline(use_llm_api: bool = False, model_type: str = "ridge"):
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
    
    # Step 5: Enhanced Real-Time Counterfactual Scenario Simulator
    print("\n[Step 5/5] Real-Time National Shock Scenario Simulations...")
    
    scenarios = [
        {
            "name": "Scenario 1: Gulf Coast Hurricane Refinery Outage",
            "headline": "Category 5 Hurricane slams into Texas Gulf Coast refining complex, halting 25% of US gasoline output."
        },
        {
            "name": "Scenario 2: Emergency OPEC Output Cut",
            "headline": "OPEC+ emergency meeting votes to immediately cut oil production by 2.0 million barrels per day."
        }
    ]
    
    base_row = splits['X_test_hybrid'].iloc[-1:].copy()
    raw_pred_price = results['model_hybrid'].predict(base_row)[0]
    current_market_price = splits['test_df']['gasoline_rbob'].iloc[-1]
    
    print(f"\n  LATEST WHOLESALE MARKET PRICE:   ${current_market_price:.3f}/gal")
    print(f"  BASELINE 5-DAY NATIONAL FORECAST: ${raw_pred_price:.3f}/gal")
    print("-" * 80)
    
    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        
        supply_impact = scores['supply_disruption'] * 0.045
        pressure_impact = scores['overall_price_pressure'] * 0.035
        geo_impact = scores['geopolitical_risk'] * 0.020
        opec_impact = scores['opec_action'] * 0.030
        net_shock_pct = supply_impact + pressure_impact + geo_impact + opec_impact
        
        shocked_forecast = raw_pred_price * (1.0 + net_shock_pct)
        delta_dollars = shocked_forecast - raw_pred_price
        
        print(f"\n  [{sc['name']}]")
        print(f"  Headline: \"{headline}\"")
        print(f"  LLM Extraction -> Supply Disruption: {scores['supply_disruption']:+.2f}, Net Pressure: {scores['overall_price_pressure']:+.2f}")
        print(f"  -> Shocked 5-Day Forecast:  ${shocked_forecast:.3f}/gal")
        print(f"  -> Estimated Price Shock:   +${delta_dollars:.3f}/gal ({net_shock_pct*100:+.2f}%)")
        
    print("=" * 80)
    print("National Pipeline Execution Complete!\n")
    
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_pipeline(use_llm_api=use_api, model_type="ridge")
