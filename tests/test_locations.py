"""
Unit Tests for src/locations subpackage registry and location modules.
"""

import pytest
import pandas as pd
from src.locations import (
    LOCATIONS,
    list_locations,
    get_location,
    run_national_pipeline,
    run_tulsa_pipeline,
    run_newark_pipeline,
    run_cincinnati_pipeline,
    run_greenville_pipeline,
    run_charlotte_pipeline,
    run_oakland_pipeline,
    run_chicago_pipeline,
    run_houston_pipeline,
    run_los_angeles_pipeline,
    run_denver_pipeline,
    run_new_york_pipeline,
    run_seattle_pipeline,
    run_phoenix_pipeline,
    run_anchorage_pipeline,
    run_honolulu_pipeline,
    run_guam_pipeline,
    run_san_juan_pipeline,
    run_boston_pipeline
)
from src.locations.tulsa.regional import fetch_tulsa_market_data, get_tulsa_regional_events, _generate_synthetic_tulsa_data
from src.locations.newark.regional import fetch_newark_market_data, get_newark_regional_events, _generate_synthetic_newark_data
from src.locations.cincinnati.regional import fetch_cincinnati_market_data, get_cincinnati_regional_events, _generate_synthetic_cincinnati_data
from src.locations.greenville.regional import fetch_greenville_market_data, get_greenville_regional_events, _generate_synthetic_greenville_data
from src.locations.charlotte.regional import fetch_charlotte_market_data, get_charlotte_regional_events, _generate_synthetic_charlotte_data
from src.locations.oakland.regional import fetch_oakland_market_data, get_oakland_regional_events, _generate_synthetic_oakland_data, TOTAL_CARB_TAX_BURDEN
from src.locations.chicago.regional import fetch_chicago_market_data, get_chicago_regional_events, _generate_synthetic_chicago_data
from src.locations.houston.regional import fetch_houston_market_data, get_houston_regional_events, _generate_synthetic_houston_data
from src.locations.los_angeles.regional import fetch_los_angeles_market_data, get_los_angeles_regional_events, _generate_synthetic_los_angeles_data
from src.locations.denver.regional import fetch_denver_market_data, get_denver_regional_events, _generate_synthetic_denver_data
from src.locations.new_york.regional import fetch_new_york_market_data, get_new_york_regional_events, _generate_synthetic_new_york_data
from src.locations.seattle.regional import fetch_seattle_market_data, get_seattle_regional_events, _generate_synthetic_seattle_data
from src.locations.phoenix.regional import fetch_phoenix_market_data, get_phoenix_regional_events, _generate_synthetic_phoenix_data
from src.locations.anchorage.regional import fetch_anchorage_market_data, get_anchorage_regional_events, _generate_synthetic_anchorage_data
from src.locations.honolulu.regional import fetch_honolulu_market_data, get_honolulu_regional_events, _generate_synthetic_honolulu_data
from src.locations.guam.regional import fetch_guam_market_data, get_guam_regional_events, _generate_synthetic_guam_data
from src.locations.san_juan.regional import (
    fetch_san_juan_market_data,
    get_san_juan_regional_events,
    _generate_synthetic_san_juan_data,
    convert_cents_per_liter_to_dollars_per_gal
)
from src.locations.boston.regional import (
    fetch_boston_market_data,
    get_boston_regional_events,
    _generate_synthetic_boston_data
)


def test_locations_registry_structure():
    """Verify that all expected locations are registered with required keys."""
    expected_locations = {
        "national", "tulsa", "newark", "cincinnati", "charlotte",
        "oakland", "port_st_lucie", "chicago", "houston", "los_angeles", "denver", "new_york",
        "seattle", "phoenix", "anchorage", "honolulu", "guam", "san_juan", "boston"
    }
    registered = set(list_locations())
    assert expected_locations.issubset(registered), f"Missing locations in registry: {expected_locations - registered}"

    for loc_id in expected_locations:
        info = get_location(loc_id)
        assert info["id"] == loc_id
        assert "name" in info
        assert callable(info["run_pipeline"])
        assert callable(info["build_notebook"])
        assert "notebook_filename" in info

    # Ensure decommissioned greenville aliases cleanly to charlotte
    grn_info = get_location("greenville")
    assert grn_info["id"] == "charlotte"


