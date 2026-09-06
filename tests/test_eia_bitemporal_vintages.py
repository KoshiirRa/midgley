"""
Unit tests for Issue #121: EIA Bitemporal Vintage Tracking (as_of)
Tests bitemporal metadata fields (as_of, valid_date, is_vintage_reconstructed),
vintage storage & point-in-time lookup helpers, and feature matrix cutoff filtering.
"""

import os
import json
import tempfile
import pytest
import pandas as pd
from datetime import datetime
from src.data_ingestion import EIADataConnector, EIAStateMetroRetailConnector
from src.feature_engineering import create_feature_matrix
from src.alternative_data_feeds import ALTERNATIVE_DATA_SOURCES

def test_eia_connector_bitemporal_fields():
    """Verify EIADataConnector & EIAStateMetroRetailConnector return as_of, valid_date, and is_vintage_reconstructed."""
    inventory_connector = EIADataConnector()
    retail_connector = EIAStateMetroRetailConnector()
    
    inventory_data = inventory_connector.fetch_padd_inventory_and_refinery_data()
    assert "as_of" in inventory_data
    assert "valid_date" in inventory_data
    assert "is_vintage_reconstructed" in inventory_data
    assert inventory_data["is_vintage_reconstructed"] is False

    state_data = retail_connector.fetch_state_retail_price("CA")
    assert "as_of" in state_data
    assert "valid_date" in state_data
    assert "is_vintage_reconstructed" in state_data

    metro_data = retail_connector.fetch_metro_retail_price("SanFrancisco")
    assert "as_of" in metro_data
    assert "valid_date" in metro_data
    assert "is_vintage_reconstructed" in metro_data


def test_eia_vintage_persistence_and_lookup():
    """Test save_eia_vintage_record and get_eia_vintages_as_of with temporary JSON datastore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = os.path.join(tmpdir, "eia_vintages_test.json")
        
        rec1 = {
            "source": "EIA WPSR Test 1",
            "as_of": "2026-08-01 10:30:00",
            "valid_date": "2026-07-25",
            "is_vintage_reconstructed": True,
            "gasoline_stocks_million_bbl": 50.0
        }
        rec2 = {
            "source": "EIA WPSR Test 2",
            "as_of": "2026-08-15 10:30:00",
            "valid_date": "2026-08-08",
            "is_vintage_reconstructed": False,
            "gasoline_stocks_million_bbl": 52.5
        }
        
        EIADataConnector.save_eia_vintage_record(rec1, filepath=tmp_file)
        EIADataConnector.save_eia_vintage_record(rec2, filepath=tmp_file)

        # Retrieve all
        all_vintages = EIADataConnector.get_eia_vintages_as_of(target_as_of=None, filepath=tmp_file)
        assert len(all_vintages) == 2

        # Retrieve as of 2026-08-05 (should return only rec1)
        aug05_vintages = EIADataConnector.get_eia_vintages_as_of(target_as_of="2026-08-05", filepath=tmp_file)
        assert len(aug05_vintages) == 1
        assert aug05_vintages[0]["as_of"] == "2026-08-01 10:30:00"

        # Retrieve as of 2026-08-20 (should return both rec1 and rec2)
        aug20_vintages = EIADataConnector.get_eia_vintages_as_of(target_as_of="2026-08-20", filepath=tmp_file)
        assert len(aug20_vintages) == 2


def test_feature_matrix_as_of_cutoff():
    """Verify create_feature_matrix accepts as_of_cutoff without throwing exceptions."""
    market_dates = pd.date_range("2026-01-01", periods=60, freq="B")
    market_df = pd.DataFrame({
        "date": market_dates,
        "gasoline_rbob": [2.50 + i * 0.01 for i in range(60)],
        "wti_crude": [70.0 + i * 0.2 for i in range(60)],
        "brent_crude": [75.0 + i * 0.2 for i in range(60)]
    })

    # Call with as_of_cutoff parameter
    feat_df = create_feature_matrix(market_df, as_of_cutoff="2026-02-15 23:59:59")
    assert not feat_df.empty
    assert len(feat_df) > 0
    assert "rbob_rsi_14" in feat_df.columns


def test_alternative_data_sources_metadata():
    """Verify ALTERNATIVE_DATA_SOURCES includes bitemporal_architecture metadata."""
    assert "bitemporal_architecture" in ALTERNATIVE_DATA_SOURCES["EIA_Weekly_Inventories"]
    bitemp = ALTERNATIVE_DATA_SOURCES["EIA_Weekly_Inventories"]["bitemporal_architecture"]
    assert "as_of" in bitemp["fields"]
    assert "valid_date" in bitemp["fields"]
    assert "is_vintage_reconstructed" in bitemp["fields"]
