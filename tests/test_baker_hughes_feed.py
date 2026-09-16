import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.alternative_data_feeds import (
    BakerHughesDataConnector,
    get_baker_hughes_rig_count_feed,
    fetch_baker_hughes_rig_counts,
    HISTORICAL_BAKER_HUGHES_RIGS
)
from src.lookup_cache import global_cache

def test_baker_hughes_historical_fallback():
    connector = BakerHughesDataConnector()
    df = connector.fetch_rig_counts()
    assert not df.empty
    assert "date" in df.columns
    assert "baker_hughes_oil_rigs" in df.columns
    assert "baker_hughes_us_rig_count" in df.columns
    assert "baker_hughes_gas_rigs" in df.columns
    assert "baker_hughes_rig_delta_1w" in df.columns
    assert len(df) >= len(HISTORICAL_BAKER_HUGHES_RIGS)

def test_fetch_baker_hughes_rig_counts_schema():
    df = fetch_baker_hughes_rig_counts(start_date="2023-01-01")
    assert not df.empty
    assert (df['date'] >= pd.to_datetime("2023-01-01")).all()
    assert all(col in df.columns for col in [
        'date', 'baker_hughes_us_rig_count', 'baker_hughes_oil_rigs', 
        'baker_hughes_gas_rigs', 'baker_hughes_rig_delta_1w'
    ])

def test_baker_hughes_bitemporal_persistence(tmp_path):
    temp_vintage_file = str(tmp_path / "baker_hughes_vintages_test.json")
    connector = BakerHughesDataConnector()
    
    test_record = {
        "source": "Baker Hughes Rig Count (Test)",
        "as_of": "2026-09-15 12:00:00",
        "valid_date": "2026-09-15",
        "latest_us_active_oil_rigs": 485,
        "latest_us_total_rigs": 585,
        "is_vintage_reconstructed": False
    }
    
    connector.save_baker_hughes_vintage_record(test_record, filepath=temp_vintage_file)
    assert os.path.exists(temp_vintage_file)
    
    vintages = connector.get_baker_hughes_vintages_as_of("2026-09-15", filepath=temp_vintage_file)
    assert len(vintages) == 1
    assert vintages[0]["latest_us_active_oil_rigs"] == 485

def test_baker_hughes_caching():
    connector = BakerHughesDataConnector()
    cache_key = "altdata:baker_hughes:all"
    global_cache.delete(cache_key)
    
    # First fetch populates cache
    df1 = connector.fetch_rig_counts()
    cached = global_cache.get(cache_key)
    assert cached is not None
    assert "records" in cached
    
    # Second fetch uses cache
    df2 = connector.fetch_rig_counts()
    assert len(df1) == len(df2)
