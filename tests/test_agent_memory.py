"""
Unit Tests for Agent Memory & Qualitative Anomaly Reflection Engine (Issue #230)
Tests Retain-Recall-Reflect with HindsightClient, SQLite FTS5 fallback, and weekly review integration.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import json

from src.hindsight_client import HindsightClient
from src.agent_memory import (
    SQLiteMemoryStore,
    AgentMemoryManager,
    extract_top_prediction_anomalies,
    format_qualitative_anomaly_reflections_markdown
)


class TestSQLiteMemoryStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_memory.sqlite")
        self.store = SQLiteMemoryStore(db_path=self.db_path)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_retain_and_recall_basic(self):
        # 1. Retain an experience
        res = self.store.retain(
            content="Delaware City FCC flaring caused temporary supply disruption in Newark DE",
            region="Newark_DE",
            anomaly_type="LARGE_OVERESTIMATE",
            error_dollars=0.3540,
            predicted_price=2.45,
            actual_price=2.10,
            forecast_target_date="2026-09-15"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("exp_", res["memory_id"])

        # 2. Recall using query
        memories = self.store.recall(query="Delaware City flaring", region="Newark_DE", top_k=2)
        self.assertTrue(len(memories) >= 1)
        self.assertEqual(memories[0]["region"], "Newark_DE")
        self.assertEqual(memories[0]["anomaly_type"], "LARGE_OVERESTIMATE")
        self.assertAlmostEqual(memories[0]["error_dollars"], 0.3540, places=3)

    def test_save_and_retrieve_reflection(self):
        reflection = {
            "region": "Tulsa_OK",
            "anomaly_type": "LARGE_UNDERESTIMATE",
            "title": "Tulsa Refinery Outage Underestimate",
            "root_cause": "HF Sinclair unscheduled maintenance expanded crack margin unexpectedly.",
            "historical_analogy": "Matches Q3 2025 crude distillation turnaround.",
            "calibration_suggestion": "Increase crack spread weight."
        }
        ok = self.store.save_reflection(reflection)
        self.assertTrue(ok)

    def test_recall_with_special_punctuation_and_operators(self):
        """Verifies that special FTS5 operators (+, -, *, :, ^, AND, OR, NOT) do not raise sqlite3 syntax errors (Issue #331)."""
        # Retain test memories with complex terms
        self.store.retain(
            content="OPEC+ production quota cut caused prompt crude surge and crack-spread expansion in PADD-1B.",
            region="Newark_DE",
            anomaly_type="LARGE_UNDERESTIMATE",
            error_dollars=0.4200,
            predicted_price=2.80,
            actual_price=3.22,
            forecast_target_date="2026-09-18"
        )

        # 1. Query containing '+' operator
        res_plus = self.store.recall(query="OPEC+ production quota", region="Newark_DE", top_k=3)
        self.assertTrue(len(res_plus) >= 1)
        self.assertEqual(res_plus[0]["region"], "Newark_DE")

        # 2. Query containing hyphens and colon
        res_hyphen = self.store.recall(query="crack-spread: expansion PADD-1B", region="Newark_DE", top_k=3)
        self.assertTrue(len(res_hyphen) >= 1)

        # 3. Query containing asterisks, carets, and boolean keywords
        res_bool = self.store.recall(query="OPEC* AND NOT OR ^production", region="Newark_DE", top_k=3)
        self.assertTrue(len(res_bool) >= 1)

        # 4. Pure punctuation query (should fall back gracefully to recent records)
        res_punct = self.store.recall(query="+++ --- *** ::: ^^^", region="Newark_DE", top_k=3)
        self.assertTrue(len(res_punct) >= 1)



class TestHindsightClient(unittest.TestCase):
    def test_unconfigured_behavior(self):
        client = HindsightClient(base_url="", api_key="")
        self.assertFalse(client.is_configured)
        self.assertFalse(client.ping())
        
        retain_res = client.retain(content="Test", region="National")
        self.assertEqual(retain_res["status"], "UNCONFIGURED")

        recall_res = client.recall(query="Test")
        self.assertEqual(recall_res, [])

        reflect_res = client.reflect(anomalies=[{"region": "National"}])
        self.assertEqual(reflect_res["status"], "UNCONFIGURED")

    @patch.dict(os.environ, {"TEST_HINDSIGHT_FORCE": "1"})
    @patch("src.hindsight_client.urllib.request.urlopen")
    def test_configured_retain_mock(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "SUCCESS", "id": "mem_123"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = HindsightClient(base_url="https://mock-hindsight.a.run.app", api_key="test-key")
        self.assertTrue(client.is_configured)
        
        res = client.retain(
            content="Mock hurricane shock in Port St Lucie",
            region="Port_St_Lucie_FL",
            anomaly_type="CI_BREACH"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["data"]["id"], "mem_123")


class TestAgentMemoryManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "manager_test.sqlite")
        self.manager = AgentMemoryManager(hindsight_url="", sqlite_path=self.db_path)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_dual_dispatch_and_fallback(self):
        # When cloud engine is offline, retains in local SQLite
        res = self.manager.retain(
            content="Cincinnati barge traffic halt due to Ohio river lock repair",
            region="Cincinnati_OH",
            anomaly_type="DIRECTIONAL_FLIP",
            error_dollars=0.2210,
            predicted_price=2.65,
            actual_price=2.87,
            forecast_target_date="2026-09-18"
        )
        self.assertEqual(res["local_status"], "SUCCESS")
        self.assertEqual(res["active_backend"], "sqlite_fts5")

        # Recall
        recalled = self.manager.recall("Ohio river barge", region="Cincinnati_OH")
        self.assertTrue(len(recalled) >= 1)
        self.assertEqual(recalled[0]["region"], "Cincinnati_OH")

    def test_deterministic_reflection(self):
        anomalies = [
            {
                "region": "Newark_DE",
                "predicted_price": 2.50,
                "actual_price": 2.10,
                "error_dollars": 0.40,
                "anomaly_type": "LARGE_OVERESTIMATE",
                "headline": "Delaware City quick turnaround completion"
            }
        ]
        reflections = self.manager.reflect_on_anomalies(anomalies)
        self.assertEqual(len(reflections), 1)
        self.assertEqual(reflections[0]["region"], "Newark_DE")
        self.assertIn("overestimated", reflections[0]["root_cause"])
        self.assertIn("half-life", reflections[0]["calibration_suggestion"])


class TestWeeklyReviewMemoryReporting(unittest.TestCase):
    def test_format_qualitative_anomaly_reflections_markdown(self):
        temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(temp_dir.name, "report_test.sqlite")
        manager = AgentMemoryManager(hindsight_url="", sqlite_path=db_path)

        # Seed an experience
        manager.retain(
            content="Oakland CARB penalty spike",
            region="Oakland_CA",
            anomaly_type="LARGE_UNDERESTIMATE",
            error_dollars=-0.3850,
            predicted_price=3.50,
            actual_price=3.8850,
            forecast_target_date="2026-09-20"
        )

        md = format_qualitative_anomaly_reflections_markdown(manager=manager, max_anomalies=2)
        self.assertIn("## 🧠 Qualitative Anomaly Post-Mortems & Episodic Memory (Issue #230)", md)
        try:
            temp_dir.cleanup()
        except Exception:
            pass


class TestHindsightWarmupAndSync(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "sync_test.sqlite")
        self.manager = AgentMemoryManager(
            hindsight_url="https://mock-hindsight.a.run.app",
            hindsight_key="mock-key",
            sqlite_path=self.db_path
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    @patch.dict(os.environ, {"TEST_HINDSIGHT_FORCE": "1"})
    @patch("src.hindsight_client.urllib.request.urlopen")
    def test_warmup_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = HindsightClient(base_url="https://mock-hindsight.a.run.app")
        ok = client.warmup(max_wait_seconds=2.0, retry_interval=0.1)
        self.assertTrue(ok)

    @patch.dict(os.environ, {"TEST_HINDSIGHT_FORCE": "1"})
    @patch("src.hindsight_client.urllib.request.urlopen")
    def test_sync_pending_memories_reconciliation(self, mock_urlopen):
        # 1. Seed local unsynced memories
        self.manager.sqlite_store.retain(
            content="Historical cold boot shock",
            region="Tulsa_OK",
            anomaly_type="LARGE_UNDERESTIMATE",
            error_dollars=0.28,
            cloud_synced=0
        )
        self.manager.sqlite_store.retain(
            content="Historical cold boot shock 2",
            region="National",
            anomaly_type="NORMAL",
            error_dollars=0.05,
            cloud_synced=0
        )

        unretained = self.manager.sqlite_store.get_unretained_memories()
        self.assertEqual(len(unretained), 2)

        # 2. Mock cloud service becoming healthy and responding
        mock_resp_health = MagicMock()
        mock_resp_health.status = 200

        mock_resp_retain = MagicMock()
        mock_resp_retain.read.return_value = json.dumps({"status": "SUCCESS"}).encode("utf-8")

        mock_urlopen.return_value.__enter__.side_effect = [mock_resp_health, mock_resp_retain, mock_resp_retain]

        synced = self.manager.sync_pending_memories(limit=10)
        self.assertEqual(synced, 2)

        # 3. Verify that zero unsynced records remain
        remaining = self.manager.sqlite_store.get_unretained_memories()
        self.assertEqual(len(remaining), 0)

    @patch.dict(os.environ, {"TEST_HINDSIGHT_FORCE": "1"})
    @patch("src.hindsight_client.urllib.request.urlopen")
    def test_hindsight_bank_stats_and_inventory_metrics(self, mock_urlopen):
        # 1. Mock remote bank stats response with durable observations
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "bank": {
                "total_documents": 42,
                "total_observations": 18,
                "total_reflections": 7
            }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = HindsightClient(base_url="https://mock-hindsight.a.run.app")
        stats = client.get_bank_stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats["memories"], 42)
        self.assertEqual(stats["observations"], 18)
        self.assertEqual(stats["reflections"], 7)

        # 2. Seed an unsynced memory locally to check pending reconciliation queue
        self.manager.sqlite_store.retain(
            content="Local unsynced anomaly",
            region="Greenville_NC",
            cloud_synced=0
        )

        inventory = self.manager.get_bank_inventory()
        self.assertEqual(inventory["source"], "remote_cloud")
        self.assertEqual(inventory["memories_count"], 42)
        self.assertEqual(inventory["observations_count"], 18)
        self.assertEqual(inventory["reflections_count"], 7)
        self.assertEqual(inventory["pending_reconciliation_count"], 1)


if __name__ == "__main__":
    unittest.main()
