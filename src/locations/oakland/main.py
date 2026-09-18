"""
Oakland & SF Bay Area Regional Master Execution Script (src/locations/oakland/main.py)
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

from src.locations.oakland.regional import fetch_oakland_market_data, get_oakland_regional_events, TOTAL_CARB_TAX_BURDEN
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models, train_multi_horizon_models
from src.prediction_logger import log_predictions, generate_performance_report, backfill_new_region_history, resolve_model_tag, backfill_actual_prices_and_evaluate
from src.live_fuel_feed import fetch_live_metro_retail_price

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_oakland_pipeline(
    live_oakland_price: float = None, 
    live_bayarea_price: float = None, 
    use_llm_api: bool = False, 
    model_type: str = "ridge"
):
    if live_oakland_price is None:
        live_oakland_price = fetch_live_metro_retail_price("Oakland_CA")["price"]
    if live_bayarea_price is None:
        live_bayarea_price = fetch_live_metro_retail_price("BayArea_CA")["price"]

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
    print(f"  -> Embedded CARB Tax & Fee Burden: ${TOTAL_CARB_TAX_BURDEN:.3f}/gal")

    # Step 2: Extract Features from Localized News, NOAA Weather, Seismic & Regulatory Feeds
    print("\n[Step 2/6] Extracting LLM Factor Metrics from Finlight, USGS Seismic, CAL FIRE & NOAA Feeds...")
    events_raw = get_oakland_regional_events()
    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api)
    
    print("  Sample Scored Events:")
    for _, r in events_df.iloc[:3].iterrows():
        print(f"    - [{r['date'].strftime('%Y-%m-%d')}] '{r['headline'][:65]}...'")
        print(f"       -> GeoRisk: {r['geopolitical_risk']}, SupplyDisruption: {r['supply_disruption']}, NetPressure: {r['overall_price_pressure']}")

    # Step 3 & 4: Multi-Horizon Feature Engineering & Model Training (1D-5D)
    print("\n[Step 3/6] Engineering Richmond Crack Spread & Fusing Decayed Event Memory (Multi-Horizon 1D-5D)...")
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
    print("      OAKLAND & BAY AREA REGIONAL MODEL EVALUATION & METRICS SUMMARY (5-DAY)")
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
    print("\n[Step 5/6] Real-Time Oakland, Seismic & Wildfire Shock Scenario Simulations...")
    scenarios = [
        {
            "name": "Scenario 1: Chevron Richmond 250k bpd Refinery Flaring Outage",
            "headline": "Chevron Richmond refinery reports major flaring and fluid catalytic cracker unit trip following power disruption."
        },
        {
            "name": "Scenario 2: M7.0 Hayward Fault Earthquake Infrastructure Rupture",
            "headline": "Magnitude 7.0 earthquake strikes Hayward Fault in East Bay, damaging Kinder Morgan SFPP pipelines and rack terminals."
        },
        {
            "name": "Scenario 3: Severe Northern California Wildfire Grid Curtailment",
            "headline": "Wildfire outbreak prompts PG&E Public Safety Power Shutoffs, curtailing Bay Area refining and terminal blending operations."
        },
        {
            "name": "Scenario 4: CARB Low Carbon Fuel Standard (LCFS) Surcharge Hike",
            "headline": "California Air Resources Board adopts amendments increasing LCFS compliance target stringency by +$0.12/gal."
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
    oakland_baseline_forecast = live_oakland_price * (1.0 + baseline_return)
    bayarea_baseline_forecast = live_bayarea_price * (1.0 + baseline_return)

    print(f"\n  CURRENT BASE PRICES: Oakland: ${live_oakland_price:.3f}/gal | Bay Area: ${live_bayarea_price:.3f}/gal")
    print(f"  BASELINE 5-DAY FORECAST (Oakland):   ${oakland_baseline_forecast:.3f}/gal ({baseline_return*100:+.2f}%)")
    print(f"  BASELINE 5-DAY FORECAST (Bay Area):  ${bayarea_baseline_forecast:.3f}/gal ({baseline_return*100:+.2f}%)")
    print("-" * 80)

    for sc in scenarios:
        headline = sc['headline']
        scores = extract_event_features_llm(headline, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
        supply_impact = scores['supply_disruption'] * 0.045
        pressure_impact = scores['overall_price_pressure'] * 0.035
        geo_impact = scores['geopolitical_risk'] * 0.020
        net_shock_pct = supply_impact + pressure_impact + geo_impact

        shocked_oakland_5d = oakland_baseline_forecast * (1.0 + net_shock_pct)
        diff = shocked_oakland_5d - oakland_baseline_forecast

        print(f"\n   * {sc['name']}")
        print(f"     Headline: \"{headline}\"")
        print(f"     Simulated Oakland 5-Day Target: ${shocked_oakland_5d:.3f}/gal | Impact: {diff:+.3f}/gal ({net_shock_pct*100:+.2f}%)")

    # Step 6: Log Out-of-Time Predictions & Historical Test Split Backfill across 1D-5D (Issue #314)
    print("\n[Step 6/6] Logging Out-of-Time Predictions (Multi-Horizon 1D-5D)...")
    oakland_version = resolve_model_tag("Oakland_CA", model_type=model_type)
    bayarea_version = resolve_model_tag("BayArea_CA", model_type=model_type)
    last_date = market_df['date'].iloc[-1]

    for h in [1, 2, 3, 4, 5]:
        h_res = multi_horizon_results.get(h)
        if not h_res:
            continue
        h_splits = h_res['splits']
        h_test_dates = h_splits['test_df']['date']
        h_preds_hybrid = h_res['predictions_hybrid']

        # Calculate historical test split prices for Oakland ($2.05 margin) and Bay Area ($2.15 margin)
        hist_oakland_base = h_splits['test_df']['gasoline_rbob'] + 2.05
        hist_oakland_pred = h_preds_hybrid + 2.05
        hist_bayarea_base = h_splits['test_df']['gasoline_rbob'] + 2.15
        hist_bayarea_pred = h_preds_hybrid + 2.15

        backfill_new_region_history(
            test_dates=h_test_dates,
            base_prices=hist_oakland_base,
            predicted_prices=hist_oakland_pred,
            region="Oakland_CA",
            model_version=oakland_version,
            forecast_horizon_days=h
        )

        backfill_new_region_history(
            test_dates=h_test_dates,
            base_prices=hist_bayarea_base,
            predicted_prices=hist_bayarea_pred,
            region="BayArea_CA",
            model_version=bayarea_version,
            forecast_horizon_days=h
        )

        raw_pred_h = float(h_res['live_pred_price'])
        last_hist_price_h = float(h_splits['test_df']['gasoline_rbob'].iloc[-1])
        baseline_return_h = (raw_pred_h - last_hist_price_h) / last_hist_price_h
        oakland_h_forecast = live_oakland_price * (1.0 + baseline_return_h)
        bayarea_h_forecast = live_bayarea_price * (1.0 + baseline_return_h)

        pred_oakland_df = pd.DataFrame([{
            'date': last_date,
            'current_price': live_oakland_price,
            'predicted_5d_price': oakland_h_forecast,
            'forecast_horizon_days': h
        }])
        pred_bayarea_df = pd.DataFrame([{
            'date': last_date,
            'current_price': live_bayarea_price,
            'predicted_5d_price': bayarea_h_forecast,
            'forecast_horizon_days': h
        }])
        log_predictions(pred_oakland_df, region="Oakland_CA", model_version=oakland_version, forecast_horizon_days=h)
        log_predictions(pred_bayarea_df, region="BayArea_CA", model_version=bayarea_version, forecast_horizon_days=h)

    backfill_actual_prices_and_evaluate()
    print(f"  -> Logged & backfilled discrete 1D-5D predictions for Oakland_CA and BayArea_CA.")

    print("\n" + "=" * 80)
    print("  OAKLAND & SF BAY AREA REGIONAL PIPELINE EXECUTION COMPLETE")
    print("=" * 80)
    return results

if __name__ == "__main__":
    run_oakland_pipeline()
