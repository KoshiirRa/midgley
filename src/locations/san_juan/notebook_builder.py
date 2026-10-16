"""
Build Script for San Juan & Caribbean Territories Regional Forecasting Notebook
(src/locations/san_juan/notebook_builder.py -> notebooks/san_juan_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_san_juan_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "san_juan_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented San Juan & Caribbean Territories Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, DACO Price Regulation & Jones Act Marine Freight Logistics ($3.49/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across San Juan Metro and U.S. Caribbean Territories (PADD 6)**.\n",
                "\n",
                "### Why San Juan & PADD 6 are Unique:\n",
                "1. **100% Maritime Island Supply Logistics:** Decoupled from mainland North American pipelines; refined gasoline is delivered via coastal product tankers from the US Gulf Coast under Jones Act build requirements.\n",
                "2. **DACO Price Regulation & Metric Pricing:** Retail fuel prices are surveyed and published daily in cents per liter (¢/L) by the Puerto Rico Department of Consumer Affairs (DACO), which enforces statutory margin caps during declared emergencies.\n",
                "3. **Tropical Cyclones & Electrical Grid Fragility:** High vulnerability to Atlantic hurricanes (NHC bulletins) and LUMA Energy grid instability, driving sudden surges in backup generator diesel and pump fuel demand.\n",
                "4. **Commonwealth Tax Framework:** Puerto Rico Commonwealth petroleum product arbitrio ($0.160/gal) combined with Federal excise ($0.184/gal) for a statutory tax baseline of $0.344/gal."
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
                "from src.locations.san_juan.regional import (\n",
                "    fetch_san_juan_market_data,\n",
                "    get_san_juan_regional_events,\n",
                "    scrape_daco_retail_prices,\n",
                "    convert_cents_per_liter_to_dollars_per_gal\n",
                ")\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"San Juan regional modules successfully loaded!\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest San Juan & PADD 6 market data\n",
                "market_df = fetch_san_juan_market_data(start_date=\"2022-01-01\", live_pump_price=3.490)\n",
                "print(f\"Market Data Shape: {market_df.shape}\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_caribbean_waterborne', 'san_juan_retail_gasoline', 'daco_retail_cents_per_liter', 'san_juan_rack_margin']].tail()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 6))\n",
                "plt.plot(market_df['date'], market_df['san_juan_retail_gasoline'], label='San Juan Retail ($/gal)', color='#f59e0b', lw=2)\n",
                "plt.plot(market_df['date'], market_df['spot_caribbean_waterborne'], label='Caribbean Waterborne Landed Benchmark ($/gal)', color='#0284c7', lw=1.5, ls='--')\n",
                "plt.title('San Juan Retail Gasoline vs. Caribbean Landed Wholesale Benchmark (PADD 6)')\n",
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
