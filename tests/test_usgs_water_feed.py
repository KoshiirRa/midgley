"""
Unit & Integration Test Suite for USGS Water Data Telemetry (tests/test_usgs_water_feed.py)
Tests USGSWaterFeedConnector, multi-regional risk indices, caching, fallback logic,
REST API endpoint /api/v1/usgs/water_levels, and MCP tool get_usgs_water_telemetry. (Issue #56)
"""

import pytest
from src.usgs_water_feed import USGSWaterFeedConnector, USGS_STATIONS
from src.lookup_cache import global_cache


def test_usgs_water_feed_connector_contract():
    connector = USGSWaterFeedConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0


def test_usgs_water_telemetry_fetch_live_or_baseline():
    connector = USGSWaterFeedConnector()
    res = connector.fetch_live_water_telemetry()

    assert res["status"] == "SUCCESS"
    assert res["source"].startswith("USGS National Water Information System")
    assert "stations" in res
    assert "indices" in res
    assert len(res["stations"]) == len(USGS_STATIONS)

    # Check station parameters
    memphis = res["stations"].get("07032000")
    assert memphis is not None
    assert memphis["name"] == "Mississippi River at Memphis, TN"
    assert memphis["cluster"] == "inland_barge"
    assert isinstance(memphis["gage_height_ft"], (int, float))

    # Check multi-regional indices
    indices = res["indices"]
    required_indices = [
        "hydrological_barge_bottleneck_index",
        "gulf_marine_departure_risk_index",
        "carquinez_berthing_risk_index",
        "delaware_refinery_thermal_index",
        "tulsa_refinery_flood_risk_index",
        "florida_canal_flood_risk_index",
        "is_barge_draft_restricted",
        "is_thermal_curtailment_risk",
        "is_gulf_departure_halted"
    ]
    for key in required_indices:
        assert key in indices, f"Missing index: {key}"

    # Bounded between 0.0 and 1.0
    for idx_name in [
        "hydrological_barge_bottleneck_index",
        "gulf_marine_departure_risk_index",
        "carquinez_berthing_risk_index",
        "delaware_refinery_thermal_index",
        "tulsa_refinery_flood_risk_index",
        "florida_canal_flood_risk_index"
    ]:
        assert 0.0 <= indices[idx_name] <= 1.0, f"Index {idx_name} out of bounds: {indices[idx_name]}"


def test_usgs_water_telemetry_cluster_filtering():
    connector = USGSWaterFeedConnector()
    
    # Inland barge cluster (Memphis, Cairo, Cincinnati)
    barge_res = connector.fetch_live_water_telemetry(cluster="inland_barge")
    assert len(barge_res["stations"]) == 3
    assert "07032000" in barge_res["stations"]
    assert "03612500" in barge_res["stations"]
    assert "03255000" in barge_res["stations"]
    assert barge_res["filtered_cluster"] == "inland_barge"

    # Gulf Coast cluster (Houston Ship Channel, Baton Rouge, Belle Chasse, Neches)
    gulf_res = connector.fetch_live_water_telemetry(cluster="gulf_coast")
    assert len(gulf_res["stations"]) == 4
    assert "08072050" in gulf_res["stations"]
    assert "07374000" in gulf_res["stations"]

    # Bay Area cluster (Carquinez Strait, Sacramento River)
    bay_res = connector.fetch_live_water_telemetry(cluster="bay_area")
    assert len(bay_res["stations"]) == 2
    assert "11162765" in bay_res["stations"]


def test_usgs_water_telemetry_caching():
    connector = USGSWaterFeedConnector()
    res1 = connector.fetch_live_water_telemetry()
    res2 = connector.fetch_live_water_telemetry()

    assert res1["timestamp"] == res2["timestamp"]
    assert res1["indices"] == res2["indices"]


def test_usgs_synthetic_baseline_and_index_computation():
    connector = USGSWaterFeedConnector()
    baseline = connector._generate_synthetic_baseline()
    assert len(baseline) == len(USGS_STATIONS)

    # Test baseline calculations
    indices = connector._compute_risk_indices(baseline)
    assert indices["hydrological_barge_bottleneck_index"] == 0.0
    assert indices["is_barge_draft_restricted"] is False

    # Simulate low-water drought shock at Memphis (-5.0 ft)
    shocked_baseline = dict(baseline)
    shocked_baseline["07032000"] = dict(baseline["07032000"])
    shocked_baseline["07032000"]["gage_height_ft"] = -5.0

    shocked_indices = connector._compute_risk_indices(shocked_baseline)
    assert shocked_indices["hydrological_barge_bottleneck_index"] >= 0.60
    assert shocked_indices["is_barge_draft_restricted"] is True


def test_api_server_usgs_endpoint():
    from fastapi.testclient import TestClient
    from src.api_server import app

    client = TestClient(app)
    response = client.get("/api/v1/usgs/water_levels")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "stations" in data
    assert "indices" in data

    # Test cluster query parameter
    cluster_resp = client.get("/api/v1/usgs/water_levels?cluster=inland_barge")
    assert cluster_resp.status_code == 200
    cluster_data = cluster_resp.json()
    assert len(cluster_data["stations"]) == 3


def test_mcp_server_usgs_tool():
    import asyncio
    import json
    from src.mcp_server import list_tools, call_tool

    tools = asyncio.run(list_tools())
    tool_names = [t.name for t in tools]
    assert "get_usgs_water_telemetry" in tool_names

    res = asyncio.run(call_tool("get_usgs_water_telemetry", {"cluster": "inland_barge"}))
    assert len(res) == 1
    content = json.loads(res[0].text)
    assert content["status"] == "SUCCESS"
    assert "stations" in content
    assert "indices" in content
