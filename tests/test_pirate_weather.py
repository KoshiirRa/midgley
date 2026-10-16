"""
Tests for Pirate Weather API Historical Reanalysis & Weather Feature Connector (Issue #442).
"""

import pandas as pd
import pytest
from src.noaa_weather import PirateWeatherConnector, PIRATE_WEATHER_REFINING_HUBS


def test_pirate_weather_hub_coordinates_resolution():
    connector = PirateWeatherConnector()

    lat, lon = connector.get_hub_coordinates("tulsa_cushing")
    assert lat == 36.154
    assert lon == -95.992

    lat_del, lon_del = connector.get_hub_coordinates("delaware_city")
    assert lat_del == 39.683
    assert lon_del == -75.750

    lat_cin, lon_cin = connector.get_hub_coordinates("cincinnati_catlettsburg")
    assert lat_cin == 39.103
    assert lon_cin == -84.512

    lat_oak, lon_oak = connector.get_hub_coordinates("oakland_richmond")
    assert lat_oak == 37.804
    assert lon_oak == -122.271

    # Fallback to default for unknown
    lat_def, lon_def = connector.get_hub_coordinates("unknown_terminal_hub")
    assert lat_def == 29.760
    assert lon_def == -95.369


def test_pirate_weather_point_reanalysis_offline_fallback():
    # Without API key, connector gracefully falls back to physics/climatological reanalysis
    connector = PirateWeatherConnector(api_key=None)

    res = connector.fetch_historical_point(lat=36.154, lon=-95.992, dt_timestamp="2023-01-15")
    assert res is not None
    assert res["lat"] == 36.154
    assert res["lon"] == -95.992
    assert "temperature" in res
    assert "apparent_temperature" in res
    assert "wind_speed" in res
    assert "pressure" in res
    assert res["date"] == "2023-01-15"


def test_pirate_weather_range_and_risk_indices():
    connector = PirateWeatherConnector(api_key=None)

    df_range = connector.fetch_historical_range(
        lat=39.103,
        lon=-84.512,
        start_date="2024-01-10",
        end_date="2024-01-15"
    )
    assert not df_range.empty
    assert len(df_range) == 6
    assert "temperature" in df_range.columns
    assert "is_freeze" in df_range.columns

    indices = connector.compute_weather_risk_indices(df_range)
    assert "freeze_days_below_32f" in indices
    assert "heat_stress_days_above_95f" in indices
    assert "heating_degree_days" in indices
    assert "cooling_degree_days" in indices
    assert 0.0 <= indices["freeze_off_risk_index"] <= 1.0


def test_pirate_weather_fetch_hub_weather():
    connector = PirateWeatherConnector(api_key=None)
    hub_res = connector.fetch_hub_weather("tulsa_cushing", target_date="2026-01-15")

    assert hub_res is not None
    assert hub_res["hub_code"] == "tulsa_cushing"
    assert "West Tulsa" in hub_res["hub_name"]
    assert "heating_degree_days_hdd" in hub_res
    assert "cooling_degree_days_cdd" in hub_res
    assert "freeze_warning" in hub_res
    assert "freeze_off_risk_index" in hub_res
    assert "wind_gust" in hub_res


def test_scenario_engine_noaa_freeze_hook():
    from src.scenario_engine import _evaluate_live_telemetry_trigger, evaluate_scenario_plausibility
    is_active, score_boost, reason = _evaluate_live_telemetry_trigger(
        telemetry_hook="noaa_freeze",
        scenario_id="polar_vortex_freeze"
    )
    assert isinstance(is_active, bool)
    assert isinstance(score_boost, float)
    assert isinstance(reason, str)
    assert len(reason) > 0

    res = evaluate_scenario_plausibility("polar_vortex_freeze", live_telemetry=True)
    assert res is not None
    assert "scenario_id" in res


def test_feature_engineering_weather_resolution():
    from src.feature_engineering import create_feature_matrix
    dates = pd.date_range("2026-08-01", "2026-09-05", freq="D")
    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": [2.50 + i * 0.01 for i in range(len(dates))],
        "wti_crude": [75.0 + i * 0.05 for i in range(len(dates))],
        "brent_crude": [78.0 + i * 0.05 for i in range(len(dates))]
    })
    feat_df = create_feature_matrix(market_df=market_df, region="Tulsa_OK")
    assert not feat_df.empty
    assert "hdd_daily" in feat_df.columns
    assert "cdd_daily" in feat_df.columns
    assert "freeze_warning_flag" in feat_df.columns


