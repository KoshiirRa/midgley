import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.key_movers_feed import (
    KeyMoversFeedConnector,
    fetch_key_movers_headlines,
    HISTORICAL_KEY_MOVERS_EVENTS
)
from src.lookup_cache import global_cache

def test_key_movers_historical_fallback():
    connector = KeyMoversFeedConnector()
    events = connector.fetch_key_movers_events(force_refresh=True)
    assert len(events) >= len(HISTORICAL_KEY_MOVERS_EVENTS)
    for ev in events:
        assert "headline" in ev
        assert "source" in ev
        assert "category" in ev

def test_key_movers_headline_extraction():
    headlines = fetch_key_movers_headlines()
    assert isinstance(headlines, list)
    assert len(headlines) > 0
    assert any("oil" in h.lower() or "gas" in h.lower() or "reserve" in h.lower() or "energy" in h.lower() or "spr" in h.lower() for h in headlines)

def test_key_movers_bitemporal_persistence(tmp_path):
    temp_vintage_file = str(tmp_path / "key_movers_vintages_test.json")
    connector = KeyMoversFeedConnector()
    
    test_record = {
        "source": "Key Movers Feed (Test)",
        "as_of": "2026-09-15 12:00:00",
        "valid_date": "2026-09-15",
        "headline": "Emergency test refinery catalyst event",
        "category": "refinery_outage",
        "is_vintage_reconstructed": False
    }
    
    connector.save_key_movers_vintage_record(test_record, filepath=temp_vintage_file)
    assert os.path.exists(temp_vintage_file)
    
    vintages = connector.get_key_movers_vintages_as_of("2026-09-15", filepath=temp_vintage_file)
    assert len(vintages) == 1
    assert vintages[0]["category"] == "refinery_outage"

def test_key_movers_caching():
    connector = KeyMoversFeedConnector()
    cache_key = "key_movers:events:all"
    global_cache.delete(cache_key)
    
    events1 = connector.fetch_key_movers_events()
    assert len(events1) > 0
    
    # Second fetch should hit cache
    events2 = connector.fetch_key_movers_events()
    assert len(events2) == len(events1)
