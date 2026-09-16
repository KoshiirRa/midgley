import os
import json
import pytest
from src.data_ingestion import FERCDataConnector
from src.lookup_cache import global_cache

def test_ferc_pipeline_tariffs():
    connector = FERCDataConnector()
    global_cache.delete("ferc_pipeline_tariffs")
    data = connector.fetch_pipeline_tariff_data()
    
    assert data["status"] in ["SUCCESS", "FALLBACK"]
    assert "ferc_colonial_line1_tariff_per_bbl" in data
    assert "ferc_plantation_tariff_per_bbl" in data
    assert "ferc_explorer_tariff_per_bbl" in data
    assert "ferc_pipeline_tariff_index_5d" in data
    assert data["ferc_colonial_line1_tariff_per_bbl"] > 0.50
    assert data["ferc_pipeline_tariff_index_5d"] > 0.50

def test_ferc_bitemporal_persistence(tmp_path):
    temp_vintage = str(tmp_path / "ferc_vintages_test.json")
    connector = FERCDataConnector()
    
    rec = {
        "status": "SUCCESS",
        "as_of": "2026-09-15 11:00:00",
        "valid_date": "2026-09-15",
        "ferc_colonial_line1_tariff_per_bbl": 2.15,
        "is_vintage_reconstructed": False
    }
    connector.save_ferc_vintage_record(rec, filepath=temp_vintage)
    vintages = connector.get_ferc_vintages_as_of("2026-09-15", filepath=temp_vintage)
    assert len(vintages) == 1
    assert vintages[0]["ferc_colonial_line1_tariff_per_bbl"] == 2.15
