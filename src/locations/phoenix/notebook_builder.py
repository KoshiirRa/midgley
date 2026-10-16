"""
Build Script for Phoenix & Desert Southwest Regional Forecasting Notebook
(src/locations/phoenix/notebook_builder.py -> notebooks/phoenix_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_phoenix_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "phoenix_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Phoenix Metro & Desert Southwest Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Dual-Corridor Pipeline Ingress & Low-Tax Southwest Dynamics ($3.25/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Phoenix Metropolitan Area and Desert Southwest District (PADD 5C)** (Maricopa, Pinal, and Pima Counties).\n",
                "\n",
                "### Why Phoenix & PADD 5C are Unique:\n",
                "1. **Zero Refining Operations:** Arizona and Nevada have zero operable petroleum refineries, functioning entirely as product import sinks.\n",
                "2. **Dual-Corridor Pipeline Arbitrage:** Phoenix is served by the Kinder Morgan SFPP West Line (from Los Angeles) and East Line (from El Paso, TX / Gulf Coast). When California spikes, flows swing to Texas barrels.\n",
                "3. **Statutory Tax Differential:** Arizona state motor fuel excise is only **$0.180/gal** (among the lowest in the U.S.), over 41 cents below California.\n",
                "4. **Maricopa County Arizona CBG:** Local ozone and CO rules require seasonal Cleaner Burning Gasoline (CBG) distinct from California CARBOB."
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
                "from src.locations.phoenix.regional import fetch_phoenix_market_data, get_phoenix_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Phoenix regional modules successfully loaded!\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Phoenix & Desert Southwest market data\n",
                "market_df = fetch_phoenix_market_data(start_date=\"2022-01-01\", live_pump_price=3.250)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_phoenix_pipe', 'phoenix_retail_gasoline', 'phoenix_rack_margin']].tail()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 6))\n",
                "plt.plot(market_df['date'], market_df['phoenix_retail_gasoline'], label='Phoenix Retail ($/gal)', color='#f97316', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_phoenix_pipe'], label='Phoenix Pipeline Wholesale ($/gal)', color='#2563eb', lw=1.5, ls='--')\n",
                "plt.title('Phoenix Metro Retail Gasoline vs. Pipeline Wholesale Benchmark (PADD 5C)')\n",
                "plt.xlabel('Date')\n",
                "plt.ylabel('Price ($/gal)')\n",
                "plt.legend()\n",
                "plt.show()"
            ]
        }
    ]

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.11"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)

    return target_path
