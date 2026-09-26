import os
import json
import pytest
from src.data_ingestion import USDABiofuelConnector
from src.lookup_cache import global_cache

def test_usda_biofuel_ethanol_offset():
    connector = USDABiofuelConnector()
    global_cache.delete("usda_ethanol_blendstock")
    data = connector.fetch_ethanol_blendstock_costs()
    
    assert data["status"] in ["SUCCESS", "OBSERVED", "ESTIMATED", "FALLBACK"]
    assert "e100_ethanol_rack_price_per_gal" in data
    assert "rin_d6_credit_value_per_gal" in data
    assert "calculated_e10_blendstock_offset_per_gal" in data
    assert data["e100_ethanol_rack_price_per_gal"] > 0
    assert data["rin_d6_credit_value_per_gal"] > 0
    assert "as_of" in data

def test_usda_biofuel_bitemporal_persistence(tmp_path):
    temp_vintage = str(tmp_path / "usda_biofuel_vintages_test.json")
    connector = USDABiofuelConnector()
    
    rec = {
        "source": "USDA Biofuel Test",
        "as_of": "2026-09-15 10:00:00",
        "valid_date": "2026-09-15",
        "e100_ethanol_rack_price_per_gal": 1.70,
        "calculated_e10_blendstock_offset_per_gal": -0.120,
        "is_vintage_reconstructed": False
    }
    connector.save_usda_biofuel_vintage_record(rec, filepath=temp_vintage)
    vintages = connector.get_usda_biofuel_vintages_as_of("2026-09-15", filepath=temp_vintage)
    assert len(vintages) == 1
    assert vintages[0]["e100_ethanol_rack_price_per_gal"] == 1.70
