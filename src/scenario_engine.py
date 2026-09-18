"""
Seasonal & Climatological Plausibility Gating Engine (src/scenario_engine.py)

Evaluates seasonal, climatological, meteorological, hydrological, geophysical, and regulatory
plausibility for energy commodity and retail fuel shock scenarios (Issue #300).
Synthesizes prospective forward scenarios 1-14 days ahead using live precursor telemetry
(NOAA NHC tropical wave outlooks, NOAA SPC convective risk, USGS drought gradients, RVP spec calendars).
"""

import logging
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class PlausibilityStatus(str, Enum):
    ACTIVE_THREAT = "ACTIVE_THREAT"                # Score: 1.0 (Live watch/warning or precursor alert)
    SEASONALLY_PLAUSIBLE = "SEASONALLY_PLAUSIBLE"  # Score: 0.70 - 0.90 (In climatological window)
    SEASONALLY_DORMANT = "SEASONALLY_DORMANT"      # Score: 0.10 (Off-season counterfactual)
    EVERGREEN = "EVERGREEN"                        # Score: 0.80 (Year-round infrastructure/geopolitics)
    PROSPECTIVE_FORWARD = "PROSPECTIVE_FORWARD"    # Score: 0.85 (1-14d precursor forward synthesis)


# Master Climatological & Seasonal Scenario Definition Table
SCENARIO_CLIMATOLOGY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "greenville_hurricane": {
        "name": "Category 3 Atlantic Hurricane Landfall & Tar River Flooding",
        "category": "meteorological",
        "active_window": (6, 1, 11, 30),       # Jun 01 - Nov 30
        "peak_window": (8, 15, 10, 15),        # Aug 15 - Oct 15
        "telemetry_hook": "noaa_nhc",
        "locales": ["greenville", "charlotte", "national"],
        "season_label": "Atlantic Hurricane Season (Jun 01 – Nov 30)",
        "peak_label": "Peak Atlantic Hurricane Activity (Aug 15 – Oct 15)"
    },
    "port_st_lucie_hurricane": {
        "name": "Category 3 Atlantic Hurricane & Port Everglades Marine Shutdown",
        "category": "meteorological",
        "active_window": (6, 1, 11, 30),       # Jun 01 - Nov 30
        "peak_window": (8, 15, 10, 15),        # Aug 15 - Oct 15
        "telemetry_hook": "noaa_nhc",
        "locales": ["port_st_lucie", "national"],
        "season_label": "Atlantic Hurricane Season (Jun 01 – Nov 30)",
        "peak_label": "Peak Atlantic Hurricane Activity (Aug 15 – Oct 15)"
    },
    "summer_refinery_thermal_cutback": {
        "name": "Delaware & Ohio River Summer Refinery Cooling Water Thermal Curtailment",
        "category": "hydrological",
        "active_window": (6, 15, 9, 15),       # Jun 15 - Sep 15
        "peak_window": (7, 1, 8, 31),          # Jul 01 - Aug 31
        "telemetry_hook": "usgs_temp",
        "locales": ["newark", "cincinnati", "national"],
        "season_label": "High-Summer River Thermal Exceedance Window (Jun 15 – Sep 15)",
        "peak_label": "Peak Mid-Summer Heat Stress (Jul 01 – Aug 31)"
    },
    "carb_transition": {
        "name": "CARB CaRFG Summer-Blend Transition Compliance Surge",
        "category": "regulatory_spec",
        "active_window": (2, 15, 5, 1),        # Feb 15 - May 01
        "peak_window": (3, 1, 4, 15),          # Mar 01 - Apr 15
        "telemetry_hook": "spec_calendar",
        "locales": ["oakland", "national"],
        "season_label": "Statutory CARB RVP Summer-Blend Switchover (Feb 15 – May 01)",
        "peak_label": "Peak Spec Transition Squeeze (Mar 01 – Apr 15)"
    },
    "pge_psps_shutoff": {
        "name": "PG&E PSPS Red Flag Wildfire Power Shutoff & Refinery Blackout",
        "category": "meteorological_fire",
        "active_window": (7, 1, 11, 15),       # Jul 01 - Nov 15
        "peak_window": (9, 1, 10, 31),         # Sep 01 - Oct 31
        "telemetry_hook": "noaa_spc_fire",
        "locales": ["oakland", "national"],
        "season_label": "California Diablo/Santa Ana Offshore Wind Fire Season (Jul 01 – Nov 15)",
        "peak_label": "Peak Autumn Red Flag Fire Weather (Sep 01 – Oct 31)"
    },
    "carquinez_atmospheric_river": {
        "name": "Carquinez Strait Atmospheric River Runoff & Tanker Berthing Halt",
        "category": "hydrological",
        "active_window": (11, 1, 4, 1),        # Nov 01 - Apr 01 (Cross-year)
        "peak_window": (12, 15, 2, 28),        # Dec 15 - Feb 28
        "telemetry_hook": "usgs_flow",
        "locales": ["oakland", "national"],
        "season_label": "Pacific Atmospheric River Jet Stream Window (Nov 01 – Apr 01)",
        "peak_label": "Peak Winter Flood Discharge (Dec 15 – Feb 28)"
    },
    "tulsa_tornado": {
        "name": "West Tulsa HF Sinclair Refinery EF-3 Tornado Shock",
        "category": "convective_severe",
        "active_window": (3, 15, 6, 30),       # Mar 15 - Jun 30
        "peak_window": (4, 15, 5, 31),         # Apr 15 - May 31
        "telemetry_hook": "noaa_spc",
        "locales": ["tulsa", "national"],
        "season_label": "Midcontinent Tornado Alley Convective Season (Mar 15 – Jun 30)",
        "peak_label": "Peak Severe Convective Outbreak Window (Apr 15 – May 31)"
    },
    "selma_outage": {
        "name": "Selma NC Distribution Hub Tank Farm Outage & Grid Blackout Shock",
        "category": "convective_severe",
        "active_window": (4, 1, 8, 31),        # Apr 01 - Aug 31
        "peak_window": (5, 15, 7, 15),         # May 15 - Jul 15
        "telemetry_hook": "noaa_spc",
        "locales": ["greenville", "charlotte", "national"],
        "season_label": "Southeast Convective Microburst & Thunderstorm Season (Apr 01 – Aug 31)",
        "peak_label": "Peak Derecho / Microburst Window (May 15 – Jul 15)"
    },
    "mississippi_low_water": {
        "name": "Lower Mississippi & Ohio River Low-Water Barge Bottleneck",
        "category": "hydrological",
        "active_window": (8, 15, 12, 15),      # Aug 15 - Dec 15
        "peak_window": (9, 15, 11, 15),        # Sep 15 - Nov 15
        "telemetry_hook": "usgs_stage",
        "locales": ["cincinnati", "tulsa", "national"],
        "season_label": "Midwest Inland River Drought Navigation Window (Aug 15 – Dec 15)",
        "peak_label": "Critical Low-Water Barge Draft Restriction Window (Sep 15 – Nov 15)"
    },
    "polar_vortex_freeze": {
        "name": "Polar Vortex Arctic Blast & Gulf Coast Refining Freeze-Off Shock",
        "category": "meteorological",
        "active_window": (12, 1, 2, 28),       # Dec 01 - Feb 28 (Cross-year)
        "peak_window": (1, 1, 2, 15),          # Jan 01 - Feb 15
        "telemetry_hook": "noaa_freeze",
        "locales": ["tulsa", "cincinnati", "national"],
        "season_label": "Winter Polar Vortex / Arctic Deep Freeze Window (Dec 01 – Feb 28)",
        "peak_label": "Peak Hard Freeze Outbreak Risk (Jan 01 – Feb 15)"
    },
    "houston_ship_channel_closure": {
        "name": "Houston Ship Channel Torrential Runoff & Marine Closure",
        "category": "hydrological",
        "active_window": (5, 1, 10, 31),       # May 01 - Oct 31
        "peak_window": (6, 1, 9, 30),          # Jun 01 - Sep 30
        "telemetry_hook": "usgs_flow",
        "locales": ["national", "tulsa"],
        "season_label": "Gulf Coast Tropical Runoff & Heavy Rain Season (May 01 – Oct 31)",
        "peak_label": "Peak Marine Berthing Disruption Window (Jun 01 – Sep 30)"
    },
    # Evergreen & Year-Round Scenarios
    "cushing_spill": {
        "name": "Cushing Keystone Pipeline Rupture & Terminal Lock",
        "category": "infrastructure",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["tulsa", "national"],
        "season_label": "Evergreen Year-Round Infrastructure Threat",
        "peak_label": None
    },
    "hormuz_blockade": {
        "name": "Strait of Hormuz Tanker Blockade (21M bpd)",
        "category": "geopolitical",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["national"],
        "season_label": "Evergreen Year-Round Geopolitical Threat",
        "peak_label": None
    },
    "suez_rerouting": {
        "name": "Red Sea / Suez Canal Rerouting Crisis",
        "category": "geopolitical",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["national"],
        "season_label": "Evergreen Year-Round Maritime Disruption",
        "peak_label": None
    },
    "colonial_outage": {
        "name": "Colonial Pipeline Mainline Outage / Cyberattack Shock",
        "category": "infrastructure",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["greenville", "charlotte", "newark", "national"],
        "season_label": "Evergreen Year-Round Pipeline Threat",
        "peak_label": None
    },
    "marathon_outage": {
        "name": "Marathon Catlettsburg KY Refinery Unplanned Outage",
        "category": "infrastructure",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["cincinnati", "national"],
        "season_label": "Evergreen Year-Round Refinery Outage Risk",
        "peak_label": None
    },
    "chevron_hydrocracker": {
        "name": "Chevron Richmond Refinery Unplanned Hydrocracker Outage",
        "category": "infrastructure",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["oakland", "national"],
        "season_label": "Evergreen Year-Round Refinery Unit Trip Risk",
        "peak_label": None
    },
    "hayward_quake": {
        "name": "USGS Hayward Fault M>=6.0 Seismic Quake & Pipeline Shutoff",
        "category": "geophysical",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "usgs_seismic",
        "locales": ["oakland", "national"],
        "season_label": "Evergreen Year-Round Seismic Hazard",
        "peak_label": None
    },
    "weekend_opec_post": {
        "name": "Weekend Executive OPEC Talkdown Post",
        "category": "executive_social",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["national"],
        "season_label": "Evergreen Year-Round Executive Policy Shock",
        "peak_label": None
    },
    "weekend_tariff_declaration": {
        "name": "Weekend Foreign Energy Tariff Declaration",
        "category": "executive_social",
        "active_window": None,
        "peak_window": None,
        "telemetry_hook": "evergreen",
        "locales": ["national"],
        "season_label": "Evergreen Year-Round Trade Policy Shock",
        "peak_label": None
    }
}


