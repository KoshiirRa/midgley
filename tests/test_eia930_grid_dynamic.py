import os
import json
import pytest
from src.data_ingestion import EIA930GridMonitorConnector
from src.lookup_cache import global_cache

def test_eia930_grid_stress_calculation():
    connector = EIA930GridMonitorConnector()
    global_cache.delete("eia930_refinery_grid_stress")
    data = connector.fetch_refinery_hub_grid_stress()
    
    assert data["status"] == "SUCCESS"
    assert "grid_stress_load_anomaly_zscore" in data
    assert isinstance(data["grid_stress_load_anomaly_zscore"], float)
    assert "rto_balancing_authorities" in data
    
    rtos = data["rto_balancing_authorities"]
    assert "ERCOT_Texas_Gulf" in rtos
    assert "MISO_Midwest_Tulsa" in rtos
    assert "PJM_MidAtlantic_Newark" in rtos
    assert "CAISO_WestCoast_Oakland" in rtos
    
    for rto, metrics in rtos.items():
        assert "load_mw" in metrics
        assert "stress_index" in metrics
        assert metrics["load_mw"] > 0
        assert 0.0 <= metrics["stress_index"] <= 1.0

def test_eia930_bitemporal_persistence(tmp_path):
    temp_vintage = str(tmp_path / "eia930_vintages_test.json")
    connector = EIA930GridMonitorConnector()
    
    rec = {
        "source": "EIA930 Test",
        "as_of": "2026-09-15 14:00:00",
        "valid_date": "2026-09-15",
        "grid_stress_load_anomaly_zscore": 0.25,
        "is_vintage_reconstructed": False
    }
    connector.save_eia930_vintage_record(rec, filepath=temp_vintage)
    vintages = connector.get_eia930_vintages_as_of("2026-09-15", filepath=temp_vintage)
    assert len(vintages) == 1
    assert vintages[0]["grid_stress_load_anomaly_zscore"] == 0.25
