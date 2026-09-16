import os
import json
import pytest
from src.data_ingestion import EIADataConnector
from src.lookup_cache import global_cache

def test_eia_padd_refinery_inventory_structure():
    connector = EIADataConnector()
    global_cache.delete("eia_padd_refinery_inventory")
    data = connector.fetch_padd_inventory_and_refinery_data()
    
    assert data["status"] == "SUCCESS"
    assert "refinery_utilization" in data
    assert "PADD1_EastCoast" in data["refinery_utilization"]
    assert "PADD2_Midwest" in data["refinery_utilization"]
    assert "PADD3_GulfCoast" in data["refinery_utilization"]
    assert "PADD5_WestCoast" in data["refinery_utilization"]
    
    assert "gasoline_stocks_million_bbl" in data
    assert "product_supplied_thousand_bpd" in data
    assert "us_motor_gasoline" in data["product_supplied_thousand_bpd"]
    assert "as_of" in data
    assert "valid_date" in data

def test_eia_padd_bitemporal_persistence(tmp_path):
    temp_vintage = str(tmp_path / "eia_vintages_test.json")
    connector = EIADataConnector()
    
    rec = {
        "source": "U.S. EIA Test",
        "as_of": "2026-09-15 10:00:00",
        "valid_date": "2026-09-15",
        "refinery_utilization": {"PADD3_GulfCoast": 95.5},
        "is_vintage_reconstructed": False
    }
    connector.save_eia_vintage_record(rec, filepath=temp_vintage)
    vintages = connector.get_eia_vintages_as_of("2026-09-15", filepath=temp_vintage)
    assert len(vintages) == 1
    assert vintages[0]["refinery_utilization"]["PADD3_GulfCoast"] == 95.5
