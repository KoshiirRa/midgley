"""
Build Script for Denver & Rocky Mountain Regional Forecasting Notebook
(src/locations/denver/notebook_builder.py -> notebooks/denver_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_denver_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "denver_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Denver Metro & Rocky Mountain Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Suncor Commerce City Outage Monitoring & High-Altitude PADD 4 Dynamics ($3.15/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Denver Metropolitan Area and Rocky Mountain District (PADD 4)** (Denver, Adams, Arapahoe, Jefferson, Douglas, Boulder, Broomfield, and Weld Counties).\n",
                "\n",
                "### Why Denver & PADD 4 are Unique:\n",
                "1. **Isolated High-Altitude Refining Island:** PADD 4 is physically isolated by the Rocky Mountains with virtually zero refined product pipeline ingress from the Gulf Coast or Midwest.\n",
                "2. **Single-Refinery Metro Dependence:** The **Suncor Commerce City Refinery (103 kbpd)** produces ~35-40% of Colorado refined products. Unplanned outages (such as the winter 2022/2023 freeze shutdown) dramatically decouple regional retail prices from NYMEX RBOB.\n",
                "3. **Crude Differentials & DJ Basin Sweet:** Regional refineries run Denver Julesburg (DJ) Basin light sweet crude and Wyoming sour blends.\n",
                "4. **Statutory Tax Burden:** Colorado state motor fuel excise tax is fixed at **$0.280/gal** (+ federal $0.184/gal = $0.464/gal statutory baseline).\n",
                "5. **EPA Ozone Nonattainment & High-Altitude Volatility:** Front Range 9-county severe ozone nonattainment mandates summer reformulated gasoline (RFG) blending standards."
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
                "from src.locations.denver.regional import fetch_denver_market_data, get_denver_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Denver regional modules successfully loaded!\")"
            ]
        },

        # Cell 3: Fetch Market Data
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Denver & Rocky Mountain market data\n",
                "market_df = fetch_denver_market_data(start_date=\"2022-01-01\", live_pump_price=3.150)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_denver_rack', 'denver_retail_gasoline', 'denver_rack_margin']].tail()"
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
                "plt.plot(market_df['date'], market_df['denver_retail_gasoline'], label='Denver Retail ($/gal)', color='#d97706', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_denver_rack'], label='Denver Wholesale Rack ($/gal)', color='#2563eb', lw=1.5, ls='--')\n",
                "plt.title('Denver Metro Retail Gasoline vs. Wholesale Rack Benchmark (PADD 4)')\n",
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
                "events_df = get_denver_regional_events()\n",
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
                "    region='Denver_CO',\n",
                "    model_type='ridge'\n",
                ")\n",
                "print(\"Denver Multi-Horizon Forecasting Complete!\")"
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
