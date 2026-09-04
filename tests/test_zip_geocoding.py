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
