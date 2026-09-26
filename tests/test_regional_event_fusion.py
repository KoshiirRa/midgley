import os
import json
import pytest
import pandas as pd
from datetime import datetime, timezone
from src.data_ingestion import load_live_regional_intraday_events, get_historical_event_dataset
from src.locations.tulsa.regional import get_tulsa_regional_events
from src.locations.newark.regional import get_newark_regional_events
from src.locations.cincinnati.regional import get_cincinnati_regional_events
from src.locations.greenville.regional import get_greenville_regional_events
from src.locations.charlotte.regional import get_charlotte_regional_events
from src.locations.oakland.regional import get_oakland_regional_events
from src.locations.port_st_lucie.regional import get_port_st_lucie_regional_events


@pytest.fixture
def mock_intraday_events(tmp_path):
    """Create a temporary intraday_events.json file for testing."""
    test_events_path = tmp_path / "intraday_events.json"
    
    events_data = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "headline": "West Tulsa Refinery unplanned FCC unit trip causes supply tightness",
            "source": "Breaking_Energy_News",
            "overall_price_pressure": 0.55,
            "supply_disruption": 0.70,
            "geopolitical_risk": 0.0,
            "target_locales": ["Tulsa"]
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "headline": "Severe flooding on Ohio River restricts barge navigation near Cincinnati",
            "source": "Inland_Maritime_Alert",
            "overall_price_pressure": 0.40,
            "supply_disruption": 0.50,
            "geopolitical_risk": 0.0,
            "target_locales": ["Cincinnati"]
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "headline": "Global crude oil price spike due to Middle East chokepoint tensions",
            "source": "Global_Wire",
            "overall_price_pressure": 0.65,
            "supply_disruption": 0.60,
            "geopolitical_risk": 0.80,
            "target_locales": ["National"]
        }
    ]
    
    with open(test_events_path, "w", encoding="utf-8") as f:
        json.dump(events_data, f, indent=2)
        
    return str(test_events_path)


def test_load_live_regional_intraday_events(mock_intraday_events):
    """Test loading and filtering live regional events for specific metro areas."""
    events_tulsa = load_live_regional_intraday_events(region_name="Tulsa", events_path=mock_intraday_events)
    assert isinstance(events_tulsa, pd.DataFrame)
    assert len(events_tulsa) == 1  # Tulsa-specific
    headlines_tulsa = events_tulsa["headline"].tolist()
    assert any("West Tulsa Refinery" in h for h in headlines_tulsa)
    
    events_cincinnati = load_live_regional_intraday_events(region_name="Cincinnati", events_path=mock_intraday_events)
    assert isinstance(events_cincinnati, pd.DataFrame)
    assert len(events_cincinnati) == 1  # Cincinnati-specific
    headlines_cincinnati = events_cincinnati["headline"].tolist()
    assert any("Ohio River" in h for h in headlines_cincinnati)
    
    events_national = load_live_regional_intraday_events(region_name="National", events_path=mock_intraday_events)
    assert isinstance(events_national, pd.DataFrame)
    assert len(events_national) == 1  # National-specific
    assert "Middle East chokepoint" in events_national.iloc[0]["headline"]

    events_oakland = load_live_regional_intraday_events(region_name="Oakland", events_path=mock_intraday_events)
    assert isinstance(events_oakland, pd.DataFrame)
    assert len(events_oakland) == 0  # No Oakland event in mock fixture


def test_regional_event_getters_fusion():
    """Test that all 7 metro regional event getters run without error and fuse live anomalies."""
    tulsa_events = get_tulsa_regional_events()
    assert isinstance(tulsa_events, pd.DataFrame)
    assert len(tulsa_events) > 0
    assert "date" in tulsa_events.columns
    
    newark_events = get_newark_regional_events()
    assert isinstance(newark_events, pd.DataFrame)
    assert len(newark_events) > 0
    assert "date" in newark_events.columns
    
    cincinnati_events = get_cincinnati_regional_events()
    assert isinstance(cincinnati_events, pd.DataFrame)
    assert len(cincinnati_events) > 0
    assert "date" in cincinnati_events.columns
    
    greenville_events = get_greenville_regional_events()
    assert isinstance(greenville_events, pd.DataFrame)
    assert len(greenville_events) > 0
    assert "date" in greenville_events.columns
    
    charlotte_events = get_charlotte_regional_events()
    assert isinstance(charlotte_events, pd.DataFrame)
    assert len(charlotte_events) > 0
    assert "date" in charlotte_events.columns
    
    oakland_events = get_oakland_regional_events()
    assert isinstance(oakland_events, pd.DataFrame)
    assert len(oakland_events) > 0
    assert "date" in oakland_events.columns
    
    port_st_lucie_events = get_port_st_lucie_regional_events()
    assert isinstance(port_st_lucie_events, pd.DataFrame)
    assert len(port_st_lucie_events) > 0
    assert "date" in port_st_lucie_events.columns
