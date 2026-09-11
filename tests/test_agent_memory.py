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

    @patch("urllib.request.urlopen")
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
        self.manager = AgentMemoryManager(sqlite_path=self.db_path)

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
        manager = AgentMemoryManager(sqlite_path=db_path)

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


if __name__ == "__main__":
    unittest.main()
