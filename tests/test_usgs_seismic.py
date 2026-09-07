"""
Unit & Integration Test Suite for USGS Earthquake Web Service Telemetry (tests/test_usgs_seismic.py)
Tests USGSSeismicConnector, distance attenuation modeling, multi-corridor risk scoring,
caching, synthetic fallback, and headline generation. (Issue #55)
"""

import pytest
from datetime import datetime, timezone
from src.usgs_seismic import (
    USGSSeismicConnector,
    SEISMIC_CORRIDORS,
    haversine_distance_km,
    calculate_hypocentral_distance_km,
    calculate_asset_seismic_shock
)
from src.lookup_cache import global_cache


def test_usgs_seismic_connector_contract():
    connector = USGSSeismicConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0


def test_haversine_and_hypocentral_distance():
    # Chevron Richmond (37.9358, -122.3963) to PBF Martinez (38.0069, -122.1155)
    d = haversine_distance_km(37.9358, -122.3963, 38.0069, -122.1155)
    assert 20.0 < d < 35.0  # Approx 25 km

    # Hypocentral distance with 10 km depth
    hypo = calculate_hypocentral_distance_km(d, depth_km=10.0)
    assert hypo > d
    assert abs(hypo - (d**2 + 10.0**2)**0.5) < 0.01


def test_calculate_asset_seismic_shock():
    # Small quake below baseline -> 0.0
    shock_small = calculate_asset_seismic_shock(mag=3.5, hypocenter_dist_km=20.0, m_base=4.2)
    assert shock_small == 0.0

    # Moderate M5.2 quake at 15 km
    shock_mod = calculate_asset_seismic_shock(mag=5.2, hypocenter_dist_km=15.0, m_base=4.2)
    assert 0.05 < shock_mod < 0.50

    # Severe M6.5 quake close to facility (10 km)
    shock_severe = calculate_asset_seismic_shock(mag=6.5, hypocenter_dist_km=10.0, m_base=4.2)
    assert shock_severe > 0.50
    assert shock_severe <= 1.0


def test_usgs_seismic_telemetry_fetch_live_or_baseline():
    connector = USGSSeismicConnector()
    res = connector.fetch_live_seismic_telemetry(corridor="bay_area")

    assert res["status"] in ["SUCCESS", "FALLBACK_BASELINE", "PARTIAL_FALLBACK"]
    assert "events" in res
    assert "corridors" in res
    assert "indices" in res
    assert "bay_area" in res["corridors"]

    indices = res["indices"]
    required_keys = [
        "bay_area_seismic_risk_index",
        "cushing_storage_seismic_risk_index",
        "socal_refining_seismic_risk_index",
        "mid_atlantic_seismic_risk_index",
        "new_madrid_seismic_risk_index",
        "composite_seismic_risk_index",
        "is_pipeline_emergency_shutdown_risk",
        "is_refinery_inspection_advisory"
    ]
    for k in required_keys:
        assert k in indices, f"Missing index key: {k}"

    # Verify bounds
    for k in [
        "bay_area_seismic_risk_index",
        "cushing_storage_seismic_risk_index",
        "socal_refining_seismic_risk_index",
        "mid_atlantic_seismic_risk_index",
        "new_madrid_seismic_risk_index",
        "composite_seismic_risk_index"
    ]:
        assert 0.0 <= indices[k] <= 1.0


def test_usgs_seismic_caching():
    connector = USGSSeismicConnector()
    res1 = connector.fetch_live_seismic_telemetry(corridor="cushing_ok")
    res2 = connector.fetch_live_seismic_telemetry(corridor="cushing_ok")

    assert res1["timestamp"] == res2["timestamp"]
    assert res1["indices"] == res2["indices"]


def test_mock_geojson_feature_parsing_and_risk_scoring():
    connector = USGSSeismicConnector()

    mock_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "nc73948291",
                "properties": {
                    "mag": 6.3,
                    "place": "4 km E of El Cerrito, CA (Hayward Fault)",
                    "time": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "mmi": 7.5,
                    "alert": "orange",
                    "felt": 12500
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-122.3100, 37.9150, 8.5]
                }
            }
        ]
    }

    parsed = connector._parse_usgs_features(mock_geojson, "bay_area")
    assert len(parsed) == 1
    ev = parsed[0]

    assert ev["magnitude"] == 6.3
    assert "Hayward Fault" in ev["place"]
    assert ev["closest_facility"] == "Chevron Richmond Refinery"
    assert ev["closest_distance_km"] < 15.0
    assert ev["max_facility_shock"] > 0.40

    c_metrics = connector._compute_corridor_indices("bay_area", parsed)
    assert c_metrics["corridor_risk_index"] > 0.40
    assert c_metrics["max_magnitude"] == 6.3
    assert c_metrics["active_events_count"] == 1

    # Test headline generation with this high-risk scenario
    mock_telemetry = {
        "corridors": {"bay_area": c_metrics},
        "indices": {"bay_area_seismic_risk_index": c_metrics["corridor_risk_index"]}
    }
    headline_info = connector.generate_seismic_event_headline("bay_area", mock_telemetry)
    assert headline_info is not None
    assert "USGS reports M6.3 earthquake" in headline_info["headline"]
    assert "Chevron Richmond Refinery" in headline_info["headline"]
    assert headline_info["seismic_risk_index"] > 0.40


def test_cushing_induced_seismicity_scoring():
    connector = USGSSeismicConnector()

    # M4.8 earthquake 5 km from Cushing storage terminal
    mock_ok_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "ok20261106",
                "properties": {
                    "mag": 4.8,
                    "place": "3 km S of Cushing, OK",
                    "time": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "mmi": 6.2,
                    "alert": "yellow",
                    "felt": 3400
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-96.7678, 35.9500, 4.0]  # Very shallow 4.0 km depth
                }
            }
        ]
    }

    parsed = connector._parse_usgs_features(mock_ok_geojson, "cushing_ok")
    assert len(parsed) == 1
    ev = parsed[0]
    assert ev["closest_facility"] == "Cushing Crude Oil Storage Terminal (WTI Delivery Point)"
    assert ev["closest_distance_km"] < 8.0
    assert ev["max_facility_shock"] > 0.25


def test_api_server_usgs_seismic_endpoint():
    from fastapi.testclient import TestClient
    from src.api_server import app

    client = TestClient(app)
    response = client.get("/api/v1/usgs/seismic")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["SUCCESS", "FALLBACK_BASELINE", "PARTIAL_FALLBACK"]
    assert "events" in data
    assert "indices" in data
    assert "corridors" in data

    # Test corridor filter
    c_resp = client.get("/api/v1/usgs/seismic?corridor=cushing_ok")
    assert c_resp.status_code == 200
    c_data = c_resp.json()
    assert c_data["filtered_corridor"] == "cushing_ok"
    assert "cushing_ok" in c_data["corridors"]


def test_mcp_server_usgs_seismic_tool():
    import asyncio
    import json
    from src.mcp_server import list_tools, call_tool

    tools = asyncio.run(list_tools())
    tool_names = [t.name for t in tools]
    assert "get_usgs_seismic_telemetry" in tool_names

    res = asyncio.run(call_tool("get_usgs_seismic_telemetry", {"corridor": "bay_area"}))
    assert len(res) == 1
    content = json.loads(res[0].text)
    assert content["status"] in ["SUCCESS", "FALLBACK_BASELINE", "PARTIAL_FALLBACK"]
    assert "events" in content
    assert "indices" in content

