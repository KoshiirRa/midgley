"""
Unit Tests for wxs.us Weather & SPC Convective Outlook Integration (tests/test_noaa_wxs.py)
"""

import pytest
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
    assert mock_urlopen.call_count == 1

    # 2nd call hits lookup cache (0 HTTP requests)
    alerts2 = fetch_live_noaa_alerts(["OK"])
    assert mock_urlopen.call_count == 1

