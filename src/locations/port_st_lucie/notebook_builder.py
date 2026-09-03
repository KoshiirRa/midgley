"""
Build Script for Port St. Lucie, FL Regional Forecasting Notebook
(src/locations/port_st_lucie/notebook_builder.py -> notebooks/port_st_lucie_gas_price_llm_forecasting.ipynb)
"""

import json
import os

def build_port_st_lucie_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "port_st_lucie_gas_price_llm_forecasting.ipynb")
        
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Port St. Lucie, Florida Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment & Live Pump Price Calibration ($3.38/gal)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices in the Port St. Lucie, Florida metropolitan area** (St. Lucie County, PADD 1C South Atlantic).\n",
                "\n",
                "### Why Port St. Lucie, FL is Unique:\n",
                "1. **Live Pump Price Calibration:** Calibrated dynamically to local pump prices (**$3.38/gal**).\n",
                "2. **Waterborne Marine Supply Chain:** Florida has zero crude oil refineries and zero interstate pipelines entering South Florida. Port St. Lucie is >95% dependent on waterborne tank vessels offloading at Port Everglades (Fort Lauderdale) and Port Canaveral.\n",
                "3. **Florida Motor Fuel Tax Structure:** Florida state excise tax + St. Lucie local option fuel tax ($\\$0.384/\\text{gal}$).\n",
                "4. **NOAA Weather & Atlantic Hurricane Risk:** Severe storm alerts, marine storm surges in the Straits of Florida, and coastal hurricane landfalls (St. Lucie County FLZ147 / Zip 34952)."
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
                "from src.locations.port_st_lucie.regional import fetch_port_st_lucie_market_data, get_port_st_lucie_regional_events\n",
                "from src.event_analyzer import process_event_dataset, extract_event_features_llm\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Port St. Lucie regional modules successfully loaded!\")"
            ]
        },
        
        # Cell 3: Data Ingestion Code
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Ingest Port St. Lucie regional market time series\n",
                "market_df = fetch_port_st_lucie_market_data(start_date=\"2022-01-01\", live_current_price=3.380)\n",
                "print(f\"Market records: {len(market_df)}\")\n",
                "market_df.tail()"
            ]
        },
        
        # Cell 4: Event Data Ingestion & Scoring
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Load raw events and score with LLM/Lexicon engine\n",
                "events_raw = get_port_st_lucie_regional_events()\n",
                "events_df = process_event_dataset(events_raw, use_llm_api=False)\n",
                "events_df.head()"
            ]
        },
        
        # Cell 5: Feature Engineering
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Fuse features & split chronologically\n",
                "features_df = create_feature_matrix(market_df, events_df, forecast_horizon=5)\n",
                "splits = prepare_chronological_splits(features_df, train_ratio=0.8, forecast_horizon=5)\n",
                "print(f\"Train size: {len(splits['X_train_hybrid'])}, Test size: {len(splits['X_test_hybrid'])}\")"
            ]
        },

        # Cell 6: Model Training & Comparison
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Train regularized models and compare metrics\n",
                "results = train_and_compare_models(splits, model_type=\"ridge\")\n",
                "print(\"Hybrid Model MAE:\", results['metrics_hybrid']['MAE'])\n",
                "print(\"Quantitative Baseline MAE:\", results['metrics_quant']['MAE'])"
            ]
        }
    ]

    notebook_content = {
        "cells": cells,
        "metadata": {
            "language_info": {"name": "python"},
            "orig_nbformat": 4
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2)

    return target_path

if __name__ == "__main__":
    path = build_port_st_lucie_notebook()
    print(f"Generated Port St. Lucie notebook at: {path}")
