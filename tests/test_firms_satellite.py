"""
Tests for NASA FIRMS Satellite Telemetry & Topological Outage Exposure (Issue #453).
"""

import pytest
from src.firms_satellite_feed import FirmsSatelliteFeedConnector, FIRMS_REFINING_BBOXES
from src.knowledge_graph import KnowledgeGraphEngine


def test_firms_refining_bboxes_configuration():
    assert "baytown_houston" in FIRMS_REFINING_BBOXES
    assert "west_tulsa_cushing" in FIRMS_REFINING_BBOXES
    assert "catlettsburg_ohio_valley" in FIRMS_REFINING_BBOXES
    assert "delaware_city_delmarva" in FIRMS_REFINING_BBOXES
    assert "richmond_martinez_bay_area" in FIRMS_REFINING_BBOXES

    for hub_code, data in FIRMS_REFINING_BBOXES.items():
        assert len(data["bbox"]) == 4
        min_lon, min_lat, max_lon, max_lat = data["bbox"]
        assert min_lon < max_lon
        assert min_lat < max_lat
        assert data["baseline_daily_frp_mw"] > 0


def test_firms_connector_offline_and_live_fallback():
    connector = FirmsSatelliteFeedConnector(map_key="22f64ca740591eb1e6d5a6802778b8a8")
    assert connector.map_key is not None

    telemetry = connector.fetch_hub_firms_telemetry("west_tulsa_cushing", days=1)
    assert telemetry is not None
    assert telemetry["hub_code"] == "west_tulsa_cushing"
    assert "total_frp_mw" in telemetry
    assert "thermal_pixel_count" in telemetry
    assert "flaring_anomaly_z_score" in telemetry
    assert isinstance(telemetry["is_major_flaring_upset"], bool)

    all_corridors = connector.fetch_all_refining_corridors()
    assert all_corridors["status"] == "SUCCESS"
    assert all_corridors["total_monitored_hubs"] >= 9
    assert "corridors" in all_corridors


def test_knowledge_graph_topological_supply_outage_exposure():
    kg = KnowledgeGraphEngine()

    # 1. Nominal conditions (zero outages, nominal satellite flaring)
    nominal_exp = kg.compute_metro_outage_exposure_index("Tulsa_OK")
    assert nominal_exp["metro_id"] == "Tulsa_OK"
    assert nominal_exp["outage_exposure_index"] == 0.0
    assert nominal_exp["exposure_severity"] == "NOMINAL"

    # 2. Outage scenario: HF Sinclair West Tulsa takes 85,000 bpd offline
    tulsa_outage = kg.compute_metro_outage_exposure_index(
        "Tulsa_OK",
        outage_capacities={"refinery_west_tulsa": 85000}
    )
    # West Tulsa represents 70% of Tulsa's supply share
    assert tulsa_outage["outage_exposure_index"] == pytest.approx(0.70, abs=1e-3)
    assert tulsa_outage["exposure_severity"] == "CRITICAL"

    # 3. Satellite flaring anomaly boost in Richmond/Martinez elevates Oakland exposure
    oakland_firms = kg.compute_metro_outage_exposure_index(
        "Oakland_CA",
        firms_anomalies={"richmond_martinez_bay_area": 3.8}  # Z >= 2.5 indicates flaring trip
    )
    assert oakland_firms["outage_exposure_index"] > 0.0
    assert oakland_firms["exposure_severity"] in ["MODERATE", "ELEVATED", "CRITICAL"]
