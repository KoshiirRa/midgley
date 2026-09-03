"""
Unit tests for RESTful API Server Gateway (src/api_server.py)
Verifies GET /health, GET /api/v1/prices/live, GET /api/v1/forecast/predict,
GET /api/v1/combined, POST /api/v1/forecast/simulate, and /.well-known/ai-plugin.json.
"""

import unittest
from fastapi.testclient import TestClient

from src.api_server import app


import os

class TestAPIServer(unittest.TestCase):

    def setUp(self):
        os.environ["TESTING"] = "1"
        self.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("Midgley", data["system"])

    def test_get_live_prices(self):
        res = self.client.get("/api/v1/prices/live?locale=oakland")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["locale"]["code"], "oakland")
        self.assertGreater(data["price_per_gal"], 0.0)
        self.assertEqual(data["carb_tax_regulatory_burden_per_gal"], 0.953)

    def test_get_live_prices_zip_code(self):
        res = self.client.get("/api/v1/prices/live?zip_code=74103")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["zip_code"], "74103")

    def test_get_forecast(self):
        res = self.client.get("/api/v1/forecast/predict?locale=tulsa&days=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        fc = data["forecast"]
        self.assertEqual(fc["model_version"], "v1.4 Finlight-LLM")
        self.assertEqual(fc["forecast_horizon_days"], 5)
        self.assertGreater(fc["predicted_price_per_gal"], 0.0)
        self.assertIn(fc["projected_direction"], ["UP", "DOWN", "FLAT"])
        self.assertIn("feature_attributions", fc)
        self.assertIn("driver_breakdown", fc)
        self.assertIn("summary_text", fc["driver_breakdown"])
        self.assertEqual(len(fc["feature_attributions"]), 6)

    def test_get_combined(self):
        res = self.client.get("/api/v1/combined?locale=cincinnati")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("live_lookup", data)
        self.assertIn("forecast", data)
        self.assertIn("key_drivers", data)
        self.assertIn("driver_breakdown", data)
        self.assertIn("summary_text", data["driver_breakdown"])
        self.assertEqual(len(data["key_drivers"]), 6)

    def test_get_greenville_forecast(self):
        res = self.client.get("/api/v1/combined?locale=greenville")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["locale"]["region_id"], "Greenville_NC")
        self.assertEqual(data["locale"]["padd_region"], "PADD 1C South Atlantic")

    def test_get_charlotte_forecast(self):
        res = self.client.get("/api/v1/combined?locale=charlotte")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["locale"]["region_id"], "Charlotte_NC")
        self.assertEqual(data["locale"]["padd_region"], "PADD 1C South Atlantic")

    def test_get_port_st_lucie_forecast(self):
        res = self.client.get("/api/v1/combined?locale=port_st_lucie")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["locale"]["region_id"], "Port_St_Lucie_FL")
        self.assertEqual(data["locale"]["padd_region"], "PADD 1C South Atlantic")

    def test_post_simulate(self):
        payload = {
            "scenario_id": "hormuz_blockade",
            "locale": "oakland"
        }
        res = self.client.post("/api/v1/forecast/simulate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scenario"]["id"], "hormuz_blockade")
        sim = data["simulation"]
        self.assertGreater(sim["simulated_price_per_gal"], sim["baseline_price_per_gal"])

    def test_post_simulate_invalid_id(self):
        payload = {
            "scenario_id": "invalid_scenario_xyz",
            "locale": "oakland"
        }
        res = self.client.post("/api/v1/forecast/simulate", json=payload)
        self.assertEqual(res.status_code, 404)

    def test_ai_plugin_manifest(self):
        res = self.client.get("/.well-known/ai-plugin.json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["schema_version"], "v1")
        self.assertEqual(data["name_for_human"], "Midgley Gas Price Intelligence")

    def test_post_webhook_hmac_verification(self):
        import hmac
        import hashlib
        import json
        from unittest.mock import patch

        secret = "test_secret_key_123"
        payload = {"headline": "Canada Announces Retaliatory Tariffs as Trade War Escalates", "url": "https://news.google.com/articles/123", "source": "Test_Runner"}
        body_bytes = json.dumps(payload).encode("utf-8")
        valid_sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        with patch.dict("os.environ", {"MIDGLEY_WEBHOOK_SECRET": secret}):
            # Test 1: Valid signature -> 200 OK
            res_valid = self.client.post(
                "/api/v1/events/webhook",
                content=body_bytes,
                headers={"Content-Type": "application/json", "X-Midgley-Signature": valid_sig}
            )
            self.assertEqual(res_valid.status_code, 200)

            # Test 2: Invalid signature -> 401 Unauthorized
            res_invalid = self.client.post(
                "/api/v1/events/webhook",
                content=body_bytes,
                headers={"Content-Type": "application/json", "X-Midgley-Signature": "bad_signature"}
            )
            self.assertEqual(res_invalid.status_code, 401)

            # Test 3: Missing signature header -> 401 Unauthorized
            res_missing = self.client.post(
                "/api/v1/events/webhook",
                content=body_bytes,
                headers={"Content-Type": "application/json"}
            )
            self.assertEqual(res_missing.status_code, 401)

    def test_post_webhook_flexible_payload_aliases(self):
        import hmac
        import hashlib
        import json
        from unittest.mock import patch

        secret = "test_secret_key_123"
        payload_alias = {
            "title": "Colonial Pipeline Halts Line 1 Intake at Selma Terminal",
            "link": "https://news.google.com/articles/456",
            "origin": "Test_Zapier_Applet"
        }
        body_bytes = json.dumps(payload_alias).encode("utf-8")
        valid_sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        with patch.dict("os.environ", {"MIDGLEY_WEBHOOK_SECRET": secret}):
            res = self.client.post(
                "/api/v1/events/webhook",
                content=body_bytes,
                headers={"Content-Type": "application/json", "X-Midgley-Signature": valid_sig}
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["result"]["headline"], "Colonial Pipeline Halts Line 1 Intake at Selma Terminal")
            self.assertEqual(data["result"]["url"], "https://news.google.com/articles/456")
            self.assertEqual(data["result"]["source"], "Test_Zapier_Applet")
            self.assertIn("Greenville", data["result"]["target_locales"])
            self.assertIn("Charlotte", data["result"]["target_locales"])

    def test_get_forecast_scoreboard(self):
        res = self.client.get("/api/v1/forecast/scoreboard?locale=tulsa&window=30")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("summary", data)
        self.assertIn("regional_breakdown", data)
        self.assertIn("recent_evaluations", data)
        self.assertEqual(data["filters"]["window_days"], "30")

        sum_data = data["summary"]
        self.assertIn("mae_dollars", sum_data)
        self.assertIn("rmse_dollars", sum_data)
        self.assertIn("directional_hit_rate_pct", sum_data)
        self.assertIn("model_uplift_mae_pct", sum_data)


if __name__ == "__main__":
    unittest.main()

