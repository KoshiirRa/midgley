"""
Port St. Lucie Regional Master Execution Script (src/locations/port_st_lucie/main.py)
Standalone 6-Step Pipeline tailored to the Port St. Lucie, Florida metropolitan area (PADD 1C):
1. Market Data Ingestion & Live Pump Price Anchoring ($3.38/gal base)
2. Unstructured Regional News, Finlight.me REST API, Port Everglades & FLZ147 NOAA Weather Processing
3. Port St. Lucie Rack Crack Spread Feature Engineering & Exponential Memory Decay
4. Quantitative Model Training & Ablation Evaluation
5. Real-Time Port St. Lucie Shock Scenario Simulations (Port Everglades Outage, Hurricane Surge, Marine Tanker Delays)
6. MLOps Prediction Logging & Rolling Performance Tracking
"""

import os
import sys
import logging
import pandas as pd
import numpy as np

from src.locations.port_st_lucie.regional import fetch_port_st_lucie_market_data, get_port_st_lucie_regional_events
from src.event_analyzer import process_event_dataset, extract_event_features_llm
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_and_compare_models, train_multi_horizon_models
from src.prediction_logger import log_predictions, generate_performance_report, backfill_new_region_history, resolve_model_tag, backfill_actual_prices_and_evaluate
from src.live_fuel_feed import fetch_live_metro_retail_price

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_port_st_lucie_pipeline(live_pump_price: float = None, use_llm_api: bool = False, model_type: str = "ridge"):
    if live_pump_price is None:
        live_pump_price = fetch_live_metro_retail_price("Port_St_Lucie_FL")["price"]

    print("=" * 80)
    print("  PORT ST. LUCIE, FLORIDA METRO GAS PRICE PREDICTION PIPELINE")
    print(f"  LIVE PUMP PRICE ANCHOR: ${live_pump_price:.2f}/gal (PADD 1C South Atlantic)")
    print("=" * 80)

    # Step 1: Ingest Market Data for Port St. Lucie Region & Anchor Live Pump Price
    print("\n[Step 1/6] Ingesting Market Data & Calibrating Live Port St. Lucie Pump Price...")
    market_df = fetch_port_st_lucie_market_data(start_date="2022-01-01", live_current_price=live_pump_price)
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Live Calibrated Port St. Lucie Pump Price Anchor: ${live_pump_price:.2f}/gal")

    # Step 2: Extract Features from Localized News, NOAA Weather, Maritime & Social Feeds
    print("\n[Step 2/6] Extracting LLM Factor Metrics from Finlight, FLZ147 NOAA, Port Everglades & Marine Feeds...")
    events_raw = get_port_st_lucie_regional_events()
    events_df = process_event_dataset(events_raw, use_llm_api=use_llm_api)
    
    print("  Sample Scored Events:")
    for _, r in events_df.iloc[:3].iterrows():
        print(f"    - [{r['date'].strftime('%Y-%m-%d')}] '{r['headline'][:65]}...'")
        print(f"       -> GeoRisk: {r['geopolitical_risk']}, SupplyDisruption: {r['supply_disruption']}, NetPressure: {r['overall_price_pressure']}")

    # Step 3 & 4: Multi-Horizon Feature Engineering & Model Training (1D-5D)
    print("\n[Step 3/6] Engineering Port St. Lucie Rack Crack Spread & Fusing Decayed Event Memory (Multi-Horizon 1D-5D)...")
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
    print("     PORT ST. LUCIE REGIONAL MODEL EVALUATION & METRICS SUMMARY (5-DAY)")
    print("=" * 65)
    print(f" Target Location: Port St. Lucie, FL Metropolitan Area (Live Base: ${live_pump_price:.2f}/gal)")
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
    print("\n[Step 5/6] Real-Time Port St. Lucie Regional & Marine Shock Scenario Simulations...")
    scenarios = [
        {
            "name": "Scenario 1: Port Everglades Marine Terminal Deluge & Loading Rack Halt",
            "headline": "Historic flash deluge floods Fort Lauderdale & Port Everglades fuel loading racks, halting tank truck dispatches into Port St. Lucie."
        },
        {
            "name": "Scenario 2: Category 3 Atlantic Hurricane Landfall & Port Closure",
            "headline": "Category 3 Hurricane storm surge forces closure of Port Everglades and Port Canaveral berths, triggering Treasure Coast fuel panic buying."
        },
        {
            "name": "Scenario 3: Straits of Florida Marine Tanker Barge Transit Bottleneck",
            "headline": "Severe gales in Straits of Florida delay Gulf Coast waterborne tank barge arrivals at South Florida marine terminals."
        },
        {
            "name": "Scenario 4: Florida Motor Fuel Tax Holiday Expiration",
            "headline": "Florida state motor fuel tax holiday expires, reinstating state excise tax and increasing retail pump prices by +$0.253/gal."
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
    
    base_row = splits.get('X_live_hybrid', splits['X_test_hybrid'].iloc[-1:]).copy()
    raw_pred_price = results['model_hybrid'].predict(base_row)[0]
    last_hist_price = float(splits.get('live_current_price', splits['test_df']['gasoline_rbob'].iloc[-1]))
    
    baseline_return = (raw_pred_price - last_hist_price) / last_hist_price
    psl_baseline_forecast = live_pump_price * (1.0 + baseline_return)
    
    print(f"\n Baseline Port St. Lucie 5-Day Forecast (No Shock): ${psl_baseline_forecast:.3f}/gal (Base: ${live_pump_price:.2f}/gal)")
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
        
        sim_psl_price = psl_baseline_forecast * (1.0 + adjusted_shock_pct)
        dollar_change = sim_psl_price - psl_baseline_forecast
        pct_change = (dollar_change / psl_baseline_forecast) * 100
        
        scenario_results.append({
            "Scenario": sc["name"],
            "Adjusted 5D Price": f"${sim_psl_price:.3f}/gal",
            "Impact ($)": f"{dollar_change:+.3f}/gal",
            "Impact (%)": f"{pct_change:+.2f}%"
        })
        print(f"  {sc['name']:<56} -> ${sim_psl_price:.3f}/gal ({dollar_change:+.3f} | {pct_change:+.2f}%)")
    print("=" * 75)

    # Step 6: MLOps Prediction Logging & Backfilling across 1D-5D (Issue #314)
    print("\n[Step 6/6] Logging Predictions to MLOps Store (Multi-Horizon 1D-5D)...")
    psl_version = resolve_model_tag("Port_St_Lucie_FL", model_type=model_type)
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
        
        hist_psl_base = h_splits['test_df']['port_st_lucie_retail_gasoline'] if 'port_st_lucie_retail_gasoline' in h_splits['test_df'].columns else (h_splits['test_df']['gasoline_rbob'] + dynamic_margin)
        rbob_hist = h_splits['test_df']['gasoline_rbob']
        pred_ret_hybrid = (h_preds_hybrid - rbob_hist) / rbob_hist
        pred_ret_quant = (h_preds_quant - rbob_hist) / rbob_hist
        hist_psl_pred = hist_psl_base * (1.0 + pred_ret_hybrid)
        hist_psl_quant = hist_psl_base * (1.0 + pred_ret_quant)

        backfill_new_region_history(
            test_dates=h_test_dates,
            base_prices=hist_psl_base,
            predicted_prices=hist_psl_pred,
            region="Port_St_Lucie_FL",
            model_version=psl_version,
            forecast_horizon_days=h,
            quant_baseline_prices=hist_psl_quant
        )

        raw_pred_h = float(h_res['live_pred_price'])
        raw_quant_h = float(h_res.get('live_pred_quant_price', raw_pred_h))
        last_hist_price_h = float(h_splits.get('live_current_price', h_splits['test_df']['gasoline_rbob'].iloc[-1]))
        baseline_return_h = (raw_pred_h - last_hist_price_h) / last_hist_price_h if last_hist_price_h > 0 else 0.0
        quant_return_h = (raw_quant_h - last_hist_price_h) / last_hist_price_h if last_hist_price_h > 0 else 0.0
        psl_h_forecast = live_pump_price * (1.0 + baseline_return_h)
        psl_h_quant = live_pump_price * (1.0 + quant_return_h)

        today_df = pd.DataFrame([{
            'date': last_date,
            'current_price': live_pump_price,
            'predicted_5d_price': psl_h_forecast,
            'quant_baseline_5d_price': psl_h_quant,
            'forecast_horizon_days': h,
            'is_retroactive_backtest': False
        }])
        log_predictions(today_df, region="Port_St_Lucie_FL", model_version=psl_version, run_type="LIVE_PROSPECTIVE", forecast_horizon_days=h, is_retroactive_backtest=False)

    backfill_actual_prices_and_evaluate(target_region="Port_St_Lucie_FL")
    print(f"  -> Logged & backfilled discrete 1D-5D predictions for Port_St_Lucie_FL.")

    return {
        "results": results,
        "baseline_forecast": psl_baseline_forecast,
        "live_pump_price": live_pump_price,
        "scenarios": scenario_results
    }


if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    model_choice = "ridge"
    for arg in sys.argv:
        if arg.startswith("--model="):
            model_choice = arg.split("=")[1].lower()
            
    run_port_st_lucie_pipeline(use_llm_api=use_api, model_type=model_choice)
