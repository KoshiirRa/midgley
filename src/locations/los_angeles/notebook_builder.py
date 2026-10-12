"""
Build Script for Los Angeles Basin & Southern California Regional Forecasting Notebook
(src/locations/los_angeles/notebook_builder.py -> notebooks/los_angeles_gas_price_llm_forecasting.ipynb)
"""

import json
import os


def build_los_angeles_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "los_angeles_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Los Angeles Basin & Southern California Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, South Bay Refining Clusters (Carson/Wilmington, El Segundo, Torrance) & CARB CaRFG Spot Basis ($4.89/gal base)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Los Angeles Basin and Southern California** (Los Angeles, Orange, Riverside, San Bernardino, and Ventura Counties).\n",
                "\n",
                "### Why the Los Angeles Basin & PADD 5 SoCal are Unique:\n",
                "1. **Dense South Bay & Harbor Refining Cluster (~1.02M bpd):** Anchored by Marathon Carson/Wilmington (363 kbpd), Chevron El Segundo (269 kbpd), PBF Energy Torrance (166 kbpd), Phillips 66 Wilmington (139 kbpd), and Valero Wilmington (85 kbpd).\n",
                "2. **Isolated CARBOB Spot Pricing Island:** Trades on the EIA Los Angeles Reformulated RBOB (CARBOB) spot benchmark (`EER_EPMRU_PF4_RLA_DPG`), where unplanned FCCU or alkylation outages trigger immediate +$0.35 to +$1.00/gal basis spikes.\n",
                "3. **Strict CARB Phase 3 & South Coast AQMD Mandates:** Enforces a strict 6.99 psi summer RVP cap and embeds $0.953/gal in state excise, Cap-and-Trade, and LCFS environmental compliance fees ($1.407/gal total tax burden with federal excise and LA County sales taxes).\n",
                "4. **Kinder Morgan SFPP Watson Hub & San Pedro Bay Ports:** Origin point at Watson Station (Carson) for Kinder Morgan SFPP West, South, and East pipeline lines supplying Orange County, San Diego, the Inland Empire, Las Vegas, and Phoenix.\n",
                "5. **Seismic & Santa Ana Wildfire Vulnerability:** Monitored continuously against USGS Newport-Inglewood and Palos Verdes fault seismicity, Santa Ana wind Red Flag Warnings, and Southern California Edison (SCE) PSPS grid curtailments."
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
                "from src.locations.los_angeles.regional import fetch_los_angeles_market_data, get_los_angeles_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Los Angeles Basin regional modules successfully loaded!\")"
            ]
        },

        # Cell 3: Fetch Market Data
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "market_df = fetch_los_angeles_market_data(start_date=\"2022-01-01\")\n",
                "print(f\"Loaded {len(market_df)} market rows for Los Angeles Basin.\")\n",
                "market_df[['date', 'gasoline_rbob', 'spot_los_angeles', 'los_angeles_retail_gasoline', 'socal_crack_spread', 'los_angeles_rack_margin']].tail()"
            ]
        },

        # Cell 4: Fetch Regional Events
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "events_raw = get_los_angeles_regional_events()\n",
                "print(f\"Loaded {len(events_raw)} regional events for Los Angeles Basin / PADD 5.\")\n",
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
                "    region=\"Los_Angeles_CA\",\n",
                "    model_type=\"ridge\",\n",
                "    log_wandb=False\n",
                ")\n",
                "print(\"Multi-horizon training complete for Los Angeles Basin!\")"
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
