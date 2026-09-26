"""Unit tests for ALFRED Publication Vintage Connector (ALFREDVintageConnector).

Tests ALFRED series vintage ingestion, publication date filtering, point-in-time snapshot
reconstruction without lookahead revision leakage, and vintage date discovery.
"""

import pandas as pd
import pytest

from src.alfred_vintages import ALFREDVintageConnector


def test_alfred_connector_initialization(tmp_path):
    """Test connector initialization with custom storage path."""
    vintage_file = tmp_path / "alfred_test.json"
    connector = ALFREDVintageConnector(vintage_path=str(vintage_file))
    assert connector.vintage_path == str(vintage_file)


def test_alfred_fetch_series_vintages():
    """Test retrieving ALFRED historical vintages for GASREGW."""
    connector = ALFREDVintageConnector()
    df = connector.fetch_series_vintages(series_id="GASREGW")
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "date" in df.columns
    assert "value" in df.columns
    assert "vintage_date" in df.columns


def test_alfred_point_in_time_snapshot_reconstruction():
    """Test that get_vintage_snapshot returns preliminary data before revision is published."""
    connector = ALFREDVintageConnector()
    
    # On 2023-06-01, the observation for 2023-05-29 was 3.571 (published 2023-05-31)
    snapshot_early = connector.get_vintage_snapshot(series_id="GASREGW", as_of="2023-06-01")
    obs_early = snapshot_early[snapshot_early["date"] == pd.Timestamp("2023-05-29")].iloc[0]
    assert obs_early["value"] == 3.571
    
    # On 2023-06-15, the revised observation for 2023-05-29 was published as 3.574 (vintage 2023-06-13)
    snapshot_late = connector.get_vintage_snapshot(series_id="GASREGW", as_of="2023-06-15")
    obs_late = snapshot_late[snapshot_late["date"] == pd.Timestamp("2023-05-29")].iloc[0]
    assert obs_late["value"] == 3.574


def test_alfred_available_vintage_dates():
    """Test retrieving list of available publication vintage dates."""
    connector = ALFREDVintageConnector()
    vintages = connector.get_available_vintage_dates(series_id="GASREGW")
    
    assert isinstance(vintages, list)
    assert len(vintages) >= 3
