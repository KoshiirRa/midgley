import os
import json
import pytest
from src.data_ingestion import EIAStateMetroRetailConnector
from src.lookup_cache import global_cache

def test_state_retail_prices():
    connector = EIAStateMetroRetailConnector()
    for st in ["CA", "TX", "NY", "OH", "FL", "MA", "MI", "MN", "CO", "WA"]:
        global_cache.delete(f"eia_state_retail_{st}")
        data = connector.fetch_state_retail_price(st)
        assert data["state_code"] == st
        assert data["price"] > 1.50
        assert "as_of" in data

def test_metro_retail_prices():
    connector = EIAStateMetroRetailConnector()
    for metro in ["SanFrancisco", "LosAngeles", "Chicago", "Houston", "Cleveland", "NewYorkCity", "Miami", "Boston", "Denver", "Seattle"]:
        global_cache.delete(f"eia_metro_retail_{metro}")
        data = connector.fetch_metro_retail_price(metro)
        assert data["metro_name"] == metro
        assert data["price"] > 1.50
        assert "as_of" in data
