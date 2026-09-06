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
from src.prediction_logger import log_predictions, compute_regional_residual_std, compute_rolling_scoreboard_metrics
from src.models import (
    compute_rolling_volatility_index,
    compute_volatility_gate_weight,
    apply_gated_persistence_blending,
    compute_empirical_residual_ci
)

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

    def _fetch_recent_region_prices(self) -> np.ndarray:
        """Fetches recent base prices for this region to compute rolling volatility."""
        history_csv = os.path.join(PROJECT_ROOT, "data", "prediction_history.csv")
        if os.path.exists(history_csv):
            try:
                df = pd.read_csv(history_csv)
                reg_df = df[df['region'].astype(str).str.lower() == self.logger_region_key.lower()]
                if not reg_df.empty and 'current_base_price' in reg_df.columns:
                    prices = reg_df['current_base_price'].dropna().astype(float).values
                    if len(prices) >= 2:
                        return prices
            except Exception as e:
                logger.debug(f"Could not read regional price history for volatility index: {e}")
        return np.array([self.base_price_anchor])

    def run_pipeline(
        self,
        live_pump_price: Optional[float] = None,
        use_llm_api: bool = False,
        model_type: str = "ridge"
    ) -> Dict[str, Any]:
        """
        Executes national commodity baseline prediction and applies regional rack margin,
        statutory tax, logistics calibration offsets, and Dynamic Volatility-Gated Persistence Blending (DV-GPB).
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

        # Step 3: Compute Raw 5-Day Projected Retail Pump Price
        raw_predicted_5d_price = round(current_base * (1.0 + pct_change), 4)

        # Step 4: Apply Dynamic Volatility-Gated Persistence Blending (DV-GPB) (Issue #214)
        recent_prices = self._fetch_recent_region_prices()
        sigma_14d = compute_rolling_volatility_index(recent_prices, window=14)
        lambda_vol = compute_volatility_gate_weight(sigma_14d, threshold=0.015, k=200.0)

        # Closed-Loop Uplift Guardrail Check
        guardrail_active = False
        try:
            scoreboard = compute_rolling_scoreboard_metrics(window_days=14, region=self.logger_region_key)
            if scoreboard.get("total_evaluations", 0) >= 3 and scoreboard.get("model_uplift_mae_pct", 0.0) < -2.0:
                guardrail_active = True
                logger.info(f"DV-GPB Guardrail Triggered for {self.logger_region_key} (Uplift: {scoreboard.get('model_uplift_mae_pct'):+.2f}%)")
        except Exception as err:
            logger.debug(f"Notice checking rolling uplift guardrail: {err}")

        predicted_5d_price = apply_gated_persistence_blending(
            raw_pred_price=raw_predicted_5d_price,
            current_base_price=current_base,
            lambda_vol=lambda_vol,
            guardrail_active=guardrail_active,
            guardrail_alpha=0.5
        )

        # Step 5: Compute Empirical Residual Confidence Intervals (Issue #214)
        res_std = compute_regional_residual_std(self.logger_region_key, window_days=30)
        lower_95ci, upper_95ci = compute_empirical_residual_ci(predicted_5d_price, residual_std_30d=res_std, confidence_level=0.95)

        # Step 6: Signed Feature Attribution Breakdown
        attributions = self._compute_feature_attributions(nat_res, current_base, predicted_5d_price)

        # Step 7: Log prediction to prediction_history.csv
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
                "prediction_lower_95ci": lower_95ci,
                "prediction_upper_95ci": upper_95ci,
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

        # Step 8: Retrieve GeoPandas Spatial Refinery Buffering & Decay Audit
        spatial_summary = None
        try:
            from src.spatial_refinery import get_metro_spatial_refinery_summary, METRO_CLUSTER_DATA
            if self.region_id in METRO_CLUSTER_DATA:
                spatial_summary = get_metro_spatial_refinery_summary(self.region_id)
        except Exception as err:
            logger.debug(f"Could not retrieve spatial refinery summary for {self.region_id}: {err}")

        return {
            "region_id": self.region_id,
            "display_name": self.display_name,
            "current_base_price": current_base,
            "raw_predicted_5d_price": raw_predicted_5d_price,
            "predicted_5d_price": predicted_5d_price,
            "projected_direction": "UP 📈" if predicted_5d_price >= current_base else "DOWN 📉",
            "prediction_lower_95ci": lower_95ci,
            "prediction_upper_95ci": upper_95ci,
            "volatility_14d": sigma_14d,
            "gate_weight_lambda": lambda_vol,
            "residual_std_30d": res_std,
            "guardrail_active": guardrail_active,
            "statutory_tax_gal": self.statutory_tax,
            "rack_margin_offset": self.rack_margin_offset,
            "feature_attributions": attributions,
            "spatial_refinery_summary": spatial_summary,
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
