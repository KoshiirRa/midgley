import os
import json
import pytest
from unittest.mock import patch
from src.data_ingestion import (
    OpenSourceAIRadarConnector,
    save_radar_vintage_record,
    get_radar_vintages_as_of
)

def test_open_source_radar_vintage_tracking(tmp_path):
    v_file = str(tmp_path / "radar_vintages.json")
    models = [
        {
            "name": "Chronos-Bolt-Large",
            "tags": ["timeseries", "forecasting"],
            "is_time_series_capable": True,
            "is_llm_reasoning": False
        },
        {
            "name": "Llama-3.3-70B-Instruct",
            "tags": ["llm", "reasoning"],
            "is_time_series_capable": False,
            "is_llm_reasoning": True
        }
    ]
    
    save_radar_vintage_record(models, filepath=v_file, as_of="2026-03-15 12:00:00")
    assert os.path.exists(v_file)
    
    all_vintages = get_radar_vintages_as_of("2026-03-16", filepath=v_file)
    assert len(all_vintages) == 2
    
    ts_vintages = get_radar_vintages_as_of("2026-03-16", category="timeseries", filepath=v_file)
    assert len(ts_vintages) == 1
    assert ts_vintages[0]["name"] == "Chronos-Bolt-Large"

def test_open_source_radar_fetch_fallback():
    connector = OpenSourceAIRadarConnector()
    with patch("urllib.request.urlopen", side_effect=Exception("API offline")):
        res = connector.fetch_radar_models(category="timeseries", force_refresh=True)
        assert len(res) > 0
        for m in res:
            assert m["is_time_series_capable"] is True or "timeseries" in m["tags"]
