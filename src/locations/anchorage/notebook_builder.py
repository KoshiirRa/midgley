"""
Build Script for Anchorage & Southcentral Alaska Regional Forecasting Notebook
(src/locations/anchorage/notebook_builder.py -> notebooks/anchorage_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_anchorage_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "anchorage_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Anchorage & Southcentral Alaska Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Kenai Refining Island & Sub-Arctic Logistics ($3.85/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Anchorage Municipality and Southcentral Alaska District (PADD 5D)** (Anchorage, Matanuska-Susitna, and Kenai Peninsula Boroughs).\n",
                "\n",
                "### Why Anchorage & Alaska PADD 5D are Unique:\n",
                "1. **Isolated Cook Inlet Refining Island:** The **Marathon Kenai Refinery (68 kbpd)** supplies over 85% of refined motor fuel consumed across the Alaska Railbelt and Southcentral region.\n",
                "2. **Arctic Logistics & Ice Seasonality:** Marine tankers must navigate Cook Inlet dynamic sea ice, while the Alaska Railroad and summer river barges supply Fairbanks and remote Bush villages.\n",
                "3. **Lowest Tax Burden in U.S.:** Alaska enforces a state motor fuel excise tax of only **$0.0895/gal**, the lowest in the nation.\n",
                "4. **Extreme Winter RVP Dynamics:** Winter sub-zero temperatures require 15.0+ psi RVP high-volatility fuel formulations to prevent engine freeze-offs."
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
                "from src.locations.anchorage.regional import fetch_anchorage_market_data, get_anchorage_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Anchorage regional modules successfully loaded!\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Anchorage & Southcentral Alaska market data\n",
                "market_df = fetch_anchorage_market_data(start_date=\"2022-01-01\", live_pump_price=3.850)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_ans_rack', 'anchorage_retail_gasoline', 'anchorage_rack_margin']].tail()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 6))\n",
                "plt.plot(market_df['date'], market_df['anchorage_retail_gasoline'], label='Anchorage Retail ($/gal)', color='#0284c7', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_ans_rack'], label='Cook Inlet / ANS Wholesale Rack ($/gal)', color='#2563eb', lw=1.5, ls='--')\n",
                "plt.title('Anchorage Metro Retail Gasoline vs. Kenai Wholesale Benchmark (PADD 5D)')\n",
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
