"""
Build Script for Greater Chicago Metro, IL & Northwest Indiana Regional Forecasting Notebook
(src/locations/chicago/notebook_builder.py -> notebooks/chicago_gas_price_llm_forecasting.ipynb)
"""

import json
import os

def build_chicago_notebook(target_path: str = None) -> str:
    if target_path is None:
        target_path = os.path.join("notebooks", "chicago_gas_price_llm_forecasting.ipynb")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    cells = [
        # Cell 1: Title & Introduction
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# LLM-Augmented Greater Chicago Metro, IL & Northwest Indiana Gas Price Prediction Model\n",
                "### Regional Retail Gasoline Forecasting using LLM Event Sentiment, BP Whiting / CITGO Lemont Logistics & Multi-Tier Fuel Taxes (IL: $3.85/gal, IN: $3.45/gal)\n",
                "\n",
                "This notebook focuses specifically on predicting **retail unleaded gasoline prices across the Greater Chicago metropolitan area** (Cook, DuPage, Will, and Lake Counties IL & Lake/Porter Counties IN).\n",
                "\n",
                "### Why Greater Chicago & Northwest Indiana are Unique:\n",
                "1. **Multi-Tier Fuel Tax & Cross-Border Arbitrage:** Illinois state motor fuel tax ($0.470/gal) + Cook County ($0.060/gal) + City of Chicago ($0.080/gal) + state/local sales tax create a statutory burden exceeding **$1.00/gal** in Chicago compared to ~$0.55/gal in Northwest Indiana, driving a persistent **~$0.40/gal retail price spread** ($3.850/gal IL base vs $3.450/gal IN base).\n",
                "2. **BP Whiting Refinery Anchor:** The 435,000 bpd BP Whiting IN refinery (6th largest in the U.S.) serves as the dominant regional refining benchmark for PADD 2, with single-point outages triggering massive prompt rack spikes.\n",
                "3. **Midwest Pipeline & Waterway Confluence:** Cleaner products flow across the Explorer, Wolverine, West Shore, and Badger pipelines, while marine barges navigate the Des Plaines River and Illinois Waterway (Lockport Lock & Dam).\n",
                "4. **EPA 7.4 psi RFG Summer Compliance:** Strict ozone non-attainment Reformulated Gasoline regulations impose a seasonal compliance premium between June 1 and September 15.\n",
                "5. **Edgeworth Price Cycle Dynamics:** Synchronized, aggressive retail cycles led by Speedway, Thorntons, BP, and Circle K create high-frequency margin undercutting and sharp price restorations."
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
                "from src.locations.chicago.regional import fetch_chicago_market_data, get_chicago_regional_events\n",
                "from src.event_analyzer import process_event_dataset\n",
                "from src.feature_engineering import create_feature_matrix, prepare_chronological_splits\n",
                "from src.models import train_and_compare_models\n",
                "\n",
                "sns.set_theme(style=\"whitegrid\")\n",
                "print(\"Chicago regional modules successfully loaded!\")"
            ]
        },

        # Cell 3: Data Ingestion Code
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "market_df = fetch_chicago_market_data(start_date=\"2022-01-01\", live_il_price=3.850, live_in_price=3.450)\n",
                "raw_events_df = get_chicago_regional_events()\n",
                "\n",
                "print(f\"Market Trading Days: {len(market_df)}\")\n",
                "print(f\"Latest Illinois Pump Price (IL):      ${market_df['chicago_il_retail_gasoline'].iloc[-1]:.3f}/gal\")\n",
                "print(f\"Latest Northwest Indiana Price (IN):  ${market_df['chicago_in_retail_gasoline'].iloc[-1]:.3f}/gal\")\n",
                "print(f\"Cross-Border Tax & Retail Gap:        ${market_df['il_in_tax_spread'].iloc[-1]:.3f}/gal\")\n",
                "display(market_df.head())\n",
                "display(raw_events_df.head())"
            ]
        },

        # Cell 4: Dual-State Visualization
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(12, 5))\n",
                "plt.plot(market_df['date'], market_df['chicago_il_retail_gasoline'], label='Chicago, IL Retail ($3.85 base / multi-tax)', color='tab:red', linewidth=2.5)\n",
                "plt.plot(market_df['date'], market_df['chicago_in_retail_gasoline'], label='Northwest Indiana Retail ($3.45 base)', color='tab:blue', linewidth=2.5)\n",
                "plt.plot(market_df['date'], market_df['gasoline_rbob'], label='Wholesale RBOB Futures ($/gal)', color='tab:green', linestyle='--')\n",
                "\n",
                "plt.title('Greater Chicago Metro Gas Prices: Illinois vs Northwest Indiana Retail', fontsize=14, fontweight='bold')\n",
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
                "scored_events_df = process_event_dataset(raw_events_df, use_llm_api=False)\n",
                "feature_df = create_feature_matrix(market_df, scored_events_df, forecast_horizon=5, decay_half_life_days=4.0)\n",
                "splits = prepare_chronological_splits(feature_df, train_ratio=0.8, forecast_horizon=5)\n",
                "results = train_and_compare_models(splits, model_type='ridge')\n",
                "display(pd.DataFrame([results['metrics_quant'], results['metrics_hybrid']], index=['Baseline (Quant Only)', 'Chicago Hybrid (Quant + LLM Events)']))"
            ]
        }
    ]

    notebook_json = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3.11 (midgley .venv)",
                "language": "python",
                "name": "midgley-venv"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(notebook_json, f, indent=2)

    print(f"Successfully generated Chicago notebook at {target_path}")
    return target_path

if __name__ == "__main__":
    build_chicago_notebook()
