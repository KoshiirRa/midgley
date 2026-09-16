import pytest
import os
import json
import pandas as pd
from src.geopolitical_feeds import (
    GeopoliticalFeedConnector,
    get_geopolitical_maritime_events,
    calculate_chokepoint_risk_index,
    save_geopolitical_vintage_record,
    get_geopolitical_vintages_as_of,
    CHOKEPOINTS
)


def test_geopolitical_historical_events():
    df = get_geopolitical_maritime_events()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "date" in df.columns
    assert "headline" in df.columns
    assert "chokepoint" in df.columns
    assert "Strait_of_Hormuz" in df["chokepoint"].values


def test_chokepoint_risk_index():
    df = get_geopolitical_maritime_events()
    scores = calculate_chokepoint_risk_index(df)
    assert isinstance(scores, dict)
    assert "Strait_of_Hormuz" in scores
    assert "Suez_Bab_el_Mandeb" in scores
    assert "Venezuela_Orinoco" in scores
    assert "chokepoint_risk_score" in scores["Strait_of_Hormuz"]


def test_geopolitical_vintage_persistence(tmp_path):
    temp_file = str(tmp_path / "geopolitical_vintages.json")
    records = [
        {"date": "2026-09-15", "headline": "Test Hormuz Event", "chokepoint": "Strait_of_Hormuz"}
    ]
    save_geopolitical_vintage_record(records, filepath=temp_file)
    assert os.path.exists(temp_file)

    loaded = get_geopolitical_vintages_as_of("2099-12-31", filepath=temp_file)
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0]["headline"] == "Test Hormuz Event"


def test_geopolitical_connector():
    connector = GeopoliticalFeedConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0
    headlines = connector.fetch_geopolitical_headlines()
    assert isinstance(headlines, list)
