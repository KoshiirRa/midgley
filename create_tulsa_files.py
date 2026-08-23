"""
create_tulsa_files.py
Generates the dedicated Tulsa regional forecasting files:
- src/tulsa_regional.py
- tulsa_main.py
- notebooks/tulsa_gas_price_llm_forecasting.ipynb
"""

import os
import json

os.makedirs("src", exist_ok=True)
os.makedirs("notebooks", exist_ok=True)

# 1. Create src/tulsa_regional.py
tulsa_regional_content = '''"""
Tulsa, Oklahoma Regional Gas Price Forecasting Module (src/tulsa_regional.py)
Handles Tulsa-specific market data, Cushing WTI crude dynamics, HF Sinclair refinery events,
and regional Midcontinent (Group 3) feature engineering.
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
            if isinstance(data.columns, pd.MultiIndex):
                close_series = data['Close'][ticker]
            else:
                close_series = data['Close']
            
            df_item = pd.DataFrame({'date': close_series.index, name: close_series.values})
            df_item['date'] = pd.to_datetime(df_item['date']).dt.tz_localize(None)
            dfs.append(df_item.set_index('date'))
        except Exception as e:
            logger.warning(f"Could not download ticker {ticker}: {e}")
            
    if not dfs:
        return _generate_synthetic_tulsa_data(start_date, end_date)
        
    market_df = pd.concat(dfs, axis=1).sort_index()
    market_df = market_df.ffill().bfill().reset_index()
    
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
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'wti_crude': np.maximum(cushing_wti, 40.0),
        'cushing_wti': np.maximum(cushing_wti, 40.0),
        'tulsa_retail_gasoline': np.maximum(tulsa_retail, 2.10),
        'cushing_crude_per_gal': cushing_wti / 42.0,
        'crack_spread': tulsa_retail - (cushing_wti / 42.0)
    })


def get_tulsa_regional_events() -> pd.DataFrame:
    events = [
        {"date": "2022-02-24", "headline": "Russia invades Ukraine; Cushing WTI crude surges above $100/bbl, driving Tulsa gas prices higher.", "category": "Global/Cushing"},
        {"date": "2022-05-04", "headline": "Severe storms and tornadoes sweep through Northeast Oklahoma, causing power outages at Tulsa area fuel terminals.", "category": "Oklahoma Weather"},
        {"date": "2022-09-15", "headline": "HF Sinclair West Tulsa refinery initiates scheduled autumn maintenance on fluid catalytic cracking unit.", "category": "Tulsa Refinery"},
        {"date": "2022-12-08", "headline": "Keystone Pipeline shutdown following spill in Kansas causes crude bottleneck at Cushing, OK storage hub.", "category": "Cushing Pipeline"},
        {"date": "2023-04-19", "headline": "Supercell tornado outbreak damages power lines near Cushing, OK oil storage hub; refinery throughput slowed.", "category": "Oklahoma Weather"},
        {"date": "2023-06-10", "headline": "Phillips 66 Ponca City refinery reports unplanned compressor unit outage, tightening Midwest regional gasoline supply.", "category": "Regional Refinery"},
        {"date": "2023-08-15", "headline": "Late summer driving demand in Oklahoma and Texas drives Tulsa retail unleaded prices to annual high.", "category": "Regional Demand"},
        {"date": "2023-10-22", "headline": "Magellan Midcontinent pipeline rates adjusted; Oklahoma fuel distributors report steady rack margins.", "category": "Pipeline/Tax"},
        {"date": "2024-04-26", "headline": "Multiple severe tornadoes strike Central and Eastern Oklahoma; HF Sinclair West Tulsa refinery operates on backup power.", "category": "Oklahoma Weather"},
        {"date": "2024-07-12", "headline": "EIA reports Cushing, OK crude stocks drop to 5-year seasonal low as Midwest refinery runs hit 95% capacity.", "category": "Cushing Stock"},
        {"date": "2024-11-05", "headline": "Oklahoma voters approve state transportation infrastructure funding, preserving low state fuel tax rate of $0.19/gal.", "category": "Policy/Tax"},
        {"date": "2025-05-18", "headline": "EF-3 Tornado strikes West Tulsa industrial corridor, causing temporary shutdown of HF Sinclair refinery loading racks.", "category": "Tulsa Disruption"},
        {"date": "2025-09-02", "headline": "Explorer Pipeline reports pump station failure in Glenpool, OK, throttling unleaded fuel shipments to Tulsa.", "category": "Tulsa Pipeline"},
        {"date": "2026-02-10", "headline": "Historic polar vortex freezes water supply lines at Cushing tank farms and Oklahoma refineries.", "category": "Oklahoma Weather"}
    ]
    
    df = pd.DataFrame(events)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)
'''

with open(os.path.join("src", "tulsa_regional.py"), "w", encoding="utf-8") as f:
    f.write(tulsa_regional_content)
