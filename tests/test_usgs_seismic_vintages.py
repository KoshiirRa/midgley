"""
Unit tests for USGS Seismic Telemetry Vintage Persistence (Issue #292).
"""
import os
import tempfile
import pytest
from src.usgs_seismic import (
    USGSSeismicConnector,
    save_seismic_vintage_record,
    get_seismic_vintages_as_of,
)

def test_seismic_vintage_persistence_and_as_of_filtering():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        rec1 = {
            "filtered_corridor": "bay_area",
            "as_of": "2026-03-01 10:00:00",
            "valid_date": "2026-03-01",
            "indices": {
                "composite_seismic_risk_index": 0.15,
                "max_magnitude": 4.2,
                "total_significant_quakes": 1
            }
        }
        rec2 = {
            "filtered_corridor": "cushing_ok",
            "as_of": "2026-03-10 10:00:00",
            "valid_date": "2026-03-10",
            "indices": {
                "composite_seismic_risk_index": 0.45,
                "max_magnitude": 4.8,
                "total_significant_quakes": 2
            }
        }
        rec3 = {
            "filtered_corridor": "bay_area",
            "as_of": "2026-03-15 10:00:00",
            "valid_date": "2026-03-15",
            "indices": {
                "composite_seismic_risk_index": 0.05,
                "max_magnitude": 3.9,
                "total_significant_quakes": 0
            }
        }

        save_seismic_vintage_record(rec1, filepath=temp_path)
        save_seismic_vintage_record(rec2, filepath=temp_path)
        save_seismic_vintage_record(rec3, filepath=temp_path)

        # Query as of 2026-03-05
        vintages_early = get_seismic_vintages_as_of("2026-03-05", filepath=temp_path)
        assert len(vintages_early) == 1
        assert vintages_early[0]["corridor_key"] == "bay_area"
        assert vintages_early[0]["max_magnitude"] == 4.2

        # Query as of 2026-03-12 for cushing_ok
        vintages_cushing = get_seismic_vintages_as_of("2026-03-12", corridor="cushing_ok", filepath=temp_path)
        assert len(vintages_cushing) == 1
        assert vintages_cushing[0]["composite_seismic_risk_index"] == 0.45

        # Query as of 2026-03-20
        vintages_all = get_seismic_vintages_as_of("2026-03-20", filepath=temp_path)
        assert len(vintages_all) == 3

        # Connector methods
        conn = USGSSeismicConnector()
        conn_vintages = conn.get_seismic_vintages_as_of("2026-03-20", corridor="bay_area", filepath=temp_path)
        assert len(conn_vintages) == 2

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
