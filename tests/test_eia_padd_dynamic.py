import os
import json
import pytest
from src.data_ingestion import EIADataConnector
from src.lookup_cache import global_cache

def test_eia_padd_refinery_inventory_structure():
    connector = EIADataConnector()
    global_cache.delete("eia_padd_refinery_inventory")
    data = connector.fetch_padd_inventory_and_refinery_data()
    
    assert data["status"] in ["SUCCESS", "OBSERVED", "ESTIMATED", "FALLBACK"]
    assert "refinery_utilization" in data
    assert "PADD1_EastCoast" in data["refinery_utilization"]
    assert "PADD2_Midwest" in data["refinery_utilization"]
    assert "PADD3_GulfCoast" in data["refinery_utilization"]
    assert "PADD4_Rockies" in data["refinery_utilization"]
    assert "PADD5_WestCoast" in data["refinery_utilization"]
    
    assert "gasoline_stocks_million_bbl" in data
    assert "PADD4" in data["gasoline_stocks_million_bbl"]
    assert "PADD5" in data["gasoline_stocks_million_bbl"]
    assert "product_supplied_thousand_bpd" in data
    assert "us_motor_gasoline" in data["product_supplied_thousand_bpd"]
    assert "as_of" in data
    assert "valid_date" in data


def test_eia_padd4_and_padd5_series_provenance():
    """Verifies PADD 4 and PADD 5 WPSR series are registered in EIA_SERIES_PROVENANCE (Issue #649)."""
    from src.eia_api_client import EIA_SERIES_PROVENANCE

    for sid in ("WGTSTP41", "WGTSTP51", "W_NA_YUP_R40_PER", "W_NA_YUP_R50_PER"):
        assert sid in EIA_SERIES_PROVENANCE
        assert EIA_SERIES_PROVENANCE[sid]["geo"] in ("PADD_4", "PADD_5")


def test_eia_phase2_inter_padd_logistics_and_flows(monkeypatch):
    """Verifies Phase 2 pipeline shipments and PADD 1/3 import-export flows & publication lags (Issue #649)."""
    from unittest.mock import MagicMock
    from src.eia_api_client import EIAClientV2, EIA_SERIES_PROVENANCE

    for sid in ("M_EPM0_MPL_R30-R10_MBBL", "WIRPUS1", "W_EPM0_IM0_R10-Z00_MBBLD", "W_EPM0_EEX_R30-Z00_MBBLD"):
        assert sid in EIA_SERIES_PROVENANCE

    # Test weekly WPSR flow parsing & Wed 15:30 UTC lag (+5 days from Friday 2026-10-02 -> 2026-10-07T15:30:00Z)
    client = EIAClientV2(api_key="test-key")
    mock_resp_wkly = MagicMock()
    mock_resp_wkly.status_code = 200
    mock_resp_wkly.json.return_value = {"response": {"data": [{"period": "2026-10-02", "value": "645.5"}]}}
    client.session = MagicMock()
    client.session.get.return_value = mock_resp_wkly
    client.vintage_store = MagicMock()

    wkly_hist = client.fetch_movement_series("W_EPM0_IM0_R10-Z00_MBBLD", frequency="weekly")
    assert wkly_hist["2026-10-02"] == 645.5
    wkly_kwargs = client.vintage_store.record_observation.call_args.kwargs
    assert wkly_kwargs["feed"] == "eia_move_wkly"
    assert wkly_kwargs["published_at"] == "2026-10-07T15:30:00Z"

    # Test monthly pipeline flow parsing & PSM lag (+60 days from 2026-08-01 -> 2026-09-30T15:00:00Z)
    mock_resp_m = MagicMock()
    mock_resp_m.status_code = 200
    mock_resp_m.json.return_value = {"response": {"data": [{"period": "2026-08", "value": "87000"}]}}
    client.session.get.return_value = mock_resp_m
    pipe_hist = client.fetch_movement_series("M_EPM0_MPL_R30-R10_MBBL", frequency="monthly")
    assert pipe_hist["2026-08"] == 87000.0
    pipe_kwargs = client.vintage_store.record_observation.call_args.kwargs
    assert pipe_kwargs["feed"] == "eia_move_pipe"
    assert pipe_kwargs["published_at"] == "2026-09-30T15:00:00Z"

    # Verify EIADataConnector exposes the Phase 2 movement keys
    connector = EIADataConnector()
    global_cache.delete("eia_padd_refinery_inventory")
    data = connector.fetch_padd_inventory_and_refinery_data()
    moves = data["inter_padd_movements"]
    assert "padd3_to_padd1_pipeline_thousand_bpd" in moves
    assert "padd1_weekly_imports_thousand_bpd" in moves
    assert "padd3_weekly_exports_thousand_bpd" in moves


