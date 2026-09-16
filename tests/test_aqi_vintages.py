"""
Unit tests for AQI & Industrial Emissions Telemetry Vintage Persistence (Issue #291).
"""
import os
import tempfile
import pytest
from src.aqi_feed import (
    AQIFeedConnector,
    save_aqi_vintage_record,
    get_aqi_vintages_as_of,
)

def test_aqi_vintage_persistence_and_as_of_filtering():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        rec1 = {
            "corridor": "bay_area",
            "zip_code": "94612",
            "as_of": "2026-03-01 10:00:00",
            "valid_date": "2026-03-01",
            "aqi": 45,
            "category": "Good",
            "is_unplanned_outage": False
        }
        rec2 = {
            "corridor": "tulsa",
            "zip_code": "74101",
            "as_of": "2026-03-10 10:00:00",
            "valid_date": "2026-03-10",
            "aqi": 115,
            "category": "Unhealthy for Sensitive Groups",
            "is_unplanned_outage": True
        }
        rec3 = {
            "corridor": "bay_area",
            "zip_code": "94612",
            "as_of": "2026-03-15 10:00:00",
            "valid_date": "2026-03-15",
            "aqi": 52,
            "category": "Moderate",
            "is_unplanned_outage": False
        }

        save_aqi_vintage_record(rec1, filepath=temp_path)
        save_aqi_vintage_record(rec2, filepath=temp_path)
        save_aqi_vintage_record(rec3, filepath=temp_path)

        # Query as of 2026-03-05
        vintages_early = get_aqi_vintages_as_of("2026-03-05", filepath=temp_path)
        assert len(vintages_early) == 1
        assert vintages_early[0]["corridor"] == "bay_area"
        assert vintages_early[0]["aqi"] == 45

        # Query as of 2026-03-12 for tulsa
        vintages_tulsa = get_aqi_vintages_as_of("2026-03-12", corridor="tulsa", filepath=temp_path)
        assert len(vintages_tulsa) == 1
        assert vintages_tulsa[0]["is_unplanned_outage"] is True

        # Query as of 2026-03-20
        vintages_all = get_aqi_vintages_as_of("2026-03-20", filepath=temp_path)
        assert len(vintages_all) == 3

        # Connector methods
        conn = AQIFeedConnector(use_cache=False)
        conn_vintages = conn.get_aqi_vintages_as_of("2026-03-20", zip_code="94612", filepath=temp_path)
        assert len(conn_vintages) == 2

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