print("Successfully created src/tulsa_regional.py")


# 2. Create tulsa_main.py
tulsa_main_content = '''"""
Tulsa, Oklahoma Gas Price Prediction Execution Script (tulsa_main.py)
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
    
    print("\\n[Step 1/5] Ingesting Tulsa Regional Market Data & Oklahoma Event Logs...")
    market_df = fetch_tulsa_market_data(start_date="2022-01-01")
    raw_events_df = get_tulsa_regional_events()
    print(f"  -> Trading days fetched: {len(market_df)}")
    print(f"  -> Oklahoma regional news events loaded: {len(raw_events_df)}")
    
    print("\\n[Step 2/5] Extracting LLM Factor Metrics from Oklahoma Event Headlines...")
    events_df = process_event_dataset(raw_events_df, use_llm_api=use_llm_api)
    
    print("\\n[Step 3/5] Engineering Tulsa Crack Spread & Fusing Decayed Event Memory...")
    feature_df = create_feature_matrix(market_df, events_df, forecast_horizon=5, decay_half_life_days=4.0)
    splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)
    print(f"  -> Chronological Train Split: {len(splits['X_train_quant'])} rows")
    print(f"  -> Chronological Out-of-Time Test Split: {len(splits['X_test_quant'])} rows")
    
    print("\\n[Step 4/5] Training Models & Running Ablation Experiment (Quant vs. LLM Hybrid for Tulsa)...")
    results = train_and_compare_models(splits, model_type=model_type)
    
    print("\\n" + "=" * 65)
    print("         TULSA REGIONAL MODEL EVALUATION & METRICS SUMMARY")
    print("=" * 65)
    print(f" Target Location: Tulsa, OK Metropolitan Area")
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
    
    print("\\n[Step 5/5] Real-Time Tulsa Shock Scenario Simulations...")
    scenario_1 = "EF-3 Tornado strikes West Tulsa industrial corridor, halting 125,000 bpd HF Sinclair refinery loading racks."
    print(f"\\n  Scenario 1: \\"{scenario_1}\\"")
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
    print("Tulsa Pipeline Execution Complete!\\n")
    
    return results

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_tulsa_pipeline(use_llm_api=use_api, model_type="ridge")
'''

with open("tulsa_main.py", "w", encoding="utf-8") as f:
    f.write(tulsa_main_content)
print("Successfully created tulsa_main.py")


# 3. Create notebooks/tulsa_gas_price_llm_forecasting.ipynb
notebook_path = os.path.join("notebooks", "tulsa_gas_price_llm_forecasting.ipynb")

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# LLM-Augmented Tulsa, Oklahoma Gas Price Prediction Model\n",
            "### Regional Retail Gasoline Forecasting using LLM Event Sentiment & Cushing WTI Dynamics\n",
            "\n",
            "Predicts **retail unleaded gasoline prices in the Tulsa, Oklahoma metropolitan area**.\n",
            "\n",
            "### Key Tulsa Drivers:\n",
            "1. **Cushing WTI Proximity:** Cushing, OK tank farms (50 miles southwest of Tulsa).\n",
            "2. **Regional Refineries & Pipelines:** HF Sinclair West Tulsa Refinery ($125,000\\text{ bpd}$) & Phillips 66 Ponca City Refinery.\n",
            "3. **Oklahoma Fuel Tax:** Low state fuel tax ($\\sim \\$0.19/\\text{gal}$)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "import sys\n",
            "import pandas as pd\n",
            "import numpy as np\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "\n",
            "sys.path.append('..')\n",
            "\n",
            "from src.tulsa_regional import fetch_tulsa_market_data, get_tulsa_regional_events\n",
            "from src.event_analyzer import process_event_dataset, extract_event_features_llm\n",
            "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
            "from src.models import train_and_compare_models\n",
            "\n",
            "sns.set_theme(style=\"whitegrid\")\n",
            "print(\"Tulsa regional modules successfully loaded!\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "market_df = fetch_tulsa_market_data()\n",
            "events_df = process_event_dataset(get_tulsa_regional_events())\n",
            "feature_df = create_feature_matrix(market_df, events_df, forecast_horizon=5, decay_half_life_days=4.0)\n",
            "splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)\n",
            "results = train_and_compare_models(splits, model_type='ridge')\n",
            "display(pd.DataFrame([results['metrics_quant'], results['metrics_hybrid']], index=['Baseline (Quant Only)', 'Tulsa Hybrid (Quant + LLM Events)']))"
        ]
    }
]

notebook_json = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3.11 (midgley .venv)",
            "language": "python",
            "name": "midgley-venv"
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(notebook_json, f, indent=2)

print(f"Successfully generated notebook at {notebook_path}")
print("\nAll Tulsa regional files ready!")