"""
Unit Tests for Locales Metadata & Batch Forecast REST Endpoints (tests/test_api_batch_locales.py)
Issue #48: Add GET /locales Metadata Endpoint & POST /forecast/batch Endpoint
"""

import os
import pytest
os.environ["TESTING"] = "1"
os.environ["MIDGLEY_ENV"] = "dev"
from fastapi.testclient import TestClient
from src.api_server import app

client = TestClient(app)



@pytest.fixture(autouse=True)
def setup_testing_env(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("MIDGLEY_ENV", "dev")


def test_get_locales_endpoint():
    """Verifies GET /api/v1/locales returns supported locales and metadata profiles."""
    resp = client.get("/api/v1/locales")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "total_locales" in data
    assert data["total_locales"] >= 8
    assert "locales" in data
    locales = data["locales"]
    assert "tulsa" in locales
    assert "oakland" in locales
    assert "newark" in locales

    tulsa = locales["tulsa"]
    assert tulsa["code"] == "tulsa"
    assert tulsa["region_id"] == "Tulsa_OK"
    assert "padd_region" in tulsa
    assert "carb_tax_regulatory_burden_per_gal" in tulsa
    assert "metadata_profile" in tulsa


def test_post_forecast_batch_endpoint():
    """Verifies POST /api/v1/forecast/batch returns forecasts for multiple requested locales."""
    payload = {
        "locales": ["tulsa", "oakland", "cincinnati"],
        "days": 5
    }
    resp = client.post("/api/v1/forecast/batch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_requested"] == 3
    assert "forecasts" in data
    forecasts = data["forecasts"]
    assert "tulsa" in forecasts
    assert "oakland" in forecasts
    assert "cincinnati" in forecasts

    tul_fc = forecasts["tulsa"]
    assert tul_fc["status"] == "success"
    assert "forecast" in tul_fc
    assert tul_fc["forecast"]["forecast_horizon_days"] == 5
    assert "predicted_price_per_gal" in tul_fc["forecast"]


def test_post_combined_batch_endpoint():
    """Verifies POST /api/v1/combined/batch returns live prices and forecasts for requested locales."""
    payload = {
        "locales": ["tulsa", "newark", "port_st_lucie"]
    }
    resp = client.post("/api/v1/combined/batch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_requested"] == 3
    assert "combined" in data
    combined = data["combined"]
    assert "tulsa" in combined
    assert "newark" in combined
    assert "port_st_lucie" in combined

    newark_comb = combined["newark"]
    assert newark_comb["status"] == "success"
    assert "live_lookup" in newark_comb
    assert "forecast" in newark_comb
    assert "provenance" in newark_comb["live_lookup"]


def test_batch_fallback_and_defaults():
    """Verifies empty list default fallbacks and clean handling for batch endpoints."""
    # 1. Empty locales list fallback to ["national"]
    resp_empty = client.post("/api/v1/forecast/batch", json={"locales": []})
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert "national" in data_empty["forecasts"]

    # 2. Combined batch empty list fallback
    resp_comb_empty = client.post("/api/v1/combined/batch", json={"locales": []})
    assert resp_comb_empty.status_code == 200
    data_comb_empty = resp_comb_empty.json()
    assert "national" in data_comb_empty["combined"]
