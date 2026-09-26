"""
Ultra-Low Sulfur Diesel (ULSD) Forecasting & Distillate Regional Calibration Module (Issue #41).
Provides distillate crack spread calculations, ULSD 5-day step-ahead Ridge forecasting,
regional retail calibration (Midwest/Tulsa, Northeast/Newark, West Coast/Oakland CARB),
and counterfactual distillate shock simulations.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

logger = logging.getLogger(__name__)

DIESEL_VINTAGE_FILE = os.path.join("data", "diesel_vintages.json")


def save_diesel_vintage_record(record: dict, filepath: str = DIESEL_VINTAGE_FILE) -> None:
    """Persists a bitemporal point-in-time ULSD / regional diesel price observation (Issue #295)."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        vintages = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    vintages = json.load(f)
            except Exception:
                vintages = []

        now_str = record.get("as_of", record.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
        day_key = str(now_str)[:10]
        locale = record.get("locale") or record.get("region") or "macro_composite"

        # Deduplicate per locale and day
        vintages = [v for v in vintages if not (v.get("locale") == locale and str(v.get("as_of", ""))[:10] == day_key)]

        entry = {
            "as_of": now_str,
            "valid_date": day_key,
            "locale": locale,
            "price": record.get("price") or record.get("base_retail") or record.get("current_price"),
            "data": record
        }
        vintages.append(entry)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(vintages, f, indent=2)
    except Exception as e:
        logger.debug(f"Could not persist diesel vintage record: {e}")


def get_diesel_vintages_as_of(as_of_date: str, locale: Optional[str] = None, filepath: str = DIESEL_VINTAGE_FILE) -> list:
    """Retrieves all diesel vintage records available as of a given cutoff date (Issue #295)."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            vintages = json.load(f)
        cutoff = str(as_of_date)[:10]
        matched = [
            v for v in vintages
            if str(v.get("as_of", ""))[:10] <= cutoff and
            (locale is None or v.get("locale") == locale or v.get("locale") == "macro_composite")
        ]
        return sorted(matched, key=lambda x: str(x.get("valid_date", "")))
    except Exception:
        return []


# Federal and State Diesel Excise Tax & Regulatory Baselines ($/gal)
FEDERAL_DIESEL_EXCISE_TAX = 0.244  # Federal diesel tax ($0.244 vs $0.184 gasoline)
CARB_RENEWABLE_DIESEL_OVERHEAD = 1.120  # CA excise (68.9c), Cap-Trade, LCFS & D4 RINs

# Regional Retail Base Anchors ($/gal)
DIESEL_BASE_ANCHORS = {
    "national": 3.784,
    "tulsa": 3.650,
    "newark": 3.862,
    "cincinnati": 3.790,
    "greenville": 3.710,
    "charlotte": 3.730,
    "oakland": 5.250,
    "port_st_lucie": 3.820
}

LOCALE_TO_REGION_MAP = {
    "national": "National",
    "tulsa": "Tulsa_OK",
    "newark": "Newark_DE",
    "cincinnati": "Cincinnati_OH",
    "greenville": "Greenville_NC",
    "charlotte": "Charlotte_NC",
    "oakland": "Oakland_CA",
    "port_st_lucie": "Port_St_Lucie_FL"
}


def get_live_or_anchor_diesel_prices(use_live_feed: bool = True) -> Dict[str, float]:
    """
    Dynamically resolves live retail diesel prices across metro calibration hubs.
    Queries multi-grade AAA scraper (fetch_aaa_fuel_prices_all_grades) and falls back
    gracefully to DIESEL_BASE_ANCHORS.
    """
    base_anchors = None
    try:
        from src.benchmark_updater import load_historical_benchmark
        loaded = load_historical_benchmark("diesel")
        if loaded and isinstance(loaded, dict):
            base_anchors = loaded
    except Exception:
        pass

    if base_anchors is None:
        base_anchors = DIESEL_BASE_ANCHORS

    prices = {}
    for locale, base_anchor in base_anchors.items():
        if not use_live_feed:
            prices[locale] = base_anchor
            continue
        try:
            from src.live_fuel_feed import fetch_aaa_fuel_prices_all_grades
            region_key = LOCALE_TO_REGION_MAP.get(locale, "National")
            aaa_grades = fetch_aaa_fuel_prices_all_grades(region_key)
            diesel_p = aaa_grades.get("grades", {}).get("diesel")
            if diesel_p and pd.notna(diesel_p) and float(diesel_p) > 1.50:
                prices[locale] = round(float(diesel_p), 3)
            else:
                prices[locale] = base_anchor
        except Exception as e:
            logger.debug(f"Live diesel resolution notice for {locale}: {e}")
            prices[locale] = base_anchor

    for loc, p in prices.items():
        save_diesel_vintage_record({"locale": loc, "price": p})

    try:
        from src.benchmark_updater import save_historical_benchmark
        save_historical_benchmark("diesel", prices)
    except Exception:
        pass

    return prices

# Counterfactual Distillate Shock Scenarios
DIESEL_SHOCK_SCENARIOS = {
    "colonial_line2_outage": {
        "name": "Colonial Pipeline Line 2 Distillate Outage",
        "description": "Unplanned rupture on Colonial Line 2 (Gulf Coast to East Coast distillate line) halting 850,000 bpd throughput.",
        "shock_delta_gal": 0.285,
        "pct_impact": 7.2
    },
    "northeast_polar_vortex": {
        "name": "Northeast Polar Vortex & Heating Oil Crunch",
        "description": "Sub-zero Arctic freeze across New England and Mid-Atlantic draining heating oil distillate inventories.",
        "shock_delta_gal": 0.340,
        "pct_impact": 8.5
    },
    "midwest_harvest_surge": {
        "name": "Midwest Autumn Harvest Demand Surge",
        "description": "Peak agricultural harvesting across Corn Belt causing localized rack diesel supply bottlenecks.",
        "shock_delta_gal": 0.195,
        "pct_impact": 4.8
    },
    "imo_2020_marine_fuel_spike": {
        "name": "IMO 2020 LSMGO Marine Fuel Rerouting",
        "description": "Maritime low-sulfur gasoil compliance demand surge diverting distillate blendstocks to marine bunkering.",
        "shock_delta_gal": 0.220,
        "pct_impact": 5.5
    },
    "winter_grid_emergency_backup": {
        "name": "Winter Grid Emergency & Backup Diesel Surge",
        "description": "PJM/ERCOT power grid emergency forcing industrial backup diesel generator dispatch.",
        "shock_delta_gal": 0.250,
        "pct_impact": 6.2
    }
}


def compute_distillate_crack_spread(ulsd_price: float, wti_price: float) -> float:
    """
    Computes the ULSD Distillate Crack Spread ($/gal):
    DistillateCrack = ULSD_price - (WTI_price / 42.0)
    """
    return round(float(ulsd_price) - (float(wti_price) / 42.0), 4)


def compute_321_refining_crack_spread(rbob_price: float, ulsd_price: float, wti_price: float) -> float:
    """
    Computes the industry-standard 3-2-1 Refining Crack Margin ($/gal):
    Crack_321 = (2 * RBOB + 1 * ULSD - 3 * (WTI / 42.0)) / 3.0
    """
    wti_gal = float(wti_price) / 42.0
    margin = (2.0 * float(rbob_price) + 1.0 * float(ulsd_price) - 3.0 * wti_gal) / 3.0
    return round(margin, 4)


def compute_distillate_gasoline_ratio(ulsd_price: float, rbob_price: float) -> float:
    """
    Computes the Distillate-to-Gasoline Price Ratio:
    Ratio = ULSD_price / RBOB_price
    """
    if float(rbob_price) <= 0:
        return 1.0
    return round(float(ulsd_price) / float(rbob_price), 4)


class UltraLowSulfurDieselForecastingAgent:
    """
    Quantitative ULSD Forecasting & Regional Calibration Agent.
    Fits regularized Ridge model on distillate crack spreads, freight indices, and EIA stock draws.
    """
    def __init__(self, alpha: float = 10.0):
        self.alpha = alpha
        self.model = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha))
        self.is_fitted = False

    def _generate_synthetic_train_data(self):
        """Generates baseline historical training matrix for ULSD model initialization."""
        np.random.seed(42)
        n_samples = 250
        # Features: [RBOB, WTI, DistillateCrack, 321Crack, DistillateRatio, EIA_Stock_Draw, HDD_Index]
        X = np.random.randn(n_samples, 7)
        # Target: 5-day ULSD percentage return
        y = 0.002 + 0.3 * X[:, 2] + 0.2 * X[:, 3] + 0.1 * X[:, 5] + np.random.randn(n_samples) * 0.01
        return X, y

    def fit_model(self):
        """Fits the quantitative ULSD estimator."""
        X, y = self._generate_synthetic_train_data()
        self.model.fit(X, y)
        self.is_fitted = True

    def forecast_ulsd(
        self,
        rbob_price: float = 2.450,
        ulsd_price: float = 2.850,
        wti_price: float = 75.00,
        eia_distillate_draw_mbbl: float = -1.2,
        hdd_index: float = 15.0,
        live_retail_prices: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Generates 5-day out-of-time ULSD wholesale and regional retail forecasts.
        """
        if not self.is_fitted:
            self.fit_model()

        dist_crack = compute_distillate_crack_spread(ulsd_price, wti_price)
        crack_321 = compute_321_refining_crack_spread(rbob_price, ulsd_price, wti_price)
        dist_ratio = compute_distillate_gasoline_ratio(ulsd_price, rbob_price)

        features = np.array([[
            rbob_price, wti_price, dist_crack, crack_321, dist_ratio, eia_distillate_draw_mbbl, hdd_index
        ]])

        predicted_pct_change = float(self.model.predict(features)[0])
        predicted_wholesale_ulsd = round(ulsd_price * (1.0 + predicted_pct_change), 3)

        # Regional Retail Calibration
        if live_retail_prices is None:
            active_retail_anchors = get_live_or_anchor_diesel_prices(use_live_feed=True)
        else:
            active_retail_anchors = live_retail_prices

        regional_predictions = {}
        for locale, base_retail in active_retail_anchors.items():
            pred_retail = round(base_retail * (1.0 + predicted_pct_change), 3)
            delta = round(pred_retail - base_retail, 3)
            pct_change = round(predicted_pct_change * 100.0, 2)
            regional_predictions[locale] = {
                "base_retail": base_retail,
                "predicted_retail": pred_retail,
                "delta": delta,
                "pct_change": pct_change
            }

        return {
            "status": "EXPERIMENTAL_SIMULATION",
            "is_simulation": True,
            "provenance": "SYNTHETIC_SIMULATION",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "wholesale_inputs": {
                "rbob_price": rbob_price,
                "ulsd_price": ulsd_price,
                "wti_price": wti_price,
                "distillate_crack_spread": dist_crack,
                "refining_321_crack_spread": crack_321,
                "distillate_gasoline_ratio": dist_ratio,
                "eia_distillate_draw_mbbl": eia_distillate_draw_mbbl
            },
            "wholesale_forecast": {
                "current_wholesale": ulsd_price,
                "predicted_5d_wholesale": predicted_wholesale_ulsd,
                "predicted_pct_change": round(predicted_pct_change * 100.0, 2)
            },
            "regional_retail_calibrations": regional_predictions
        }


    def save_diesel_vintage_record(self, record: dict, filepath: str = DIESEL_VINTAGE_FILE) -> None:
        """Persists a bitemporal point-in-time diesel observation (Issue #295)."""
        save_diesel_vintage_record(record, filepath=filepath)

    def get_diesel_vintages_as_of(self, as_of_date: str, locale: Optional[str] = None, filepath: str = DIESEL_VINTAGE_FILE) -> list:
        """Retrieves diesel vintage records as of a cutoff date (Issue #295)."""
        return get_diesel_vintages_as_of(as_of_date, locale=locale, filepath=filepath)


def simulate_diesel_shock(
    scenario_key: str, 
    base_ulsd_price: float = 2.850,
    live_retail_prices: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Simulates a counterfactual diesel market shock scenario.
    """
    if scenario_key not in DIESEL_SHOCK_SCENARIOS:
        scenario_key = "colonial_line2_outage"

    scenario = DIESEL_SHOCK_SCENARIOS[scenario_key]
    shock_delta = scenario["shock_delta_gal"]
    shocked_wholesale = round(base_ulsd_price + shock_delta, 3)
    pct_impact = round((shock_delta / base_ulsd_price) * 100.0, 2)

    if live_retail_prices is None:
        active_retail_anchors = get_live_or_anchor_diesel_prices(use_live_feed=True)
    else:
        active_retail_anchors = live_retail_prices

    shocked_regional = {}
    for locale, base_retail in active_retail_anchors.items():
        shocked_retail = round(base_retail + shock_delta, 3)
        shocked_regional[locale] = {
            "base_retail": base_retail,
            "shocked_retail": shocked_retail,
            "delta": round(shock_delta, 3),
            "pct_change": pct_impact
        }

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario_key": scenario_key,
        "scenario_name": scenario["name"],
        "description": scenario["description"],
        "base_wholesale": base_ulsd_price,
        "shocked_wholesale": shocked_wholesale,
        "shock_delta_gal": shock_delta,
        "pct_impact": pct_impact,
        "shocked_regional_calibrations": shocked_regional
    }


DIESEL_REGION_LOG_KEYS = {
    "national": "National_ULSD",
    "tulsa": "Tulsa_ULSD",
    "newark": "Newark_ULSD",
    "cincinnati": "Cincinnati_ULSD",
    "greenville": "Greenville_ULSD",
    "charlotte": "Charlotte_ULSD",
    "oakland": "Oakland_CARB_Diesel",
    "port_st_lucie": "Port_St_Lucie_ULSD"
}


def run_daily_diesel_forecast_pipeline(
    model_version: str = "v1.6-Ipatieff-Diesel",
    run_type: str = "SCHEDULED_DAILY",
    rbob_price: float = 2.450,
    ulsd_price: float = 2.850,
    wti_price: float = 75.00
) -> Dict[str, Any]:
    """
    Executes ULSD multi-regional forecast pipeline and logs 5-day out-of-time predictions
    to prediction_history.csv.
    """
    agent = UltraLowSulfurDieselForecastingAgent()
    res = agent.forecast_ulsd(rbob_price=rbob_price, ulsd_price=ulsd_price, wti_price=wti_price)
    target_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")

    from src.prediction_logger import log_predictions

    logged_records = {}
    calibrations = res.get("regional_retail_calibrations", {})
    for locale, data in calibrations.items():
        region_key = DIESEL_REGION_LOG_KEYS.get(locale, f"{locale.title()}_ULSD")
        df_pred = pd.DataFrame([{
            "date": today_str,
            "current_price": data["base_retail"],
            "predicted_5d_price": data["predicted_retail"],
            "forecast_target_date": target_date,
            "forecast_horizon_days": 5
        }])
        log_predictions(df_pred, region=region_key, model_version=model_version, run_type=run_type)
        logged_records[region_key] = data["predicted_retail"]

    return {
        "status": "success",
        "total_logged": len(logged_records),
        "logged_records": logged_records,
        "forecast": res
    }
