"""
Build Script for Guam & Pacific Island Territories Regional Forecasting Notebook
(src/locations/guam/notebook_builder.py -> notebooks/guam_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_guam_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "guam_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Guam & Pacific Island Territories Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, MOPS Benchmark & Trans-Pacific Tanker Logistics ($4.89/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across Hagåtña / Apra Harbor, Guam and U.S. Pacific Island Territories (PADD 7)**.\n",
                "\n",
                "### Why Guam & PADD 7 are Unique:\n",
                "1. **Isolated Trans-Pacific Supply Chains:** Decoupled from the North American domestic pipeline grid; 100% of finished motor gasoline is imported via Medium Range (MR) product tankers from Asian refining hubs (Singapore, South Korea, Japan).\n",
                "2. **Benchmark Decoupling (MOPS vs NYMEX RBOB):** Acquisition costs track the Mean of Platts Singapore (MOPS) 92 RON Mogas benchmark rather than Gulf Coast RBOB, plus trans-Pacific tanker freight charters.\n",
                "3. **Territorial Tax & Oligopoly Retail Structure:** Retail distribution is managed by Mobil Oil Guam, Shell Guam (IP&E), and South Pacific Petroleum Corp (76), with a territorial tax burden of $0.190/gal ($0.150 Liquid Fuel Tax + $0.040 Mass Transit surcharge).\n",
                "4. **Western Pacific Typhoon Alley:** Exposure to Joint Typhoon Warning Center (JTWC) and WFO Guam tropical alerts, sparking panic buying and Apra Harbor port closures."
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
                "from src.locations.guam.regional import fetch_guam_market_data, get_guam_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Guam regional modules successfully loaded!\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Guam & PADD 7 market data\n",
                "market_df = fetch_guam_market_data(start_date=\"2022-01-01\", live_pump_price=4.890)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_mops_92_rack', 'guam_retail_gasoline', 'guam_rack_margin']].tail()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 6))\n",
                "plt.plot(market_df['date'], market_df['guam_retail_gasoline'], label='Guam Retail ($/gal)', color='#0284c7', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_mops_92_rack'], label='MOPS 92 Landed Benchmark ($/gal)', color='#f59e0b', lw=1.5, ls='--')\n",
                "plt.title('Guam Retail Gasoline vs. MOPS 92 Landed Wholesale Benchmark (PADD 7)')\n",
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
