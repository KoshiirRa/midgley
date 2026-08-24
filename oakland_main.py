"""
Oakland & SF Bay Area Regional Master Execution Script (oakland_main.py)
Standalone 6-Step Pipeline tailored to Oakland, CA & 9-County SF Bay Area (PADD 5 West Coast):
1. Market Data Ingestion & Pump Price Anchoring (Oakland Base: $4.950/gal | SF Bay Area Avg: $5.050/gal)
2. Unstructured Regional News, Finlight.me REST API, Chevron Richmond Refinery, Kinder Morgan SFPP Pipeline, CARB Regulatory Burden ($0.953/gal), USGS Seismic, CAL FIRE Wildfire & NOAA CA Weather Processing
3. Richmond Crack Spread Feature Engineering & Decayed Event Memory Fusion
4. Quantitative Model Training & Ablation Evaluation
5. Real-Time Oakland Regional, Seismic, Wildfire & Maritime Shock Scenario Simulations
6. MLOps Prediction Logging & Rolling Performance Tracking
"""

import os
import sys
import logging
import pandas as pd
import numpy as np

from src.oakland_regional import fetch_oakland_market_data, get_oakland_regional_events, TOTAL_CARB_TAX_BURDEN
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models
from src.prediction_logger import log_predictions, generate_performance_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_oakland_pipeline(
    live_oakland_price: float = 5.550, 
    live_bayarea_price: float = 5.650, 
    use_llm_api: bool = False, 
    model_type: str = "ridge"
):
    print("=" * 80)
    print("  OAKLAND & SF BAY AREA METRO GAS PRICE PREDICTION PIPELINE (PADD 5 WEST COAST)")
    print(f"  LIVE PUMP PRICE ANCHORS: Oakland (East Bay): ${live_oakland_price:.3f}/gal | SF Bay Area Avg: ${live_bayarea_price:.3f}/gal")
    print(f"  CARB TOTAL TAX & REGULATORY BURDEN: ${TOTAL_CARB_TAX_BURDEN:.3f}/gal")
    print("=" * 80)

    # Step 1: Ingest Market Data for Oakland & SF Bay Area Region & Anchor Pump Prices
    print("\n[Step 1/6] Ingesting Market Data & Calibrating Regional Pump Prices...")
    market_df = fetch_oakland_market_data(
        start_date="2022-01-01", 
        live_oakland_price=live_oakland_price, 
        live_bayarea_price=live_bayarea_price
    )
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Oakland Retail Base (East Bay): ${live_oakland_price:.3f}/gal")
    print(f"  -> SF Bay Area Regional Average:   ${live_bayarea_price:.3f}/gal")
    print(f"  -> San Francisco Metro Base:      ${live_oakland_price + 0.170:.3f}/gal")
    print(f"  -> San Jose / Silicon Valley Base: ${live_oakland_price + 0.030:.3f}/gal")
    print(f"  -> North Bay / Solano Base:        ${live_oakland_price - 0.100:.3f}/gal")
    print(f"  -> Embedded CARB Tax & Fee Burden: ${TOTAL_CARB_TAX_BURDEN:.3f}/gal")

    # Step 2: Extract Features from Localized News, NOAA Weather, Seismic & Regulatory Feeds
    print("\n[Step 2/6] Extracting LLM Factor Metrics from Finlight, USGS Seismic, CAL FIRE & NOAA Feeds...")
    events_raw = get_oakland_regional_events()
    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api)
    
    print("  Sample Scored Events:")
    for _, r in events_df.iloc[:3].iterrows():
        print(f"    - [{r['date'].strftime('%Y-%m-%d')}] '{r['headline'][:65]}...'")
        print(f"       -> GeoRisk: {r['geopolitical_risk']}, SupplyDisruption: {r['supply_disruption']}, NetPressure: {r['overall_price_pressure']}")

    # Step 3: Feature Engineering & Decayed Memory Fusion
    print("\n[Step 3/6] Engineering Richmond Crack Spread & Fusing Decayed Event Memory...")
    features_df = create_feature_matrix(market_df, events_df, forecast_horizon=5)
    splits = prepare_chronological_splits(features_df, train_ratio=0.8, forecast_horizon=5)
    
    print(f"  -> Chronological Train Split: {len(splits['X_train_hybrid'])} rows")
    print(f"  -> Chronological Out-of-Time Test Split: {len(splits['X_test_hybrid'])} rows")

    # Step 4: Model Training & Evaluation
    print("\n[Step 4/6] Training Models & Running Ablation Experiment...")
    results = train_and_compare_models(splits, model_type=model_type)

    print("\n" + "=" * 65)
    print("      OAKLAND & BAY AREA REGIONAL MODEL EVALUATION & METRICS SUMMARY")
    print("=" * 65)
    print(f" Target Location: Oakland CA & SF Bay Area (Oakland Base: ${live_oakland_price:.3f}/gal | Bay Area Avg: ${live_bayarea_price:.3f}/gal)")
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
    print("\n[Step 5/6] Real-Time Oakland Regional, Seismic, Wildfire & Maritime Scenario Simulations...")
    scenarios = [
        {
            "name": "Scenario 1: USGS Hayward Fault M>=6.0 Seismic Quake & Kinder Morgan Pipeline Shutoff",
            "headline": "M6.3 earthquake on Hayward Fault ruptures feeder lines, forces automatic refinery hydrocracker trips, and halts Kinder Morgan SFPP pipeline pump stations."
        },
        {
            "name": "Scenario 2: CAL FIRE Red Flag & PG&E PSPS Wildfire Power Shutoff",
            "headline": "Severe Diablo winds trigger PG&E Public Safety Power Shutoff (PSPS) across East Bay hills, tripping Chevron Richmond and PBF Martinez power grids."
        },
        {
            "name": "Scenario 3: Chevron Richmond Refinery Unplanned Hydrocracker Outage",
            "headline": "Unplanned hydrocracker unit trip at 245,000 bpd Chevron Richmond refinery triggers emergency flaring and tightens PADD 5 unleaded rack supplies."
        },
        {
            "name": "Scenario 4: CARB CaRFG Summer-Blend Transition Compliance Surge",
            "headline": "California Air Resources Board (CARB) mandates summer CaRFG blend transition, surging refining compliance costs."
        },
        {
            "name": "Scenario 5: NOAA PTWC Pacific Tsunami Warning & Carquinez Strait Dock Closure",
            "headline": "Pacific subduction zone earthquake triggers NOAA Tsunami Advisory; US Coast Guard restricts crude oil tanker docking in Carquinez Strait."
        },
        {
            "name": "Scenario 6: NHC EPAC Tropical Storm Remnant Grid Failure",
            "headline": "Remnants of Eastern Pacific tropical storm dump heavy rain across Bay Area, causing PG&E substation flooding."
        }
    ]

    base_row = splits['X_test_hybrid'].iloc[-1:].copy()
    raw_pred_price = results['model_hybrid'].predict(base_row)[0]
    last_hist_price = splits['test_df']['gasoline_rbob'].iloc[-1]
    
    baseline_return = (raw_pred_price - last_hist_price) / last_hist_price
    oakland_baseline_forecast = live_oakland_price * (1.0 + baseline_return)
    bayarea_baseline_forecast = live_bayarea_price * (1.0 + baseline_return)

    print(f"\n  Baseline 5-Day Projected Pump Prices (No Shock):")
    print(f"   -> Oakland Retail 5-Day Target:   ${oakland_baseline_forecast:.3f}/gal (Current: ${live_oakland_price:.3f}/gal)")
    print(f"   -> SF Bay Area 5-Day Target:     ${bayarea_baseline_forecast:.3f}/gal (Current: ${live_bayarea_price:.3f}/gal)")

    print("\n  Simulating Counterfactual Shock Scenarios:")
    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        
        supply_impact = scores['supply_disruption'] * 0.055
        pressure_impact = scores['overall_price_pressure'] * 0.040
        geo_impact = scores['geopolitical_risk'] * 0.025
        net_shock_pct = supply_impact + pressure_impact + geo_impact

        shocked_oakland_5d = oakland_baseline_forecast * (1.0 + net_shock_pct)
        diff = shocked_oakland_5d - oakland_baseline_forecast

        print(f"\n   * {sc['name']}")
        print(f"     Headline: \"{headline}\"")
        print(f"     Simulated Oakland 5-Day Target: ${shocked_oakland_5d:.3f}/gal | Impact: {diff:+.3f}/gal ({net_shock_pct*100:+.2f}%)")

    # Step 6: Log Out-of-Time Predictions
    print("\n[Step 6/6] Logging Out-of-Time Predictions to prediction_history.csv...")
    last_date = market_df['date'].iloc[-1]
    pred_oakland_df = pd.DataFrame([{
        'date': last_date,
        'current_price': live_oakland_price,
        'predicted_5d_price': oakland_baseline_forecast
    }])
    log_predictions(pred_oakland_df, region="Oakland_CA", model_version=f"v1.4-{model_type.capitalize()}")

    pred_bayarea_df = pd.DataFrame([{
        'date': last_date,
        'current_price': live_bayarea_price,
        'predicted_5d_price': bayarea_baseline_forecast
    }])
    log_predictions(pred_bayarea_df, region="BayArea_CA", model_version=f"v1.4-{model_type.capitalize()}")

    print("\n" + "=" * 80)
    print("  OAKLAND & SF BAY AREA REGIONAL PIPELINE EXECUTION COMPLETE")
    print("=" * 80)
    return results

if __name__ == "__main__":
    run_oakland_pipeline()
