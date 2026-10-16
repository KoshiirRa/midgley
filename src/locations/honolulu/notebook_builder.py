"""
Build Script for Honolulu & Hawaii Regional Forecasting Notebook
(src/locations/honolulu/notebook_builder.py -> notebooks/honolulu_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_honolulu_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "honolulu_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Honolulu & Hawaii Island Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Kapolei Refining & Ocean Barge Logistics ($4.65/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Honolulu Urban Area and Hawaiian Island Archipelago (PADD 5D)** (Honolulu, Maui, Hawaii, and Kauai Counties).\n",
                "\n",
                "### Why Honolulu & Hawaii PADD 5D are Unique:\n",
                "1. **Isolated Island Refining Complex:** The **Par Hawaii Kapolei Refinery (94 kbpd)** on Oahu processes waterborne crude imports and supplies the entire state.\n",
                "2. **Inter-Island Ocean Barge Logistics:** Fuel is barged from Oahu across open Pacific channels to neighbor islands via specialized ocean tugs and barges (Young Brothers).\n",
                "3. **Composite Island Tax Burden:** State excise ($0.160/gal), county fuel taxes ($0.165/gal Honolulu, up to $0.23/gal Maui), and General Excise Tax (GET ~4.5%) total ~$0.33 to $0.51/gal.\n",
                "4. **Tropical Marine Stability:** Ambient temperatures remain consistently warm year-round (~75-85°F) with virtually flat seasonal RVP volatility."
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
                "from src.locations.honolulu.regional import fetch_honolulu_market_data, get_honolulu_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Honolulu regional modules successfully loaded!\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Honolulu & Hawaii market data\n",
                "market_df = fetch_honolulu_market_data(start_date=\"2022-01-01\", live_pump_price=4.650)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_oahu_rack', 'honolulu_retail_gasoline', 'honolulu_rack_margin']].tail()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 6))\n",
                "plt.plot(market_df['date'], market_df['honolulu_retail_gasoline'], label='Honolulu Retail ($/gal)', color='#0d9488', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_oahu_rack'], label='Kapolei Wholesale Rack ($/gal)', color='#2563eb', lw=1.5, ls='--')\n",
                "plt.title('Honolulu Metro Retail Gasoline vs. Kapolei Wholesale Benchmark (PADD 5D)')\n",
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
