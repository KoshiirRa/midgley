"""Motor fuel tax lookup and 50-state schedule routes (Issues #562, #623)."""

from typing import Optional
from fastapi import APIRouter, Query

from src.zip_geocoding import compute_tax_breakdown, load_local_tax_schedules, resolve_location

router = APIRouter(tags=["Fuel Tax Schedules"])


@router.get("/api/v1/tax/lookup", summary="Itemized Motor Fuel Tax Lookup by ZIP Code or GPS Coordinates")
def tax_lookup_endpoint(
    zip: Optional[str] = Query(None, description="5-digit US ZIP code (e.g. 60601)"),
    lat: Optional[float] = Query(None, description="Latitude coordinate (e.g. 41.8781)"),
    lon: Optional[float] = Query(None, description="Longitude coordinate (e.g. -87.6298)"),
    target_date: Optional[str] = Query(None, description="Optional target date (YYYY-MM-DD) for point-in-time tax holidays"),
    as_of_date: Optional[str] = Query(None, description="Optional forecast origin date (YYYY-MM-DD)"),
):
    """
    Returns an itemized motor fuel tax breakdown (federal excise, point-in-time state excise,
    environmental/UST fees, county/municipal LOFT adders, and estimated sales tax) for any US locale (Issue #623).
    """
    loc_res = resolve_location(zip_code=zip, lat=lat, lon=lon)
    state_code = loc_res.get("state", "US")
    breakdown = compute_tax_breakdown(
        state_code=state_code,
        zip_code=zip,
        target_date=target_date,
        as_of_date=as_of_date,
    )
    return {
        "status": "success",
        "locale": loc_res.get("location_name") or loc_res.get("name") or state_code,
        "state": state_code,
        "zip_code": loc_res.get("zip_code") or zip,
        "padd_region": loc_res.get("padd_region"),
        "tax_breakdown": breakdown,
    }


@router.get("/api/v1/tax/schedule", summary="Full 50-State + DC Motor Fuel Tax Schedule Matrix")
def tax_schedule_endpoint():
    """
    Returns the complete 50-state + DC motor fuel tax schedule (incorporating IFTA quarterly
    revisions when available) alongside local option fuel tax (LOFT) schedule metadata (Issue #623).
    """
    from src.state_open_data import IFTAFuelTaxConnector

    connector = IFTAFuelTaxConnector()
    matrix = connector.fetch_quarterly_matrix()
    loft = load_local_tax_schedules()
    matrix["local_option_fuel_taxes"] = loft.get("local_option_fuel_taxes", {})
    return matrix
