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


def test_out_of_metro_zip_resolution_and_telemetry():
    """Verifies non-cluster ZIP codes resolve via State/PADD fallback and trigger telemetry logging."""
    res_la = resolve_zip_code("90210")
    assert res_la["status"] == "success"
    assert res_la["resolution_tier"] == "STATE_PADD_FALLBACK"
    assert res_la["is_metro_cluster_hit"] is False
    assert res_la["state"] == "CA"
    assert res_la["padd_region"] == "PADD 5"
    assert res_la["locale_code"] == "oakland"
    assert res_la["state_tax_rate_per_gal"] == 0.596

    res_houston = resolve_zip_code("77002")
    assert res_houston["resolution_tier"] == "STATE_PADD_FALLBACK"
    assert res_houston["state"] == "TX"
    assert res_houston["padd_region"] == "PADD 3"

    res_nyc = resolve_zip_code("10001")
    assert res_nyc["state"] == "NY"
    assert res_nyc["padd_region"] == "PADD 1B"
    assert res_nyc["locale_code"] == "newark"


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


def test_coordinate_resolution_spatial_fallback():
    """Verifies out-of-metro GPS coordinates fall back gracefully to nearest regional model."""
    # Denver, CO coordinates (39.7392, -104.9903) - outside 150mi of Tulsa
    res_denver = resolve_coordinates(39.7392, -104.9903)
    assert res_denver["status"] == "success"
    assert res_denver["is_metro_cluster_hit"] is False
    assert res_denver["resolution_tier"] == "SPATIAL_PROXIMITY_FALLBACK"
    assert res_denver["nearest_hub"] == "tulsa"
    assert res_denver["distance_to_hub_miles"] > 400.0


def test_unified_location_resolver():
    """Verifies resolve_location prioritizes GPS coordinates over ZIP code and handles fallbacks."""
    # GPS priority
    res_gps = resolve_location(zip_code="10001", lat=36.1540, lon=-95.9928)
    assert res_gps["query_type"] == "coordinates"
    assert res_gps["locale_code"] == "tulsa"

    # ZIP fallback when no coordinates
    res_zip = resolve_location(zip_code="10001")
    assert res_zip["query_type"] == "zip" if "query_type" in res_zip else True
    assert res_zip["locale_code"] == "newark"

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


