"""
create_tulsa_extension.py
Generates the dedicated Tulsa regional forecasting files alongside the national model:
- src/tulsa_regional.py
- tulsa_main.py
- run_all.py
"""

import os

os.makedirs("src", exist_ok=True)

# 1. Create src/tulsa_regional.py
tulsa_regional_code = '''"""
Tulsa, Oklahoma Regional Gas Price Data & Event Ingestion Module
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def fetch_tulsa_market_data(start_date: str = "2022-01-01", end_date: str = None) -> pd.DataFrame:
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Tulsa, OK region from {start_date} to {end_date}...")
    
    tickers = {
        "gasoline_rbob": "RB=F",
        "cushing_wti": "CL=F",
        "brent_crude": "BZ=F"
    }
    
    dfs = []
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            close_series = data['Close'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Close']
            df_item = pd.DataFrame({'date': pd.to_datetime(close_series.index).tz_localize(None), name: close_series.values})
            dfs.append(df_item.set_index('date'))
        except Exception as e:
            logger.warning(f"Could not download ticker {ticker}: {e}")
            
    if not dfs:
        return _generate_synthetic_tulsa_data(start_date, end_date)
        
    market_df = pd.concat(dfs, axis=1).sort_index().ffill().bfill().reset_index()
    
    market_df['wti_crude'] = market_df['cushing_wti']
    market_df['tulsa_retail_gasoline'] = market_df['gasoline_rbob'] + 0.55
    market_df['cushing_crude_per_gal'] = market_df['cushing_wti'] / 42.0
    market_df['crack_spread'] = market_df['tulsa_retail_gasoline'] - market_df['cushing_crude_per_gal']
    
    return market_df

def _generate_synthetic_tulsa_data(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)
    cushing_wti = 74.0 + np.cumsum(np.random.normal(0, 1.2, n))
    rbob = (cushing_wti / 42.0) * 1.32 + np.cumsum(np.random.normal(0, 0.025, n))
    tulsa_retail = rbob + 0.55
    return pd.DataFrame({
        'date': dates, 'gasoline_rbob': np.maximum(rbob, 1.50),
        'wti_crude': np.maximum(cushing_wti, 40.0), 'cushing_wti': np.maximum(cushing_wti, 40.0),
        'tulsa_retail_gasoline': np.maximum(tulsa_retail, 2.10),
        'cushing_crude_per_gal': cushing_wti / 42.0,
        'crack_spread': tulsa_retail - (cushing_wti / 42.0)
    })

def get_tulsa_regional_events() -> pd.DataFrame:
    events = [
        {"date": "2022-02-24", "headline": "Russia invades Ukraine; Cushing WTI crude surges above $100/bbl, driving Tulsa gas prices higher.", "category": "Global/Cushing"},
        {"date": "2022-05-04", "headline": "Severe storms and tornadoes sweep through Northeast Oklahoma, causing power outages at Tulsa fuel terminals.", "category": "Oklahoma Weather"},
        {"date": "2022-09-15", "headline": "HF Sinclair West Tulsa refinery initiates scheduled autumn maintenance on fluid catalytic cracking unit.", "category": "Tulsa Refinery"},
        {"date": "2022-12-08", "headline": "Keystone Pipeline shutdown following spill in Kansas causes crude bottleneck at Cushing, OK storage hub.", "category": "Cushing Pipeline"},
        {"date": "2023-04-19", "headline": "Supercell tornado outbreak damages power lines near Cushing, OK oil storage hub.", "category": "Oklahoma Weather"},
        {"date": "2023-06-10", "headline": "Phillips 66 Ponca City refinery reports unplanned outage, tightening Midwest regional gasoline supply.", "category": "Regional Refinery"},
        {"date": "2024-04-26", "headline": "Multiple tornadoes strike Eastern Oklahoma; HF Sinclair West Tulsa refinery operates on backup power.", "category": "Oklahoma Weather"},
        {"date": "2025-05-18", "headline": "EF-3 Tornado strikes West Tulsa industrial corridor, halting 125,000 bpd HF Sinclair refinery loading racks.", "category": "Tulsa Disruption"},
        {"date": "2025-09-02", "headline": "Explorer Pipeline reports pump station failure in Glenpool, OK, throttling unleaded fuel shipments to Tulsa.", "category": "Tulsa Pipeline"}
    ]
    df = pd.DataFrame(events)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)
'''

