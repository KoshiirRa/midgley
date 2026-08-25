"""
Build Script for Tulsa, OK Regional Forecasting Notebook
(src/locations/tulsa/notebook_builder.py -> notebooks/tulsa_gas_price_llm_forecasting.ipynb)
"""

import json
import os

def build_tulsa_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "tulsa_gas_price_llm_forecasting.ipynb")
        
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Tulsa, Oklahoma Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment & Live Pump Price Calibration ($3.89/gal)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices in the Tulsa, Oklahoma metropolitan area**.\n",
                "\n",
                "### Why Tulsa, OK is Unique:\n",
                "1. **Live Pump Price Calibration:** Calibrated dynamically to local pump prices (**$3.89/gal**).\n",
                "2. **Cushing WTI Proximity:** Cushing, Oklahoma—the physical delivery hub for WTI crude oil—is located just **50 miles southwest of Tulsa**.\n",
                "3. **Regional Refineries & Pipelines:** Local rack prices are driven by the **HF Sinclair West Tulsa Refinery** ($125,000\\text{ bpd capacity}$), **Phillips 66 Ponca City Refinery**, and **Explorer Pipeline** throughput.\n",
                "4. **Oklahoma State Fuel Tax:** Oklahoma maintains a low state motor fuel tax rate ($\\sim \\$0.19/\\text{gal}$)."
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
                "from src.locations.tulsa.regional import fetch_tulsa_market_data, get_tulsa_regional_events\n",
                "from src.event_analyzer import process_event_dataset, extract_event_features_llm\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Tulsa regional modules successfully loaded!\")"
            ]
        },
        
        # Cell 3: Data Ingestion Code
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "market_df = fetch_tulsa_market_data(start_date=\"2022-01-01\", live_current_price=3.89)\n",
                "raw_events_df = get_tulsa_regional_events()\n",
                "\n",
                "print(f\"Market Trading Days: {len(market_df)}\")\n",
                "print(f\"Latest Tulsa Pump Price Calibrated: ${market_df['tulsa_retail_gasoline'].iloc[-1]:.2f}/gal\")\n",
                "display(market_df.head())\n",
                "display(raw_events_df.head())"
            ]
        },
        
        # Cell 4: Visualization
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 5))\n",
                "plt.plot(market_df['date'], market_df['tulsa_retail_gasoline'], label='Tulsa Retail Gas ($/gal)', color='tab:green', linewidth=2.5)\n",
                "plt.plot(market_df['date'], market_df['gasoline_rbob'], label='Wholesale RBOB Futures ($/gal)', color='tab:blue', linestyle='--')\n",
                "plt.plot(market_df['date'], market_df['cushing_crude_per_gal'], label='Cushing WTI Crude ($/gal equiv)', color='tab:orange', linestyle=':')\n",
                "\n",
                "plt.title('Tulsa, OK Retail Gas Prices vs Wholesale RBOB & Cushing WTI Crude', fontsize=14, fontweight='bold')\n",
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

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(notebook_json, f, indent=2)

    print(f"Successfully generated Tulsa notebook at {target_path}")
    return target_path

if __name__ == "__main__":
    build_tulsa_notebook()
