"""
Build Script for Boston Metro & New England Regional Forecasting Notebook
(src/locations/boston/notebook_builder.py -> notebooks/boston_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_boston_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "boston_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Boston Metro & New England Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Waterborne Tanker Logistics, Irving Oil Supply Monitoring & Massachusetts Tax Structure ($3.45/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Boston Metropolitan Area and New England (PADD 1A)** (Suffolk, Middlesex, Norfolk, Essex, Worcester, Southern NH, Providence RI, and Southern Maine).\n",
                "\n",
                "### Why Boston & New England are Unique:\n",
                "1. **Zero Operational Refining Capacity (100% Import Dependent):** New England possesses no operable petroleum refineries and relies entirely on ocean-going product tankers, coastal barges from New York Harbor, and pipeline terminuses in southern New England.\n",
                "2. **The Irving Oil Canadian Supply Link:** Anchored by the 320 kbpd Irving Oil Refinery in Saint John, New Brunswick, Canada, which exports substantial clean gasoline volumes directly into Boston Harbor and Portland, ME.\n",
                "3. **Severe Winter Distillate Competition:** Harsh winters drive intense competition between residential heating oil, dual-fuel power generation, and transportation fuels, causing sharp logistical bottlenecks at marine terminals.\n",
                "4. **Multi-State Tax Arbitrage:** Massachusetts imposes a statutory excise tax of **$0.240/gal** ($0.424/gal total baseline with federal excise), generating active cross-border fuel arbitrage against New Hampshire ($0.222/gal), Connecticut ($0.250/gal), and Rhode Island ($0.370/gal).\n",
                "5. **EPA Reformulated Gasoline (RFG):** Subject to strict federal RFG standards requiring 7.4 psi low-RVP summer gasoline blends."
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
                "from src.locations.boston.regional import fetch_boston_market_data, get_boston_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Boston regional modules successfully loaded!\")"
            ]
        },

        # Cell 3: Fetch Market Data
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Boston Metro & New England market data\n",
                "market_df = fetch_boston_market_data(start_date=\"2022-01-01\", live_pump_price=3.450)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_ny_harbor', 'boston_retail_gasoline', 'boston_rack_margin']].tail()"
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
                "plt.plot(market_df['date'], market_df['boston_retail_gasoline'], label='Boston Retail ($/gal)', color='#2563eb', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_ny_harbor'], label='NY Harbor Wholesale Spot ($/gal)', color='#dc2626', lw=1.5, ls='--')\n",
                "plt.title('Boston Retail Gasoline vs. NY Harbor Wholesale Spot Benchmark (PADD 1A)')\n",
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
                "# Extract Boston & New England regional event shocks\n",
                "events_df = get_boston_regional_events()\n",
                "print(f\"Total regional events: {len(events_df)}\")\n",
                "events_df.tail(5)"
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
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(notebook_dict, f, indent=2)

    return target_path