def test_eia_phase3_days_of_supply_and_crack_features():
    """Verifies Phase 3 finished vs. blendstock stocks, Days of Forward Supply, and 3:2:1 cash crack helpers (Issue #649)."""
    from src.eia_api_client import EIA_SERIES_PROVENANCE
    from src.feature_engineering import compute_days_of_forward_supply, compute_physical_cash_crack_321

    for sid in ("WGFSTUS1", "WGIOREST1", "EER_EPD2DXL0_PF4_RGC_DPG", "EER_EPD2DXL0_PF4_YNY_DPG", "EER_EPD2DXL0_PF4_RLA_DPG"):
        assert sid in EIA_SERIES_PROVENANCE

    # 200 million bbl / 10,000 thousand bpd = 20.0 days (below 22-day scarcity threshold)
    assert compute_days_of_forward_supply(200.0, 10000.0) == 20.0
    # ((2 * 2.50 * 42) + (1 * 2.60 * 42) - (3 * 70.0)) / 3 = (210 + 109.2 - 210) / 3 = 36.4
    assert compute_physical_cash_crack_321(2.50, 2.60, 70.0) == 36.4

    connector = EIADataConnector()
    global_cache.delete("eia_padd_refinery_inventory")
    data = connector.fetch_padd_inventory_and_refinery_data()
    assert "finished_vs_blendstock_stocks" in data
    assert "us_finished_gasoline_million_bbl" in data["finished_vs_blendstock_stocks"]
    assert "us_blending_components_million_bbl" in data["finished_vs_blendstock_stocks"]
    assert "days_of_forward_supply" in data
    assert data["days_of_forward_supply"] > 10.0
    assert isinstance(data["scarcity_buffer_below_22d"], bool)


def test_eia_phase4_steo_and_gallon_breakdown():
    """Verifies Phase 4 STEO projections and 'What We Pay for in a Gallon of Gasoline' breakdown (Issue #649)."""
    from unittest.mock import MagicMock
    from src.eia_api_client import EIAClientV2, EIA_SERIES_PROVENANCE

    for sid in ("MGRARUS", "MGWHUUS", "WTIPUUS"):
        assert sid in EIA_SERIES_PROVENANCE

    client = EIAClientV2(api_key="test-key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": {"data": [{"period": "2026-11", "value": "3.15"}]}}
    client.session = MagicMock()
    client.session.get.return_value = mock_resp
    client.vintage_store = MagicMock()

    hist = client.fetch_steo_series("MGRARUS", record_vintages=True)
    assert hist["2026-11"] == 3.15
    assert client.vintage_store.record_observation.call_args.kwargs["feed"] == "eia_steo"

    # Offline / baseline breakdown sums to 100.0%
    offline_client = EIAClientV2(api_key="")
    breakdown = offline_client.fetch_gallon_cost_breakdown()
    total_pct = (
        breakdown["crude_oil_pct"]
        + breakdown["refining_pct"]
        + breakdown["distribution_marketing_pct"]
        + breakdown["taxes_pct"]
    )
    assert abs(total_pct - 100.0) < 0.2
    assert breakdown["provenance_type"] == "BENCHMARK_BASELINE"

def test_eia_padd_bitemporal_persistence(tmp_path):
    temp_vintage = str(tmp_path / "eia_vintages_test.json")
    connector = EIADataConnector()
    
    rec = {
        "source": "U.S. EIA Test",
        "as_of": "2026-09-15 10:00:00",
        "valid_date": "2026-09-15",
        "refinery_utilization": {"PADD3_GulfCoast": 95.5},
        "is_vintage_reconstructed": False
    }
    connector.save_eia_vintage_record(rec, filepath=temp_vintage)
    vintages = connector.get_eia_vintages_as_of("2026-09-15", filepath=temp_vintage)
    assert len(vintages) == 1
    assert vintages[0]["refinery_utilization"]["PADD3_GulfCoast"] == 95.5
