"""
Unit Tests for wxs.us Weather & SPC Convective Outlook Integration (tests/test_noaa_wxs.py)
"""

import pytest
from urllib.parse import urlparse
from unittest.mock import patch, MagicMock
from src.noaa_weather import (
    fetch_wxs_weather_data,
    extract_spc_convective_risk,
    get_all_metro_spc_convective_outlooks,
    SPC_RISK_CATEGORY_MAP,
    METRO_ZIP_MAP
)

MOCK_WXS_RESPONSE = {
    "location": "74101",
    "alerts": [
        {"event": "Tornado Warning", "headline": "NOAA NWS Tornado Warning for Tulsa County (OKZ060)"}
    ],
    "outlooks": {
        "categorical": "ENH",
        "tornado": "SLGT",
        "hail": "ENH",
        "wind": "MDT"
    }
}


def test_spc_risk_category_map():
    assert SPC_RISK_CATEGORY_MAP["HIGH"] == 1.00
    assert SPC_RISK_CATEGORY_MAP["MDT"] == 0.80
    assert SPC_RISK_CATEGORY_MAP["ENH"] == 0.60
    assert SPC_RISK_CATEGORY_MAP["SLGT"] == 0.40
    assert SPC_RISK_CATEGORY_MAP["MRGL"] == 0.20
    assert SPC_RISK_CATEGORY_MAP["NONE"] == 0.00


def test_extract_spc_convective_risk_parsed():
    res = extract_spc_convective_risk("74101", raw_data=MOCK_WXS_RESPONSE)
    assert res["location"] == "74101"
    # Tornado Warning alert overrides cat_risk to MDT (0.80) or higher
    assert res["convective_risk_score"] >= 0.80
    assert res["tornado_risk_score"] == 0.80
    assert res["hail_risk_score"] == 0.60
    assert res["wind_risk_score"] == 0.80
    assert len(res["active_alerts"]) == 1
    assert "Tornado Warning" in res["active_alerts"][0]
    assert "Location 74101" in res["summary_token_compact"]


def test_extract_spc_convective_risk_none():
    mock_empty = {"location": "94612", "alerts": [], "outlooks": {}}
    res = extract_spc_convective_risk("94612", raw_data=mock_empty)
    assert res["location"] == "94612"
    assert res["categorical_risk"] == "NONE"
    assert res["convective_risk_score"] == 0.0
    assert res["tornado_risk_score"] == 0.0
    assert res["active_alerts"] == []


@patch("src.noaa_weather.fetch_wxs_weather_data")
def test_get_all_metro_spc_convective_outlooks(mock_fetch):
    mock_fetch.return_value = MOCK_WXS_RESPONSE
    outlooks = get_all_metro_spc_convective_outlooks()
    
    assert len(outlooks) == len(METRO_ZIP_MAP)
    for metro_name in METRO_ZIP_MAP.keys():
        assert metro_name in outlooks
        assert "convective_risk_score" in outlooks[metro_name]
        assert "summary_token_compact" in outlooks[metro_name]


@patch("src.noaa_weather.urllib.request.urlopen")
def test_fetch_live_noaa_alerts_caching(mock_urlopen):
    from src.noaa_weather import fetch_live_noaa_alerts
    from src.lookup_cache import global_cache

    global_cache.clear()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"features": []}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # 1st call fetches via HTTP
    alerts1 = fetch_live_noaa_alerts(["OK"])
    noaa_calls1 = [c for c in mock_urlopen.call_args_list if c.args and hasattr(c.args[0], "full_url") and urlparse(c.args[0].full_url).hostname == "api.weather.gov"]
    assert len(noaa_calls1) == 1

    # 2nd call hits lookup cache (0 additional NOAA HTTP requests)
    alerts2 = fetch_live_noaa_alerts(["OK"])
    noaa_calls2 = [c for c in mock_urlopen.call_args_list if c.args and hasattr(c.args[0], "full_url") and urlparse(c.args[0].full_url).hostname == "api.weather.gov"]
    assert len(noaa_calls2) == 1


@patch("src.noaa_weather.urllib.request.urlopen")
def test_fetch_live_noaa_alerts_zone_and_area_routing(mock_urlopen):
    from src.noaa_weather import fetch_live_noaa_alerts
    from src.lookup_cache import global_cache

    global_cache.clear()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"features": []}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Test state area routing: "IL" -> /alerts/active/area/IL
    fetch_live_noaa_alerts(["IL"])
    call_url_il = mock_urlopen.call_args_list[-1].args[0].full_url
    assert "/alerts/active/area/IL" in call_url_il

    # Test NWS zone routing: "ILZ104" -> /alerts/active/zone/ILZ104
    fetch_live_noaa_alerts(["ILZ104"])
    call_url_zone = mock_urlopen.call_args_list[-1].args[0].full_url
    assert "/alerts/active/zone/ILZ104" in call_url_zone


@patch("src.noaa_weather.fetch_live_noaa_alerts")
@patch("src.noaa_weather.extract_spc_convective_risk")
@patch("src.noaa_weather.OpenMeteoDegreeDaysConnector.fetch_hub_degree_days")
def test_get_chicago_weather_dataset_live_merge(mock_meteo, mock_spc, mock_noaa):
    from src.noaa_weather import get_chicago_weather_dataset

    mock_noaa.return_value = [
        {
            "id": "alert-123",
            "area": "ILZ104",
            "event": "Lake Michigan Blizzard Warning",
            "headline": "NOAA NWS Blizzard Warning for Central Cook County IL",
            "effective": "2026-10-12T10:00:00Z"
        }
    ]
    mock_spc.return_value = {
        "active_alerts": ["Tornado Watch"],
        "convective_risk_score": 0.80,
        "categorical_risk": "MDT",
        "tornado_risk_score": 0.80,
        "hail_risk_score": 0.60,
        "wind_risk_score": 0.80
    }
    mock_meteo.return_value = {
        "hub_code": "Chicago_IL",
        "min_temp_f": 18.0,
        "max_temp_f": 30.0,
        "heating_degree_days_hdd": 41.0,
        "freeze_warning": True,
        "extreme_heat_warning": False
    }

    df = get_chicago_weather_dataset(include_live=True)
    assert not df.empty
    assert len(df) > 8  # 8 historical + live alerts

    headlines = df["headline"].tolist()
    assert any("Blizzard Warning" in h for h in headlines)
    assert any("Freeze Warning" in h for h in headlines)


