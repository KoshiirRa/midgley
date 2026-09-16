"""
Unit tests for USGS Water Data Telemetry Vintage Persistence (Issue #293).
"""
import os
import tempfile
import pytest
from src.usgs_water_feed import (
    USGSWaterFeedConnector,
    save_water_vintage_record,
    get_water_vintages_as_of,
)

def test_water_vintage_persistence_and_as_of_filtering():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        rec1 = {
            "filtered_cluster": "inland_barge",
            "as_of": "2026-03-01 10:00:00",
            "valid_date": "2026-03-01",
            "stations_monitored": 3,
            "indices": {
                "hydrological_barge_bottleneck_index": 0.20,
                "is_barge_draft_restricted": False
            }
        }
        rec2 = {
            "filtered_cluster": "gulf_coast",
            "as_of": "2026-03-10 10:00:00",
            "valid_date": "2026-03-10",
            "stations_monitored": 4,
            "indices": {
                "gulf_marine_departure_risk_index": 0.55,
                "is_gulf_departure_halted": True
            }
        }
        rec3 = {
            "filtered_cluster": "inland_barge",
            "as_of": "2026-03-15 10:00:00",
            "valid_date": "2026-03-15",
            "stations_monitored": 3,
            "indices": {
                "hydrological_barge_bottleneck_index": 0.42,
                "is_barge_draft_restricted": True
            }
        }

        save_water_vintage_record(rec1, filepath=temp_path)
        save_water_vintage_record(rec2, filepath=temp_path)
        save_water_vintage_record(rec3, filepath=temp_path)

        # Query as of 2026-03-05
        vintages_early = get_water_vintages_as_of("2026-03-05", filepath=temp_path)
        assert len(vintages_early) == 1
        assert vintages_early[0]["cluster_key"] == "inland_barge"

        # Query as of 2026-03-12 for gulf_coast
        vintages_gulf = get_water_vintages_as_of("2026-03-12", cluster="gulf_coast", filepath=temp_path)
        assert len(vintages_gulf) == 1
        assert vintages_gulf[0]["indices"]["is_gulf_departure_halted"] is True

        # Query as of 2026-03-20
        vintages_all = get_water_vintages_as_of("2026-03-20", filepath=temp_path)
        assert len(vintages_all) == 3

        # Connector methods
        conn = USGSWaterFeedConnector()
        conn_vintages = conn.get_water_vintages_as_of("2026-03-20", cluster="inland_barge", filepath=temp_path)
        assert len(conn_vintages) == 2

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
