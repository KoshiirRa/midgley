"""
Unit Test Suite for Sprint 2 Research Connectors (tests/test_sprint2_research_connectors.py)
Tests NHCHurricaneConnector, BSEEShutInConnector, EIA930GridMonitorConnector,
expanded EIADataConnector, and USACELockConnector. (Issues #177-#181)
"""

import pytest
from src.nhc_hurricane import NHCHurricaneConnector
from src.bsee_shutins import BSEEShutInConnector
from src.data_ingestion import EIADataConnector, EIA930GridMonitorConnector
from src.usace_locks import USACELockConnector

def test_nhc_hurricane_connector():
    connector = NHCHurricaneConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0

    res = connector.fetch_active_hurricane_threats()
    assert res["status"] == "SUCCESS" or res["status"].startswith("PARTIAL_FALLBACK")
    assert "nhc_hurricane_threat_index" in res
    assert "nhc_gulf_refinery_exposure_score" in res
    assert 0.0 <= res["nhc_hurricane_threat_index"] <= 1.0


def test_bsee_shutin_connector():
    connector = BSEEShutInConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0

    res = connector.fetch_gulf_shutin_data()
    assert res["status"] == "SUCCESS"
    assert "bsee_gulf_oil_shutin_pct" in res
    assert "bsee_gulf_gas_shutin_pct" in res
    assert res["bsee_gulf_oil_shutin_pct"] >= 0.0


def test_eia930_grid_monitor_connector():
    connector = EIA930GridMonitorConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0

    res = connector.fetch_refinery_hub_grid_stress()
    assert res["status"] == "SUCCESS"
    assert "grid_stress_load_anomaly_zscore" in res
    assert "rto_balancing_authorities" in res
    assert "ERCOT_Texas_Gulf" in res["rto_balancing_authorities"]


def test_expanded_eia_data_connector():
    connector = EIADataConnector()
    res = connector.fetch_padd_inventory_and_refinery_data()
    assert res["status"] == "SUCCESS"
    assert "product_supplied_thousand_bpd" in res
    assert "refiner_net_production_thousand_bpd" in res
    assert "inter_padd_movements" in res
    assert res["product_supplied_thousand_bpd"]["us_motor_gasoline"] > 0.0


def test_usace_lock_connector():
    connector = USACELockConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0

    res = connector.fetch_ohio_river_lock_delays()
    assert res["status"] == "SUCCESS"
    assert "usace_ohio_river_lock_delay_hours" in res
    assert "usace_cincinnati_barge_bottleneck_index" in res
    assert "Markland_Lock_OH_Mile531" in res["monitored_locks"]