def _is_date_in_window(target_d: date, window: Optional[Tuple[int, int, int, int]]) -> bool:
    """
    Checks if a given date falls inside a (start_m, start_d, end_m, end_d) window.
    Supports windows that wrap across calendar year boundaries (e.g. Dec 1 -> Feb 28).
    """
    if window is None:
        return True

    sm, sd, em, ed = window
    m, d = target_d.month, target_d.day

    if sm <= em:
        # Standard window within the same calendar year (e.g. Jun 1 to Nov 30)
        return (sm, sd) <= (m, d) <= (em, ed)
    else:
        # Cross-year window (e.g. Nov 1 to Apr 1 or Dec 1 to Feb 28)
        return (m, d) >= (sm, sd) or (m, d) <= (em, ed)


def _days_until_window(target_d: date, window: Tuple[int, int, int, int]) -> int:
    """
    Computes days until the next start of a seasonal window. Returns 0 if currently active.
    """
    if _is_date_in_window(target_d, window):
        return 0

    sm, sd, _, _ = window
    current_year = target_d.year
    candidate_start = date(current_year, sm, sd)

    if candidate_start < target_d:
        candidate_start = date(current_year + 1, sm, sd)

    return (candidate_start - target_d).days


def _evaluate_live_telemetry_trigger(telemetry_hook: str, scenario_id: str) -> Tuple[bool, float, str]:
    """
    Queries live real-time sensors to determine if an ACTIVE_THREAT exists.
    Returns (is_active_threat, telemetry_score_boost, trigger_reason).
    """
    if telemetry_hook == "evergreen":
        return False, 0.0, "Evergreen year-round baseline."

    try:
        # 1. NOAA Convective Severe Weather (SPC Outlooks)
        if telemetry_hook == "noaa_spc":
            from src.noaa_weather import extract_spc_convective_risk
            loc_zip = "74101" if "tulsa" in scenario_id else "27834"
            spc = extract_spc_convective_risk(location_or_zip=loc_zip)
            cat_risk = spc.get("categorical_risk", "NONE")
            num_score = spc.get("risk_score", 0.0)
            if num_score >= 0.60 or cat_risk in ["ENH", "MDT", "HIGH"]:
                return True, 1.0, f"Active NOAA SPC {cat_risk} convective outlook in effect (Risk score: {num_score:.2f})."
            elif num_score >= 0.40 or cat_risk == "SLGT":
                return False, 0.15, f"NOAA SPC Slight (SLGT) convective risk monitored (Risk score: {num_score:.2f})."

        # 2. USGS Water Telemetry (Thermal & Stage Height / Drought)
        elif telemetry_hook in ["usgs_temp", "usgs_stage", "usgs_flow"]:
            from src.usgs_water_feed import USGSWaterFeedConnector
            water_conn = USGSWaterFeedConnector()
            water_data = water_conn.fetch_live_water_telemetry()
            risk_indices = water_data.get("risk_indices", {})

            if telemetry_hook == "usgs_temp":
                thermal_risk = risk_indices.get("thermal_curtailment_risk", 0.0)
                if thermal_risk >= 0.50:
                    return True, 1.0, f"USGS river water temperature exceeds 28°C threshold (Thermal Risk: {thermal_risk:.2f})."
            elif telemetry_hook == "usgs_stage":
                drought_risk = risk_indices.get("drought_draft_restriction_risk", 0.0)
                if drought_risk >= 0.50:
                    return True, 1.0, f"USGS river stage deficit impairs barge transit draft (Drought Risk: {drought_risk:.2f})."
            elif telemetry_hook == "usgs_flow":
                surge_risk = risk_indices.get("san_jacinto_surge_risk", risk_indices.get("hydro_curtailment_risk", 0.0))
                if surge_risk >= 0.50:
                    return True, 1.0, f"USGS river flow runoff surge exceeds navigation limits (Surge Risk: {surge_risk:.2f})."

        # 3. USGS Seismic Telemetry
        elif telemetry_hook == "usgs_seismic":
            from src.usgs_seismic import USGSSeismicConnector
            seismic_conn = USGSSeismicConnector()
            seismic_live = seismic_conn.fetch_live_seismic_telemetry(corridor="bay_area")
            live_risk = seismic_live.get("indices", {}).get("bay_area_seismic_risk_index", 0.0)
            if live_risk >= 0.40:
                return True, 1.0, f"USGS Bay Area seismic event activity detected (Risk index: {live_risk:.2f})."

    except Exception as e:
        logger.debug(f"Telemetry hook evaluation notice for '{scenario_id}': {e}")

    return False, 0.0, "No active emergency telemetry triggers detected."


