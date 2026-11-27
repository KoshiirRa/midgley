"""Location resolution and telemetry routes (Issue #562)."""

from typing import Optional
from fastapi import APIRouter, Query

from src.zip_geocoding import get_unmapped_zip_telemetry, resolve_location

router = APIRouter(tags=["Location & Telemetry"])


@router.get("/api/v1/locations/resolve", summary="Resolve GPS Coordinates or ZIP Code to Metro Refining Hub")
def resolve_location_endpoint(
    lat: Optional[float] = Query(None, description="Latitude coordinate (e.g. 36.1540)"),
    lon: Optional[float] = Query(None, description="Longitude coordinate (e.g. -95.9928)"),
    zip_code: Optional[str] = Query(None, description="Optional 5-digit US ZIP code"),
):
    """
    Resolves arbitrary GPS coordinates or a 5-digit US ZIP code to its nearest
    Midgley metropolitan refining hub, PADD sub-region, and statutory motor fuel tax structure.
    """
    return resolve_location(zip_code=zip_code, lat=lat, lon=lon)


@router.get("/api/v1/telemetry/unmapped-zips", summary="Get Unmapped Out-of-Metro ZIP Code Search Telemetry")
def get_unmapped_zip_telemetry_endpoint():
    """
    Returns aggregated telemetry statistics for out-of-metro ZIP code lookups (Issue #50 & #195),
    including query hit counts, state/PADD distributions, and candidate expansion metro hubs.
    """
    return get_unmapped_zip_telemetry()


@router.get("/api/v1/telemetry/fallback-status", summary="Get Zero-Cost Fallback & Token Savings Telemetry")
def get_fallback_telemetry_endpoint():
    """
    Returns aggregated telemetry statistics for zero-cost fallback provider invocations (Issue #196),
    basic tier API key routing counts, provider distribution, and estimated LLM token/dollar cost savings.
    """
    from src.fallback_telemetry import fallback_logger

    return fallback_logger.get_summary()