def test_tulsa_synthetic_market_data():
    """Verify Tulsa regional data generator creates required feature columns."""
    df = _generate_synthetic_tulsa_data("2024-01-01", "2024-01-31", live_current_price=3.89)
    assert not df.empty
    assert "tulsa_retail_gasoline" in df.columns
    assert "cushing_crude_per_gal" in df.columns
    assert "crack_spread" in df.columns
    assert pytest.approx(df["tulsa_retail_gasoline"].iloc[-1], rel=1e-3) == 3.89


def test_newark_synthetic_market_data():
    """Verify Newark regional data generator creates required feature columns."""
    df = _generate_synthetic_newark_data("2024-01-01", "2024-01-31", live_current_price=3.35)
    assert not df.empty
    assert "newark_retail_gasoline" in df.columns
    assert "brent_crude_per_gal" in df.columns
    assert "delaware_city_crack_spread" in df.columns
    assert pytest.approx(df["newark_retail_gasoline"].iloc[-1], rel=1e-3) == 3.35


def test_cincinnati_synthetic_market_data():
    """Verify Cincinnati dual-state regional data generator creates required OH & KY columns."""
    df = _generate_synthetic_cincinnati_data("2024-01-01", "2024-01-31", live_oh_price=3.450, live_ky_price=3.325)
    assert not df.empty
    assert "cincinnati_oh_retail_gasoline" in df.columns
    assert "cincinnati_ky_retail_gasoline" in df.columns
    assert "oh_ky_tax_spread" in df.columns
    assert "catlettsburg_crack_spread" in df.columns
    assert pytest.approx(df["oh_ky_tax_spread"].iloc[-1], rel=1e-2) == 0.125


def test_greenville_synthetic_market_data():
    """Verify Greenville regional data generator creates required feature columns."""
    df = _generate_synthetic_greenville_data("2024-01-01", "2024-01-31", live_current_price=3.25)
    assert not df.empty
    assert "greenville_retail_gasoline" in df.columns
    assert "selma_rack_crack_spread" in df.columns
    assert pytest.approx(df["greenville_retail_gasoline"].iloc[-1], rel=1e-3) == 3.25


def test_charlotte_synthetic_market_data():
    """Verify Charlotte regional data generator creates required feature columns."""
    df = _generate_synthetic_charlotte_data("2024-01-01", "2024-01-31", live_current_price=3.28)
    assert not df.empty
    assert "charlotte_retail_gasoline" in df.columns
    assert "paw_creek_rack_crack_spread" in df.columns
    assert pytest.approx(df["charlotte_retail_gasoline"].iloc[-1], rel=1e-3) == 3.28


def test_oakland_synthetic_market_data():
    """Verify Oakland & Bay Area regional data generator includes CARB tax burden breakdown."""
    df = _generate_synthetic_oakland_data("2024-01-01", "2024-01-31", live_oakland_price=4.950, live_bayarea_price=5.050)
    assert not df.empty
    assert "oakland_retail_gasoline" in df.columns
    assert "bayarea_avg_retail_gasoline" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["total_regulatory_tax_burden"].iloc[0], rel=1e-3) == TOTAL_CARB_TAX_BURDEN


def test_chicago_synthetic_market_data():
    """Verify Chicago regional data generator creates required feature columns."""
    df = _generate_synthetic_chicago_data("2024-01-01", "2024-01-31", live_il_price=3.850, live_in_price=3.450)
    assert not df.empty
    assert "chicago_il_retail_gasoline" in df.columns
    assert "chicago_in_retail_gasoline" in df.columns
    assert "il_in_tax_spread" in df.columns
    assert "whiting_crack_spread" in df.columns
    assert pytest.approx(df["chicago_il_retail_gasoline"].iloc[-1], rel=1e-3) == 3.850
    assert pytest.approx(df["il_in_tax_spread"].iloc[-1], rel=1e-2) == 0.400