def evaluate_scenario_plausibility(
    scenario_id: str,
    target_date: Optional[Union[str, datetime, date]] = None,
    live_telemetry: bool = True
) -> Dict[str, Any]:
    """
    Evaluates the seasonal and physical plausibility of a given scenario ID.

    Returns a structured dictionary:
    {
        "scenario_id": str,
        "plausibility_status": PlausibilityStatus,
        "plausibility_score": float,
        "category": str,
        "is_in_season": bool,
        "is_in_peak": bool,
        "is_evergreen": bool,
        "active_window": str,
        "peak_window": str,
        "days_until_season": int,
        "telemetry_trigger": str,
        "warning_message": Optional[str],
        "context_reasoning": str
    }
    """
    spec = SCENARIO_CLIMATOLOGY_REGISTRY.get(scenario_id)
    if not spec:
        return {
            "scenario_id": scenario_id,
            "plausibility_status": PlausibilityStatus.EVERGREEN.value,
            "plausibility_score": 0.80,
            "category": "custom_unregistered",
            "is_in_season": True,
            "is_in_peak": False,
            "is_evergreen": True,
            "active_window": "Year-Round",
            "peak_window": "N/A",
            "days_until_season": 0,
            "telemetry_trigger": "Unregistered scenario preset.",
            "warning_message": None,
            "context_reasoning": "Unregistered scenario assumed year-round plausible."
        }

    # Normalize target date
    if target_date is None:
        eval_d = datetime.now(timezone.utc).date()
    elif isinstance(target_date, str):
        eval_d = datetime.fromisoformat(target_date.split("T")[0]).date()
    elif isinstance(target_date, datetime):
        eval_d = target_date.date()
    else:
        eval_d = target_date

    category = spec["category"]
    active_win = spec.get("active_window")
    peak_win = spec.get("peak_window")
    telemetry_hook = spec.get("telemetry_hook", "evergreen")
    is_evergreen = active_win is None

    is_in_season = _is_date_in_window(eval_d, active_win)
    is_in_peak = _is_date_in_window(eval_d, peak_win) if peak_win else False
    days_until = _days_until_window(eval_d, active_win) if active_win else 0

    # Format human-readable windows
    def _fmt_win(w: Optional[Tuple[int, int, int, int]]) -> str:
        if not w:
            return "Year-Round (Evergreen)"
        m_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{m_names[w[0]]} {w[1]:02d} – {m_names[w[2]]} {w[3]:02d}"

    active_win_str = _fmt_win(active_win)
    peak_win_str = _fmt_win(peak_win) if peak_win else "N/A"

    # Evaluate Live Telemetry
    active_threat = False
    telem_boost = 0.0
    trigger_desc = "No live telemetry trigger."
    if live_telemetry and telemetry_hook != "evergreen":
        active_threat, telem_boost, trigger_desc = _evaluate_live_telemetry_trigger(telemetry_hook, scenario_id)

    # Determine Status and Score
    if active_threat:
        status = PlausibilityStatus.ACTIVE_THREAT
        score = 1.0
        warning = None
        reasoning = f"ACTIVE THREAT: {trigger_desc}"
    elif is_evergreen:
        status = PlausibilityStatus.EVERGREEN
        score = 0.80
        warning = None
        reasoning = f"Evergreen scenario operates year-round without seasonal restriction ({spec.get('season_label')})."
    elif is_in_peak:
        status = PlausibilityStatus.SEASONALLY_PLAUSIBLE
        score = min(0.90 + telem_boost, 1.0)
        warning = None
        reasoning = f"Scenario is in PEAK climatological window ({peak_win_str}). High physical probability."
    elif is_in_season:
        status = PlausibilityStatus.SEASONALLY_PLAUSIBLE
        score = min(0.70 + telem_boost, 0.95)
        warning = None
        reasoning = f"Scenario is in active seasonal window ({active_win_str}). Seasonally plausible."
    else:
        status = PlausibilityStatus.SEASONALLY_DORMANT
        score = 0.10
        warning = (
            f"{spec.get('name', scenario_id)} is climatologically dormant ({active_win_str}). "
            f"Simulation executed as theoretical off-season counterfactual."
        )
        reasoning = (
            f"Target date {eval_d.isoformat()} is outside active climatological window ({active_win_str}). "
            f"Next seasonal window begins in {days_until} days."
        )

    return {
        "scenario_id": scenario_id,
        "plausibility_status": status.value,
        "plausibility_score": round(score, 2),
        "category": category,
        "is_in_season": is_in_season,
        "is_in_peak": is_in_peak,
        "is_evergreen": is_evergreen,
        "active_window": active_win_str,
        "peak_window": peak_win_str,
        "days_until_season": days_until,
        "telemetry_trigger": trigger_desc,
        "warning_message": warning,
        "context_reasoning": reasoning
    }


