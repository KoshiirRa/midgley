import os
import json
import pytest
from src.usace_locks import USACELockConnector
from src.lookup_cache import global_cache

def test_usace_lock_delays():
    connector = USACELockConnector()
    hour_bucket = datetime_now = ""
    # Clear cache
    from datetime import datetime
    hb = datetime.now().strftime("%Y-%m-%d-%H")
    global_cache.delete(f"usace_ohio_river_lock_delays:{hb}")
    
    data = connector.fetch_ohio_river_lock_delays()
    assert data["status"] == "SUCCESS"
    assert "usace_ohio_river_lock_delay_hours" in data
    assert "usace_cincinnati_barge_bottleneck_index" in data
    assert "monitored_locks" in data
    assert "Markland_Lock_OH_Mile531" in data["monitored_locks"]
    assert "McAlpine_Lock_OH_Mile606" in data["monitored_locks"]
    assert data["usace_ohio_river_lock_delay_hours"] >= 0.0
    assert 0.0 <= data["usace_cincinnati_barge_bottleneck_index"] <= 1.0

def test_usace_lock_bitemporal_persistence(tmp_path):
    temp_vintage = str(tmp_path / "usace_lock_vintages_test.json")
    connector = USACELockConnector()
    
    rec = {
        "status": "SUCCESS",
        "as_of": "2026-09-15 09:00:00",
        "valid_date": "2026-09-15",
        "usace_ohio_river_lock_delay_hours": 1.4,
        "is_vintage_reconstructed": False
    }
    connector.save_usace_lock_vintage_record(rec, filepath=temp_vintage)
    vintages = connector.get_usace_lock_vintages_as_of("2026-09-15", filepath=temp_vintage)
    assert len(vintages) == 1
    assert vintages[0]["usace_ohio_river_lock_delay_hours"] == 1.4
