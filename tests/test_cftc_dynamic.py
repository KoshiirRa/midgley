import pytest
import os
import json
from src.data_ingestion import (
    CFTCDataConnector,
    save_cftc_vintage_record,
    get_cftc_vintages_as_of
)


def test_cftc_cot_positioning_schema():
    connector = CFTCDataConnector()
    data = connector.fetch_cot_positioning_data()
    assert isinstance(data, dict)
    assert "report_date" in data
    assert "cot_rbob_net_speculative" in data
    assert "cot_rbob_zscore_3y" in data
    assert "cot_commercial_hedger_ratio" in data
    assert "cot_net_position_delta_1w" in data
    assert data["is_free_alternative"] is True


def test_cftc_vintage_persistence(tmp_path):
    temp_file = str(tmp_path / "cftc_vintages.json")
    record = {
        "report_date": "2026-09-15",
        "cot_rbob_net_speculative": 85000.0,
        "cot_net_position_delta_1w": 2500.0,
        "status": "SUCCESS"
    }
    save_cftc_vintage_record(record, filepath=temp_file)
    assert os.path.exists(temp_file)

    loaded = get_cftc_vintages_as_of("2099-12-31", filepath=temp_file)
    assert loaded is not None
    assert loaded["cot_rbob_net_speculative"] == 85000.0
