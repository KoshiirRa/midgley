"""
Build Script for Seattle & Puget Sound Regional Forecasting Notebook
(src/locations/seattle/notebook_builder.py -> notebooks/seattle_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_seattle_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "seattle_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Seattle-Tacoma & Puget Sound Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Puget Sound Refining & Olympic Pipeline Logistics ($4.15/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Seattle-Tacoma Metropolitan Area and Puget Sound District (PADD 5B)** (King, Pierce, Snohomish, Kitsap, Skagit, Whatcom, and Thurston Counties).\n",
                "\n",
                "### Why Seattle & PADD 5B are Unique:\n",
                "1. **Autonomous Refining Island:** Four regional refineries (bp Cherry Point, Phillips 66 Ferndale, Marathon Anacortes, HF Sinclair Puget Sound; 616 kbpd) operate independently of California CARBOB formulations.\n",
                "2. **Olympic Pipeline Corridor:** Refined products move south from Puget Sound through Seattle, Tacoma, and terminate in Portland, OR.\n",
                "3. **Trans Mountain & ANS Feedstocks:** Refineries process Canadian crude delivered via the Trans Mountain Pipeline and Alaska North Slope crude via ocean tanker.\n",
                "4. **Climate Commitment Act (CCA):** Washington state statutory excise ($0.494/gal) plus cap-and-invest carbon allowance compliance costs establish an autonomous regulatory environment distinct from California CARB."
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
                "from src.locations.seattle.regional import fetch_seattle_market_data, get_seattle_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Seattle regional modules successfully loaded!\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Seattle & Puget Sound market data\n",
                "market_df = fetch_seattle_market_data(start_date=\"2022-01-01\", live_pump_price=4.150)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_pnw_rack', 'seattle_retail_gasoline', 'seattle_rack_margin']].tail()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 6))\n",
                "plt.plot(market_df['date'], market_df['seattle_retail_gasoline'], label='Seattle Retail ($/gal)', color='#059669', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_pnw_rack'], label='Puget Sound Wholesale Rack ($/gal)', color='#2563eb', lw=1.5, ls='--')\n",
                "plt.title('Seattle Metro Retail Gasoline vs. Puget Sound Wholesale Benchmark (PADD 5B)')\n",
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
