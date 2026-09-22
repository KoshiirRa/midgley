"""
EPA Reid Vapor Pressure (RVP) Regulatory Standards & Seasonal Blend Engine (src/rvp_regulations.py)
Models Title 40 CFR Part 1090 statutory volatility limits, CARB Phase 3 CaRFG regulations,
and jurisdiction-specific seasonal blend transition countdowns across regional metro hubs (Issue #366).
"""

import os
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

RVP_RULES_FILE = os.path.join("data", "regulatory_rvp_rules.json")

# Default statutory RVP baselines (Title 40 CFR Part 1090 & CARB)
DEFAULT_RVP_RULES = {
    "rules_version": "2026.1",
    "citation": "EPA Title 40 CFR Part 1090 & CARB Phase 3 CaRFG",
    "default_schedule": {
        "spring_ramp_start": "03-01",
        "refinery_terminal_deadline": "05-01",
        "retail_compliance_start": "06-01",
        "retail_compliance_end": "09-15",
        "winter_transition_start": "09-16"
    },
    "regions": {
        "National": {
            "name": "National Conventional Baseline",
            "program": "Conventional Gasoline (CG)",
            "summer_rvp_psi": 9.0,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.08,
            "is_rfg": False,
            "is_carb": False
        },
        "Tulsa_OK": {
            "name": "Tulsa Metro & Mid-Continent",
            "program": "EPA Non-Attainment / 7.8 psi Region",
            "summer_rvp_psi": 7.8,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.14,
            "is_rfg": False,
            "is_carb": False
        },
        "Cincinnati_OH": {
            "name": "Cincinnati Tri-State (OH/KY/IN)",
            "program": "EPA Non-Attainment / Low-RVP Control Area",
            "summer_rvp_psi": 7.8,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.15,
            "is_rfg": False,
            "is_carb": False
        },
        "Dallas_TX": {
            "name": "Dallas-Fort Worth Metroplex",
            "program": "EPA Non-Attainment Control Area",
            "summer_rvp_psi": 7.8,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.13,
            "is_rfg": False,
            "is_carb": False
        },
        "Houston_TX": {
            "name": "Houston-Galveston-Brazoria",
            "program": "EPA Non-Attainment / RFG Adjacent Area",
            "summer_rvp_psi": 7.8,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.14,
            "is_rfg": False,
            "is_carb": False
        },
        "Newark_NJ": {
            "name": "Newark & NY Harbor (PADD 1B)",
            "program": "EPA Reformulated Gasoline (RFG)",
            "summer_rvp_psi": 7.4,
            "winter_rvp_psi": 12.0,
            "summer_compliance_premium_per_gal": 0.18,
            "is_rfg": True,
            "is_carb": False
        },
        "Oakland_CA": {
            "name": "Oakland & SF Bay Area (PADD 5)",
            "program": "CARB Phase 3 CaRFG",
            "summer_rvp_psi": 6.99,
            "winter_rvp_psi": 9.0,
            "summer_compliance_premium_per_gal": 0.28,
            "is_rfg": False,
            "is_carb": True
        },
        "BayArea_CA": {
            "name": "San Francisco Bay Area Regional Hub",
            "program": "CARB Phase 3 CaRFG",
            "summer_rvp_psi": 6.99,
            "winter_rvp_psi": 9.0,
            "summer_compliance_premium_per_gal": 0.28,
            "is_rfg": False,
            "is_carb": True
        },
        "Greenville_NC": {
            "name": "Greenville / Eastern NC (PADD 1C)",
            "program": "Conventional Low-RVP Area",
            "summer_rvp_psi": 7.8,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.12,
            "is_rfg": False,
            "is_carb": False
        },
        "Charlotte_NC": {
            "name": "Charlotte Metro (PADD 1C)",
            "program": "Conventional Low-RVP Area",
            "summer_rvp_psi": 7.8,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.12,
            "is_rfg": False,
            "is_carb": False
        },
        "Port_St_Lucie_FL": {
            "name": "Port St. Lucie & South Florida",
            "program": "Conventional Gasoline (PADD 1C Waterborne)",
            "summer_rvp_psi": 9.0,
            "winter_rvp_psi": 13.5,
            "summer_compliance_premium_per_gal": 0.10,
            "is_rfg": False,
            "is_carb": False
        }
    },
    "emergency_waivers": []
}


