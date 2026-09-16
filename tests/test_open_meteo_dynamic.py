import os
import json
import pytest
from unittest.mock import patch
from src.noaa_weather import (
    OpenMeteoDegreeDaysConnector,
    save_degree_days_vintage_record,
    get_degree_days_vintages_as_of
)

def test_open_meteo_degree_days_caching_and_vintages(tmp_path):
    v_file = str(tmp_path / "degree_days_vintages.json")
    connector = OpenMeteoDegreeDaysConnector()
    
    mock_payload = {
        "hub_code": "Tulsa_OK",
        "name": "West Tulsa HF Sinclair & Cushing Hub",
        "mean_temp_f": 68.0,
        "max_temp_f": 78.0,
        "min_temp_f": 58.0,
        "heating_degree_days_hdd": 0.0,
        "cooling_degree_days_cdd": 3.0,
        "freeze_warning": False,
        "extreme_heat_warning": False,
        "as_of": "2026-03-15 12:00:00",
        "valid_date": "2026-03-15",
        "source": "Open-Meteo Weather API (Zero-Cost)",
        "is_free_alternative": True,
        "cost_per_query": 0.0,
        "timestamp": "2026-03-15 12:00:00"
    }
    
    save_degree_days_vintage_record(mock_payload, filepath=v_file)
    assert os.path.exists(v_file)
    
    vintages = get_degree_days_vintages_as_of("2026-03-16", hub_code="Tulsa_OK", filepath=v_file)
    assert len(vintages) == 1
    assert vintages[0]["hub_code"] == "Tulsa_OK"
    assert vintages[0]["cooling_degree_days_cdd"] == 3.0

def test_open_meteo_fetch_hub_fallback():
    connector = OpenMeteoDegreeDaysConnector()
    with patch("urllib.request.urlopen", side_effect=Exception("API offline")):
        res = connector.fetch_hub_degree_days("Tulsa_OK")
        assert res["hub_code"] == "Tulsa_OK"
        assert res["mean_temp_f"] == 65.0
        assert res["is_free_alternative"] is True
