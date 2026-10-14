"""
Build Script for New York Harbor & New York State Regional Forecasting Notebook
(src/locations/new_york/notebook_builder.py -> notebooks/new_york_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_new_york_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "new_york_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented New York Harbor & New York State Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, New York Harbor Barge Logistics, Buckeye Pipeline Monitoring & NY State Tax Structure ($3.48/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the New York Metropolitan Area and New York State (PADD 1B)** (NYC Five Boroughs, Long Island, Hudson Valley, Capital District, and Upstate New York).\n",
                "\n",
                "### Why New York & NY Harbor are Unique:\n",
                "1. **Wholesale Pricing Epicenter:** New York Harbor is the physical delivery point and pricing anchor for the NYMEX RBOB gasoline futures contract.\n",
                "2. **Midstream Pipeline & Waterborne Logistics:** Supply flows via the Buckeye Pipeline system (from Linden, NJ terminals to NYC airports, Albany, and Rochester), Colonial Pipeline Line 1 terminus, and Hudson River / Long Island Sound barge lightering.\n",
                "3. **Refining Complex:** Anchored by Phillips 66 Bayway Refinery (258 kbpd in Linden, NJ), with coastal product waterborne receipts from Europe and Gulf Coast PADD 3.\n",
                "4. **High Statutory Tax Burden:** New York State fuel taxes (excise + Petroleum Business Tax + state sales tax) total **$0.472/gal** baseline (exceeding **$0.55/gal** with local county sales taxes), in sharp contrast to neighboring Delaware ($0.230/gal).\n",
                "5. **Bifurcated Environmental Standards:** Strict EPA Reformulated Gasoline (RFG) summer standards for NYC and Long Island vs 9.0 psi conventional rules for Upstate New York."
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
                "from src.locations.new_york.regional import fetch_new_york_market_data, get_new_york_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"New York regional modules successfully loaded!\")"
            ]
        },

        # Cell 3: Fetch Market Data
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest New York Harbor & NY State market data\n",
                "market_df = fetch_new_york_market_data(start_date=\"2022-01-01\", live_pump_price=3.480)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_ny_harbor', 'new_york_retail_gasoline', 'new_york_rack_margin']].tail()"
            ]
        },

        # Cell 4: Plot Historical Dynamics
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 6))\n",
                "plt.plot(market_df['date'], market_df['new_york_retail_gasoline'], label='New York Retail ($/gal)', color='#0284c7', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_ny_harbor'], label='NY Harbor Wholesale Spot ($/gal)', color='#e11d48', lw=1.5, ls='--')\n",
                "plt.title('New York Retail Gasoline vs. NY Harbor Wholesale Spot Benchmark (PADD 1B)')\n",
                "plt.xlabel('Date')\n",
                "plt.ylabel('Price ($/gal)')\n",
                "plt.legend()\n",
                "plt.show()"
            ]
        },

        # Cell 5: Regional Events & LLM Sentiment
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "events_df = get_new_york_regional_events()\n",
                "print(f\"Total Regional & Macro Events: {len(events_df)}\")\n",
                "processed_events = process_event_dataset(events_df, use_llm_api=False)\n",
                "processed_events.tail(10)"
            ]
        },

        # Cell 6: Train Multi-Horizon Models
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.models import train_multi_horizon_models\n",
                "\n",
                "results = train_multi_horizon_models(\n",
                "    market_df=market_df,\n",
                "    events_df=processed_events,\n",
                "    horizons=[1, 2, 3, 4, 5],\n",
                "    region='New_York_NY',\n",
                "    model_type='ridge'\n",
                ")\n",
                "print(\"New York Multi-Horizon Forecasting Complete!\")"
            ]
        }
    ]

    notebook_dict = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(notebook_dict, f, indent=1)

    return target_path