def test_houston_synthetic_market_data():
    """Verify Houston regional data generator creates required feature columns."""
    df = _generate_synthetic_houston_data("2024-01-01", "2024-01-31", live_pump_price=2.850)
    assert not df.empty
    assert "houston_tx_retail_gasoline" in df.columns
    assert "spot_gulf_coast" in df.columns
    assert "usgc_crack_spread" in df.columns
    assert "houston_rack_margin" in df.columns
    assert pytest.approx(df["houston_tx_retail_gasoline"].iloc[-1], rel=1e-3) == 2.850


def test_los_angeles_synthetic_market_data():
    """Verify Los Angeles regional data generator creates required feature columns."""
    df = _generate_synthetic_los_angeles_data("2024-01-01", "2024-01-31", live_pump_price=4.890)
    assert not df.empty
    assert "los_angeles_ca_retail_gasoline" in df.columns
    assert "spot_los_angeles" in df.columns
    assert "el_segundo_crack_spread" in df.columns
    assert "los_angeles_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["los_angeles_ca_retail_gasoline"].iloc[-1], rel=1e-3) == 4.890


def test_denver_synthetic_market_data():
    """Verify Denver regional data generator creates required feature columns."""
    df = _generate_synthetic_denver_data("2024-01-01", "2024-01-31", live_pump_price=3.150)
    assert not df.empty
    assert "denver_co_retail_gasoline" in df.columns
    assert "spot_denver_rack" in df.columns
    assert "suncor_crack_spread" in df.columns
    assert "denver_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["denver_co_retail_gasoline"].iloc[-1], rel=1e-3) == 3.150


def test_new_york_synthetic_market_data():
    """Verify New York regional data generator creates required feature columns."""
    df = _generate_synthetic_new_york_data("2024-01-01", "2024-01-31", live_pump_price=3.480)
    assert not df.empty
    assert "new_york_ny_retail_gasoline" in df.columns
    assert "spot_ny_harbor" in df.columns
    assert "new_york_crack_spread" in df.columns
    assert "new_york_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["new_york_ny_retail_gasoline"].iloc[-1], rel=1e-3) == 3.480


def test_seattle_synthetic_market_data():
    """Verify Seattle regional data generator creates required feature columns."""
    df = _generate_synthetic_seattle_data("2024-01-01", "2024-01-31", live_pump_price=4.250)
    assert not df.empty
    assert "seattle_wa_retail_gasoline" in df.columns
    assert "spot_pnw_rack" in df.columns
    assert "puget_sound_crack_spread" in df.columns
    assert "seattle_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["seattle_wa_retail_gasoline"].iloc[-1], rel=1e-3) == 4.250


def test_phoenix_synthetic_market_data():
    """Verify Phoenix regional data generator creates required feature columns."""
    df = _generate_synthetic_phoenix_data("2024-01-01", "2024-01-31", live_pump_price=3.550)
    assert not df.empty
    assert "phoenix_az_retail_gasoline" in df.columns
    assert "spot_phoenix_pipe" in df.columns
    assert "desert_crack_spread" in df.columns
    assert "phoenix_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["phoenix_az_retail_gasoline"].iloc[-1], rel=1e-3) == 3.550


def test_anchorage_synthetic_market_data():
    """Verify Anchorage regional data generator creates required feature columns."""
    df = _generate_synthetic_anchorage_data("2024-01-01", "2024-01-31", live_pump_price=3.850)
    assert not df.empty
    assert "anchorage_ak_retail_gasoline" in df.columns
    assert "spot_ans_rack" in df.columns
    assert "kenai_crack_spread" in df.columns
    assert "anchorage_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["anchorage_ak_retail_gasoline"].iloc[-1], rel=1e-3) == 3.850


def test_honolulu_synthetic_market_data():
    """Verify Honolulu regional data generator creates required feature columns."""
    df = _generate_synthetic_honolulu_data("2024-01-01", "2024-01-31", live_pump_price=4.750)
    assert not df.empty
    assert "honolulu_hi_retail_gasoline" in df.columns
    assert "spot_oahu_rack" in df.columns
    assert "kapolei_crack_spread" in df.columns
    assert "honolulu_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["honolulu_hi_retail_gasoline"].iloc[-1], rel=1e-3) == 4.750


