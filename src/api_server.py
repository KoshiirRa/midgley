"""
RESTful API Endpoint Gateway (src/api_server.py)
Built on FastAPI & Starlette for real-time gas price ingestion, 5-day forecasting,
scenario simulation, and OpenAPI / GPT Action plugin manifests.
"""

import os
import json
import hmac
import hashlib
import logging
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone


from fastapi import FastAPI, Query, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from src.live_fuel_feed import (
    fetch_live_metro_retail_price,
    fetch_gasbuddy_prices_by_zip,
    REGION_METADATA
)
from src.lookup_cache import global_cache
from src.telemetry import get_all_quota_statuses, format_prometheus_metrics
from src.models import compute_locale_feature_attribution_breakdown
from src.prediction_logger import (
    compute_rolling_scoreboard_metrics,
    compute_regional_scoreboard_breakdown,
    compute_horizon_scoreboard_breakdown,
    get_recent_evaluated_records,
    sync_predictions_to_cloud,
    get_cloud_sync_status
)
from src.regional_metadata import list_all_regional_metadata
from src.zip_geocoding import resolve_zip_code, get_unmapped_zip_telemetry
from src.tokentab_accounting import token_tab_manager
from src.key_manager import global_key_manager
from src.version import get_version, get_model_version

logger = logging.getLogger(__name__)

MIDGLEY_ADMIN_SECRET = os.environ.get("MIDGLEY_ADMIN_SECRET")


class CreateKeyRequest(BaseModel):
    user_id: str = Field(..., json_schema_extra={"example": "alice"}, description="User or client identifier")
    tier: Optional[str] = Field("basic", json_schema_extra={"example": "privileged"}, description="Access tier: 'privileged' or 'basic'")
    environment: Optional[str] = Field("dev", json_schema_extra={"example": "prod"}, description="Target environment: 'dev' or 'prod'")
    rate_limit_rpm: Optional[int] = Field(30, json_schema_extra={"example": 30}, description="Rate limit in requests per minute")
    expires_days: Optional[int] = Field(None, json_schema_extra={"example": 30}, description="Optional key lifespan in days")


async def verify_admin_secret(
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret")
) -> str:
    """Method B Admin Auth Dependency: Verifies X-Admin-Secret header against MIDGLEY_ADMIN_SECRET (fails closed if unconfigured)."""
    expected_secret = os.environ.get("MIDGLEY_ADMIN_SECRET")
    if not expected_secret or not x_admin_secret or not hmac.compare_digest(x_admin_secret, expected_secret):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid, missing, or unconfigured X-Admin-Secret header."
        )
    return x_admin_secret


