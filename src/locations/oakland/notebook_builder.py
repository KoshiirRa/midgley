"""
Build Script for Oakland, CA & SF Bay Area Regional Forecasting Notebook
(src/locations/oakland/notebook_builder.py -> notebooks/oakland_gas_price_llm_forecasting.ipynb)
"""

import json
import os

def build_oakland_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "oakland_gas_price_llm_forecasting.ipynb")
        
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Oakland, CA & SF Bay Area Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, CARB Regulatory Costs ($0.953/gal), PADD 5 Refining Isolation, USGS Seismic Risks & PG&E PSPS Wildfire Alerts\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across Oakland, CA and the broader 9-County San Francisco Bay Area** (Alameda, Contra Costa, San Francisco, Santa Clara, San Mateo, Marin, Solano, Napa, Sonoma).\n",
                "\n",
                "### Why Oakland, CA & the SF Bay Area are Unique:\n",
                "1. **Unprecedented Tax & Environmental Regulatory Burden:** California state excise tax (63.4¢/gal), Cap-and-Trade carbon fees (~25.0¢/gal), Low Carbon Fuel Standard (LCFS) credit costs (~18.5¢/gal), state/local sales taxes & UST fee (~15.0¢/gal), and federal tax (18.4¢/gal) create a **$0.953/gal embedded regulatory burden** at Bay Area pumps ($4.950/gal Oakland base, $5.050/gal SF Bay Area average).\n",
                "2. **PADD 5 'Refining Island' Geographic Isolation:** Zero interstate refined product pipelines cross the Rockies or Sierra Nevada into California. Shortfalls cannot be backfilled from Gulf Coast or Midwest pipelines; deficits must be imported via ocean oil tankers from Asia/Middle East (3+ week transit) or Alaska North Slope (ANS) crude routes.\n",
                "3. **SF Bay Area Refining Hub & Pipelines:** Chevron Richmond (245k bpd), PBF Martinez (156k bpd), and Valero Benicia (145k bpd) supply Northern California and Nevada via the **Kinder Morgan SFPP (Santa Fe Pacific Pipeline)** system.\n",
                "4. **USGS Seismic & CAL FIRE / PG&E PSPS Wildfire Hazards:** The Hayward & San Andreas faults cross pipeline corridors, while Red Flag Diablo winds trigger PG&E Public Safety Power Shutoffs (PSPS), causing 2–3 week refinery hydrocracker blackout trips."
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
                "from src.locations.oakland.regional import fetch_oakland_market_data, get_oakland_regional_events, TOTAL_CARB_TAX_BURDEN\n",
                "from src.event_analyzer import process_event_dataset, extract_event_features_llm\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Oakland & SF Bay Area regional modules successfully loaded!\")"
            ]
        },
        
        # Cell 3: Data Ingestion Code
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "market_df = fetch_oakland_market_data(start_date=\"2022-01-01\", live_oakland_price=4.950, live_bayarea_price=5.050)\n",
                "raw_events_df = get_oakland_regional_events()\n",
                "\n",
                "print(f\"Market Trading Days: {len(market_df)}\")\n",
                "print(f\"Latest Oakland Retail Price:      ${market_df['oakland_retail_gasoline'].iloc[-1]:.3f}/gal\")\n",
                "print(f\"Latest SF Bay Area Regional Avg: ${market_df['bayarea_avg_retail_gasoline'].iloc[-1]:.3f}/gal\")\n",
                "print(f\"CARB Total Tax & Regulatory Fee: ${TOTAL_CARB_TAX_BURDEN:.3f}/gal\")\n",
                "display(market_df.head())\n",
                "display(raw_events_df.head())"
            ]
        },
        
        # Cell 4: 9-County Regional Visualization
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 5))\n",
                "plt.plot(market_df['date'], market_df['san_francisco_retail_gasoline'], label='San Francisco ($5.12 base)', color='tab:purple', linewidth=2)\n",
                "plt.plot(market_df['date'], market_df['bayarea_avg_retail_gasoline'], label='SF Bay Area 9-County Avg ($5.05 base)', color='tab:red', linewidth=2.5)\n",
                "plt.plot(market_df['date'], market_df['oakland_retail_gasoline'], label='Oakland / East Bay ($4.95 base)', color='tab:orange', linewidth=2.5)\n",
                "plt.plot(market_df['date'], market_df['north_bay_retail_gasoline'], label='North Bay / Solano ($4.85 base)', color='tab:green', linewidth=2)\n",
                "plt.plot(market_df['date'], market_df['gasoline_rbob'], label='Wholesale RBOB Futures ($/gal)', color='tab:gray', linestyle='--')\n",
                "\n",
                "plt.title('SF Bay Area Regional Retail Gas Prices across 9-County Metro Corridor', fontsize=14, fontweight='bold')\n",
                "plt.xlabel('Date')\n",
                "plt.ylabel('$/Gallon')\n",
                "plt.legend(fontsize=11)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        
        # Cell 5: Model Training
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "events_df = process_event_dataset(raw_events_df, use_llm_api=False)\n",
                "features_df = create_feature_matrix(market_df, events_df, forecast_horizon=5)\n",
                "splits = prepare_chronological_splits(features_df, train_ratio=0.8, forecast_horizon=5)\n",
                "results = train_and_compare_models(splits, model_type='ridge')\n",
                "\n",
                "print(\"Oakland Hybrid Model Evaluation Complete!\")"
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

    print(f"Successfully generated notebook at {target_path}")
    return target_path

if __name__ == "__main__":
    build_oakland_notebook()
