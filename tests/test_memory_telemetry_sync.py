"""
Unit Tests for Remote Memory Bank Telemetry Synchronization (Issue #310)
Tests HindsightClient.get_bank_stats(), AgentMemoryManager.get_bank_inventory(),
and Dashboard Generator Active Memory Bank card rendering.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from src.hindsight_client import HindsightClient
from src.agent_memory import AgentMemoryManager, SQLiteMemoryStore


def test_hindsight_client_get_bank_stats_unconfigured():
    client = HindsightClient(base_url="")
    assert client.get_bank_stats() is None


def test_hindsight_client_get_bank_stats_success():
    client = HindsightClient(base_url="https://hindsight-test.a.run.app", api_key="test_key", bank_id="midgley-gas-forecasting")
    
    mock_resp_data = {
        "stats": {
            "memories_count": 1065,
            "reflections_count": 66
        }
    }
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("os.environ.get", return_value="0"), \
         patch("urllib.request.urlopen", return_value=mock_response):
        stats = client.get_bank_stats()
        assert stats is not None
        assert stats["memories"] == 1065
        assert stats["reflections"] == 66


def test_agent_memory_manager_get_bank_inventory_cloud_priority(tmp_path):
    sqlite_db = str(tmp_path / "test_agent_memory.sqlite")
    manager = AgentMemoryManager(
        hindsight_url="https://hindsight-test.a.run.app",
        hindsight_key="test_key",
        sqlite_path=sqlite_db
    )

    mock_cloud_stats = {"memories": 1065, "reflections": 66}
    with patch.object(manager.hindsight_client, "get_bank_stats", return_value=mock_cloud_stats):
        inventory = manager.get_bank_inventory()
        assert inventory["source"] == "remote_cloud"
        assert inventory["memories_count"] == 1065
        assert inventory["reflections_count"] == 66
        assert "Vectorize Hindsight" in inventory["backend"]


def test_agent_memory_manager_get_bank_inventory_local_fallback(tmp_path):
    sqlite_db = str(tmp_path / "test_agent_memory.sqlite")
    manager = AgentMemoryManager(
        hindsight_url="",
        sqlite_path=sqlite_db
    )
    # Seed 2 local memories and 1 reflection
    manager.sqlite_store.retain("Memory 1", region="Tulsa")
    manager.sqlite_store.retain("Memory 2", region="Newark")
    manager.sqlite_store.save_reflection({
        "region": "Tulsa",
        "anomaly_type": "LARGE_OVERESTIMATE",
        "title": "Test Anomaly",
        "root_cause": "Test Cause",
        "historical_analogy": "Test Analogy",
        "calibration_suggestion": "Test Suggestion"
    })

    inventory = manager.get_bank_inventory()
    assert inventory["source"] == "local_sqlite"
    assert inventory["memories_count"] == 2
    assert inventory["reflections_count"] == 1
    assert "Local SQLite" in inventory["backend"]
