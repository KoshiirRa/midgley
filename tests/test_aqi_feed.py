"""
Unit & Integration Test Suite for Air Quality (AQI) Telemetry Connector (tests/test_aqi_feed.py)
Tests AQIFeedConnector, multi-feed ingestion (PurpleAir, OpenAQ, EPA AirNow),
statistical Z-score anomaly detection, flaring vs. wildfire discrimination,
15-minute lookup caching, and headline generation. (Issue #54)
"""

import pytest
from datetime import datetime, timezone

from src.aqi_feed import (
    AQIFeedConnector,
    AQI_CORRIDORS,
    haversine_distance_km,
    calculate_zscore
)
from src.lookup_cache import global_cache


def test_aqi_feed_connector_contract():
    connector = AQIFeedConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0


def test_haversine_distance():
    # Chevron Richmond (37.9358, -122.3963) to PBF Martinez (38.0069, -122.1155)
    d = haversine_distance_km(37.9358, -122.3963, 38.0069, -122.1155)
    assert 20.0 < d < 35.0


def test_zscore_calculation():
    # Normal score
    z = calculate_zscore(15.0, 10.0, 2.5)
    assert abs(z - 2.0) < 1e-4

    # Zero std protection
    z_zero = calculate_zscore(10.0, 10.0, 0.0)
    assert z_zero == 0.0


def test_purpleair_sensors_fetch():
    connector = AQIFeedConnector(use_cache=False)
    sensors = connector.fetch_purpleair_sensors(37.9542, -122.3853, radius_km=15.0)
    assert len(sensors) >= 3
    for s in sensors:
        assert "sensor_index" in s
        assert "pm2_5_atm" in s
        assert "pm10_0_atm" in s
        assert "distance_km" in s
        assert s["distance_km"] <= 15.0


def test_openaq_measurements_fetch():
    connector = AQIFeedConnector(use_cache=False)
    data = connector.fetch_openaq_measurements(37.9542, -122.3853)
    assert "so2_ppb" in data
    assert "no2_ppb" in data
    assert "pm25_ugm3" in data
    assert "o3_ppm" in data
    assert data["so2_ppb"] > 0.0


def test_airnow_aqi_fetch():
    connector = AQIFeedConnector(use_cache=False)
    data = connector.fetch_airnow_aqi("94612")
    assert data["zip_code"] == "94612"
    assert "aqi" in data
    assert "category" in data
    assert "is_ozone_action_day" in data


def test_evaluate_corridor_baseline():
    connector = AQIFeedConnector(use_cache=False)
    eval_res = connector.evaluate_corridor_aqi("bay_area")

    assert eval_res["corridor"] == "bay_area"
    assert eval_res["is_unplanned_outage"] is False
    assert eval_res["is_wildfire_smoke"] is False
    assert eval_res["outage_risk_index"] <= 0.20
    assert eval_res["estimated_rack_shock_per_gal"] <= 0.06


def test_evaluate_corridor_unplanned_flaring():
    connector = AQIFeedConnector(use_cache=False)
    # Severe flaring simulation: PM2.5 = 45 ug/m3, SO2 = 12.0 ppb
    eval_res = connector.evaluate_corridor_aqi("bay_area", observed_pm25=45.0, observed_so2=12.0)

    assert eval_res["is_unplanned_outage"] is True
    assert eval_res["is_wildfire_smoke"] is False
    assert eval_res["z_score_pm25"] >= 3.5
    assert eval_res["z_score_so2"] >= 2.5
    assert eval_res["outage_risk_index"] >= 0.60
    assert eval_res["estimated_rack_shock_per_gal"] >= 0.15


def test_evaluate_corridor_wildfire_discrimination():
    connector = AQIFeedConnector(use_cache=False)
    # Wildfire simulation: very high particulate PM2.5 = 65 ug/m3, but clean ambient SO2 = 2.0 ppb
    eval_res = connector.evaluate_corridor_aqi("bay_area", observed_pm25=65.0, observed_so2=2.0)

    assert eval_res["is_wildfire_smoke"] is True
    assert eval_res["is_unplanned_outage"] is False
    # Risk index should be sharply attenuated to prevent false-positive refinery outage alerts
    assert eval_res["outage_risk_index"] <= 0.10


def test_fetch_live_aqi_telemetry_indices():
    connector = AQIFeedConnector(use_cache=False)
    data = connector.fetch_live_aqi_telemetry()

    assert data["status"] == "SUCCESS"
    assert "indices" in data
    assert "corridors" in data
    assert "active_outages" in data

    indices = data["indices"]
    expected_keys = [
        "bay_area_outage_risk_index",
        "tulsa_outage_risk_index",
        "delaware_valley_outage_risk_index",
        "tri_state_outage_risk_index",
        "composite_aqi_shock_index",
        "is_unplanned_refinery_outage_detected",
        "active_outage_count"
    ]
    for k in expected_keys:
        assert k in indices

    for c in ["bay_area", "tulsa", "delaware_valley", "tri_state"]:
        idx = indices[f"{c}_outage_risk_index"]
        assert 0.0 <= idx <= 1.0


def test_generate_aqi_event_headline():
    connector = AQIFeedConnector(use_cache=False)

    # Baseline quiet conditions -> None
    hl_none = connector.generate_aqi_event_headline("bay_area")
    assert hl_none is None

    # Elevated flaring condition -> Generates structured event
    high_telemetry = {
        "corridors": {
            "bay_area": {
                "name": "SF Bay Area Refining Corridor (PADD 5)",
                "outage_risk_index": 0.75,
                "estimated_rack_shock_per_gal": 0.21,
                "z_score_pm25": 4.2,
                "z_score_so2": 3.1
            }
        }
    }
    hl = connector.generate_aqi_event_headline("bay_area", telemetry=high_telemetry)
    assert hl is not None
    assert "headline" in hl
    assert "outage" in hl["headline"].lower()
    assert hl["corridor"] == "bay_area"
    assert hl["risk_index"] == 0.75
    assert hl["rack_margin_shock"] == 0.21


def test_aqi_caching():
    connector = AQIFeedConnector(use_cache=True)
    res1 = connector.fetch_live_aqi_telemetry(corridor="tulsa")
    res2 = connector.fetch_live_aqi_telemetry(corridor="tulsa")
    assert res1["as_of"] == res2["as_of"]


def test_api_server_aqi_live_endpoint():
    from fastapi.testclient import TestClient
    from src.api_server import app

    client = TestClient(app)
    response = client.get("/api/v1/aqi/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "indices" in data
    assert "corridors" in data

    # Test corridor filter
    c_resp = client.get("/api/v1/aqi/live?corridor=tulsa")
    assert c_resp.status_code == 200
    c_data = c_resp.json()
    assert "tulsa" in c_data["corridors"]


def test_mcp_server_aqi_tool():
    import asyncio
    import json
    from src.mcp_server import list_tools, call_tool

    tools = asyncio.run(list_tools())
    tool_names = [t.name for t in tools]
    assert "get_refinery_aqi_anomalies" in tool_names

    res = asyncio.run(call_tool("get_refinery_aqi_anomalies", {"corridor": "bay_area"}))
    assert len(res) == 1
    content = json.loads(res[0].text)
    assert content["status"] == "SUCCESS"
    assert "indices" in content

