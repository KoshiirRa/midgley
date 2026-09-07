"""
Unit Tests for Open Source AI Radar Connector & API Integration (tests/test_open_source_ai_radar.py)
Issue #187
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.data_ingestion import OpenSourceAIRadarConnector, get_open_source_ai_radar_models
from src.weekly_issue_reporter import format_ai_radar_markdown_section
from src.api_server import app


class TestOpenSourceAIRadar(unittest.TestCase):
    def setUp(self):
        self.connector = OpenSourceAIRadarConnector()
        self.client = TestClient(app)
        if os.path.exists(self.connector.CACHE_FILE):
            os.remove(self.connector.CACHE_FILE)

    def tearDown(self):
        if os.path.exists(self.connector.CACHE_FILE):
            os.remove(self.connector.CACHE_FILE)

    def test_curated_baseline_fallback(self):
        models = self.connector.CURATED_BASELINE_MODELS
        self.assertGreaterEqual(len(models), 5)
        names = [m["name"] for m in models]
        self.assertIn("Llama-3.3-70B-Instruct", names)
        self.assertIn("Chronos-Bolt-Large", names)

    def test_fetch_radar_models_fallback_when_offline(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Simulated offline")
            models = self.connector.fetch_radar_models(max_results=5, force_refresh=True)
            self.assertGreater(len(models), 0)
            self.assertLessEqual(len(models), 5)
            self.assertTrue(any("Llama" in m["name"] or "DeepSeek" in m["name"] for m in models))

    def test_fetch_radar_models_online_mock_success(self):
        mock_payload = json.dumps([
            {
                "name": "MockModel-7B-Instruct",
                "organization": "TestOrg",
                "license": "Apache-2.0",
                "parameters": "7B",
                "context_window": 32768,
                "release_date": "2026-08-01",
                "tags": ["llm", "reasoning"],
                "benchmark_score": 89.5,
                "url": "https://huggingface.co/TestOrg/MockModel-7B-Instruct"
            }
        ]).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = mock_payload

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            models = self.connector.fetch_radar_models(max_results=10, force_refresh=True)
            self.assertEqual(len(models), 1)
            self.assertEqual(models[0]["name"], "MockModel-7B-Instruct")
            self.assertEqual(models[0]["organization"], "TestOrg")
            self.assertTrue(models[0]["is_llm_reasoning"])

    def test_filter_by_category(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Simulated offline")
            models = self.connector.fetch_radar_models(category="timeseries", force_refresh=True)
            self.assertGreater(len(models), 0)
            self.assertTrue(all(m.get("is_time_series_capable") or "timeseries" in m.get("tags", []) for m in models))

    def test_format_ai_radar_markdown_section(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Simulated offline")
            md = format_ai_radar_markdown_section(limit=3)
            self.assertIn("### 📡 Open Source AI Radar Discovered Models", md)
            self.assertIn("| Model | Provider | License |", md)
            self.assertIn("Llama-3.3-70B-Instruct", md)

    def test_api_server_radar_endpoint(self):
        res = self.client.get("/api/v1/system/radar?limit=4")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("models", data)
        self.assertLessEqual(len(data["models"]), 4)


if __name__ == "__main__":
    unittest.main()
