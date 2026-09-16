import os
import json
import pytest
from unittest.mock import patch
from src.data_ingestion import (
    FREDDataConnector,
    save_fred_vintage_record,
    get_fred_vintages_as_of
)

def test_fred_vintage_tracking(tmp_path):
    v_file = str(tmp_path / "fred_vintages.json")
    record = {
        "series_id": "DCOILWTICO",
        "value": 78.50,
        "as_of": "2026-03-15 12:00:00",
        "valid_date": "2026-03-15",
        "source": "FRED API (DCOILWTICO)"
    }
    
    save_fred_vintage_record(record, filepath=v_file)
    assert os.path.exists(v_file)
    
    vintages = get_fred_vintages_as_of("2026-03-16", series_id="DCOILWTICO", filepath=v_file)
    assert len(vintages) == 1
    assert vintages[0]["series_id"] == "DCOILWTICO"
    assert vintages[0]["value"] == 78.50

def test_fred_connector_vintage_integration(tmp_path):
    v_file = str(tmp_path / "fred_vintages.json")
    connector = FREDDataConnector()
    connector.VINTAGE_FILE = v_file
    
    # In offline fallback, it should return anchor data and save vintage
    res = connector.fetch_series("GASREGW")
    assert res["status"] in ("FALLBACK", "SUCCESS")
    assert res["series_id"] == "GASREGW"
    assert res["value"] is not None
