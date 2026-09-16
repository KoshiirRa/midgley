import pytest
import os
import json
from src.nhc_hurricane import (
    NHCHurricaneConnector,
    save_nhc_vintage_record,
    get_nhc_vintages_as_of
)


def test_nhc_hurricane_connector_schema():
    connector = NHCHurricaneConnector()
    data = connector.fetch_active_hurricane_threats()
    assert isinstance(data, dict)
    assert "active_storms_count" in data
    assert "gulf_hurricane_active" in data
    assert "nhc_hurricane_threat_index" in data
    assert "nhc_gulf_refinery_exposure_score" in data
    assert "nhc_colonial_pipeline_risk_score" in data


def test_nhc_vintage_persistence(tmp_path):
    temp_file = str(tmp_path / "nhc_vintages.json")
    record = {
        "active_storms_count": 2,
        "gulf_hurricane_active": True,
        "nhc_hurricane_threat_index": 0.70,
        "nhc_gulf_refinery_exposure_score": 1.05
    }
    save_nhc_vintage_record(record, filepath=temp_file)
    assert os.path.exists(temp_file)

    loaded = get_nhc_vintages_as_of("2099-12-31", filepath=temp_file)
    assert loaded is not None
    assert loaded["nhc_hurricane_threat_index"] == 0.70
    assert loaded["gulf_hurricane_active"] is True
