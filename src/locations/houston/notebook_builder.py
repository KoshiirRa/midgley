"""
Build Script for Houston & USGC Refining Complex Regional Forecasting Notebook
(src/locations/houston/notebook_builder.py -> notebooks/houston_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_houston_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "houston_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Houston & USGC Refining Complex Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, Mega-Refinery Clusters (Baytown, Port Arthur, Galveston Bay) & Razor-Thin USGC Margins ($2.85/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Houston Metropolitan Area and Upper Texas Gulf Coast** (Harris, Galveston, Brazoria, Chambers, Fort Bend, Montgomery, Liberty, and Jefferson Counties).\n",
                "\n",
                "### Why Houston & PADD 3 are Unique:\n",
                "1. **The Epicenter of North American Refining (>52% of U.S. Capacity):** Home to the world's dense mega-refinery clusters along the Houston Ship Channel, Galveston Bay, Baytown (ExxonMobil, 560 kbpd), Beaumont (ExxonMobil, 630 kbpd), and Port Arthur (Motiva, 630 kbpd).\n",
                "2. **Arterial Pipeline Origins:** Origin point for the nation's critical refined product pipelines: **Colonial Pipeline (Lines 1 & 2)** delivering clean products to the East Coast, and the **Explorer Pipeline** supplying the Midwest.\n",
                "3. **Razor-Thin Rack Margins:** Direct gate proximity to world-scale refining assets compresses retail rack margins to ~$0.65–$0.75/gal above wholesale spot.\n",
                "4. **Low Statutory Motor Fuel Taxes:** Texas state excise tax is fixed at **$0.200/gal** with zero local sales tax add-on, creating one of the lowest statutory fuel tax burdens in the nation ($0.384/gal total with federal excise).\n",
                "5. **High Tropical & Hurricane Vulnerability:** Severe exposure to Gulf of Mexico tropical cyclones, hurricane storm surge shut-ins along the Houston Ship Channel, and rare deep Arctic freeze-offs (Winter Storm Uri)."
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
                "from src.locations.houston.regional import fetch_houston_market_data, get_houston_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Houston regional modules successfully loaded!\")"
            ]
        },

        # Cell 3: Fetch Market Data
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "market_df = fetch_houston_market_data(start_date=\"2022-01-01\")\n",
                "print(f\"Loaded {len(market_df)} market rows for Houston & USGC.\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_gulf_coast', 'houston_retail_gasoline', 'usgc_crack_spread', 'houston_rack_margin']].tail()"
            ]
        },

        # Cell 4: Fetch Regional Events
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "events_raw = get_houston_regional_events()\n",
                "print(f\"Loaded {len(events_raw)} regional events for Houston/PADD 3.\")\n",
                "events_raw.tail(10)"
            ]
        },

        # Cell 5: Process Events with LLM / Finlight
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "events_df = process_event_dataset(events_raw, use_llm_api=False)\n",
                "print(f\"Processed {len(events_df)} scored events.\")\n",
                "events_df[['date', 'headline', 'price_pressure', 'supply_disruption_p']].head()"
            ]
        },

        # Cell 6: Multi-Horizon Feature Engineering & Model Training
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.models import train_multi_horizon_models\n",
                "results = train_multi_horizon_models(\n",
                "    market_df=market_df,\n",
                "    events_df=events_df,\n",
                "    horizons=[1, 2, 3, 4, 5],\n",
                "    region=\"Houston_TX\",\n",
                "    model_type=\"ridge\",\n",
                "    log_wandb=False\n",
                ")\n",
                "print(\"Multi-horizon training complete for Houston & USGC!\")"
            ]
        }
    ]

    notebook_content = {
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
        json.dump(notebook_content, f, indent=2)

    return target_path
