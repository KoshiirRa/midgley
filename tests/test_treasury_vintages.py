"""
Unit tests for U.S. Treasury Yield Telemetry Vintage Persistence (Issue #294).
"""
import os
import tempfile
import pytest
from src.treasury_yield_feed import (
    TreasuryYieldConnector,
    save_treasury_vintage_record,
    get_treasury_vintages_as_of,
)

def test_treasury_vintage_persistence_and_as_of_filtering():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        rec1 = {
            "date": "2026-03-01",
            "as_of": "2026-03-01 16:00:00",
            "treasury_yield_10y": 4.25,
            "treasury_yield_2y": 4.05,
            "treasury_yield_10y_2y_spread": 0.20,
            "tips_10y_real_yield": 2.00,
            "curve_state": "Normal Sloped"
        }
        rec2 = {
            "date": "2026-03-10",
            "as_of": "2026-03-10 16:00:00",
            "treasury_yield_10y": 4.10,
            "treasury_yield_2y": 4.25,
            "treasury_yield_10y_2y_spread": -0.15,
            "tips_10y_real_yield": 1.90,
            "curve_state": "Inverted (Recessionary Warning)"
        }
        rec3 = {
            "date": "2026-03-15",
            "as_of": "2026-03-15 16:00:00",
            "treasury_yield_10y": 4.30,
            "treasury_yield_2y": 4.15,
            "treasury_yield_10y_2y_spread": 0.15,
            "tips_10y_real_yield": 2.05,
            "curve_state": "Normal Sloped"
        }

        save_treasury_vintage_record(rec1, filepath=temp_path)
        save_treasury_vintage_record(rec2, filepath=temp_path)
        save_treasury_vintage_record(rec3, filepath=temp_path)

        # Query as of 2026-03-05
        vintages_early = get_treasury_vintages_as_of("2026-03-05", filepath=temp_path)
        assert len(vintages_early) == 1
        assert vintages_early[0]["treasury_yield_10y_2y_spread"] == 0.20

        # Query as of 2026-03-12
        vintages_mid = get_treasury_vintages_as_of("2026-03-12", filepath=temp_path)
        assert len(vintages_mid) == 2
        assert vintages_mid[1]["curve_state"] == "Inverted (Recessionary Warning)"

        # Query as of 2026-03-20
        vintages_all = get_treasury_vintages_as_of("2026-03-20", filepath=temp_path)
        assert len(vintages_all) == 3

        # Connector methods
        conn = TreasuryYieldConnector()
        conn_vintages = conn.get_treasury_vintages_as_of("2026-03-20", filepath=temp_path)
        assert len(conn_vintages) == 3

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
