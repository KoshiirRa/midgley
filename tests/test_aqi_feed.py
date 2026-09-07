"""
Unit & Integration Test Suite for Air Quality (AQI) & Ozone Telemetry Connector (tests/test_aqi_feed.py)
Tests AQIFeedConnector, multi-feed ingestion (PurpleAir, OpenAQ, EPA AirNow),
statistical Z-score anomaly detection, flaring vs. wildfire discrimination,
Ozone Action Day detection, statutory seasonal RVP compliance calculations,
15-minute / 1-hour lookup caching, and headline generation. (Issues #54 & #73)
"""

import pytest
import unittest.mock as mock
import json
from datetime import datetime, timezone

from src.aqi_feed import (
    AQIFeedConnector,
    AQI_CORRIDORS,
    METRO_ZIP_MAP,
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


def test_airnow_aqi_fetch_all_target_metros():
    connector = AQIFeedConnector(use_cache=False)
    target_zips = ["94612", "45202", "74101", "19711", "27834", "28202", "34984"]
    for z in target_zips:
        data = connector.fetch_airnow_aqi(z)
        assert data["zip_code"] == z
        assert "aqi" in data
        assert "category" in data
        assert "ozone_aqi" in data
        assert "is_ozone_action_day" in data
        assert isinstance(data["is_ozone_action_day"], bool)


def test_airnow_api_live_mock():
    connector = AQIFeedConnector(use_cache=False)
    mock_airnow_payload = [
        {
            "DateObserved": "2026-07-15",
            "HourObserved": 14,
            "LocalTimeZone": "PST",
            "ReportingArea": "San Francisco-Oakland",
            "StateCode": "CA",
            "Latitude": 37.8,
            "Longitude": -122.3,
            "ParameterName": "O3",
            "AQI": 115,
            "Category": {"Number": 3, "Name": "Unhealthy for Sensitive Groups"}
        },
        {
            "DateObserved": "2026-07-15",
            "HourObserved": 14,
            "LocalTimeZone": "PST",
            "ReportingArea": "San Francisco-Oakland",
            "StateCode": "CA",
            "Latitude": 37.8,
            "Longitude": -122.3,
            "ParameterName": "PM2.5",
            "AQI": 45,
            "Category": {"Number": 1, "Name": "Good"}
        }
    ]

    mock_resp = mock.MagicMock()
    mock_resp.read.return_value = json.dumps(mock_airnow_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with mock.patch("urllib.request.urlopen", return_value=mock_resp):
        res = connector.fetch_airnow_aqi("94612", api_key="TEST_MOCK_KEY")
        assert res["source"] == "EPA_AIRNOW_LIVE"
        assert res["ozone_aqi"] == 115
        assert res["pm25_aqi"] == 45
        assert res["is_ozone_action_day"] is True
        assert res["primary_parameter"] == "OZONE"


def test_seasonal_rvp_surcharges_across_seasons():
    connector = AQIFeedConnector(use_cache=False)
    
    # 1. Summer Blend (July 15) in Bay Area (CARB 7.0 psi)
    summer_res = connector.get_seasonal_rvp_surcharge(date="2026-07-15", corridor_or_zip="bay_area")
    assert summer_res["season"] == "SUMMER_BLEND"
    assert summer_res["statutory_rvp_psi"] == 7.0
    assert summer_res["base_rvp_surcharge_per_gal"] == 0.180
    assert summer_res["ozone_action_surcharge_per_gal"] == 0.000
    assert summer_res["total_rvp_compliance_surcharge_per_gal"] == 0.180

    # 2. Summer Blend in Cincinnati with active Ozone Action Day
    cincy_action = connector.get_seasonal_rvp_surcharge(date="2026-07-15", corridor_or_zip="cincinnati", ozone_aqi=120, is_action_day=True)
    assert cincy_action["season"] == "SUMMER_BLEND"
    assert cincy_action["statutory_rvp_psi"] == 7.8
    assert cincy_action["base_rvp_surcharge_per_gal"] == 0.085
    assert cincy_action["ozone_action_surcharge_per_gal"] == 0.040
    assert abs(cincy_action["total_rvp_compliance_surcharge_per_gal"] - 0.125) < 1e-4

    # 3. Spring Shoulder (April 15) in Tulsa
    spring_res = connector.get_seasonal_rvp_surcharge(date="2026-04-15", corridor_or_zip="tulsa")
    assert spring_res["season"] == "SPRING_SHOULDER"
    assert spring_res["base_rvp_surcharge_per_gal"] == 0.025

    # 4. Winter Season (January 15) in Newark
    winter_res = connector.get_seasonal_rvp_surcharge(date="2026-01-15", corridor_or_zip="newark")
    assert winter_res["season"] == "WINTER_BLEND"
    assert winter_res["base_rvp_surcharge_per_gal"] == 0.000
    assert winter_res["total_rvp_compliance_surcharge_per_gal"] == 0.000


def test_evaluate_corridor_baseline():
    connector = AQIFeedConnector(use_cache=False)
    eval_res = connector.evaluate_corridor_aqi("bay_area")

    assert eval_res["corridor"] == "bay_area"
    assert eval_res["is_unplanned_outage"] is False
    assert eval_res["is_wildfire_smoke"] is False
    assert eval_res["outage_risk_index"] <= 0.20
    assert "statutory_rvp_psi" in eval_res
    assert "seasonal_blend_state" in eval_res
    assert "rvp_compliance_surcharge_per_gal" in eval_res


def test_evaluate_corridor_unplanned_flaring():
    connector = AQIFeedConnector(use_cache=False)
    # Severe flaring simulation: PM2.5 = 45 ug/m3, SO2 = 12.0 ppb
    eval_res = connector.evaluate_corridor_aqi("bay_area", observed_pm25=45.0, observed_so2=12.0)

    assert eval_res["is_unplanned_outage"] is True
    assert eval_res["is_wildfire_smoke"] is False
    assert eval_res["z_score_pm25"] >= 3.5
    assert eval_res["z_score_so2"] >= 2.5
    assert eval_res["outage_risk_index"] >= 0.60
    assert eval_res["flaring_rack_shock_per_gal"] >= 0.15


def test_evaluate_corridor_wildfire_discrimination():
    connector = AQIFeedConnector(use_cache=False)
    # Wildfire simulation: very high particulate PM2.5 = 65 ug/m3, but clean ambient SO2 = 2.0 ppb
    eval_res = connector.evaluate_corridor_aqi("bay_area", observed_pm25=65.0, observed_so2=2.0)

    assert eval_res["is_wildfire_smoke"] is True
    assert eval_res["is_unplanned_outage"] is False
    assert eval_res["outage_risk_index"] <= 0.10


def test_fetch_live_aqi_telemetry_indices():
    connector = AQIFeedConnector(use_cache=False)
    data = connector.fetch_live_aqi_telemetry()

    assert data["status"] == "SUCCESS"
    assert "indices" in data
    assert "corridors" in data
    assert "active_outages" in data
    assert "active_ozone_action_corridors" in data

    indices = data["indices"]
    expected_keys = [
        "bay_area_outage_risk_index",
        "tulsa_outage_risk_index",
        "delaware_valley_outage_risk_index",
        "tri_state_outage_risk_index",
        "carolinas_coastal_outage_risk_index",
        "carolinas_piedmont_outage_risk_index",
        "south_florida_outage_risk_index",
        "composite_aqi_shock_index",
        "is_unplanned_refinery_outage_detected",
        "active_outage_count",
        "ozone_action_day_count",
        "max_rvp_compliance_surcharge_per_gal"
    ]
    for k in expected_keys:
        assert k in indices

    for c in ["bay_area", "tulsa", "delaware_valley", "tri_state", "carolinas_coastal", "carolinas_piedmont", "south_florida"]:
        idx = indices[f"{c}_outage_risk_index"]
        assert 0.0 <= idx <= 1.0


def test_generate_aqi_event_headline():
    connector = AQIFeedConnector(use_cache=False)

    # Elevated flaring condition -> Generates flaring headline
    high_telemetry = {
        "corridors": {
            "bay_area": {
                "name": "SF Bay Area Refining Corridor (PADD 5)",
                "outage_risk_index": 0.75,
                "is_ozone_action_day": False,
                "flaring_rack_shock_per_gal": 0.21,
                "rvp_compliance_surcharge_per_gal": 0.18,
                "z_score_pm25": 4.2,
                "z_score_so2": 3.1,
                "observed_ozone_aqi": 52
            }
        }
    }
    hl = connector.generate_aqi_event_headline("bay_area", telemetry=high_telemetry)
    assert hl is not None
    assert "headline" in hl
    assert "outage" in hl["headline"].lower()
    assert hl["corridor"] == "bay_area"
    assert hl["risk_index"] == 0.75

    # Ozone Action Day alert -> Generates ozone alert headline
    ozone_telemetry = {
        "corridors": {
            "tri_state": {
                "name": "Ohio River Valley / Tri-State Refining Hub (PADD 2)",
                "outage_risk_index": 0.10,
                "is_ozone_action_day": True,
                "flaring_rack_shock_per_gal": 0.02,
                "rvp_compliance_surcharge_per_gal": 0.125,
                "z_score_pm25": 1.1,
                "z_score_so2": 0.8,
                "observed_ozone_aqi": 118
            }
        }
    }
    hl_ozone = connector.generate_aqi_event_headline("tri_state", telemetry=ozone_telemetry)
    assert hl_ozone is not None
    assert "ozone" in hl_ozone["headline"].lower()
    assert hl_ozone["category"] == "EPA Ozone Action Alert & RVP Compliance"
    assert hl_ozone["ozone_aqi"] == 118


def test_aqi_caching():
    connector = AQIFeedConnector(use_cache=True)
    res1 = connector.fetch_live_aqi_telemetry(corridor="tulsa")
    res2 = connector.fetch_live_aqi_telemetry(corridor="tulsa")
    assert res1["as_of"] == res2["as_of"]


def test_api_server_aqi_endpoints():
    from fastapi.testclient import TestClient
    from src.api_server import app

    client = TestClient(app)
    
    # 1. Live AQI endpoint
    resp1 = client.get("/api/v1/aqi/live")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "SUCCESS"
    assert "indices" in data1
    assert "corridors" in data1

    # 2. Ozone Alerts endpoint
    resp2 = client.get("/api/v1/aqi/ozone-alerts")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "SUCCESS"
    assert "ozone_action_day_count" in data2
    assert "max_rvp_compliance_surcharge_per_gal" in data2

    # 3. Direct ZIP query on Ozone Alerts endpoint
    resp3 = client.get("/api/v1/aqi/ozone-alerts?zip_code=45202")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["airnow"]["zip_code"] == "45202"
    assert "seasonal_rvp_compliance" in data3


def test_mcp_server_ozone_tools():
    import asyncio
    import json
    from src.mcp_server import list_tools, call_tool

    tools = asyncio.run(list_tools())
    tool_names = [t.name for t in tools]
    assert "get_refinery_aqi_anomalies" in tool_names
    assert "get_regional_ozone_alerts" in tool_names

    res = asyncio.run(call_tool("get_regional_ozone_alerts", {"corridor": "bay_area"}))
    assert len(res) == 1
    content = json.loads(res[0].text)
    assert content["status"] == "SUCCESS"
    assert "corridors" in content

