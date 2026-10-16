"""
Build Script for Cincinnati, OH / Northern KY Regional Forecasting Notebook
(src/locations/cincinnati/notebook_builder.py -> notebooks/cincinnati_gas_price_llm_forecasting.ipynb)
"""

import json
import os

def build_cincinnati_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "cincinnati_gas_price_llm_forecasting.ipynb")
        
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Cincinnati, OH / Northern KY Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Mississippi Downriver Logistics & Dual-State Gas Tax Differential (OH: $3.45/gal, KY: $3.325/gal)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Cincinnati, OH / Northern Kentucky metropolitan area** (Hamilton County OH & Boone/Kenton/Campbell Counties KY).\n",
                "\n",
                "### Why Cincinnati, OH & Northern KY are Unique:\n",
                "1. **Dual-State Gas Tax & Price Differential:** Ohio state motor fuel tax ($0.385/gal) vs Kentucky state motor fuel tax ($0.260/gal) creates a persistent **~$0.125/gal retail price gap** ($3.450/gal OH base vs $3.325/gal KY base).\n",
                "2. **Marathon Catlettsburg Refinery Proximity:** The 291,000 bpd Catlettsburg KY refinery serves as the primary regional refining benchmark for the Ohio Valley.\n",
                "3. **Mississippi & Lower Ohio River Downriver Barge Logistics:** Refined fuel barges moving north from Gulf Coast refining hubs enter the Ohio River at the **Cairo, IL confluence** (Mile 981 on Lower Mississippi / Mile 0 on Ohio River). Autumn low-water drought crises (e.g., Memphis/Cairo gage drops) enforce -40% barge payload draft limits, surging spot freight rates +300% and expanding Cincinnati rack margins (+14.5¢/gal).\n",
                "4. **Ohio River Lock Logistics (Markland Locks & Dam):** Winter ice jams and lock maintenance near Cincinnati choke barge throughput and force reliance on higher-cost rail transport.\n",
                "5. **Cross-River Consumer Arbitrage:** Commuters frequently cross the Ohio River bridges to fuel up in Northern Kentucky to save ~$0.125/gal."
            ]
        },
        
        # Cell 2: Imports
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
                "from src.locations.cincinnati.regional import fetch_cincinnati_market_data, get_cincinnati_regional_events\n",
                "from src.event_analyzer import process_event_dataset, extract_event_features_llm\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Cincinnati regional modules successfully loaded!\")"
            ]
        },
        
        # Cell 3: Data Ingestion Code
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "market_df = fetch_cincinnati_market_data(start_date=\"2022-01-01\", live_oh_price=3.450, live_ky_price=3.325)\n",
                "raw_events_df = get_cincinnati_regional_events()\n",
                "\n",
                "print(f\"Market Trading Days: {len(market_df)}\")\n",
                "print(f\"Latest Ohio Pump Price (OH):     ${market_df['cincinnati_oh_retail_gasoline'].iloc[-1]:.3f}/gal\")\n",
                "print(f\"Latest Kentucky Pump Price (KY): ${market_df['cincinnati_ky_retail_gasoline'].iloc[-1]:.3f}/gal\")\n",
                "print(f\"Cross-River Tax & Price Gap:    ${market_df['oh_ky_tax_spread'].iloc[-1]:.3f}/gal\")\n",
                "display(market_df.head())\n",
                "display(raw_events_df.head())"
            ]
        },
        
        # Cell 4: Dual-State Visualization
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 5))\n",
                "plt.plot(market_df['date'], market_df['cincinnati_oh_retail_gasoline'], label='Cincinnati, OH Retail ($3.45 base / 38.5¢ tax)', color='tab:red', linewidth=2.5)\n",
                "plt.plot(market_df['date'], market_df['cincinnati_ky_retail_gasoline'], label='Northern Kentucky Retail ($3.325 base / 26.0¢ tax)', color='tab:blue', linewidth=2.5)\n",
                "plt.plot(market_df['date'], market_df['gasoline_rbob'], label='Wholesale RBOB Futures ($/gal)', color='tab:green', linestyle='--')\n",
                "\n",
                "plt.title('Cincinnati Metro Cross-River Gas Prices: Ohio vs Northern Kentucky Retail', fontsize=14, fontweight='bold')\n",
                "plt.xlabel('Date')\n",
                "plt.ylabel('$/Gallon')\n",
                "plt.legend(fontsize=11)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        
        # Cell 5: Model Training
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "scored_events_df = process_event_dataset(raw_events_df, use_llm_api=False)\n",
                "feature_df = create_feature_matrix(market_df, scored_events_df, forecast_horizon=5, decay_half_life_days=4.0)\n",
                "splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)\n",
                "results = train_and_compare_models(splits, model_type='ridge')\n",
                "display(pd.DataFrame([results['metrics_quant'], results['metrics_hybrid']], index=['Baseline (Quant Only)', 'Cincinnati Hybrid (Quant + LLM Events)']))"
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

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(notebook_json, f, indent=2)

    print(f"Successfully generated Cincinnati notebook at {target_path}")
    return target_path

if __name__ == "__main__":
    build_cincinnati_notebook()
