"""
Unit and Integration Tests for Ultra-Low Sulfur Diesel (ULSD) Forecasting & Distillate Calibration (Issue #41).
"""

import pytest
from fastapi.testclient import TestClient
from src.api_server import app
from src.diesel_regional import (
    compute_distillate_crack_spread,
    compute_321_refining_crack_spread,
    compute_distillate_gasoline_ratio,
    UltraLowSulfurDieselForecastingAgent,
    simulate_diesel_shock
)

client = TestClient(app)

def test_distillate_crack_spread_math():
    """Tests Distillate Crack Spread math."""
    # HO=F $2.850/gal, WTI $75.00/bbl => 75 / 42 = $1.7857/gal. Crack = 2.850 - 1.7857 = 1.0643
    crack = compute_distillate_crack_spread(2.850, 75.00)
    assert round(crack, 3) == 1.064


def test_321_refining_crack_spread_math():
    """Tests 3-2-1 refining crack margin formula."""
    margin = compute_321_refining_crack_spread(2.450, 2.850, 75.00)
    assert margin > 0.0


def test_distillate_gasoline_ratio():
    """Tests distillate to gasoline price ratio."""
    ratio = compute_distillate_gasoline_ratio(2.850, 2.450)
    assert ratio > 1.0


def test_ulsd_forecasting_agent():
    """Tests UltraLowSulfurDieselForecastingAgent predictions and calibrations."""
    agent = UltraLowSulfurDieselForecastingAgent(alpha=10.0)
    res = agent.forecast_ulsd(rbob_price=2.450, ulsd_price=2.850, wti_price=75.00)

    assert res["status"] == "success"
    assert "wholesale_forecast" in res
    assert res["wholesale_forecast"]["predicted_5d_wholesale"] > 0.0
    assert "regional_retail_calibrations" in res
    assert "tulsa" in res["regional_retail_calibrations"]
    assert "oakland" in res["regional_retail_calibrations"]


def test_simulate_diesel_shock():
    """Tests counterfactual diesel market shock simulations."""
    res = simulate_diesel_shock(scenario_key="colonial_line2_outage", base_ulsd_price=2.850)
    assert res["status"] == "success"
    assert res["shocked_wholesale"] == 3.135
    assert res["pct_impact"] == 10.0


def test_api_diesel_endpoints():
    """Tests REST API endpoints for diesel live, forecast, and simulate."""
    # GET /api/v1/diesel/live
    resp_live = client.get("/api/v1/diesel/live")
    assert resp_live.status_code == 200
    data_live = resp_live.json()
    assert data_live["status"] == "success"
    assert "futures" in data_live

    # GET /api/v1/diesel/forecast
    resp_fc = client.get("/api/v1/diesel/forecast?rbob=2.450&ulsd=2.850&wti=75.00")
    assert resp_fc.status_code == 200
    data_fc = resp_fc.json()
    assert data_fc["status"] == "success"

    # GET /api/v1/diesel/simulate
    resp_sim = client.get("/api/v1/diesel/simulate?scenario=colonial_line2_outage")
    assert resp_sim.status_code == 200
    data_sim = resp_sim.json()
    assert data_sim["status"] == "success"