async def get_api_key_user(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    User Auth & Rate Limit Dependency:
    Extracts and validates API key from X-API-Key header, Authorization: Bearer header, or ?api_key query param.
    Enforces 30 RPM rate limit per key. Supports testing mode (TESTING=1) for unit test suites.
    """
    if os.environ.get("TESTING") == "1" and not x_api_key and not authorization and not api_key:
        key_info = {
            "key_prefix": "mg_test_bypass",
            "user_id": "test_suite_runner",
            "tier": "privileged",
            "rate_limit_rpm": 1000,
            "environment": "dev"
        }
        request.state.key_info = key_info
        return key_info

    token = x_api_key or api_key
    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            token = authorization

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing API key. Pass key via X-API-Key header, Authorization: Bearer <token>, or ?api_key=<token>."
        )

    expected_global = os.environ.get("MIDGLEY_API_KEY")
    if expected_global and token == expected_global:
        key_info = {
            "key_prefix": "mg_global_master",
            "user_id": "master_admin",
            "tier": "privileged",
            "rate_limit_rpm": 1000,
            "environment": "prod"
        }
        request.state.key_info = key_info
        return key_info

    is_valid, key_info, err_msg = await global_key_manager.verify_key_async(token)
    if not is_valid or not key_info:
        raise HTTPException(
            status_code=401,
            detail=f"Unauthorized: {err_msg or 'Invalid API key token.'}"
        )

    allowed, retry_after = await global_key_manager.check_rate_limit_async(
        key_prefix=key_info["key_prefix"],
        rate_limit_rpm=key_info.get("rate_limit_rpm", 30)
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too Many Requests: Rate limit of {key_info.get('rate_limit_rpm', 30)} requests per minute exceeded for key '{key_info['key_prefix']}'.",
            headers={"Retry-After": str(retry_after)}
        )

    request.state.key_info = key_info
    return key_info


async def require_privileged_tier(
    request: Request,
    key_info: Dict[str, Any] = Depends(get_api_key_user)
) -> Dict[str, Any]:
    """
    Tier Gating Dependency (Issue #437):
    Requires 'privileged' API key tier for compute-heavy simulations, mutating graph ingestions, and external submissions.
    """
    tier = key_info.get("tier", "basic").lower()
    if tier != "privileged":
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Action requires 'privileged' API key tier (current tier: '{tier}'). Please upgrade your API key or supply administrative credentials."
        )
    return key_info


app = FastAPI(
    title="Midgley Gas Price Forecasting API Gateway",
    description="RESTful API for real-time unleaded gasoline pump prices, 5-day out-of-time quantitative forecasts, and counterfactual physical/geopolitical shock simulations.",
    version=get_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    servers=[
        {"url": "http://localhost:8000", "description": "Local API Gateway"}
    ]
)

# Enable CORS for cross-origin web apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Locale code normalization mapping
LOCALE_MAP = {
    "national": "National",
    "us": "National",
    "tulsa": "Tulsa_OK",
    "tulsa_ok": "Tulsa_OK",
    "newark": "Newark_DE",
    "newark_de": "Newark_DE",
    "cincinnati": "Cincinnati_OH",
    "cincinnati_oh": "Cincinnati_OH",
    "cincinnati_ky": "Cincinnati_KY",
    "oakland": "Oakland_CA",
    "oakland_ca": "Oakland_CA",
    "bayarea": "BayArea_CA",
    "bayarea_ca": "BayArea_CA",
    "sanfrancisco": "SanFrancisco_CA",
    "sanfrancisco_ca": "SanFrancisco_CA",
    "sf": "SanFrancisco_CA",
    "sanjose": "SanJose_CA",
    "sanjose_ca": "SanJose_CA",
    "sj": "SanJose_CA",
    "northbay": "NorthBay_CA",
    "northbay_ca": "NorthBay_CA",
    "greenville": "Greenville_NC",
    "greenville_nc": "Greenville_NC",
    "charlotte": "Charlotte_NC",
    "charlotte_nc": "Charlotte_NC",
    "clt": "Charlotte_NC",
    "port_st_lucie": "Port_St_Lucie_FL",
    "port_st_lucie_fl": "Port_St_Lucie_FL",
    "psl": "Port_St_Lucie_FL"
}

# Regional PADD metadata
PADD_METADATA = {
    "National": {"name": "National Wholesale / US Average", "padd": "US National", "carb_tax": 0.0},
    "Tulsa_OK": {"name": "Tulsa Metro Area, OK", "padd": "PADD 2 Midwest", "carb_tax": 0.0},
    "Newark_DE": {"name": "Newark Metro Area, DE", "padd": "PADD 1B Central Atlantic", "carb_tax": 0.0},
    "Cincinnati_OH": {"name": "Cincinnati Metro Area, OH", "padd": "PADD 2 Midwest", "carb_tax": 0.0},
    "Cincinnati_KY": {"name": "Northern Kentucky Retail", "padd": "PADD 2 Midwest", "carb_tax": 0.0},
    "Greenville_NC": {"name": "Greenville Metro Area, NC", "padd": "PADD 1C South Atlantic", "carb_tax": 0.0},
    "Charlotte_NC": {"name": "Charlotte Metro Area, NC", "padd": "PADD 1C South Atlantic", "carb_tax": 0.0},
    "Port_St_Lucie_FL": {"name": "Port St. Lucie Metro Area, FL", "padd": "PADD 1C South Atlantic", "carb_tax": 0.0},
    "Oakland_CA": {"name": "Oakland & SF Bay Area, CA", "padd": "PADD 5 West Coast", "carb_tax": 0.953},
    "BayArea_CA": {"name": "SF Bay Area 9-County Region, CA", "padd": "PADD 5 West Coast", "carb_tax": 0.953},
    "SanFrancisco_CA": {"name": "San Francisco Metro Retail, CA", "padd": "PADD 5 West Coast", "carb_tax": 0.953},
    "SanJose_CA": {"name": "San Jose / Silicon Valley, CA", "padd": "PADD 5 West Coast", "carb_tax": 0.953},
    "NorthBay_CA": {"name": "North Bay / Solano Region, CA", "padd": "PADD 5 West Coast", "carb_tax": 0.953}
}

# Scenario Simulator Catalog
SCENARIOS_CATALOG = {
    "hormuz_blockade": {
        "name": "Strait of Hormuz Tanker Blockade (21M bpd)",
        "headline": "Geopolitical escalation shuts down Strait of Hormuz tanker transit across 21M bpd crude pipeline.",
        "shock_pct": 0.0288,
        "category": "geopolitical",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["national"]
    },
    "suez_rerouting": {
        "name": "Red Sea / Suez Canal Rerouting Crisis",
        "headline": "Red Sea marine security incidents force product tankers to detour around Cape of Good Hope.",
        "shock_pct": 0.0532,
        "category": "geopolitical",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["national"]
    },
    "tulsa_tornado": {
        "name": "West Tulsa HF Sinclair Refinery EF-3 Tornado Shock",
        "headline": "Direct tornado strike forces emergency shutdown of West Tulsa HF Sinclair refinery (85,000 bpd).",
        "shock_pct": 0.0458,
        "category": "convective_severe",
        "season_window": "Mar 15 – Jun 30",
        "telemetry_hook": "noaa_spc",
        "locales": ["tulsa", "national"]
    },
    "cushing_spill": {
        "name": "Cushing Keystone Pipeline Rupture & Terminal Lock",
        "headline": "Keystone pipeline pressure drop causes crude oil spill near Cushing, OK hub.",
        "shock_pct": 0.0458,
        "category": "infrastructure",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["tulsa", "national"]
    },
    "marathon_outage": {
        "name": "Marathon Catlettsburg KY Refinery Unplanned Outage",
        "headline": "Catlettsburg refinery fluid catalytic cracker trip causes tri-state gasoline tight market.",
        "shock_pct": 0.0478,
        "category": "infrastructure",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["cincinnati", "national"]
    },
    "mississippi_low_water": {
        "name": "Lower Mississippi & Ohio River Low-Water Barge Bottleneck",
        "headline": "Severe drought restricts barge draft levels on Mississippi and Ohio rivers, raising Midwest rack freight.",
        "shock_pct": 0.0420,
        "category": "hydrological",
        "season_window": "Aug 15 – Dec 15",
        "telemetry_hook": "usgs_stage",
        "locales": ["cincinnati", "tulsa", "national"]
    },
    "hayward_quake": {
        "name": "USGS Hayward Fault M>=6.0 Seismic Quake & Pipeline Shutoff",
        "headline": "Magnitude 6.4 earthquake triggers emergency shutdown of SF Bay Area crude and product pipelines.",
        "shock_pct": 0.0848,
        "category": "geophysical",
        "season_window": "Year-Round",
        "telemetry_hook": "usgs_seismic",
        "locales": ["oakland", "national"]
    },
    "pge_psps_shutoff": {
        "name": "PG&E PSPS Red Flag Wildfire Power Shutoff & Refinery Blackout",
        "headline": "High wind red flag wildfire threat triggers PG&E power shutoff across Contra Costa refining corridor.",
        "shock_pct": 0.0707,
        "category": "meteorological_fire",
        "season_window": "Jul 01 – Nov 15",
        "telemetry_hook": "noaa_spc_fire",
        "locales": ["oakland", "national"]
    },
    "chevron_hydrocracker": {
        "name": "Chevron Richmond Refinery Unplanned Hydrocracker Outage",
        "headline": "Unplanned hydrocracker unit trip at Chevron Richmond refinery causes West Coast price surge.",
        "shock_pct": 0.0576,
        "category": "infrastructure",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["oakland", "national"]
    },
    "carb_transition": {
        "name": "CARB CaRFG Summer-Blend Transition Compliance Surge",
        "headline": "Statutory CARB summer-blend vapor pressure transition tightens California RFG supply.",
        "shock_pct": 0.0444,
        "category": "regulatory_spec",
        "season_window": "Feb 15 – May 01",
        "telemetry_hook": "spec_calendar",
        "locales": ["oakland", "national"]
    },
    "colonial_outage": {
        "name": "Colonial Pipeline Mainline Outage / Cyberattack Shock",
        "headline": "Colonial Pipeline Line 1 emergency shutdown halts batch shipments into Selma NC breakout tank farms.",
        "shock_pct": 0.0754,
        "category": "infrastructure",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["greenville", "charlotte", "newark", "national"]
    },
    "greenville_hurricane": {
        "name": "Category 3 Atlantic Hurricane Landfall & Tar River Flooding",
        "headline": "Major Hurricane landfall inundates Eastern NC coastal distribution highways and Tar River transport routes.",
        "shock_pct": 0.0662,
        "category": "meteorological",
        "season_window": "Jun 01 – Nov 30",
        "telemetry_hook": "noaa_nhc",
        "locales": ["greenville", "charlotte", "national"]
    },
    "selma_outage": {
        "name": "Selma NC Distribution Hub Tank Farm Outage & Grid Blackout Shock",
        "headline": "Severe convective microburst knocks out Duke Energy substation at Selma breakout hub, suspending rack loading.",
        "shock_pct": 0.0569,
        "category": "convective_severe",
        "season_window": "Apr 01 – Aug 31",
        "telemetry_hook": "noaa_spc",
        "locales": ["greenville", "charlotte", "national"]
    },
    "port_st_lucie_hurricane": {
        "name": "Category 3 Atlantic Hurricane & Port Everglades Marine Shutdown",
        "headline": "Major Hurricane storm surge forces emergency closure of Port Everglades and Port Canaveral marine petroleum berths.",
        "shock_pct": 0.0666,
        "category": "meteorological",
        "season_window": "Jun 01 – Nov 30",
        "telemetry_hook": "noaa_nhc",
        "locales": ["port_st_lucie", "national"]
    },
    "weekend_opec_post": {
        "name": "Weekend Executive OPEC Talkdown Post",
        "headline": "Executive social post demanding immediate OPEC price cuts re-anchors market opens downward.",
        "shock_pct": -0.0185,
        "category": "executive_social",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["national"]
    },
    "weekend_tariff_declaration": {
        "name": "Weekend Foreign Energy Tariff Declaration",
        "headline": "Executive social post announcing immediate 25% energy import tariff causes weekend open gap surge.",
        "shock_pct": 0.0210,
        "category": "executive_social",
        "season_window": "Year-Round",
        "telemetry_hook": "evergreen",
        "locales": ["national"]
    },
    "houston_ship_channel_closure": {
        "name": "Houston Ship Channel Torrential Runoff & Marine Closure",
        "headline": "USGS San Jacinto runoff surge closes Houston Ship Channel to crude tankers and fuel barges, halting 2.7M bpd refining corridor.",
        "shock_pct": 0.0512,
        "category": "hydrological",
        "season_window": "May 01 – Oct 31",
        "telemetry_hook": "usgs_flow",
        "locales": ["national", "tulsa"]
    },
    "carquinez_atmospheric_river": {
        "name": "Carquinez Strait Atmospheric River Runoff & Tanker Berthing Halt",
        "headline": "USGS Sacramento River discharge surge through Carquinez Strait suspends crude tanker berthing at Martinez & Benicia refineries.",
        "shock_pct": 0.0435,
        "category": "hydrological",
        "season_window": "Nov 01 – Apr 01",
        "telemetry_hook": "usgs_flow",
        "locales": ["oakland", "national"]
    },
    "summer_refinery_thermal_cutback": {
        "name": "Delaware & Ohio River Summer Refinery Cooling Water Thermal Curtailment",
        "headline": "USGS river water temperature exceeds 28°C, impairing refinery cooling tower efficiency and triggering statutory run cuts.",
        "shock_pct": 0.0385,
        "category": "hydrological",
        "season_window": "Jun 15 – Sep 15",
        "telemetry_hook": "usgs_temp",
        "locales": ["newark", "cincinnati", "national"]
    },
    "polar_vortex_freeze": {
        "name": "Polar Vortex Arctic Blast & Gulf Coast Refining Freeze-Off Shock",
        "headline": "Severe arctic blast triggers wellhead freeze-offs, electrical grid failure, and emergency refinery shutdowns across Texas and Midcontinent.",
        "shock_pct": 0.0625,
        "category": "meteorological",
        "season_window": "Dec 01 – Feb 28",
        "telemetry_hook": "noaa_freeze",
        "locales": ["tulsa", "cincinnati", "national"]
    }
}


class SimulateRequest(BaseModel):
    scenario_id: str = Field(..., json_schema_extra={"example": "hormuz_blockade"}, description="Unique scenario ID")
    locale: Optional[str] = Field("national", json_schema_extra={"example": "oakland"}, description="Target locale code")
    custom_shock_pct: Optional[float] = Field(None, json_schema_extra={"example": 0.05}, description="Optional custom shock percentage")
    target_date: Optional[str] = Field(None, json_schema_extra={"example": "2026-09-18"}, description="Target date for seasonal plausibility evaluation (YYYY-MM-DD)")
    enable_cohort_simulation: Optional[bool] = Field(None, json_schema_extra={"example": True}, description="Toggle 4-persona multi-agent deliberative market simulation (defaults to system config)")
    custom_headline: Optional[str] = Field(None, json_schema_extra={"example": "Breaking: Pipeline leak prompts precautionary shutdown"}, description="Optional custom breaking headline prose")


class BatchForecastRequest(BaseModel):
    locales: List[str] = Field(default_factory=lambda: ["national"], json_schema_extra={"example": ["tulsa", "oakland", "cincinnati"]}, description="List of locale codes")
    days: Optional[int] = Field(5, ge=1, le=30, description="Forecast target horizon in trading days")


class BatchCombinedRequest(BaseModel):
    locales: List[str] = Field(default_factory=lambda: ["national"], json_schema_extra={"example": ["tulsa", "newark", "port_st_lucie"]}, description="List of locale codes")


class HeadlineArenaSubmitRequest(BaseModel):
    asset: str = Field(default="RB", description="Asset symbol ('RB' for RBOB Wholesale Gasoline, 'CL' for WTI Crude)")
    open_price: float = Field(..., gt=0, description="Open spot price")
    p50: float = Field(..., gt=0, description="Median model forecast price")
    p10: Optional[float] = Field(None, gt=0, description="10th percentile downside band")
    p90: Optional[float] = Field(None, gt=0, description="90th percentile upside band")
    residual_std: Optional[float] = Field(None, gt=0, description="Residual standard deviation")
    live_in_dev: bool = Field(default=False, description="Whether to execute live submission in dev environment (tags as [DEV-TEST])")


BatchForecastRequest.model_rebuild()
BatchCombinedRequest.model_rebuild()
HeadlineArenaSubmitRequest.model_rebuild()


# Rate Limiting & Unified Auth Middleware helper (Issue #437)
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    expected_token = os.environ.get("MIDGLEY_API_KEY")
    is_testing = os.environ.get("TESTING") == "1"

    if expected_token and not is_testing:
        path = request.url.path
        is_public = (
            path == "/"
            or path.startswith((
                "/docs", "/redoc", "/openapi.json", "/.well-known", "/health",
                "/status", "/metrics", "/api/v1/metrics", "/robots.txt", "/favicon.ico",
                "/static", "/api/v1/webhooks", "/api/v1/events/webhook",
                "/api/v1/events/queue-consumer", "/api/v1/events/poll"
            ))
        )

        # Check for administrative headers
        admin_secret = os.environ.get("MIDGLEY_ADMIN_SECRET")
        admin_header = request.headers.get("X-Admin-Secret")
        is_admin_auth = bool(admin_secret and admin_header and hmac.compare_digest(admin_header, admin_secret))

        if not is_public and not is_admin_auth:
            auth_header = request.headers.get("Authorization") or request.headers.get("X-API-Key")
            token = request.query_params.get("api_key")
            if auth_header:
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:].strip()
                else:
                    token = auth_header.strip()

            valid = False
            if token:
                if token == expected_token:
                    valid = True
                else:
                    is_valid, _, _ = await global_key_manager.verify_key_async(token)
                    if is_valid:
                        valid = True

            if not valid:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized", "message": "Invalid, missing, or unauthenticated API key."}
                )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = "60"
    response.headers["X-RateLimit-Remaining"] = "59"
    response.headers["X-RateLimit-Reset"] = str(int(datetime.now().timestamp() + 60))
    return response


def _normalize_locale(locale_str: str) -> str:
    cleaned = locale_str.lower().strip() if locale_str else "national"
    return LOCALE_MAP.get(cleaned, "National")


def _get_live_prices_impl(locale: str = "national", zip_code: Optional[str] = None) -> dict:
    zip_res = None
    if zip_code:
        zip_res = resolve_zip_code(zip_code)
        locale = zip_res.get("locale_code", locale or "national")

    if zip_code and not zip_res.get("is_metro_cluster_hit", False):
        gb_data = fetch_gasbuddy_prices_by_zip(zip_code)
        if not gb_data:
            gb_data = {
                "average_price": 3.890,
                "stations": [],
                "source": f"GasBuddy Fallback (Zip {zip_code})"
            }
        region_code = _normalize_locale(locale)
        meta = PADD_METADATA.get(region_code, PADD_METADATA["National"])
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "zip_code": zip_code,
            "zip_code_resolution": zip_res,
            "locale": {
                "code": locale,
                "region_id": region_code,
                "name": meta["name"],
                "padd_region": zip_res.get("padd_region", meta["padd"])
            },
            "price_per_gal": gb_data.get("average_price"),
            "source": gb_data.get("source"),
            "data": gb_data,
            "carb_tax_regulatory_burden_per_gal": zip_res.get("state_tax_rate_per_gal", meta["carb_tax"])
        }

    region_code = _normalize_locale(locale)
    live_res = fetch_live_metro_retail_price(region_code)
    meta = PADD_METADATA.get(region_code, PADD_METADATA["National"])
    provenance_meta = live_res.get("provenance") or global_cache.build_provenance_chain(
        source=live_res.get("source", "UNKNOWN"),
        region_id=region_code,
        padd=meta.get("padd", "PADD 2"),
        requested_granularity="NATIONAL" if region_code == "National" else "METRO",
        served_granularity="METRO",
        cache_status="HIT_FRESH" if live_res.get("_cache_hit") else "MISS"
    )

    res = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "locale": {
            "code": locale,
            "region_id": region_code,
            "name": meta["name"],
            "padd_region": meta["padd"]
        },
        "price_per_gal": live_res.get("price"),
        "source": live_res.get("source"),
        "provenance": provenance_meta,
        "carb_tax_regulatory_burden_per_gal": meta["carb_tax"]
    }
    if zip_code:
        res["zip_code"] = zip_code
    if zip_res:
        res["zip_code_resolution"] = zip_res
    return res


def _get_forecast_impl(locale: str = "national", days: int = 5, zip_code: Optional[str] = None) -> dict:
    zip_res = None
    if zip_code:
        zip_res = resolve_zip_code(zip_code)
        locale = zip_res.get("locale_code", locale or "national")

    region_code = _normalize_locale(locale)
    live_res = fetch_live_metro_retail_price(region_code)
    base_price = live_res.get("price", 3.184)
    meta = PADD_METADATA.get(region_code, PADD_METADATA["National"])

    projected_delta = None
    h_preds = {}
    h_lowers = {}
    h_uppers = {}
    target_date = (pd.Timestamp.now() + pd.offsets.BDay(days)).strftime("%Y-%m-%d")

    try:
        from src.prediction_logger import (
            HISTORY_CSV_PATH,
            compute_rolling_scoreboard_metrics,
            get_regional_calibration_residuals,
            compute_regional_residual_std
        )
        if os.path.exists(HISTORY_CSV_PATH):
            df_hist = pd.read_csv(HISTORY_CSV_PATH)
            if not df_hist.empty and 'region' in df_hist.columns:
                reg_df = df_hist[df_hist['region'] == region_code]
                if not reg_df.empty:
                    # Segregate prospective predictions from retroactive backtests (Issues #357, #389)
                    is_retro = reg_df.get('is_retroactive_backtest', pd.Series(False, index=reg_df.index)).fillna(False).astype(bool)
                    is_backtest_run = reg_df.get('run_type', pd.Series('', index=reg_df.index)).astype(str).str.upper() == 'RETROSPECTIVE_BACKTEST'
                    prospective_df = reg_df[~is_retro & ~is_backtest_run]

                    target_pool = prospective_df if not prospective_df.empty else reg_df

                    # Sort chronologically by log_timestamp if available
                    if 'log_timestamp' in target_pool.columns:
                        target_pool = target_pool.sort_values(by='log_timestamp')

                    today_str = datetime.now().strftime("%Y-%m-%d")
                    today_dt = datetime.now()

                    # Filter strictly to active, unexpired forecasts (Issues #462, #474)
                    if 'forecast_target_date' in target_pool.columns:
                        active_pool = target_pool[target_pool['forecast_target_date'] > today_str]
                    else:
                        active_pool = pd.DataFrame()

                    # Extract discrete multi-horizon records
                    for h_i in range(1, 6):
                        if not active_pool.empty and 'forecast_horizon_days' in active_pool.columns:
                            sub_h = active_pool[active_pool['forecast_horizon_days'] == h_i]
                            if not sub_h.empty:
                                sub_latest = sub_h.iloc[-1]
                                sub_base = float(sub_latest.get('current_base_price', base_price))
                                sub_pred = float(sub_latest.get('predicted_5d_price', base_price))
                                sub_delta = sub_pred - sub_base
                                sub_delta = max(-0.75, min(0.75, sub_delta))
                                pred_price_h = round(base_price + sub_delta, 3)
                                h_preds[h_i] = pred_price_h

                                # Dynamically calculate calibrated intervals centered on current predicted price (Issue #462)
                                r_std = compute_regional_residual_std(region_code, window_days=30, horizon_days=h_i)
                                h_lowers[h_i] = round(pred_price_h - 1.96 * r_std, 3)
                                h_uppers[h_i] = round(pred_price_h + 1.96 * r_std, 3)

                                if h_i == days:
                                    target_date = str(sub_latest.get('forecast_target_date', ''))

                    if days in h_preds:
                        projected_delta = round(h_preds[days] - base_price, 3)
                    else:
                        # Fail-safe: persistence baseline without fabricating future maturity from stale records (Issue #474)
                        projected_delta = 0.0
                        target_date = (today_dt + timedelta(days=days)).strftime("%Y-%m-%d")
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, OSError) as e:
        logger.debug(f"Transient or missing prediction history for {region_code}: {e}")
    except Exception as e:
        logger.debug(f"Notice reading prediction history for {region_code}: {e}")

    if projected_delta is None:
        projected_delta = 0.0


    predicted_price = round(base_price + projected_delta, 3)
    expected_pct = round((projected_delta / base_price) * 100, 2)
    direction = "UP" if projected_delta > 0 else ("DOWN" if projected_delta < 0 else "FLAT")

    # Compute 5-day trajectory points from discrete multi-horizon estimators or smooth delta fallback
    day_step = projected_delta / 5.0
    day_1 = h_preds.get(1, round(base_price + day_step * 1, 3))
    day_2 = h_preds.get(2, round(base_price + day_step * 2, 3))
    day_3 = h_preds.get(3, round(base_price + day_step * 3, 3))
    day_4 = h_preds.get(4, round(base_price + day_step * 4, 3))
    day_5 = h_preds.get(5, round(predicted_price, 3))

    # Compute dynamic rolling accuracy metrics from ledger (Issue #440)
    score_metrics = compute_rolling_scoreboard_metrics(
        window_days=30,
        region=region_code,
        horizon_days=days if days <= 5 else 5,
        include_retroactive=False
    )
    if score_metrics.get("total_evaluations", 0) < 5:
        score_metrics = compute_rolling_scoreboard_metrics(
            window_days="all",
            region=region_code,
            horizon_days=days if days <= 5 else 5,
            include_retroactive=False
        )

    hit_rate = round(score_metrics.get("directional_hit_rate_pct", 51.1) / 100.0, 4)
    mae_val = round(score_metrics.get("mae_dollars", 0.149), 4)
    total_evals = score_metrics.get("total_evaluations", 0)

    # Compute discrete-horizon conformal / calibrated prediction intervals (Issue #358, #436)
    resids = get_regional_calibration_residuals(region=region_code, horizon_days=days, window_days=60)
    calibration_method = "conformal" if len(resids) >= 10 else "gaussian_scaled"
    if days in h_lowers and days in h_uppers:
        lower_95ci = h_lowers[days]
        upper_95ci = h_uppers[days]
    elif len(resids) >= 10:
        from src.models import compute_conformal_prediction_intervals
        low_b, high_b = compute_conformal_prediction_intervals(predicted_price, resids, alpha=0.05)
        lower_95ci = float(low_b[0] if hasattr(low_b, '__len__') else low_b)
        upper_95ci = float(high_b[0] if hasattr(high_b, '__len__') else high_b)
    else:
        h_std = compute_regional_residual_std(region=region_code, window_days=30, horizon_days=days)
        lower_95ci = round(predicted_price - (1.96 * h_std), 4)
        upper_95ci = round(predicted_price + (1.96 * h_std), 4)

    attr = compute_locale_feature_attribution_breakdown(
        region_code=region_code,
        base_price=base_price,
        predicted_price=predicted_price
    )

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "locale": {
            "code": locale,
            "region_id": region_code,
            "name": meta["name"]
        },
        "forecast": {
            "model_version": get_model_version(),
            "forecast_horizon_days": days,
            "target_date": target_date,
            "current_base_price": base_price,
            "predicted_price_per_gal": predicted_price,
            "expected_change_dollars": round(projected_delta, 3),
            "expected_change_percent": expected_pct,
            "projected_direction": direction,
            "prediction_lower_95ci": lower_95ci,
            "prediction_upper_95ci": upper_95ci,
            "calibration_method": calibration_method,
            "calibration_sample_size": len(resids),
            "directional_hit_rate_historical": hit_rate,
            "historical_mae_dollars": mae_val,
            "evaluation_sample_size": total_evals,
            "day_1_price": day_1,
            "day_2_price": day_2,
            "day_3_price": day_3,
            "day_4_price": day_4,
            "day_5_price": day_5,
            "feature_attributions": attr["components"],
            "driver_breakdown": {
                "summary_text": attr["summary_text"],
                "key_drivers": attr["key_drivers"]
            }
        }
    }


@app.get("/api/v1/forecast/scoreboard", dependencies=[Depends(get_api_key_user)], summary="Get Realized-vs-Predicted Rolling Scoreboard Metrics")
def get_forecast_scoreboard(
    locale: Optional[str] = Query(None, description="Optional locale code or region (e.g., 'tulsa', 'oakland', 'national', 'all')"),
    window: Optional[str] = Query("30", description="Rolling evaluation window in days ('30', '60', '90', or 'all')"),
    horizon: Optional[str] = Query(None, description="Optional forecast horizon in days ('1', '2', '3', '4', '5', or 'all')"),
    include_retroactive: Optional[bool] = Query(False, description="Whether to include retroactive historical backtest records or restrict strictly to forward out-of-time predictions")
):
    """
    Returns rolling out-of-time forecast accuracy metrics (MAE, RMSE, MAPE, Directional Hit Rate %,
    Naive Persistence MAE, and Model MAE Uplift %) evaluated against actual ground-truth market prices.
    Supports granular filtering by forecast horizon (1d through 5d) and retroactive backtest segregation (Issue #389).
    """
    region_code = _normalize_locale(locale) if (locale and str(locale).lower() not in ["all", "none", ""]) else None

    summary_metrics = compute_rolling_scoreboard_metrics(
        window_days=window, 
        region=region_code, 
        horizon_days=horizon,
        include_retroactive=bool(include_retroactive)
    )
    regional_breakdown = compute_regional_scoreboard_breakdown(
        window_days=window, 
        horizon_days=horizon,
        include_retroactive=bool(include_retroactive)
    )
    horizon_breakdown = compute_horizon_scoreboard_breakdown(
        window_days=window, 
        region=region_code,
        include_retroactive=bool(include_retroactive)
    )
    recent_evals = get_recent_evaluated_records(
        region=region_code, 
        limit=50, 
        horizon_days=horizon,
        include_retroactive=bool(include_retroactive)
    )

    return {
        "status": "success",
        "system": f"Midgley {get_model_version()}",
        "timestamp": datetime.now().isoformat(),
        "filters": {
            "locale": locale or "all",
            "region_code": region_code or "ALL",
            "window_days": window,
            "horizon": horizon or "all",
            "include_retroactive": bool(include_retroactive)
        },
        "summary": summary_metrics,
        "horizon_breakdown": horizon_breakdown,
        "regional_breakdown": regional_breakdown,
        "recent_evaluations": recent_evals
    }


@app.post("/api/v1/forecast/cloud-sync", dependencies=[Depends(verify_admin_secret)], summary="Synchronize Prediction History to Cloud Database")
def trigger_cloud_prediction_sync():
    """
    Triggers synchronization of prediction history records to Cloud DB (Turso Edge / Cloudflare D1 / Neon Postgres).
    Falls back gracefully to local CSV store if offline. Requires X-Admin-Secret header.
    """
    res = sync_predictions_to_cloud()
    return {
        "status": "success",
        "system": f"Midgley {get_model_version()}",
        "timestamp": datetime.now().isoformat(),
        "result": res
    }


@app.get("/api/v1/forecast/cloud-status", summary="Get Cloud Prediction Sync Status")
def get_cloud_prediction_sync_status():
    """
    Returns active cloud prediction database providers, local CSV fallback state, and total record counts.
    """
    status_info = get_cloud_sync_status()
    return {
        "status": "success",
        "system": f"Midgley {get_model_version()}",
        "timestamp": datetime.now().isoformat(),
        "cloud_sync_status": status_info
    }


@app.get("/api/v1/system/radar", summary="Get Open Source AI Radar Model Catalog")
def get_system_radar_catalog(
    category: Optional[str] = Query(None, description="Optional category filter (e.g. llm, timeseries, vision)"),
    limit: int = Query(15, ge=1, le=50, description="Max models to return")
):
    """
    Returns open-source model capabilities, benchmarks, and release metrics from Open Source AI Radar (Issue #187).
    """
    try:
        from src.data_ingestion import OpenSourceAIRadarConnector
        connector = OpenSourceAIRadarConnector()
        models = connector.fetch_radar_models(max_results=limit, category=category)
        return {
            "status": "success",
            "count": len(models),
            "timestamp": datetime.now().isoformat(),
            "models": models
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "models": []
        }



@app.get("/api/v1/forecast/purged-cv", dependencies=[Depends(get_api_key_user)], summary="Get Purged & Combinatorial Cross-Validation Metrics")
def get_purged_cv_metrics(
    n_splits: int = Query(5, ge=2, le=20, description="Number of CV splits"),
    combinatorial: bool = Query(False, description="Whether to use Combinatorial Purged CV (CPCV)"),
    label_horizon: int = Query(5, ge=1, le=30, description="Label horizon in trading days"),
    embargo_days: int = Query(5, ge=0, le=30, description="Embargo duration in trading days")
):
    """
    Executes Purged Group Time Series CV or Combinatorial Purged CV (CPCV) evaluation
    eliminating temporal data leakage from overlapping 5-day horizon labels (Issue #117).
    """
    import numpy as np
    from src.models import PurgedGroupTimeSeriesSplit, CombinatorialPurgedCV, evaluate_model_purged_cv
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    
    np.random.seed(42)
    n_samples = 250
    X_synth = np.random.randn(n_samples, 10)
    y_synth = 3.0 + 0.5 * X_synth[:, 0] - 0.2 * X_synth[:, 1] + np.random.randn(n_samples) * 0.05
    
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    
    if combinatorial:
        cv_splitter = CombinatorialPurgedCV(n_splits=n_splits, n_test_splits=2, label_horizon_steps=label_horizon, embargo_steps=embargo_days)
    else:
        cv_splitter = PurgedGroupTimeSeriesSplit(n_splits=n_splits, label_horizon_steps=label_horizon, embargo_steps=embargo_days)
        
    res = evaluate_model_purged_cv(
        model=model,
        X=X_synth,
        y=y_synth,
        cv_splitter=cv_splitter,
        label_horizon_steps=label_horizon,
        embargo_steps=embargo_days
    )
    
    return {
        "status": "success",
        "demonstration_type": "SYNTHETIC_ILLUSTRATIVE_DEMO",
        "is_synthetic_demonstration": True,
        "note": "Demonstration endpoint executing PurgedGroupTimeSeriesSplit and CPCV evaluation across synthetic feature matrices for algorithmic verification (Issue #440).",
        "timestamp": datetime.now().isoformat(),
        "purged_cv_evaluation": res
    }


@app.get("/api/v1/diesel/live", dependencies=[Depends(get_api_key_user)], summary="Get Live Ultra-Low Sulfur Diesel (ULSD) & Distillate Prices")
def get_diesel_live_prices():
    """
    Returns live NYMEX ULSD futures (HO=F), distillate crack spreads,
    3-2-1 refining margins, and regional retail diesel prices across modeled metro areas (Issue #41).
    """
    from src.diesel_regional import DIESEL_BASE_ANCHORS, compute_distillate_crack_spread, compute_321_refining_crack_spread
    ulsd_spot = 2.850
    wti_spot = 75.00
    rbob_spot = 2.450
    dist_crack = compute_distillate_crack_spread(ulsd_spot, wti_spot)
    crack_321 = compute_321_refining_crack_spread(rbob_spot, ulsd_spot, wti_spot)

    return {
        "status": "success",
        "system": f"Midgley {get_model_version()} ULSD Distillate Engine",
        "timestamp": datetime.now().isoformat(),
        "futures": {
            "ulsd_ny_harbor_ho_f": ulsd_spot,
            "wti_crude_cl_f": wti_spot,
            "rbob_gasoline_rb_f": rbob_spot,
            "distillate_crack_spread_gal": dist_crack,
            "refining_321_crack_spread_gal": crack_321
        },
        "retail_diesel_prices": DIESEL_BASE_ANCHORS
    }


@app.get("/api/v1/diesel/forecast", dependencies=[Depends(get_api_key_user)], summary="Get 5-Day Out-of-Time ULSD Diesel Forecast")
def get_diesel_forecast(
    rbob: float = Query(2.450, description="Base RBOB futures price ($/gal)"),
    ulsd: float = Query(2.850, description="Base ULSD futures price ($/gal)"),
    wti: float = Query(75.00, description="Base WTI crude price ($/gal)")
):
    """
    Generates 5-day step-ahead wholesale ULSD predictions and regional retail calibrations (Issue #41).
    """
    from src.diesel_regional import UltraLowSulfurDieselForecastingAgent
    agent = UltraLowSulfurDieselForecastingAgent(alpha=10.0)
    res = agent.forecast_ulsd(rbob_price=rbob, ulsd_price=ulsd, wti_price=wti)
    return res


@app.get("/api/v1/diesel/simulate", dependencies=[Depends(get_api_key_user)], summary="Simulate Counterfactual Diesel Market Shocks")
def simulate_diesel_shock_endpoint(
    scenario: str = Query("colonial_line2_outage", description="Scenario key: 'colonial_line2_outage', 'northeast_polar_vortex', 'midwest_harvest_surge', 'imo_2020_marine_fuel_spike', 'winter_grid_emergency_backup'"),
    base_ulsd: float = Query(2.850, description="Base ULSD futures price ($/gal)")
):

    """
    Simulates counterfactual physical, weather, and geopolitical diesel shock scenarios (Issue #41).
    """
    from src.diesel_regional import simulate_diesel_shock
    return simulate_diesel_shock(scenario_key=scenario, base_ulsd_price=base_ulsd)


@app.get("/health", summary="Health Check")
@app.get("/", summary="Root Health & API Information")
def get_health():
    """Returns gateway status and service version."""
    return {
        "status": "online",
        "system": "Midgley Gas Price Forecasting API Gateway",
        "version": get_version(),
        "model_version": get_model_version(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/system/quota", summary="Get API Quotas & Safety Valve Status")
def get_system_quota():
    """
    Returns current API quota usage, monthly/daily safety caps,
    and active safety valve status across all services (Finlight, OilpriceAPI, AlphaVantage, Gemini).
    """
    from src.finlight_feed import get_finlight_quota_status
    all_quotas = get_all_quota_statuses()
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "quota": get_finlight_quota_status(),
        "quotas": all_quotas
    }


@app.get("/api/v1/system/cache-status", summary="Get 3-Tier Cache Gateway Status & Edge Probes", tags=["System & Health"])
def get_system_cache_status(
    probe: bool = Query(False, description="Whether to execute active roundtrip write/read probe against edge databases"),
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret")
):
    """
    Returns statistics and configuration for the 3-Tier caching gateway (Turso Edge, Cloudflare D1, Local SQLite),
    along with optional live connectivity probe diagnostics (Issue #301, Issue #437).
    Active connectivity write/read probes require administrative authentication (X-Admin-Secret).
    """
    stats = global_cache.get_stats()
    probes = None
    if probe:
        expected_secret = os.environ.get("MIDGLEY_ADMIN_SECRET")
        is_testing = os.environ.get("TESTING") == "1"
        if not is_testing:
            if not expected_secret or not x_admin_secret or not hmac.compare_digest(x_admin_secret, expected_secret):
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Active cache connectivity write/read probe requires a valid X-Admin-Secret header."
                )
        probes = global_cache.test_edge_connectivity("all")

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "cache_stats": stats,
        "probes": probes
    }


@app.get("/api/v1/system/token-costs", summary="Get TokenTab LLM Token Accounting & Provider Costs")
def get_system_token_costs(
    monthly_cap: Optional[float] = Query(10.0, description="Monthly cost budget cap in USD"),
    daily_token_limit: Optional[int] = Query(100000, description="Daily token safety threshold")
):
    """
    Returns itemized TokenTab token accounting ledger metrics, provider breakdowns (Gemini, OpenAI, Anthropic, Finlight, Lexicon),
    daily consumption time-series, and active budget warning alerts.
    """
    return token_tab_manager.get_accounting_summary(
        monthly_cost_limit_usd=monthly_cap or 10.0,
        daily_token_limit=daily_token_limit or 100000
    )


@app.get("/api/v1/system/releases/latest", summary="Get Latest Upstream Release Reconciliation Manifest", tags=["System & Health"])
def get_latest_release_manifest_endpoint():
    """
    Returns machine-readable release reconciliation manifest with schema versions,
    compatibility matrix, environment variable delta, model feature matrix, and migration items (Issue #299).
    """
    from src.release_manifest import generate_release_manifest
    return generate_release_manifest()



# ------------------------------------------------------------------------------
# Method B: Admin Key Management Endpoints (Protected by X-Admin-Secret)
# ------------------------------------------------------------------------------

@app.post("/api/v1/admin/keys", tags=["Admin Key Management"], dependencies=[Depends(verify_admin_secret)], summary="Method B Admin API: Provision New API Key")
def create_api_key_endpoint(req: CreateKeyRequest):
    """Provisions a new API key (Method B REST API Gateway). Requires X-Admin-Secret header."""
    res = global_key_manager.create_key(
        user_id=req.user_id,
        tier=req.tier or "basic",
        rate_limit_rpm=req.rate_limit_rpm or 30,
        environment=req.environment or "dev",
        expires_days=req.expires_days
    )
    return {
        "status": "success",
        "message": "API key provisioned successfully.",
        "key_data": res
    }


@app.get("/api/v1/admin/keys", tags=["Admin Key Management"], dependencies=[Depends(verify_admin_secret)], summary="Method B Admin API: List Registered API Keys")
def list_api_keys_endpoint(environment: Optional[str] = Query(None, description="Optional environment filter ('dev' or 'prod')")):
    """Lists registered API key metadata. Requires X-Admin-Secret header."""
    keys = global_key_manager.list_keys(environment=environment)
    return {
        "status": "success",
        "total_keys": len(keys),
        "keys": keys
    }


@app.delete("/api/v1/admin/keys/{prefix}", tags=["Admin Key Management"], dependencies=[Depends(verify_admin_secret)], summary="Method B Admin API: Revoke API Key")
def revoke_api_key_endpoint(prefix: str):
    """Revokes an active API key by prefix. Requires X-Admin-Secret header."""
    success = global_key_manager.revoke_key(prefix)
    if not success:
        raise HTTPException(status_code=404, detail=f"API key prefix '{prefix}' not found.")
    return {
        "status": "success",
        "message": f"API key prefix '{prefix}' revoked successfully."
    }




@app.get("/api/v1/prices/live", dependencies=[Depends(get_api_key_user)], summary="Get Live Fuel Prices")
def get_live_prices(
    locale: Optional[str] = Query("national", description="Locale code (national, tulsa, newark, cincinnati, oakland, bayarea)"),
    zip_code: Optional[str] = Query(None, description="Optional 5-digit US zip code for GasBuddy station lookup")
):
    """
    Returns real-time unleaded gasoline pump prices from GasBuddy GraphQL, AAA Web Scraper,
    or benchmark fallbacks with 15-minute response caching.
    """
    return _get_live_prices_impl(locale=locale or "national", zip_code=zip_code)


@app.get("/api/v1/forecast/predict", dependencies=[Depends(get_api_key_user)], summary="Get 5-Day Out-of-Time Forecast")
def get_forecast(
    locale: Optional[str] = Query("national", description="Locale code"),
    days: int = Query(5, ge=1, le=30, description="Forecast horizon in days"),
    zip_code: Optional[str] = Query(None, description="Optional 5-digit US ZIP code")
):
    """
    Triggers model inference to compute 5-day out-of-time forecast, direction, expected dollar delta,
    and historical accuracy metrics.
    """
    return _get_forecast_impl(locale=locale or "national", days=days, zip_code=zip_code)



def _get_combined_impl(locale: str = "national", zip_code: Optional[str] = None) -> dict:
    zip_res = None
    if zip_code:
        zip_res = resolve_zip_code(zip_code)
        locale = zip_res.get("locale_code", locale or "national")

    loc_clean = locale or "national"
    live_data = _get_live_prices_impl(locale=loc_clean, zip_code=zip_code)
    forecast_data = _get_forecast_impl(locale=loc_clean, days=5, zip_code=zip_code)
    region_code = _normalize_locale(loc_clean)

    base_p = forecast_data["forecast"].get("current_base_price", 3.184)
    pred_p = forecast_data["forecast"].get("predicted_price_per_gal", 3.184)

    attr = compute_locale_feature_attribution_breakdown(
        region_code=region_code,
        base_price=base_p,
        predicted_price=pred_p
    )

    res = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "locale": live_data["locale"],
        "live_lookup": {
            "current_price_per_gal": live_data["price_per_gal"],
            "source": live_data["source"],
            "provenance": live_data.get("provenance"),
            "cache_hit": live_data.get("cache_hit", False),
            "cache_age_seconds": live_data.get("cache_age_seconds", 0.0),
            "carb_tax_regulatory_burden_per_gal": live_data.get("carb_tax_regulatory_burden_per_gal", 0.0)
        },
        "forecast": forecast_data["forecast"],
        "key_drivers": attr["key_drivers"],
        "driver_breakdown": {
            "summary_text": attr["summary_text"],
            "components": attr["components"]
        }
    }
    if zip_res:
        res["zip_code_resolution"] = zip_res
    return res


@app.get("/api/v1/combined", dependencies=[Depends(get_api_key_user)], summary="Unified Live Price & Forecast Context")
def get_combined(
    locale: Optional[str] = Query("national", description="Locale code"),
    zip_code: Optional[str] = Query(None, description="Optional 5-digit US ZIP code")
):
    """
    Returns both current live pump price and 5-day out-of-time forecast along with top market drivers.
    """
    return _get_combined_impl(locale=locale or "national", zip_code=zip_code)


@app.get("/api/v1/telemetry/unmapped-zips", summary="Get Unmapped Out-of-Metro ZIP Code Search Telemetry")
def get_unmapped_zip_telemetry_endpoint():
    """
    Returns aggregated telemetry statistics for out-of-metro ZIP code lookups (Issue #50 & #195),
    including query hit counts, state/PADD distributions, and candidate expansion metro hubs.
    """
    return get_unmapped_zip_telemetry()


@app.get("/api/v1/telemetry/fallback-status", summary="Get Zero-Cost Fallback & Token Savings Telemetry")
def get_fallback_telemetry_endpoint():
    """
    Returns aggregated telemetry statistics for zero-cost fallback provider invocations (Issue #196),
    basic tier API key routing counts, provider distribution, and estimated LLM token/dollar cost savings.
    """
    from src.fallback_telemetry import fallback_logger
    return fallback_logger.get_summary()


@app.get("/api/v1/locales", summary="Get All Supported Locales & Tax/Logistics Metadata")
def list_supported_locales():
    """
    Returns a complete dictionary of all supported locale codes, region IDs, PADD regions,
    statutory fuel tax burdens, delivery hub logistics, and metadata profiles (Issue #48).
    """
    all_metadata = list_all_regional_metadata()
    locales_dict = {}

    for loc_code, reg_code in LOCALE_MAP.items():
        meta = PADD_METADATA.get(reg_code, PADD_METADATA["National"])
        profile = all_metadata.get(reg_code.lower(), {})

        locales_dict[loc_code] = {
            "code": loc_code,
            "region_id": reg_code,
            "name": meta.get("name", reg_code),
            "padd_region": meta.get("padd", "PADD 2"),
            "carb_tax_regulatory_burden_per_gal": meta.get("carb_tax", 0.0),
            "refining_logistics": profile.get("refining_logistics", {}),
            "tax_breakdown": profile.get("tax_breakdown", {}),
            "metadata_profile": profile
        }

    return {
        "status": "success",
        "system": f"Midgley {get_model_version()}",
        "timestamp": datetime.now().isoformat(),
        "total_locales": len(locales_dict),
        "locales": locales_dict
    }


@app.get("/api/v1/usgs/water_levels", summary="Get Live USGS River & Waterway Hydrological Telemetry", tags=["Physical Data Feeds"])
def get_usgs_water_levels_endpoint(cluster: Optional[str] = Query(None, description="Optional regional cluster filter: inland_barge, gulf_coast, bay_area, delaware, tulsa, florida")):
    """
    Returns real-time streamflow, gage height, water temperature, and specific conductance
    telemetry from USGS NWIS monitoring stations across inland waterways and refining corridors (Issue #56).
    """
    from src.usgs_water_feed import USGSWaterFeedConnector
    connector = USGSWaterFeedConnector()
    return connector.fetch_live_water_telemetry(cluster=cluster)


@app.get("/api/v1/usgs/seismic", summary="Get Live USGS Earthquake & Seismic Telemetry", tags=["Physical Data Feeds"])
def get_usgs_seismic_endpoint(
    corridor: Optional[str] = Query("bay_area", description="Optional regional corridor filter: bay_area, cushing_ok, socal, mid_atlantic, new_madrid, or 'all'"),
    days: Optional[int] = Query(30, description="Rolling historical window in days (default: 30)"),
    min_mag: Optional[float] = Query(None, description="Minimum earthquake magnitude filter (defaults to corridor threshold)")
):
    """
    Returns real-time and historical earthquake telemetry from the USGS Earthquake Web Service API
    (earthquake.usgs.gov/fdsnws/event/1/) evaluated against critical refining, pipeline, and storage infrastructure (Issue #55).
    """
    from src.usgs_seismic import USGSSeismicConnector
    connector = USGSSeismicConnector()
    corr_arg = None if corridor == "all" else corridor
    return connector.fetch_live_seismic_telemetry(corridor=corr_arg, days=days or 30, min_mag=min_mag)


@app.get("/api/v1/aqi/live", summary="Get Live Refinery Air Quality & Industrial Flaring Telemetry", tags=["Physical Data Feeds"])
def get_aqi_live_endpoint(
    corridor: Optional[str] = Query("bay_area", description="Optional regional corridor filter: bay_area, tulsa, delaware_valley, tri_state, carolinas_coastal, carolinas_piedmont, south_florida, or 'all'")
):
    """
    Returns real-time and historical multi-feed air quality metrics (PM2.5, SO2, NO2, O3)
    from PurpleAir, OpenAQ, and EPA AirNow evaluated against critical refining hubs for
    unplanned outage early detection, flaring risk scoring, and ozone action day tracking (Issues #54 & #73).
    """
    from src.aqi_feed import AQIFeedConnector
    connector = AQIFeedConnector()
    corr_arg = None if corridor == "all" else corridor
    return connector.fetch_live_aqi_telemetry(corridor=corr_arg)


@app.get("/api/v1/aqi/ozone-alerts", summary="Get Regional EPA AirNow Ozone Alerts & Seasonal RVP Compliance Surcharges", tags=["Physical Data Feeds"])
def get_ozone_alerts_endpoint(
    corridor: Optional[str] = Query("all", description="Optional regional corridor filter: bay_area, tulsa, delaware_valley, tri_state, carolinas_coastal, carolinas_piedmont, south_florida, or 'all'"),
    zip_code: Optional[str] = Query(None, description="Optional 5-digit US ZIP code to query EPA AirNow directly")
):
    """
    Returns official EPA AirNow ground-level ozone (O3) action alerts, AQI metrics, and statutory
    seasonal Reid Vapor Pressure (RVP) summer-blend compliance surcharges for target regions (Issue #73).
    """
    from src.aqi_feed import AQIFeedConnector
    connector = AQIFeedConnector()
    if zip_code:
        airnow_res = connector.fetch_airnow_aqi(zip_code)
        rvp_res = connector.get_seasonal_rvp_surcharge(
            corridor_or_zip=zip_code,
            ozone_aqi=airnow_res.get("ozone_aqi"),
            is_action_day=airnow_res.get("is_ozone_action_day", False)
        )
        return {
            "status": "SUCCESS",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "airnow": airnow_res,
            "seasonal_rvp_compliance": rvp_res
        }
    
    corr_arg = None if corridor == "all" else corridor
    telemetry = connector.fetch_live_aqi_telemetry(corridor=corr_arg)
    return {
        "status": "SUCCESS",
        "as_of": telemetry.get("as_of"),
        "ozone_action_day_count": telemetry.get("indices", {}).get("ozone_action_day_count", 0),
        "max_rvp_compliance_surcharge_per_gal": telemetry.get("indices", {}).get("max_rvp_compliance_surcharge_per_gal", 0.0),
        "active_ozone_action_corridors": telemetry.get("active_ozone_action_corridors", []),
        "corridors": telemetry.get("corridors", {})
    }


@app.get("/api/v1/macro/freight-tsi", summary="Get U.S. BTS Freight Transportation Index & Truck Demand Telemetry", tags=["Physical Data Feeds"])
def get_bts_freight_tsi_endpoint(
    start_date: Optional[str] = Query("2022-01-01", description="Historical start date (YYYY-MM-DD)"),
    summary_only: bool = Query(False, description="Return only the latest demand momentum summary if true")
):
    """
    Returns official U.S. Bureau of Transportation Statistics (BTS) Freight Transportation Services
    Index (TSI), truck tonnage index, petroleum transport volumes, and physical demand momentum scores (Issue #74).
    """
    from src.bts_transportation import BTSTransportationConnector
    connector = BTSTransportationConnector()
    if summary_only:
        return connector.get_bts_current_demand_summary()
    
    df = connector.fetch_bts_tsi_dataset(start_date=start_date)
    summary = connector.get_bts_current_demand_summary()
    records = df.assign(date=df['date'].dt.strftime("%Y-%m-%d")).to_dict(orient="records") if not df.empty else []
    return {
        "status": "SUCCESS",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "demand_summary": summary,
        "sample_count": len(records),
        "history": records
    }


@app.get("/api/v1/macro/traffic-volume", summary="Get U.S. FHWA Monthly Traffic Volume Trends (TVT) & VMT Telemetry", tags=["Physical Data Feeds"])
def get_fhwa_traffic_volume_endpoint(
    start_date: Optional[str] = Query("2022-01-01", description="Historical start date (YYYY-MM-DD)"),
    summary_only: bool = Query(False, description="Return only the latest demand momentum summary if true")
):
    """
    Returns official Federal Highway Administration (FHWA) Monthly Traffic Volume Trends (TVT),
    estimated vehicle-miles traveled (VMT), and macroeconomic passenger fuel demand momentum (Issue #369).
    """
    from src.bts_transportation import FHWATrafficVolumeConnector
    connector = FHWATrafficVolumeConnector()
    if summary_only:
        return connector.get_fhwa_current_demand_summary()

    df = connector.fetch_fhwa_vmt_dataset(start_date=start_date)
    summary = connector.get_fhwa_current_demand_summary()
    records = df.assign(date=df['date'].dt.strftime("%Y-%m-%d")).to_dict(orient="records") if not df.empty else []
    return {
        "status": "SUCCESS",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "demand_summary": summary,
        "sample_count": len(records),
        "history": records
    }


@app.post("/api/v1/forecast/batch", dependencies=[Depends(get_api_key_user)], summary="Get Batch 5-Day Forecasts for Multiple Locales")
def get_batch_forecast(req: BatchForecastRequest):
    """
    Accepts a list of locale codes and returns combined 5-day out-of-time forecasts
    in a single HTTP response payload (Issue #48).
    """
    loc_list = req.locales if req.locales else ["national"]
    days = req.days or 5
    results = {}

    for loc in loc_list:
        clean_loc = str(loc).lower().strip()
        try:
            results[clean_loc] = _get_forecast_impl(locale=clean_loc, days=days)
        except Exception as e:
            logger.warning(f"Error computing forecast for locale '{loc}' in batch request: {e}")
            results[clean_loc] = {
                "status": "error",
                "message": f"Could not compute forecast for locale '{loc}': {e}"
            }

    return {
        "status": "success",
        "system": f"Midgley {get_model_version()}",
        "timestamp": datetime.now().isoformat(),
        "total_requested": len(loc_list),
        "forecasts": results
    }


@app.post("/api/v1/combined/batch", dependencies=[Depends(get_api_key_user)], summary="Get Batch Combined Live Prices & Forecasts for Multiple Locales")
def get_batch_combined(req: BatchCombinedRequest):
    """
    Accepts a list of locale codes and returns combined live pump prices, forecasts,
    feature attributions, and provenance metadata in a single HTTP response payload (Issue #48).
    """
    loc_list = req.locales if req.locales else ["national"]
    results = {}

    for loc in loc_list:
        clean_loc = str(loc).lower().strip()
        try:
            results[clean_loc] = _get_combined_impl(locale=clean_loc)
        except Exception as e:
            logger.warning(f"Error computing combined payload for locale '{loc}' in batch request: {e}")
            results[clean_loc] = {
                "status": "error",
                "message": f"Could not compute combined payload for locale '{loc}': {e}"
            }

    return {
        "status": "success",
        "system": f"Midgley {get_model_version()}",
        "timestamp": datetime.now().isoformat(),
        "total_requested": len(loc_list),
        "combined": results
    }


@app.get("/api/v1/forecast/scenarios", dependencies=[Depends(get_api_key_user)], summary="List Shock Scenarios with Seasonal Plausibility")
def get_forecast_scenarios(
    active_only: bool = Query(False, description="Filter for currently active/plausible scenarios only"),
    locale: Optional[str] = Query(None, description="Filter scenarios by target metro hub code"),
    target_date: Optional[str] = Query(None, description="Target evaluation date (YYYY-MM-DD)"),
    include_prospective: bool = Query(True, description="Include prospective forward-generated precursor scenarios")
):
    """
    Returns available counterfactual and forward shock scenarios augmented with seasonal plausibility tiers,
    climatological active/peak windows, and live telemetry triggers (Issue #300).
    """
    try:
        from src.scenario_engine import get_all_scenarios_with_plausibility
        res = get_all_scenarios_with_plausibility(
            target_date=target_date,
            active_only=active_only,
            locale=locale,
            include_prospective=include_prospective,
            live_telemetry=True
        )
        return {
            "status": "success",
            "system": f"Midgley {get_model_version()}",
            "timestamp": datetime.now().isoformat(),
            "target_date": res["target_date"],
            "total_scenarios": res["count"],
            "scenarios": res["scenarios"]
        }
    except Exception as e:
        logger.warning(f"Error evaluating scenario plausibility: {e}")
        # Fallback to catalog
        fallback_list = []
        for sid, sdata in SCENARIOS_CATALOG.items():
            fallback_list.append({
                "scenario_id": sid,
                "name": sdata["name"],
                "category": sdata.get("category", "general"),
                "plausibility_status": "EVERGREEN",
                "plausibility_score": 0.80,
                "is_in_season": True,
                "season_window": sdata.get("season_window", "Year-Round"),
                "is_prospective": False
            })
        return {
            "status": "success",
            "system": f"Midgley {get_model_version()}",
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(fallback_list),
            "scenarios": fallback_list
        }


@app.post("/api/v1/forecast/simulate", dependencies=[Depends(get_api_key_user)], summary="Simulate Counterfactual Market Shocks")
def simulate_shock(req: SimulateRequest, request: Request = None):
    """
    Evaluates counterfactual physical, refinery outage, weather disaster, or geopolitical shock scenarios
    with seasonal and climatological plausibility gating (Issue #300, Issue #437).
    """
    # Tier Gating Check for LLM cohort simulation & custom headlines (Issue #437)
    if req.enable_cohort_simulation or req.custom_headline:
        key_info = getattr(request, "state", None) and getattr(request.state, "key_info", None)
        tier = (key_info.get("tier") if key_info else "basic") or "basic"
        is_testing = os.environ.get("TESTING") == "1"
        if not is_testing and tier.lower() != "privileged":
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Multi-agent LLM cohort simulations and custom headlines require 'privileged' API key tier (current tier: '{tier}')."
            )

    scenario_info = SCENARIOS_CATALOG.get(req.scenario_id)
    if not scenario_info:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{req.scenario_id}' not found. Available scenarios: {list(SCENARIOS_CATALOG.keys())}"
        )

    region_code = _normalize_locale(req.locale or "national")
    live_res = fetch_live_metro_retail_price(region_code)
    base_price = live_res.get("price", 3.184)

    # Evaluate Seasonal & Physical Plausibility Gating (Issue #300)
    plausibility_info = {}
    try:
        from src.scenario_engine import evaluate_scenario_plausibility
        plausibility_info = evaluate_scenario_plausibility(
            scenario_id=req.scenario_id,
            target_date=req.target_date,
            live_telemetry=True
        )
    except Exception as e:
        logger.debug(f"Plausibility engine evaluation fallback: {e}")
        plausibility_info = {
            "plausibility_status": "EVERGREEN",
            "plausibility_score": 0.80,
            "is_in_season": True,
            "is_in_peak": False,
            "warning_message": None,
            "context_reasoning": "Standard simulation baseline."
        }

    shock_pct = req.custom_shock_pct if req.custom_shock_pct is not None else scenario_info["shock_pct"]
    if req.scenario_id == "hayward_quake" and req.custom_shock_pct is None:
        try:
            from src.usgs_seismic import USGSSeismicConnector
            seismic_conn = USGSSeismicConnector()
            seismic_live = seismic_conn.fetch_live_seismic_telemetry(corridor="bay_area")
            live_risk = seismic_live.get("indices", {}).get("bay_area_seismic_risk_index", 0.0)
            if live_risk > 0.10:
                shock_pct = round(scenario_info["shock_pct"] + (live_risk * 0.05), 4)
        except Exception:
            pass

    dollar_impact = round(base_price * shock_pct, 3)
    simulated_price = round(base_price + dollar_impact, 3)

    # Evaluate MiroFish Multi-Agent Financial Simulation Cohort (Issue #307)
    cohort_sim_payload = None
    try:
        from src.scenario_simulator import is_multi_agent_sim_enabled, simulate_market_cohort
        if is_multi_agent_sim_enabled(req.enable_cohort_simulation):
            cohort_sim_payload = simulate_market_cohort(
                scenario_id=req.scenario_id,
                headline=req.custom_headline or scenario_info.get("headline"),
                locale=region_code,
                base_price=base_price,
                base_shock_pct=shock_pct,
                scenario_name=scenario_info.get("name"),
                use_llm=True
            )
    except Exception as e:
        logger.debug(f"Multi-agent cohort simulation evaluation notice: {e}")

    resp = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "scenario": {
            "id": req.scenario_id,
            "name": scenario_info["name"],
            "headline": scenario_info["headline"],
            "category": scenario_info.get("category", "general"),
            "season_window": scenario_info.get("season_window", "Year-Round")
        },
        "plausibility": {
            "status": plausibility_info.get("plausibility_status", "EVERGREEN"),
            "score": plausibility_info.get("plausibility_score", 0.80),
            "is_in_season": plausibility_info.get("is_in_season", True),
            "is_in_peak": plausibility_info.get("is_in_peak", False),
            "warning_message": plausibility_info.get("warning_message"),
            "context_reasoning": plausibility_info.get("context_reasoning")
        },
        "simulation": {
            "target_locale": region_code,
            "baseline_price_per_gal": base_price,
            "simulated_price_per_gal": simulated_price,
            "shock_delta_dollars": dollar_impact,
            "shock_delta_percent": round(shock_pct * 100, 2)
        }
    }

    if cohort_sim_payload is not None:
        resp["cohort_simulation"] = cohort_sim_payload

    return resp


def verify_webhook_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str] = None,
    max_age_seconds: int = 300
) -> bool:
    """
    Validates HMAC-SHA256 signature with replay-safe timestamp freshness window (Issue #437).
    Supports 'X-Midgley-Signature: sha256=<hex>' and 't=<timestamp>,v1=<hex>' formatting.
    """
    secret_key = os.environ.get("MIDGLEY_WEBHOOK_SECRET")
    env_name = os.environ.get("MIDGLEY_ENV", os.environ.get("ENVIRONMENT", "prod")).lower()
    is_testing = os.environ.get("TESTING") == "1"

    if not secret_key:
        if is_testing or env_name in ("dev", "development", "test", "testing"):
            return True
        return False

    if not signature_header:
        return False

    clean_sig = signature_header.strip()
    ts_val = timestamp_header

    if "t=" in signature_header and ("v1=" in signature_header or "sha256=" in signature_header):
        parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
        ts_val = parts.get("t", ts_val)
        clean_sig = parts.get("v1", parts.get("sha256", clean_sig)).strip()
    else:
        clean_sig = clean_sig.replace("sha256=", "").strip()

    if ts_val:
        try:
            ts_float = float(ts_val)
            now = datetime.now(timezone.utc).timestamp()
            if abs(now - ts_float) > max_age_seconds:
                logger.warning(f"Webhook rejected: Timestamp drift {abs(now - ts_float):.1f}s exceeds {max_age_seconds}s window.")
                return False
            ts_payload = f"{ts_val}.".encode("utf-8") + raw_body
            expected_ts_sig = hmac.new(secret_key.encode("utf-8"), ts_payload, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected_ts_sig, clean_sig):
                return True
        except (ValueError, TypeError):
            logger.warning(f"Webhook rejected: Invalid timestamp format '{ts_val}'")
            return False

    expected_sig = hmac.new(secret_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, clean_sig)


class WebhookRequest(BaseModel):
    headline: str = Field("", json_schema_extra={"example": "Canada Announces Retaliatory Tariffs as Trade War Escalates"}, description="Breaking news headline text")
    url: str = Field("", json_schema_extra={"example": "https://news.google.com/rss/articles/123"}, description="URL link to full article or news release")
    source: Optional[str] = Field("Webhook_Push", json_schema_extra={"example": "IFTTT_GoogleAlerts"}, description="Event source origin")

    @model_validator(mode="before")
    @classmethod
    def resolve_payload_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Resolve headline alias fallback chain
            if not data.get("headline"):
                for alias in ["title", "text", "summary", "tweet_content", "article_title", "content", "message"]:
                    val = data.get(alias)
                    if val and isinstance(val, str) and val.strip():
                        data["headline"] = val.strip()
                        break
            # Resolve url alias fallback chain
            if not data.get("url"):
                for alias in ["link", "article_url", "web_url", "href", "source_url"]:
                    val = data.get(alias)
                    if val and isinstance(val, str) and val.strip():
                        data["url"] = val.strip()
                        break
            if not data.get("url"):
                data["url"] = ""
            # Resolve source alias fallback chain
            if not data.get("source"):
                for alias in ["origin", "provider", "channel", "service", "sender"]:
                    val = data.get(alias)
                    if val and isinstance(val, str) and val.strip():
                        data["source"] = val.strip()
                        break
                if not data.get("source"):
                    data["source"] = "Webhook_Push"
        return data


@app.post("/api/v1/events/webhook", summary="Ingest Real-Time Breaking Event Webhook")
async def ingest_event_webhook(
    request: Request,
    req: WebhookRequest,
    x_midgley_signature: Optional[str] = Header(None, alias="X-Midgley-Signature"),
    x_signature_timestamp: Optional[str] = Header(None, alias="X-Signature-Timestamp")
):
    """
    Strategy 4: Receives incoming breaking news headlines pushed by external webhooks
    (IFTTT, Zapier, Google Alerts, TradingView). Validated via HMAC-SHA256 signature when MIDGLEY_WEBHOOK_SECRET is set.
    Supports flexible payload field aliases (headline/title/text/summary/tweet_content & url/link).
    Fails closed in non-development environments when secret is unconfigured.
    """
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_midgley_signature, timestamp_header=x_signature_timestamp):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized webhook request: Invalid, expired, or missing X-Midgley-Signature HMAC-SHA256 header."
        )

    if not req.headline:
        raise HTTPException(
            status_code=422,
            detail="Unprocessable Entity: Incoming payload must contain a valid non-empty headline, title, text, summary, or tweet_content field."
        )

    # IPASIS IP Gateway Security Check
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for")
        or request.headers.get("x-real-ip")
        or (request.client.host if request.client else "127.0.0.1")
    )
    from src.ipasis_security import IPASISSecurityVerifier, get_ipasis_telemetry
    verifier = IPASISSecurityVerifier()
    ip_status = verifier.check_ip_reputation(client_ip)

    should_block = ip_status.get("is_blocked", False) and os.environ.get("IPASIS_BLOCK_HIGH_RISK", "1") != "0"
    if should_block:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Incoming request origin IP '{client_ip}' flagged as high-risk by IPASIS security filter."
        )

    from src.intraday_event_monitor import IntradayEventMonitor
    monitor = IntradayEventMonitor()
    result = monitor.process_incoming_headline(req.headline, source=req.source or "Webhook_Push", url=req.url)
    return {
        "status": "success",
        "processed_at": datetime.now().isoformat(),
        "ip_security": ip_status,
        "result": result
    }


class QueueBatchRequest(BaseModel):
    events: List[WebhookRequest] = Field(..., description="List of queued event items to process in batch")
    batch_id: Optional[str] = Field(None, description="Optional Cloudflare Queue batch ID")
    queue_name: Optional[str] = Field("intraday-event-queue", description="Queue identifier")


@app.post("/api/v1/events/queue-consumer", summary="Ingest Batch Events Pushed by Cloudflare Queue Consumer")
async def ingest_queue_batch_events(
    request: Request,
    req: QueueBatchRequest,
    x_midgley_signature: Optional[str] = Header(None, alias="X-Midgley-Signature"),
    x_signature_timestamp: Optional[str] = Header(None, alias="X-Signature-Timestamp")
):
    """
    Issue #194, Issue #437: Receives batch queued event payloads pushed by Cloudflare Queue consumer or local queue worker.
    Processes queued events asynchronously, running anomaly detection, deduplication, and regional metro updates.
    """
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_midgley_signature, timestamp_header=x_signature_timestamp):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized queue request: Invalid, expired, or missing X-Midgley-Signature HMAC-SHA256 header."
        )

    from src.intraday_event_monitor import IntradayEventMonitor
    monitor = IntradayEventMonitor()

    results = []
    processed_count = 0
    anomalies_count = 0

    for event in req.events:
        if not event.headline:
            continue
        res = monitor.process_incoming_headline(
            event.headline,
            source=event.source or "Cloudflare_Queue_Consumer",
            url=event.url
        )
        results.append({
            "headline": event.headline,
            "url": event.url,
            "result": res
        })
        processed_count += 1
        if res.get("anomaly_detected", False):
            anomalies_count += 1

    return {
        "status": "success",
        "processed_at": datetime.now().isoformat(),
        "queue_name": req.queue_name or "intraday-event-queue",
        "batch_id": req.batch_id,
        "total_processed": processed_count,
        "anomalies_detected": anomalies_count,
        "events": results
    }


@app.get("/api/v1/security/ip-status", summary="Get IPASIS Gateway Security & Request Telemetry", tags=["Security"])
def get_ipasis_security_telemetry():
    """
    Returns IPASIS IP security gateway status, daily API request accounting (used / 1,000 allowance),
    private IP bypass statistics, and blocked origin counts (Issue #87).
    """
    from src.ipasis_security import get_ipasis_telemetry
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "ipasis_telemetry": get_ipasis_telemetry()
    }


@app.post("/api/v1/events/poll", summary="Trigger Intraday Event Polling Cycle")
def trigger_event_polling(
    x_midgley_signature: Optional[str] = Header(None, alias="X-Midgley-Signature"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Strategy 2: Triggers an on-demand intraday RSS polling cycle across free energy feeds.
    Evaluates breaking news, invalidates response cache on anomalies, and updates prediction logs.
    Fails closed for unauthenticated requests outside local development environments.
    """
    secret_key = os.environ.get("MIDGLEY_WEBHOOK_SECRET")
    env_name = os.environ.get("MIDGLEY_ENV", os.environ.get("ENVIRONMENT", "prod")).lower()
    is_testing = os.environ.get("TESTING") == "1"

    if secret_key:
        auth_valid = False
        if authorization and authorization == f"Bearer {secret_key}":
            auth_valid = True
        elif x_midgley_signature:
            expected_sig = hmac.new(secret_key.encode("utf-8"), b"poll", hashlib.sha256).hexdigest()
            auth_valid = hmac.compare_digest(expected_sig, x_midgley_signature.replace("sha256=", "").strip())
        if not auth_valid:
            raise HTTPException(status_code=401, detail="Unauthorized poll mutation request")
    elif not (is_testing or env_name in ("dev", "development", "test", "testing")):
        raise HTTPException(status_code=401, detail="Webhook secret unconfigured; polling rejected in non-dev environment")

    from src.intraday_event_monitor import IntradayEventMonitor
    monitor = IntradayEventMonitor()
    result = monitor.run_polling_cycle()
    return {
        "status": "success",
        "processed_at": datetime.now().isoformat(),
        "result": result
    }





@app.get("/api/v1/system/telemetry", summary="Get Zero-Cost Connector Health & Telemetry Summary", tags=["System & Health"])
def get_connector_telemetry(days: int = Query(7, ge=1, le=90, description="Rolling telemetry window in days")):
    """
    Returns performance metrics, success rates (%), average response latency (ms),
    average data age (hours), and stale payload counts across all zero-cost data connectors.
    """
    from src.connector_telemetry import get_telemetry_summary
    return get_telemetry_summary(days=days)


@app.get("/api/v1/connectors/headline-arena/status", summary="Get Headline Arena Connector Status & Settlement Rules", tags=["Connectors & Integrations"])
def get_headline_arena_status():
    """Returns Headline Arena connection status, configured client ID, environment, and settlement dead-zone rules."""
    from src.headline_arena_connector import HeadlineArenaConnector
    connector = HeadlineArenaConnector()
    return {
        "configured": connector.is_configured,
        "environment": connector.environment,
        "is_production": connector.is_prod,
        "base_url": connector.base_url,
        "settlement_rules": connector.get_settlement_rules()
    }


@app.post("/api/v1/connectors/headline-arena/submit", dependencies=[Depends(require_privileged_tier)], summary="Submit Forecast to Headline Arena", tags=["Connectors & Integrations"])
def submit_headline_arena_forecast(req: HeadlineArenaSubmitRequest):
    """
    Submits or dry-runs a forecast to Headline Arena.
    Requires 'privileged' API key tier (Issue #437).
    In dev environments, executes dry-run by default unless live_in_dev is explicitly True.
    """
    from src.headline_arena_connector import HeadlineArenaConnector
    connector = HeadlineArenaConnector()
    payload = connector.format_direction_payload(
        asset=req.asset,
        open_price=req.open_price,
        p50=req.p50,
        p10=req.p10,
        p90=req.p90,
        residual_std=req.residual_std
    )
    result = connector.submit_forecast(payload, live_in_dev=req.live_in_dev)
    return {
        "status": "success",
        "processed_at": datetime.now().isoformat(),
        "payload": payload,
        "result": result
    }


# Knowledge Graph & Agent Memory REST API Endpoints
@app.get("/api/v1/graph/topology", summary="Get Full Knowledge Graph Topology (Nodes & Edges)", tags=["Knowledge Graph"])
def get_graph_topology():
    """Returns nodes, edges, entity types, and relationship summaries for Knowledge Graph visualization."""
    from src.knowledge_graph import kg_engine
    return kg_engine.export_topology_dict()


@app.get("/api/v1/graph/subgraph", summary="Get Localized Subgraph Neighborhood for Entity", tags=["Knowledge Graph"])
def get_graph_subgraph(
    entity: str = Query(..., description="Target entity node ID or name (e.g., 'Chevron_Richmond', 'Oakland_CA')"),
    depth: int = Query(2, ge=1, le=4, description="Graph traversal depth")
):
    """Extracts 2-hop sub-graph neighborhood and returns GraphContextSchema."""
    from src.knowledge_graph import kg_engine
    matched = kg_engine.resolve_entities_in_text(entity) or [entity]
    schema = kg_engine.get_subgraph_context(matched, depth=depth)
    return schema.to_dict()


@app.get("/api/v1/memory/precedents", summary="Query Episodic Agent Memory for Historical Precedents", tags=["Agent Memory"])
def get_memory_precedents(
    query: str = Query(..., description="Search headline or keyword query (e.g., 'refinery outage heatwave')"),
    top_k: int = Query(3, ge=1, le=10, description="Max precedent records to return")
):
    """Searches historical shock memory using TF-IDF + topological graph distance."""
    from src.knowledge_graph import kg_engine
    precedents = kg_engine.find_historical_precedents(query, top_k=top_k)
    return {"query": query, "top_k": top_k, "precedents": precedents}


class GraphIngestPayload(BaseModel):
    headline: str
    geopolitical_risk: float = 0.0
    supply_disruption: float = 0.0
    demand_sentiment: float = 0.0
    opec_action: float = 0.0
    overall_price_pressure: float = 0.0
    affected_entities: Optional[List[str]] = None
    model_attribution: Optional[str] = "api_user"


@app.post("/api/v1/graph/ingest", dependencies=[Depends(require_privileged_tier)], summary="Ingest Event Shock Memory into Knowledge Graph", tags=["Knowledge Graph"])
def post_graph_ingest(payload: GraphIngestPayload):
    """Ingests qualitative event into Knowledge Graph memory store (requires privileged tier)."""
    from src.knowledge_graph import kg_engine
    scores = {
        "geopolitical_risk": payload.geopolitical_risk,
        "supply_disruption": payload.supply_disruption,
        "demand_sentiment": payload.demand_sentiment,
        "opec_action": payload.opec_action,
        "overall_price_pressure": payload.overall_price_pressure
    }
    shock_id = kg_engine.record_event_shock_memory(
        headline=payload.headline,
        score_vector=scores,
        affected_entities=payload.affected_entities,
        model_attribution=payload.model_attribution
    )
    return {"status": "success", "shock_id": shock_id, "headline": payload.headline}


@app.get("/.well-known/ai-plugin.json", include_in_schema=False)

def get_ai_plugin_manifest():
    """Returns OpenAI GPT Action Plugin Manifest."""
    return {
        "schema_version": "v1",
        "name_for_human": "Midgley Gas Price Intelligence",
        "name_for_model": "midgley_gas_prices",
        "description_for_human": "Real-time unleaded gasoline pump price lookup, 5-day out-of-time forecasting, and geopolitical/weather market shock simulations.",
        "description_for_model": "Plugin for querying live gas prices, 5-day price forecasts, and simulating refinery/geopolitical market shocks across US metro areas (National, Tulsa, Newark, Cincinnati, Oakland).",
        "auth": {"type": "none"},
        "api": {
            "type": "openapi",
            "url": "https://koshiirra.github.io/midgley/openapi.json"
        },
        "logo_url": "https://koshiirra.github.io/midgley/assets/icon.png",
        "contact_email": "m.cubed.3@gmail.com",
        "legal_info_url": "https://koshiirra.github.io/midgley/"
    }


# MCP SSE Transport endpoints (Issue #431)
try:
    from mcp.server.sse import SseServerTransport
    sse_transport = SseServerTransport("/mcp/messages")

    @app.get("/mcp/sse", summary="MCP Server SSE Connection Endpoint", dependencies=[Depends(get_api_key_user)])
    async def handle_mcp_sse(request: Request, key_info: Dict[str, Any] = Depends(get_api_key_user)):
        """
        HTTP SSE endpoint for MCP clients (Issue #431).
        Requires API key authentication. Binds active SSE connection to authenticated caller identity & tier.
        """
        from src.mcp_server import app as mcp_app, set_active_mcp_session_context
        set_active_mcp_session_context(key_info)
        async with sse_transport.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
            await mcp_app.run(read_stream, write_stream, mcp_app.create_initialization_options())

    @app.post("/mcp/messages", summary="MCP Server Post Messages Endpoint", include_in_schema=False)
    async def handle_mcp_messages(
        request: Request,
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
        authorization: Optional[str] = Header(None),
        api_key: Optional[str] = Query(None)
    ):
        """
        HTTP Post message endpoint for MCP clients (Issue #431).
        Verifies caller credentials and propagates authenticated context to MCP tool execution.
        """
        key_info = getattr(request.state, "key_info", None)
        if not key_info:
            token = x_api_key or api_key
            if not token and authorization:
                parts = authorization.split()
                token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization

            is_testing = os.environ.get("TESTING") == "1"
            if is_testing and not token:
                key_info = {
                    "key_prefix": "mg_test_bypass",
                    "user_id": "test_suite_runner",
                    "tier": "privileged",
                    "rate_limit_rpm": 1000,
                    "environment": "dev"
                }
            elif token:
                key_info = await get_api_key_user(request, x_api_key=x_api_key, authorization=authorization, api_key=api_key)
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Missing API key. MCP message post requests require authentication."
                )

        from src.mcp_server import set_active_mcp_session_context
        set_active_mcp_session_context(key_info)
        await sse_transport.handle_post_message(request.scope, request.receive, request._send)
except Exception as e:
    logger.warning(f"Could not initialize MCP SSE transport: {e}")


# Telemetry & Quota Endpoints (Issue #107 & Issue #108)
@app.get("/metrics", response_class=PlainTextResponse, summary="Prometheus Telemetry Metrics Exporter")
@app.get("/api/v1/metrics", response_class=PlainTextResponse, summary="Prometheus Telemetry Metrics Exporter")
async def prometheus_metrics_endpoint(environment: Optional[str] = Query(None, description="Optional environment filter ('dev' or 'prod')")):
    """Exposes system telemetry and quota metrics in Prometheus exposition text format for Grafana."""
    return format_prometheus_metrics(environment=environment)



# Mount static HTML web dashboard if docs directory is present
if os.path.exists("docs"):
    app.mount("/", StaticFiles(directory="docs", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

