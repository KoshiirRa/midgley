import pytest
import os
import json
from src.bsee_shutins import (
    BSEEShutInConnector,
    save_bsee_vintage_record,
    get_bsee_vintages_as_of,
    BSEE_VINTAGE_FILE
)
from src.lookup_cache import global_cache


def test_bsee_shutin_connector_schema():
    connector = BSEEShutInConnector()
    data = connector.fetch_gulf_shutin_data()
    assert isinstance(data, dict)
    assert "source" in data
    assert "timestamp" in data
    assert "bsee_gulf_oil_shutin_pct" in data
    assert "bsee_gulf_gas_shutin_pct" in data
    assert "bsee_evacuated_platforms_count" in data
    assert "is_storm_evacuation_active" in data
    assert data["status"] == "SUCCESS"


def test_bsee_bitemporal_persistence(tmp_path):
    temp_vintage = str(tmp_path / "bsee_vintages.json")
    record = {
        "source": "BSEE Test",
        "bsee_gulf_oil_shutin_pct": 14.5,
        "bsee_gulf_gas_shutin_pct": 9.2,
        "bsee_evacuated_platforms_count": 22,
        "is_storm_evacuation_active": True,
        "status": "SUCCESS"
    }
    save_bsee_vintage_record(record, filepath=temp_vintage)
    assert os.path.exists(temp_vintage)

    loaded = get_bsee_vintages_as_of("2099-12-31", filepath=temp_vintage)
    assert loaded is not None
    assert loaded["bsee_gulf_oil_shutin_pct"] == 14.5
    assert loaded["is_storm_evacuation_active"] is True
