"""
Unit tests for System Telemetry & API Quota Protection Engine (Issues #107 & #108).
"""

import os
import unittest
from fastapi.testclient import TestClient
from src.api_server import app
from src.telemetry import (
    get_current_environment,
    calculate_llm_cost,
    log_llm_usage,
    get_all_quota_statuses,
    format_prometheus_metrics,
    is_api_call_suppressed_for_environment
)

class TestSystemTelemetry(unittest.TestCase):

    def setUp(self):
        os.environ["TESTING"] = "1"
        self.client = TestClient(app)

    def test_environment_detection_default_dev(self):
        """Verify environment defaults to 'dev' when MIDGLEY_ENV is unset."""
        if "MIDGLEY_ENV" in os.environ:
            del os.environ["MIDGLEY_ENV"]
        if "GITHUB_ACTIONS" in os.environ:
            del os.environ["GITHUB_ACTIONS"]
            
        self.assertEqual(get_current_environment(), "dev")

    def test_environment_detection_prod_override(self):
        """Verify MIDGLEY_ENV=prod resolves to 'prod'."""
        os.environ["MIDGLEY_ENV"] = "prod"
        self.assertEqual(get_current_environment(), "prod")
        del os.environ["MIDGLEY_ENV"]

    def test_llm_cost_calculation(self):
        """Verify LLM cost estimation logic per 1M tokens."""
        cost_gemini = calculate_llm_cost("gemini-2.5-flash", prompt_tokens=100_000, completion_tokens=100_000)
        # (0.1M * 0.075) + (0.1M * 0.30) = 0.0075 + 0.03 = 0.0375
        self.assertAlmostEqual(cost_gemini, 0.0375, places=4)

        cost_gpt = calculate_llm_cost("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
        # (1M * 0.15) + (1M * 0.60) = 0.75
        self.assertAlmostEqual(cost_gpt, 0.75, places=4)

    def test_telemetry_logging_persistence_test_mode(self):
        """Verify log_llm_usage respects testing suppression or persistence flags."""
        os.environ["TEST_TELEMETRY_PERSIST"] = "1"
        res = log_llm_usage("google", "gemini-2.5-flash", prompt_tokens=150, completion_tokens=50, environment="dev")
        self.assertIn("total_tokens", res)
        self.assertEqual(res["total_tokens"], 200)
        del os.environ["TEST_TELEMETRY_PERSIST"]

    def test_get_all_quota_statuses(self):
        """Verify get_all_quota_statuses returns finlight, oilpriceapi, alpha_vantage, and gemini keys."""
        quotas = get_all_quota_statuses()
        self.assertIn("finlight", quotas)
        self.assertIn("oilpriceapi", quotas)
        self.assertIn("alpha_vantage", quotas)
        self.assertIn("gemini_llm", quotas)

    def test_format_prometheus_metrics(self):
        """Verify format_prometheus_metrics generates valid Prometheus text feed."""
        metrics_text = format_prometheus_metrics(environment="dev")
        self.assertIn("llm_tokens_consumed_total", metrics_text)
        self.assertIn("llm_estimated_cost_usd_total", metrics_text)
        self.assertIn("api_quota_remaining_ratio", metrics_text)
        self.assertIn('environment="dev"', metrics_text)

    def test_api_call_suppression(self):
        """Verify API call suppression rule when TESTING=1."""
        os.environ["TESTING"] = "1"
        self.assertTrue(is_api_call_suppressed_for_environment("finlight"))

    def test_api_server_prometheus_metrics_endpoint(self):
        """Verify GET /metrics endpoint returns 200 text/plain Prometheus feed."""
        res = self.client.get("/metrics?environment=dev")
        self.assertEqual(res.status_code, 200)
        self.assertIn("llm_tokens_consumed_total", res.text)
        self.assertIn('environment="dev"', res.text)

    def test_api_server_quota_endpoint(self):
        """Verify GET /api/v1/system/quota endpoint returns 200 JSON with quotas."""
        res = self.client.get("/api/v1/system/quota")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"].lower(), "success")
        self.assertIn("quotas", data)
        self.assertIn("finlight", data["quotas"])

if __name__ == '__main__':
    unittest.main()