def test_guam_synthetic_market_data():
    """Verify Guam regional data generator creates required feature columns."""
    df = _generate_synthetic_guam_data("2024-01-01", "2024-01-31", live_pump_price=4.890)
    assert not df.empty
    assert "guam_gu_retail_gasoline" in df.columns
    assert "spot_mops_92_rack" in df.columns
    assert "mops_crack_spread" in df.columns
    assert "guam_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["guam_gu_retail_gasoline"].iloc[-1], rel=1e-3) == 4.890


def test_san_juan_synthetic_market_data():
    """Verify San Juan regional data generator creates required feature columns and conversions."""
    df = _generate_synthetic_san_juan_data("2024-01-01", "2024-01-31", live_pump_price=3.490)
    assert not df.empty
    assert "san_juan_pr_retail_gasoline" in df.columns
    assert "san_juan_retail_gasoline" in df.columns
    assert "daco_retail_cents_per_liter" in df.columns
    assert "spot_caribbean_waterborne" in df.columns
    assert "jones_act_freight_differential" in df.columns
    assert "san_juan_crack_spread" in df.columns
    assert "san_juan_rack_margin" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["san_juan_pr_retail_gasoline"].iloc[-1], rel=1e-3) == 3.490

    # Verify metric conversion: 92.2 ¢/L -> ~$3.490/gal
    gal_price = convert_cents_per_liter_to_dollars_per_gal(92.20)
    assert pytest.approx(gal_price, rel=1e-2) == 3.490


def test_boston_synthetic_market_data():
    """Verify Boston regional data generator creates required feature columns."""
    df = _generate_synthetic_boston_data("2024-01-01", "2024-01-31", live_current_price=3.450)
    assert not df.empty
    assert "boston_retail_gasoline" in df.columns
    assert "boston_ma_retail_gasoline" in df.columns
    assert "massachusetts_retail_gasoline" in df.columns
    assert "new_england_retail_gasoline" in df.columns
    assert "spot_ny_harbor" in df.columns
    assert "brent_crude_per_gal" in df.columns
    assert "boston_harbor_crack_spread" in df.columns
    assert "waterborne_barge_freight" in df.columns
    assert "winter_distillate_spread" in df.columns
    assert "cross_border_nh_arbitrage" in df.columns
    assert pytest.approx(df["boston_retail_gasoline"].iloc[-1], rel=1e-3) == 3.450


def test_regional_events_loading():
    """Verify regional events functions return populated DataFrames."""
    tulsa_events = get_tulsa_regional_events()
    newark_events = get_newark_regional_events()
    cincinnati_events = get_cincinnati_regional_events()
    greenville_events = get_greenville_regional_events()
    charlotte_events = get_charlotte_regional_events()
    oakland_events = get_oakland_regional_events()
    chicago_events = get_chicago_regional_events()
    houston_events = get_houston_regional_events()
    los_angeles_events = get_los_angeles_regional_events()
    denver_events = get_denver_regional_events()
    new_york_events = get_new_york_regional_events()
    seattle_events = get_seattle_regional_events()
    phoenix_events = get_phoenix_regional_events()
    anchorage_events = get_anchorage_regional_events()
    honolulu_events = get_honolulu_regional_events()
    guam_events = get_guam_regional_events()
    san_juan_events = get_san_juan_regional_events()
    boston_events = get_boston_regional_events()

    for name, ev_df in [
        ("Tulsa", tulsa_events),
        ("Newark", newark_events),
        ("Cincinnati", cincinnati_events),
        ("Greenville", greenville_events),
        ("Charlotte", charlotte_events),
        ("Oakland", oakland_events),
        ("Chicago", chicago_events),
        ("Houston", houston_events),
        ("Los Angeles", los_angeles_events),
        ("Denver", denver_events),
        ("New York", new_york_events),
        ("Seattle", seattle_events),
        ("Phoenix", phoenix_events),
        ("Anchorage", anchorage_events),
        ("Honolulu", honolulu_events),
        ("Guam", guam_events),
        ("San Juan", san_juan_events),
        ("Boston", boston_events)
    ]:
        assert isinstance(ev_df, pd.DataFrame), f"{name} events is not a DataFrame"
        assert not ev_df.empty, f"{name} events DataFrame is empty"
        assert "date" in ev_df.columns
        assert "headline" in ev_df.columns