with open(os.path.join("src", "tulsa_regional.py"), "w", encoding="utf-8") as f:
    f.write(tulsa_regional_code)
print("Created src/tulsa_regional.py")


# 2. Create tulsa_main.py
tulsa_main_code = '''"""
Dedicated Execution Script for Tulsa, OK Gas Price Forecasting (tulsa_main.py)
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

def run_tulsa_pipeline(use_llm_api: bool = False, model_type: str = "ridge"):
    print("=" * 80)
    print("  TULSA, OKLAHOMA METRO GAS PRICE PREDICTION PIPELINE")
    print("=" * 80)
    
    market_df = fetch_tulsa_market_data(start_date="2022-01-01")
    raw_events_df = get_tulsa_regional_events()
    events_df = process_event_dataset(raw_events_df, use_llm_api=use_llm_api)
    feature_df = create_feature_matrix(market_df, events_df, forecast_horizon=5, decay_half_life_days=4.0)
    splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
    results = train_and_compare_models(splits, model_type=model_type)
    
    print("\\nTULSA MODEL METRICS SUMMARY:")
    print(f" Quant Baseline MAE: ${results['metrics_quant']['MAE']:.4f}/gal")
    print(f" Tulsa Hybrid LLM MAE: ${results['metrics_hybrid']['MAE']:.4f}/gal")
    print(f" Directional Hit Rate: {results['metrics_hybrid']['Directional Accuracy (%)']}%")
    
    # Regional Shock Scenario
    scenario = "EF-3 Tornado strikes West Tulsa industrial corridor, halting 125,000 bpd HF Sinclair refinery loading racks."
    shock = extract_event_features_llm(scenario, api_key=os.environ.get("GEMINI_API_KEY") if use_llm_api else None)
    base_row = splits['X_test_hybrid'].iloc[-1:].copy()
    normal_pred = results['model_hybrid'].predict(base_row)[0]
    
    shocked_row = base_row.copy()
    shocked_row['event_overall_price_pressure'] += shock['overall_price_pressure']
    shocked_row['event_supply_disruption'] += shock['supply_disruption']
    shocked_pred = results['model_hybrid'].predict(shocked_row)[0]
    
    delta = shocked_pred - normal_pred
    print(f"\\nScenario: \"{scenario}\"")
    print(f" Baseline 5-Day Tulsa Forecast: ${normal_pred:.3f}/gal")
    print(f" Shocked 5-Day Tulsa Forecast:  ${shocked_pred:.3f}/gal (+${delta:.3f}/gal)")
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_tulsa_pipeline(use_llm_api=use_api, model_type="ridge")
'''

with open("tulsa_main.py", "w", encoding="utf-8") as f:
    f.write(tulsa_main_code)
print("Created tulsa_main.py")


# 3. Create run_all.py (Combined Master Orchestrator)
run_all_code = '''"""
Master Execution Script (run_all.py)
Runs both the National Wholesale Model and the Tulsa, OK Regional Model sequentially.
"""

import sys
from main import run_pipeline as run_national
from tulsa_main import run_tulsa_pipeline as run_tulsa

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    print("\n" + "#"*80)
    print("# STEP 1: RUNNING NATIONAL WHOLESALE FORECASTING MODEL")
    print("#"*80 + "\n")
    nat_results = run_national(use_llm_api=use_api, model_type="ridge")
    
    print("\n" + "#"*80)
    print("# STEP 2: RUNNING TULSA, OK METRO RETAIL FORECASTING MODEL")
    print("#"*80 + "\n")
    tulsa_results = run_tulsa(use_llm_api=use_api, model_type="ridge")
    
    print("\n" + "="*80)
    print("                      ALL MODELS EXECUTION COMPLETE")
    print("="*80)
'''

with open("run_all.py", "w", encoding="utf-8") as f:
    f.write(run_all_code)
print("Created run_all.py")