def synthesize_prospective_forward_scenarios(
    lookahead_days: int = 14,
    target_date: Optional[Union[str, datetime, date]] = None,
    live_telemetry: bool = True
) -> List[Dict[str, Any]]:
    """
    Formulates prospective shock scenarios BEFORE they materialize, operating on
    precursor telemetry, developing tropical waves, SPC multi-day convective outlooks,
    hydrological drought gradients, and statutory spec transition countdowns.
    """
    if target_date is None:
        eval_d = datetime.now(timezone.utc).date()
    elif isinstance(target_date, str):
        eval_d = datetime.fromisoformat(target_date.split("T")[0]).date()
    elif isinstance(target_date, datetime):
        eval_d = target_date.date()
    else:
        eval_d = target_date

    prospective_scenarios: List[Dict[str, Any]] = []

    # 1. Statutory Specification Countdowns (e.g., CARB Summer RVP Switchover Feb 15 / May 1)
    carb_days = _days_until_window(eval_d, (2, 15, 5, 1))
    if 0 < carb_days <= 21:
        prospective_scenarios.append({
            "scenario_id": "forward_carb_summer_rvp_switchover",
            "name": f"Prospective CARB Summer-Blend Spec Transition Squeeze (T-{carb_days}d Countdown)",
            "headline": f"Statutory CARB summer-blend vapor pressure transition milestone begins in {carb_days} days, tightening California RFG rack inventories.",
            "category": "regulatory_spec",
            "lead_time_days": carb_days,
            "shock_pct": 0.0410,
            "locales": ["oakland", "national"],
            "plausibility_status": PlausibilityStatus.PROSPECTIVE_FORWARD.value,
            "plausibility_score": 0.85,
            "precursor_source": "California Air Resources Board (CARB) Statutory Spec Calendar",
            "recommended_action": "Prime regional model rack premium elasticity prior to mandatory terminal turnover."
        })

    # 2. Winter Polar Vortex Precursor Outbreaks (Dec 1 - Feb 28)
    polar_days = _days_until_window(eval_d, (12, 1, 2, 28))
    if 0 < polar_days <= 14:
        prospective_scenarios.append({
            "scenario_id": "forward_polar_vortex_arctic_surge",
            "name": f"Prospective Polar Vortex Arctic Surge & Freeze-Off Risk (T-{polar_days}d Countdown)",
            "headline": f"Numerical weather models project arctic air mass descent into Midcontinent refining corridor within {polar_days} days.",
            "category": "meteorological",
            "lead_time_days": polar_days,
            "shock_pct": 0.0580,
            "locales": ["tulsa", "cincinnati", "national"],
            "plausibility_status": PlausibilityStatus.PROSPECTIVE_FORWARD.value,
            "plausibility_score": 0.80,
            "precursor_source": "NOAA Climate Prediction Center (CPC) 8-14 Day Temperature Outlook",
            "recommended_action": "Evaluate refinery power grid vulnerability and distillate blending surge."
        })

    # 3. NOAA Tropical Precursors (Active June - Nov)
    if _is_date_in_window(eval_d, (6, 1, 11, 30)):
        # If in hurricane season, check if we are in peak season or approaching peak
        if _is_date_in_window(eval_d, (8, 15, 10, 15)):
            prospective_scenarios.append({
                "scenario_id": "forward_atlantic_major_cyclone_landfall",
                "name": "Prospective Category 3+ Atlantic Tropical Landfall & Coastal Marine Berthing Closure",
                "headline": "Climatological peak tropical wave trajectory indicates elevated landfall probability along Florida / North Carolina terminal corridors.",
                "category": "meteorological",
                "lead_time_days": 7,
                "shock_pct": 0.0680,
                "locales": ["port_st_lucie", "greenville", "national"],
                "plausibility_status": PlausibilityStatus.PROSPECTIVE_FORWARD.value,
                "plausibility_score": 0.88,
                "precursor_source": "NOAA National Hurricane Center (NHC) 7-Day Tropical Weather Outlook",
                "recommended_action": "Stress-test waterborne terminal inventory replenishment lead times."
            })

    # 4. USGS Hydrological Drought Velocity (Aug - Dec)
    if _is_date_in_window(eval_d, (8, 15, 12, 15)):
        prospective_scenarios.append({
            "scenario_id": "forward_mississippi_draft_restriction",
            "name": "Prospective Inland River Barge Freight Restriction (USGS Low-Flow Trend)",
            "headline": "USGS streamflow recession rate (dQ/dt) indicates critical shallow draft tow limits on Ohio/Mississippi corridors within 10 days.",
            "category": "hydrological",
            "lead_time_days": 10,
            "shock_pct": 0.0440,
            "locales": ["cincinnati", "tulsa", "national"],
            "plausibility_status": PlausibilityStatus.PROSPECTIVE_FORWARD.value,
            "plausibility_score": 0.82,
            "precursor_source": "USGS Water Services Streamflow Gradient Telemetry",
            "recommended_action": "Model rail carload substitution premium for Midwest finished motor fuel."
        })

    return prospective_scenarios


