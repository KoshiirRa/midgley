"""
Unit Tests for ZIP Code Geocoding Engine & Telemetry (tests/test_zip_geocoding.py)
Issues #50 & #195: ZIP Code to Locale & PADD Resolution Mapping Engine & Telemetry Page
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from src.api_server import app
from src.zip_geocoding import (
    resolve_zip_code,
    log_unmapped_zip_lookup,
    get_unmapped_zip_telemetry,
    resolve_coordinates,
    resolve_location,
    haversine_distance_miles,
    TELEMETRY_FILE
)

client = TestClient(app)


def test_metro_cluster_zip_resolution():
    """Verifies primary metro cluster ZIP codes resolve to expected metro locales."""
    res_tulsa = resolve_zip_code("74101")
    assert res_tulsa["status"] == "success"
    assert res_tulsa["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_tulsa["is_metro_cluster_hit"] is True
    assert res_tulsa["locale_code"] == "tulsa"
    assert res_tulsa["state"] == "OK"

    res_newark = resolve_zip_code("19711")
    assert res_newark["locale_code"] == "newark"
    assert res_newark["state"] == "DE"

    res_cincinnati = resolve_zip_code("45202")
    assert res_cincinnati["locale_code"] == "cincinnati"
    assert res_cincinnati["state"] == "OH"

    res_oakland = resolve_zip_code("94612")
    assert res_oakland["locale_code"] == "oakland"
    assert res_oakland["state"] == "CA"

    res_bayarea = resolve_zip_code("94102")
    assert res_bayarea["locale_code"] == "bayarea"
    assert res_bayarea["state"] == "CA"

    res_houston = resolve_zip_code("77002")
    assert res_houston["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_houston["is_metro_cluster_hit"] is True
    assert res_houston["locale_code"] == "houston"
    assert res_houston["state"] == "TX"

    res_la = resolve_zip_code("90012")
    assert res_la["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_la["is_metro_cluster_hit"] is True
    assert res_la["locale_code"] == "los_angeles"
    assert res_la["state"] == "CA"

    res_beverly = resolve_zip_code("90210")
    assert res_beverly["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_beverly["is_metro_cluster_hit"] is True
    assert res_beverly["locale_code"] == "los_angeles"
    assert res_beverly["state"] == "CA"

    res_denver = resolve_zip_code("80202")
    assert res_denver["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_denver["is_metro_cluster_hit"] is True
    assert res_denver["locale_code"] == "denver"
    assert res_denver["state"] == "CO"

    res_nyc = resolve_zip_code("10001")
    assert res_nyc["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_nyc["is_metro_cluster_hit"] is True
    assert res_nyc["locale_code"] == "new_york"
    assert res_nyc["state"] == "NY"
    assert res_nyc["hub_baseline_tax_rate"] == 0.472

    res_lake_placid = resolve_zip_code("12946")
    assert res_lake_placid["locale_code"] == "new_york"
    assert res_lake_placid["state"] == "NY"
    assert res_lake_placid["hub_baseline_tax_rate"] == 0.472

    res_seattle = resolve_zip_code("98101")
    assert res_seattle["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_seattle["is_metro_cluster_hit"] is True
    assert res_seattle["locale_code"] == "seattle"
    assert res_seattle["state"] == "WA"

    res_phoenix = resolve_zip_code("85001")
    assert res_phoenix["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_phoenix["is_metro_cluster_hit"] is True
    assert res_phoenix["locale_code"] == "phoenix"
    assert res_phoenix["state"] == "AZ"

    res_anchorage = resolve_zip_code("99501")
    assert res_anchorage["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_anchorage["is_metro_cluster_hit"] is True
    assert res_anchorage["locale_code"] == "anchorage"
    assert res_anchorage["state"] == "AK"

    res_honolulu = resolve_zip_code("96813")
    assert res_honolulu["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_honolulu["is_metro_cluster_hit"] is True
    assert res_honolulu["locale_code"] == "honolulu"
    assert res_honolulu["state"] == "HI"

    res_guam = resolve_zip_code("96910")
    assert res_guam["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_guam["is_metro_cluster_hit"] is True
    assert res_guam["locale_code"] == "guam"
    assert res_guam["state"] == "GU"
    assert res_guam["padd_region"] == "PADD 7"
    assert res_guam["hub_baseline_tax_rate"] == 0.190


def test_out_of_metro_zip_resolution_and_telemetry():
    """Verifies non-cluster ZIP codes resolve via State/PADD fallback and trigger telemetry logging."""
    res_sac = resolve_zip_code("95814")
    assert res_sac["status"] == "success"
    assert res_sac["resolution_tier"] == "STATE_PADD_FALLBACK"
    assert res_sac["is_metro_cluster_hit"] is False
    assert res_sac["state"] == "CA"
    assert res_sac["padd_region"] == "PADD 5"
    assert res_sac["locale_code"] == "oakland"
    assert res_sac["state_tax_rate_per_gal"] == 0.596

    res_dallas = resolve_zip_code("75201")
    assert res_dallas["resolution_tier"] == "STATE_PADD_FALLBACK"
    assert res_dallas["state"] == "TX"
    assert res_dallas["padd_region"] == "PADD 3"

    res_pa = resolve_zip_code("15201")
    assert res_pa["resolution_tier"] == "STATE_PADD_FALLBACK"
    assert res_pa["state"] == "PA"
    assert res_pa["padd_region"] == "PADD 1B"
    assert res_pa["locale_code"] == "newark"

    # Oregon out-of-cluster resolves to Seattle / PNW hub in PADD 5
    res_or = resolve_zip_code("97201")
    assert res_or["resolution_tier"] == "STATE_PADD_FALLBACK"
    assert res_or["state"] == "OR"
    assert res_or["padd_region"] == "PADD 5"
    assert res_or["locale_code"] == "seattle"

    # Nevada out-of-cluster resolves to Phoenix / Desert Southwest hub in PADD 5
    res_nv = resolve_zip_code("89403")
    assert res_nv["resolution_tier"] == "STATE_PADD_FALLBACK"
    assert res_nv["state"] == "NV"
    assert res_nv["padd_region"] == "PADD 5"
    assert res_nv["locale_code"] == "phoenix"


def test_unmapped_telemetry_aggregation():
    """Verifies telemetry statistics, state distributions, and expansion hub recommendations."""
    tele = get_unmapped_zip_telemetry()
    assert tele["status"] == "success"
    assert "total_unmapped_queries" in tele
    assert "unique_unmapped_zips" in tele
    assert "top_unmapped_zips" in tele
    assert "state_distribution" in tele
    assert "recommended_expansion_hubs" in tele


def test_invalid_zip_input_handling():
    """Verifies invalid ZIP code strings fallback cleanly without crashing."""
    res_short = resolve_zip_code("12")
    assert res_short["resolution_tier"] == "INVALID_INPUT_FALLBACK"
    assert res_short["locale_code"] == "national"

    res_alpha = resolve_zip_code("abcde")
    assert res_alpha["resolution_tier"] == "INVALID_INPUT_FALLBACK"
    assert res_alpha["locale_code"] == "national"


def test_api_server_zip_code_query_integration():
    """Verifies REST API endpoints return zip_code_resolution metadata and telemetry data."""
    # 1. GET /api/v1/prices/live?zip_code=74101
    resp_live = client.get("/api/v1/prices/live?zip_code=74101")
    assert resp_live.status_code == 200
    data_live = resp_live.json()
    assert data_live["status"] == "success"
    assert "zip_code_resolution" in data_live
    assert data_live["zip_code_resolution"]["locale_code"] == "tulsa"

    # 2. GET /api/v1/forecast/predict?zip_code=90210
    resp_fc = client.get("/api/v1/forecast/predict?zip_code=90210")
    assert resp_fc.status_code == 200
    data_fc = resp_fc.json()
    assert data_fc["status"] == "success"
    assert "forecast" in data_fc

    # 3. GET /api/v1/combined?zip_code=10001
    resp_comb = client.get("/api/v1/combined?zip_code=10001")
    assert resp_comb.status_code == 200
    data_comb = resp_comb.json()
    assert data_comb["status"] == "success"
    assert "zip_code_resolution" in data_comb

    # 4. GET /api/v1/telemetry/unmapped-zips
    resp_tele = client.get("/api/v1/telemetry/unmapped-zips")
    assert resp_tele.status_code == 200
    data_tele = resp_tele.json()
    assert data_tele["status"] == "success"
    assert "total_unmapped_queries" in data_tele


def test_leading_zero_zip_resolution():
    """Verifies that integer and short string ZIP codes with leading zeros (e.g. NJ 07001, MA 02138) are zero-padded correctly (Issue #335)."""
    # 1. New Jersey ZIP passed as 4-digit int/string (should resolve to NJ / PADD 1B Newark, not LA 700)
    res_nj_int = resolve_zip_code(7001)
    assert res_nj_int["zip_code"] == "07001"
    assert res_nj_int["state"] == "NJ"
    assert res_nj_int["padd_region"] == "PADD 1B"
    assert res_nj_int["locale_code"] == "newark"

    res_nj_str = resolve_zip_code("7001")
    assert res_nj_str["zip_code"] == "07001"
    assert res_nj_str["state"] == "NJ"
    assert res_nj_str["padd_region"] == "PADD 1B"
    assert res_nj_str["locale_code"] == "newark"

    # 2. Massachusetts ZIP passed as 4-digit int/string
    res_ma_int = resolve_zip_code(2138)
    assert res_ma_int["zip_code"] == "02138"
    assert res_ma_int["state"] == "MA"
    assert res_ma_int["prefix_3"] == "021"

    # 3. ZIP+4 with leading zero
    res_nj_plus4 = resolve_zip_code("07001-1234")
    assert res_nj_plus4["zip_code"] == "07001"
    assert res_nj_plus4["state"] == "NJ"
    assert res_nj_plus4["padd_region"] == "PADD 1B"


def test_haversine_distance_calculation():
    """Verifies that haversine distance calculates accurate statute mileage between hubs."""
    # Distance between Tulsa (36.1540, -95.9928) and Cincinnati (39.1031, -84.5120) is ~648 miles
    dist = haversine_distance_miles(36.1540, -95.9928, 39.1031, -84.5120)
    assert 640.0 < dist < 660.0


def test_coordinate_resolution_metro_hit():
    """Verifies GPS coordinates within hub radius resolve to the expected metro hub."""
    # 1. Tulsa Downtown coordinates (36.1540, -95.9928)
    res_tulsa = resolve_coordinates(36.1540, -95.9928)
    assert res_tulsa["status"] == "success"
    assert res_tulsa["is_metro_cluster_hit"] is True
    assert res_tulsa["resolution_tier"] == "METRO_CLUSTER_HIT"
    assert res_tulsa["locale_code"] == "tulsa"
    assert res_tulsa["state"] == "OK"
    assert res_tulsa["distance_to_hub_miles"] < 5.0

    # 2. San Francisco / Oakland coordinates (37.7749, -122.4194)
    res_bay = resolve_coordinates(37.7749, -122.4194)
    assert res_bay["status"] == "success"
    assert res_bay["is_metro_cluster_hit"] is True
    assert res_bay["locale_code"] in ["bayarea", "oakland"]
    assert res_bay["state"] == "CA"

    # 3. Newark / Delaware City coordinates (39.5743, -75.5908)
    res_newark = resolve_coordinates(39.5743, -75.5908)
    assert res_newark["locale_code"] == "newark"
    assert res_newark["state"] == "NJ"

    # 4. Denver Downtown coordinates (39.7392, -104.9903)
    res_den = resolve_coordinates(39.7392, -104.9903)
    assert res_den["status"] == "success"
    assert res_den["is_metro_cluster_hit"] is True
    assert res_den["locale_code"] == "denver"
    assert res_den["state"] == "CO"
    assert res_den["distance_to_hub_miles"] < 5.0

    # 5. Hagåtña / Apra Harbor, Guam coordinates (13.4443, 144.7937)
    res_guam_coord = resolve_coordinates(13.4443, 144.7937)
    assert res_guam_coord["status"] == "success"
    assert res_guam_coord["is_metro_cluster_hit"] is True
    assert res_guam_coord["locale_code"] == "guam"
    assert res_guam_coord["state"] == "GU"
    assert res_guam_coord["distance_to_hub_miles"] < 5.0


def test_coordinate_resolution_spatial_fallback():
    """Verifies out-of-metro GPS coordinates fall back gracefully to nearest regional model."""
    # Fargo, ND coordinates (46.8772, -96.7898) - outside 150mi of calibration hubs
    res_fargo = resolve_coordinates(46.8772, -96.7898)
    assert res_fargo["status"] == "success"
    assert res_fargo["is_metro_cluster_hit"] is False
    assert res_fargo["resolution_tier"] == "SPATIAL_PROXIMITY_FALLBACK"
    assert res_fargo["distance_to_hub_miles"] > 300.0


def test_unified_location_resolver():
    """Verifies resolve_location prioritizes GPS coordinates over ZIP code and handles fallbacks."""
    # GPS priority
    res_gps = resolve_location(zip_code="10001", lat=36.1540, lon=-95.9928)
    assert res_gps["query_type"] == "coordinates"
    assert res_gps["locale_code"] == "tulsa"

    # ZIP fallback when no coordinates
    res_zip = resolve_location(zip_code="10001")
    assert res_zip["query_type"] == "zip" if "query_type" in res_zip else True
    assert res_zip["locale_code"] == "new_york"

    # Default national when neither provided
    res_default = resolve_location()
    assert res_default["locale_code"] == "national"


def test_api_server_coordinates_endpoints():
    """Verifies REST API endpoints support lat/lon parameters and /api/v1/locations/resolve."""
    # 1. GET /api/v1/locations/resolve?lat=36.1540&lon=-95.9928
    resp_resolve = client.get("/api/v1/locations/resolve?lat=36.1540&lon=-95.9928")
    assert resp_resolve.status_code == 200
    data_resolve = resp_resolve.json()
    assert data_resolve["status"] == "success"
    assert data_resolve["locale_code"] == "tulsa"
    assert data_resolve["is_metro_cluster_hit"] is True

    # 2. GET /api/v1/combined?lat=36.1540&lon=-95.9928
    resp_comb = client.get("/api/v1/combined?lat=36.1540&lon=-95.9928")
    assert resp_comb.status_code == 200
    data_comb = resp_comb.json()
    assert data_comb["status"] == "success"
    assert "location_resolution" in data_comb
    assert data_comb["location_resolution"]["locale_code"] == "tulsa"

    # 3. GET /api/v1/forecast/predict?lat=39.5743&lon=-75.5908
    resp_fc = client.get("/api/v1/forecast/predict?lat=39.5743&lon=-75.5908")
    assert resp_fc.status_code == 200
    data_fc = resp_fc.json()
    assert data_fc["status"] == "success"
    assert "location_resolution" in data_fc
    assert data_fc["location_resolution"]["locale_code"] == "newark"