class RVPRegulatoryEngine:
    """
    Zero-Cost EPA / CARB Reid Vapor Pressure (RVP) Regulatory Engine (Issue #366).
    Calculates jurisdiction-specific volatility limits, summer/winter transition countdowns,
    refinery compliance deadlines, and seasonal cost premiums.
    """
    def __init__(self, rules_path: str = RVP_RULES_FILE):
        self.rules_path = rules_path
        self.is_free_alternative = True
        self.cost_per_query = 0.0
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "regions" in data:
                        return data
            except Exception as e:
                logger.warning(f"Could not load RVP rules from {self.rules_path}: {e}")
        return DEFAULT_RVP_RULES

    def get_regional_rvp_spec(self, region: str = "National", as_of_date: Optional[str] = None) -> dict:
        """
        Calculates active RVP specifications and transition countdowns for a given region and date.
        """
        if as_of_date is None:
            dt = datetime.now().date()
        elif isinstance(as_of_date, str):
            dt = datetime.strptime(as_of_date[:10], "%Y-%m-%d").date()
        elif isinstance(as_of_date, datetime):
            dt = as_of_date.date()
        elif isinstance(as_of_date, date):
            dt = as_of_date
        else:
            dt = datetime.now().date()

        year = dt.year

        reg_key = region
        regions = self.rules.get("regions", DEFAULT_RVP_RULES["regions"])
        if reg_key not in regions:
            alias_map = {
                "Tulsa": "Tulsa_OK",
                "Cincinnati": "Cincinnati_OH",
                "Dallas": "Dallas_TX",
                "Houston": "Houston_TX",
                "Newark": "Newark_NJ",
                "Oakland": "Oakland_CA",
                "Greenville": "Greenville_NC",
                "Charlotte": "Charlotte_NC",
                "Port_St_Lucie": "Port_St_Lucie_FL",
                "PADD1B": "Newark_NJ",
                "PADD5": "Oakland_CA",
                "PADD2": "Tulsa_OK",
                "PADD3": "Houston_TX",
                "PADD1C": "Charlotte_NC"
            }
            reg_key = alias_map.get(region, "National")
            if reg_key not in regions:
                reg_key = "National"

        reg_conf = regions.get(reg_key, regions["National"])
        summer_psi = float(reg_conf.get("summer_rvp_psi", 9.0))
        winter_psi = float(reg_conf.get("winter_rvp_psi", 13.5))
        max_premium = float(reg_conf.get("summer_compliance_premium_per_gal", 0.10))

        retail_start = date(year, 6, 1)
        retail_end = date(year, 9, 15)
        terminal_deadline = date(year, 5, 1)
        spring_ramp_start = date(year, 3, 1)

        is_summer_active = False
        is_terminal_transition = False
        is_spring_ramp = False
        spring_ramp_factor = 0.0

        if retail_start <= dt <= retail_end:
            is_summer_active = True
            current_max_psi = summer_psi
            compliance_premium = max_premium
            summer_days_remaining = 0
            terminal_days_remaining = 0
            spring_ramp_factor = 1.0
        elif terminal_deadline <= dt < retail_start:
            is_terminal_transition = True
            current_max_psi = summer_psi
            days_into_terminal = (dt - terminal_deadline).days
            terminal_factor = min(1.0, (days_into_terminal + 1) / 31.0)
            compliance_premium = round(max_premium * (0.70 + 0.30 * terminal_factor), 3)
            summer_days_remaining = (retail_start - dt).days
            terminal_days_remaining = 0
            spring_ramp_factor = 1.0
        elif spring_ramp_start <= dt < terminal_deadline:
            is_spring_ramp = True
            current_max_psi = winter_psi
            total_ramp_days = (terminal_deadline - spring_ramp_start).days
            days_into_ramp = (dt - spring_ramp_start).days
            spring_ramp_factor = round(min(1.0, max(0.0, days_into_ramp / float(total_ramp_days))), 3)
            compliance_premium = round(max_premium * 0.70 * spring_ramp_factor, 3)
            summer_days_remaining = (retail_start - dt).days
            terminal_days_remaining = (terminal_deadline - dt).days
        else:
            current_max_psi = winter_psi
            compliance_premium = 0.0
            spring_ramp_factor = 0.0
            target_year = year if dt < spring_ramp_start else year + 1
            next_retail_start = date(target_year, 6, 1)
            next_terminal_deadline = date(target_year, 5, 1)
            summer_days_remaining = (next_retail_start - dt).days
            terminal_days_remaining = (next_terminal_deadline - dt).days

        waiver_active = False
        waiver_reason = None
        waivers = self.rules.get("emergency_waivers", [])
        dt_str = dt.strftime("%Y-%m-%d")
        for w in waivers:
            w_reg = w.get("region")
            if w_reg in ["all", "National", reg_key, region]:
                s_dt = w.get("start_date", "1970-01-01")
                e_dt = w.get("end_date", "2099-12-31")
                if s_dt <= dt_str <= e_dt:
                    waiver_active = True
                    waiver_reason = w.get("reason", "Emergency Fuel Waiver")
                    temp_psi = float(w.get("temporary_psi", current_max_psi))
                    current_max_psi = max(current_max_psi, temp_psi)
                    compliance_premium = max(0.0, compliance_premium - 0.08)

        return {
            "region": reg_key,
            "program": reg_conf.get("program", "Conventional"),
            "as_of_date": dt_str,
            "rvp_max_allowable_psi": round(current_max_psi, 2),
            "rvp_summer_limit_psi": summer_psi,
            "rvp_winter_limit_psi": winter_psi,
            "rvp_is_summer_active": is_summer_active,
            "rvp_is_terminal_transition": is_terminal_transition,
            "rvp_is_spring_ramp": is_spring_ramp,
            "rvp_summer_transition_days_remaining": summer_days_remaining,
            "rvp_terminal_deadline_days_remaining": terminal_days_remaining,
            "rvp_spring_ramp_factor": spring_ramp_factor,
            "rvp_seasonal_compliance_premium": round(compliance_premium, 3),
            "is_rfg": reg_conf.get("is_rfg", False),
            "is_carb": reg_conf.get("is_carb", False),
            "emergency_waiver_active": waiver_active,
            "emergency_waiver_reason": waiver_reason
        }

    def compute_rvp_feature_dataframe(self, dates: pd.Series, region: str = "National") -> pd.DataFrame:
        """
        Generates full RVP feature columns for a given date series.
        """
        records = []
        for d in dates:
            spec = self.get_regional_rvp_spec(region=region, as_of_date=d)
            records.append({
                "date": pd.to_datetime(spec["as_of_date"]),
                "rvp_max_allowable_psi": spec["rvp_max_allowable_psi"],
                "rvp_is_summer_active": 1.0 if spec["rvp_is_summer_active"] else 0.0,
                "rvp_summer_transition_days_remaining": float(spec["rvp_summer_transition_days_remaining"]),
                "rvp_terminal_deadline_days_remaining": float(spec["rvp_terminal_deadline_days_remaining"]),
                "rvp_spring_ramp_factor": float(spec["rvp_spring_ramp_factor"]),
                "rvp_seasonal_compliance_premium": float(spec["rvp_seasonal_compliance_premium"]),
                "rvp_emergency_waiver_active": 1.0 if spec["emergency_waiver_active"] else 0.0
            })
        return pd.DataFrame(records)

    def apply_emergency_waiver(self, region: str, temporary_psi: float, start_date: str, end_date: str, reason: str = "Emergency Supply Waiver") -> dict:
        """
        Applies and records an emergency fuel waiver relaxing RVP standards (Issue #366).
        """
        waiver = {
            "region": region,
            "temporary_psi": float(temporary_psi),
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if "emergency_waivers" not in self.rules:
            self.rules["emergency_waivers"] = []
        self.rules["emergency_waivers"].append(waiver)

        try:
            os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist emergency waiver to {self.rules_path}: {e}")
        return waiver