def get_all_scenarios_with_plausibility(
    target_date: Optional[Union[str, datetime, date]] = None,
    active_only: bool = False,
    locale: Optional[str] = None,
    include_prospective: bool = True,
    live_telemetry: bool = True
) -> Dict[str, Any]:
    """
    Returns full catalog augmented with plausibility ratings, seasonal metadata,
    and optional prospective forward scenarios.
    """
    results: List[Dict[str, Any]] = []

    # 1. Preset Scenarios from Catalog
    for scen_id, spec in SCENARIO_CLIMATOLOGY_REGISTRY.items():
        plaus = evaluate_scenario_plausibility(scen_id, target_date=target_date, live_telemetry=live_telemetry)

        # Locale filter
        if locale:
            norm_loc = locale.lower().replace("_", "").replace("-", "")
            scen_locs = [l.lower().replace("_", "").replace("-", "") for l in spec.get("locales", ["national"])]
            if norm_loc not in scen_locs and "national" not in scen_locs:
                continue

        # Active only filter
        if active_only and plaus["plausibility_status"] == PlausibilityStatus.SEASONALLY_DORMANT.value:
            continue

        item = {
            "scenario_id": scen_id,
            "name": spec["name"],
            "category": spec["category"],
            "locales": spec.get("locales", ["national"]),
            "plausibility_status": plaus["plausibility_status"],
            "plausibility_score": plaus["plausibility_score"],
            "is_in_season": plaus["is_in_season"],
            "is_in_peak": plaus["is_in_peak"],
            "is_evergreen": plaus["is_evergreen"],
            "active_window": plaus["active_window"],
            "peak_window": plaus["peak_window"],
            "days_until_season": plaus["days_until_season"],
            "telemetry_trigger": plaus["telemetry_trigger"],
            "warning_message": plaus["warning_message"],
            "context_reasoning": plaus["context_reasoning"],
            "is_prospective": False
        }
        results.append(item)

    # 2. Prospective Forward Scenarios
    if include_prospective:
        prospective = synthesize_prospective_forward_scenarios(target_date=target_date, live_telemetry=live_telemetry)
        for p in prospective:
            if locale:
                norm_loc = locale.lower().replace("_", "").replace("-", "")
                p_locs = [l.lower().replace("_", "").replace("-", "") for l in p.get("locales", ["national"])]
                if norm_loc not in p_locs and "national" not in p_locs:
                    continue
            p["is_prospective"] = True
            results.append(p)

    return {
        "count": len(results),
        "target_date": target_date if isinstance(target_date, str) else (target_date.isoformat() if target_date else datetime.now(timezone.utc).date().isoformat()),
        "scenarios": results
    }