@patch("src.noaa_weather.fetch_live_noaa_alerts")
@patch("src.noaa_weather.extract_spc_convective_risk")
@patch("src.noaa_weather.OpenMeteoDegreeDaysConnector.fetch_hub_degree_days")
def test_get_houston_weather_dataset_live_merge(mock_meteo, mock_spc, mock_noaa):
    from src.noaa_weather import get_houston_weather_dataset

    mock_noaa.return_value = [
        {
            "id": "alert-456",
            "area": "TXZ213",
            "event": "Gulf Hurricane Warning",
            "headline": "NOAA NWS Hurricane Warning for Harris County and Upper Texas Coast",
            "effective": "2026-10-12T10:00:00Z"
        }
    ]
    mock_spc.return_value = {
        "active_alerts": ["Severe Convective Surge"],
        "convective_risk_score": 0.85,
        "categorical_risk": "MDT",
        "tornado_risk_score": 0.50,
        "hail_risk_score": 0.60,
        "wind_risk_score": 0.90
    }
    mock_meteo.return_value = {
        "hub_code": "Houston_TX",
        "min_temp_f": 72.0,
        "max_temp_f": 92.0,
        "heating_degree_days_hdd": 0.0,
        "cooling_degree_days_cdd": 22.0,
        "freeze_warning": False,
        "extreme_heat_warning": True
    }

    df = get_houston_weather_dataset(include_live=True)
    assert not df.empty
    assert len(df) > 8  # 8 historical + live alerts

    headlines = df["headline"].tolist()
    assert any("Hurricane Warning" in h for h in headlines)
    assert any("Excessive Heat Warning" in h for h in headlines)


@patch("src.noaa_weather.fetch_live_noaa_alerts")
@patch("src.noaa_weather.extract_spc_convective_risk")
@patch("src.noaa_weather.OpenMeteoDegreeDaysConnector.fetch_hub_degree_days")
def test_get_los_angeles_weather_dataset_live_merge(mock_meteo, mock_spc, mock_noaa):
    from src.noaa_weather import get_los_angeles_weather_dataset

    mock_noaa.return_value = [
        {
            "id": "alert-789",
            "area": "CAZ041",
            "event": "Red Flag Warning",
            "headline": "NOAA NWS Red Flag Warning for Los Angeles County Coast and Basin",
            "effective": "2026-10-12T10:00:00Z"
        }
    ]
    mock_spc.return_value = {
        "active_alerts": ["High Wind Watch"],
        "convective_risk_score": 0.70,
        "categorical_risk": "ENH",
        "tornado_risk_score": 0.10,
        "hail_risk_score": 0.20,
        "wind_risk_score": 0.85
    }
    mock_meteo.return_value = {
        "hub_code": "Los_Angeles_CA",
        "min_temp_f": 68.0,
        "max_temp_f": 96.0,
        "heating_degree_days_hdd": 0.0,
        "cooling_degree_days_cdd": 17.0,
        "freeze_warning": False,
        "extreme_heat_warning": True
    }

    df = get_los_angeles_weather_dataset(include_live=True)
    assert not df.empty
    assert len(df) > 8  # 8 historical + live alerts

    headlines = df["headline"].tolist()
    assert any("Red Flag Warning" in h for h in headlines)
    assert any("Excessive Heat Warning" in h for h in headlines)


@patch("src.noaa_weather.fetch_live_noaa_alerts")
@patch("src.noaa_weather.extract_spc_convective_risk")
@patch("src.noaa_weather.OpenMeteoDegreeDaysConnector.fetch_hub_degree_days")
def test_get_denver_weather_dataset_live_merge(mock_meteo, mock_spc, mock_noaa):
    from src.noaa_weather import get_denver_weather_dataset

    mock_noaa.return_value = [
        {
            "id": "alert-den-123",
            "area": "COZ040",
            "event": "Blizzard Warning",
            "headline": "NOAA NWS Blizzard Warning for Denver Metro and Front Range",
            "effective": "2026-10-12T10:00:00Z"
        }
    ]
    mock_spc.return_value = {
        "active_alerts": ["Severe Thunderstorm Watch"],
        "convective_risk_score": 0.60,
        "categorical_risk": "SLGT",
        "tornado_risk_score": 0.20,
        "hail_risk_score": 0.60,
        "wind_risk_score": 0.40
    }
    mock_meteo.return_value = {
        "hub_code": "Denver_CO",
        "min_temp_f": 5.0,
        "max_temp_f": 25.0,
        "heating_degree_days_hdd": 50.0,
        "cooling_degree_days_cdd": 0.0,
        "freeze_warning": True,
        "extreme_heat_warning": False
    }

    df = get_denver_weather_dataset(include_live=True)
    assert not df.empty
    assert len(df) > 8  # 8 historical + live alerts

    headlines = df["headline"].tolist()
    assert any("Blizzard Warning" in h for h in headlines)
    assert any("Freeze Warning" in h for h in headlines)
