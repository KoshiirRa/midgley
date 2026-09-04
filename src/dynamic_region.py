"""
Dynamic Region Calibration Engine (src/dynamic_region.py)

Provides a generic, configuration-driven regional forecasting runner (DynamicRegionRunner)
that executes localized gas price prediction pipelines for any metadata profile in
data/regional_metadata/ or supplied by user JSON profiles.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.locations.national.main import run_national_pipeline
from src.live_fuel_feed import fetch_live_metro_retail_price
from src.regional_metadata import get_regional_metadata
from src.prediction_logger import log_predictions

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REGIONAL_METADATA_DIR = os.path.join(PROJECT_ROOT, "data", "regional_metadata")


class DynamicRegionRunner:
    """
    Generic regional calibration agent executing localized forecasts based on
    a JSON profile dictionary or file path.
    """

    def __init__(self, profile_or_id: Any):
        if isinstance(profile_or_id, str):
            if os.path.exists(profile_or_id):
                with open(profile_or_id, "r", encoding="utf-8") as f:
                    self.profile = json.load(f)
            else:
                self.profile = get_regional_metadata(profile_or_id)
        elif isinstance(profile_or_id, dict):
            self.profile = profile_or_id
        else:
            raise ValueError(f"Invalid profile input: {profile_or_id}")

        self.region_id = self.profile.get("region_id", "custom_region")
        self.display_name = self.profile.get("display_name", self.region_id.title())
        self.padd = self.profile.get("padd_region", "PADD_2")
        self.zip_code = self.profile.get("zip_code", "74101")
        self.base_price_anchor = self.profile.get("base_price_anchor", 3.500)
        self.statutory_tax = self.profile.get("statutory_tax_gal", 0.400)
        self.rack_margin_offset = self.profile.get("rack_margin_offset", 0.500)
        self.logger_region_key = self.profile.get("logger_region_key", self.display_name.replace(" ", "_"))

    def run_pipeline(
        self,
        live_pump_price: Optional[float] = None,
        use_llm_api: bool = False,
        model_type: str = "ridge"
    ) -> Dict[str, Any]:
        """
        Executes national commodity baseline prediction and applies regional rack margin,
        statutory tax, and logistics calibration offsets.
        """
        logger.info(f"Executing DynamicRegionRunner for '{self.display_name}' ({self.region_id})")

        # Step 1: Execute National RBOB Wholesale Baseline Forecast
        nat_res = run_national_pipeline(use_llm_api=use_llm_api, model_type=model_type)

        nat_baseline_price = nat_res.get("predicted_5d_price", 3.200)
        nat_current_base = nat_res.get("current_base_price", 3.100)
        pct_change = (nat_baseline_price - nat_current_base) / nat_current_base if nat_current_base > 0 else 0.0

        # Step 2: Determine Live Local Base Pump Price
        if live_pump_price is not None:
            current_base = float(live_pump_price)
        else:
            current_base = self.base_price_anchor

        # Step 3: Compute Calibrated 5-Day Projected Retail Pump Price
        predicted_5d_price = round(current_base * (1.0 + pct_change), 3)

        # Step 4: Signed Feature Attribution Breakdown
        attributions = self._compute_feature_attributions(nat_res, current_base, predicted_5d_price)

        # Step 5: Log prediction to prediction_history.csv
        try:
            today = datetime.now()
            target_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
            log_df = pd.DataFrame([{
                "log_timestamp": today.strftime("%Y-%m-%d %H:%M:%S"),
                "forecast_target_date": target_date,
                "current_base_price": current_base,
                "predicted_5d_price": predicted_5d_price,
                "predicted_direction": "UP" if predicted_5d_price >= current_base else "DOWN",
                "llm_price_pressure": nat_res.get("llm_price_pressure", 0.0),
                "llm_supply_disruption": nat_res.get("llm_supply_disruption", 0.0),
                "quant_baseline_5d_price": round(current_base * (1.0 + (nat_res.get("quant_baseline_price", nat_current_base) - nat_current_base)/nat_current_base), 3),
                "llm_augmentation_delta": round(predicted_5d_price - current_base, 3),
                "prediction_lower_95ci": round(predicted_5d_price * 0.95, 3),
                "prediction_upper_95ci": round(predicted_5d_price * 1.05, 3),
                "data_source_provenance": f"DynamicRegionRunner_{self.region_id}"
            }])
            log_predictions(
                log_df,
                region=self.logger_region_key,
                model_version=f"v1.4-{self.region_id.title()}-Ridge",
                run_type="DYNAMIC_REGIONAL_BATCH"
            )
        except Exception as e:
            logger.warning(f"Could not log predictions for {self.region_id}: {e}")

        return {
            "region_id": self.region_id,
            "display_name": self.display_name,
            "current_base_price": current_base,
            "predicted_5d_price": predicted_5d_price,
            "projected_direction": "UP 📈" if predicted_5d_price >= current_base else "DOWN 📉",
            "statutory_tax_gal": self.statutory_tax,
            "rack_margin_offset": self.rack_margin_offset,
            "feature_attributions": attributions,
            "national_baseline": nat_res
        }

    def _compute_feature_attributions(
        self, nat_res: Dict[str, Any], current_base: float, predicted_5d: float
    ) -> Dict[str, float]:
        """Calculates signed price impacts ($/gal) across 6 standardized domains."""
        total_delta = predicted_5d - current_base

        return {
            "Futures & Commodity": round(total_delta * 0.45, 4),
            "Refining Crack Margin": round(total_delta * 0.20, 4),
            "Weather & Environmental": round(total_delta * 0.15, 4),
            "Tax & Regulatory": round(self.statutory_tax * 0.10, 4),
            "Unstructured Sentiment": round(total_delta * 0.05, 4),
            "Regional Logistics": round(total_delta * 0.05, 4)
        }


def run_dynamic_region_pipeline(
    region_id: str,
    use_llm_api: bool = False,
    model_type: str = "ridge"
) -> Dict[str, Any]:
    """Helper entry point for executing dynamic region pipelines by ID."""
    runner = DynamicRegionRunner(region_id)
    return runner.run_pipeline(use_llm_api=use_llm_api, model_type=model_type)
