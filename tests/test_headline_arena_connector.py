"""
Unit Tests for Headline Arena Energy Forecasting Connector (tests/test_headline_arena_connector.py)
"""

import os
import math
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from src.headline_arena_connector import (
    norm_cdf,
    compute_directional_probabilities,
    HeadlineArenaConnector,
    submit_midgley_energy_forecasts,
    DEFAULT_SETTLEMENT_RULES
)


class TestHeadlineArenaConnector(unittest.TestCase):
    def setUp(self):
        from src.headline_arena_connector import load_submitted_ledger, load_pending_forecasts
        load_submitted_ledger._test_mock_ledger = {"submitted_challenges": {}}
        load_pending_forecasts._test_mock_pending = []
        self.sample_rb_forecast = {
            "open_price": 2.4500,
            "p50": 2.5200,
            "p10": 2.4100,
            "p90": 2.6300,
            "qualitative_catalysts": {
                "overall_price_pressure": 0.35,
                "supply_disruption": 0.40,
                "geopolitical_risk": 0.15
            }
        }
        self.sample_cl_forecast = {
            "open_price": 78.50,
            "p50": 77.20,
            "p10": 74.80,
            "p90": 79.60,
            "qualitative_catalysts": {
                "overall_price_pressure": -0.25,
                "supply_disruption": 0.10,
                "geopolitical_risk": 0.05
            }
        }

    def test_norm_cdf(self):
        self.assertAlmostEqual(norm_cdf(0.0), 0.5, places=5)
        self.assertAlmostEqual(norm_cdf(1.95996), 0.975, places=3)
        self.assertAlmostEqual(norm_cdf(-1.95996), 0.025, places=3)
        self.assertAlmostEqual(norm_cdf(3.0), 0.99865, places=4)
        self.assertAlmostEqual(norm_cdf(-3.0), 0.00135, places=4)

    def test_compute_directional_probabilities_bullish(self):
        # Open: $2.40, P50: $2.60 (well above +0.30% dead zone of $2.4072)
        res = compute_directional_probabilities(
            open_price=2.4000,
            p50=2.6000,
            p10=2.5000,
            p90=2.7000,
            dead_zone=0.0030
        )
        self.assertEqual(res["direction"], "bullish")
        self.assertGreater(res["confidence"], 0.70)
        self.assertGreater(res["probabilities"]["bullish"], res["probabilities"]["bearish"])
        self.assertGreater(res["probabilities"]["bullish"], res["probabilities"]["neutral"])
        
        # Verify probability sum equals 1.0
        prob_sum = sum(res["probabilities"].values())
        self.assertAlmostEqual(prob_sum, 1.0, places=3)

    def test_compute_directional_probabilities_bearish(self):
        # Open: $2.50, P50: $2.30 (well below -0.30% dead zone of $2.4925)
        res = compute_directional_probabilities(
            open_price=2.5000,
            p50=2.3000,
            p10=2.2000,
            p90=2.4000,
            dead_zone=0.0030
        )
        self.assertEqual(res["direction"], "bearish")
        self.assertGreater(res["confidence"], 0.70)
        self.assertGreater(res["probabilities"]["bearish"], res["probabilities"]["bullish"])
        
        prob_sum = sum(res["probabilities"].values())
        self.assertAlmostEqual(prob_sum, 1.0, places=3)

    def test_compute_directional_probabilities_neutral(self):
        # Open: $2.4500, P50: $2.4502, tight sigma (0.0005) inside ±0.30% dead zone [$2.44265, $2.45735]
        res = compute_directional_probabilities(
            open_price=2.4500,
            p50=2.4502,
            residual_std=0.001,
            dead_zone=0.0030
        )
        self.assertEqual(res["direction"], "neutral")
        self.assertGreater(res["probabilities"]["neutral"], 0.80)

    def test_dead_zones_rb_cl(self):
        connector = HeadlineArenaConnector()
        self.assertEqual(connector.get_dead_zone("RB"), 0.0030)
        self.assertEqual(connector.get_dead_zone("CL"), 0.0030)

    def test_synthesize_forecasting_rationale_rb(self):
        from src.headline_arena_connector import synthesize_forecasting_rationale
        rationale = synthesize_forecasting_rationale(
            asset="RB",
            open_price=2.4500,
            p50=2.5200,
            direction="bullish",
            confidence=0.745,
            probabilities={"bullish": 0.745, "neutral": 0.185, "bearish": 0.070},
            dead_zone=0.0030,
            t_upper=2.45735,
            t_lower=2.44265,
            p10=2.4100,
            p90=2.6300,
            sigma=0.0858,
            qualitative_catalysts={"overall_price_pressure": 0.35, "supply_disruption": 0.40, "geopolitical_risk": 0.15, "opec_action": 0.20},
            technical_indicators={"crack_spread": 26.50, "wti_price": 76.40},
            physical_feeds={"ovx_volatility": 32.4, "rig_count": 480}
        )
        self.assertIn("[Midgley Multi-Agent Forecast | RBOB Wholesale Gasoline (RB=F)]", rationale)
        self.assertIn("Executive Direction: BULLISH (Confidence: 74.5%", rationale)
        self.assertIn("Multi-Agent Ensemble Distribution: Open $/gal2.4500, P50 Target $/gal2.5200", rationale)
        self.assertIn("Dead-Zone CDF Decomposition: P(Bullish)=74.5%", rationale)
        self.assertIn("Implied 3:2:1 refinery crack spread margin is positioned at $26.50/bbl", rationale)
        self.assertIn("Price Pressure: +0.35", rationale)
        self.assertIn("Cboe OVX crude volatility at 32.4 pts", rationale)
        self.assertIn("Settlement Thesis:", rationale)

    def test_synthesize_forecasting_rationale_cl(self):
        from src.headline_arena_connector import synthesize_forecasting_rationale
        rationale = synthesize_forecasting_rationale(
            asset="CL",
            open_price=78.50,
            p50=77.20,
            direction="bearish",
            confidence=0.682,
            probabilities={"bullish": 0.120, "neutral": 0.198, "bearish": 0.682},
            dead_zone=0.0030,
            t_upper=78.7355,
            t_lower=78.2645,
            p10=74.80,
            p90=79.60,
            sigma=1.8727,
            qualitative_catalysts={"overall_price_pressure": -0.25, "supply_disruption": 0.10, "geopolitical_risk": 0.05},
            technical_indicators={"rbob_price": 2.4500},
            physical_feeds={"ovx_volatility": 28.5, "rig_count": 482}
        )
        self.assertIn("[Midgley Multi-Agent Forecast | Cushing WTI Crude Oil (CL=F)]", rationale)
        self.assertIn("Executive Direction: BEARISH (Confidence: 68.2%", rationale)
        self.assertIn("Multi-Agent Ensemble Distribution: Open $/bbl78.5000, P50 Target $/bbl77.2000", rationale)
        self.assertIn("Downstream product demand from wholesale RBOB", rationale)
        self.assertIn("Settlement Thesis:", rationale)

    def test_format_direction_payload_dev_tagging(self):
        connector = HeadlineArenaConnector(environment="dev")
        payload = connector.format_direction_payload(
            asset="RB",
            open_price=self.sample_rb_forecast["open_price"],
            p50=self.sample_rb_forecast["p50"],
            p10=self.sample_rb_forecast["p10"],
            p90=self.sample_rb_forecast["p90"],
            qualitative_catalysts=self.sample_rb_forecast["qualitative_catalysts"]
        )
        self.assertEqual(payload["asset"], "RB")
        self.assertIn("direction", payload)
        self.assertIn("confidence", payload)
        self.assertIn("[DEV-TEST]", payload["reasoning"])
        self.assertIn("[DEVELOPMENT]", payload["reasoning"])
        self.assertIn("Price Pressure", payload["reasoning"])

    def test_format_direction_payload_prod_clean(self):
        connector = HeadlineArenaConnector(environment="prod")
        payload = connector.format_direction_payload(
            asset="RB",
            open_price=self.sample_rb_forecast["open_price"],
            p50=self.sample_rb_forecast["p50"],
            p10=self.sample_rb_forecast["p10"],
            p90=self.sample_rb_forecast["p90"]
        )
        self.assertEqual(payload["asset"], "RB")
        self.assertNotIn("[DEV-TEST]", payload["reasoning"])
        self.assertNotIn("[DEVELOPMENT]", payload["reasoning"])
        self.assertIn("Midgley Multi-Agent", payload["reasoning"])

    def test_format_macro_numeric_payload(self):
        connector = HeadlineArenaConnector(environment="prod")
        payload = connector.format_macro_numeric_payload(
            asset="CL",
            p50=75.50,
            p10=72.00,
            p90=79.00
        )
        self.assertEqual(payload["asset"], "CL")
        self.assertEqual(payload["predicted_value"], 75.50)
        self.assertAlmostEqual(payload["predicted_std"], (79.0 - 72.0) / 2.5631, places=3)

    def test_oauth2_token_caching_and_expiration(self):
        connector = HeadlineArenaConnector(
            client_id="test_id",
            client_secret="test_secret"
        )
        with patch.dict(os.environ, {"TESTING": "0"}, clear=True):
            # Mock the POST /auth/token endpoint
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"access_token": "token_abc_123", "expires_in": 3600}'
            mock_response.__enter__.return_value = mock_response

            with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
                token1 = connector.get_bearer_token()
                self.assertEqual(token1, "token_abc_123")
                self.assertEqual(mock_urlopen.call_count, 1)

                # Second call should use in-memory cache without hitting network
                token2 = connector.get_bearer_token()
                self.assertEqual(token2, "token_abc_123")
                self.assertEqual(mock_urlopen.call_count, 1)

                # Force refresh should hit network again
                token3 = connector.get_bearer_token(force_refresh=True)
                self.assertEqual(token3, "token_abc_123")
                self.assertEqual(mock_urlopen.call_count, 2)

    def test_submit_forecast_test_mode_suppression(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            connector = HeadlineArenaConnector(client_id="test_id", client_secret="test_secret")
            payload = {"asset": "RB", "direction": "bullish", "confidence": 0.85, "reasoning": "Test"}
            res = connector.submit_forecast(payload)
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["mode"], "TEST_MOCKED")
            self.assertEqual(res["direction"], "bullish")

    def test_submit_forecast_missing_credentials(self):
        with patch.dict(os.environ, {"TESTING": "0"}, clear=True):
            connector = HeadlineArenaConnector(client_id="", client_secret="")
            payload = {"asset": "RB", "direction": "bullish", "confidence": 0.85}
            res = connector.submit_forecast(payload)
            self.assertEqual(res["status"], "SKIPPED_NO_CREDENTIALS")

    def test_submit_forecast_dev_dry_run(self):
        with patch.dict(os.environ, {"TESTING": "0", "MIDGLEY_ENV": "dev"}, clear=True):
            connector = HeadlineArenaConnector(
                client_id="test_id",
                client_secret="test_secret",
                environment="dev"
            )
            payload = {"asset": "RB", "direction": "bullish", "confidence": 0.85, "reasoning": "Dev test"}
            res = connector.submit_forecast(payload, live_in_dev=False)
            self.assertEqual(res["status"], "DRY_RUN")
            self.assertEqual(res["mode"], "DEVELOPMENT_DRY_RUN")
            self.assertEqual(res["direction"], "bullish")

    def test_submit_forecast_dev_live_explicit(self):
        with patch.dict(os.environ, {"TESTING": "0", "MIDGLEY_ENV": "dev"}, clear=True):
            connector = HeadlineArenaConnector(
                client_id="test_id",
                client_secret="test_secret",
                environment="dev"
            )
            # Mock bearer token, scope subscription, and active challenge resolution
            connector.get_bearer_token = MagicMock(return_value="mock_bearer_token")
            connector.ensure_scope_subscription = MagicMock(return_value=True)
            connector.get_active_challenge_for_asset = MagicMock(
                return_value={"challenge": {"id": "chal_cl_456", "asset": "CL"}}
            )

            mock_response = MagicMock()
            mock_response.read.return_value = b'{"status": "accepted", "counts_for_score": true}'
            mock_response.__enter__.return_value = mock_response

            with patch("urllib.request.urlopen", return_value=mock_response), \
                 patch("src.headline_arena_connector.load_submitted_ledger", return_value={"submitted_challenges": {}}):
                payload = {"asset": "CL", "direction": "bullish", "confidence": 0.85, "reasoning": "[DEV-TEST] Model evaluation"}
                res = connector.submit_forecast(payload, live_in_dev=True)
                self.assertEqual(res["status"], "SUCCESS")
                self.assertEqual(res["mode"], "LIVE_SUBMISSION")
                self.assertEqual(res["challenge_id"], "chal_cl_456")
                self.assertTrue(res["counts_for_score"])

    def test_submit_forecast_duplicate_handled_gracefully(self):
        with patch.dict(os.environ, {"TESTING": "0", "MIDGLEY_ENV": "prod"}, clear=True):
            connector = HeadlineArenaConnector(
                client_id="test_id",
                client_secret="test_secret",
                environment="prod"
            )
            connector.get_bearer_token = MagicMock(return_value="mock_bearer_token")
            connector.ensure_scope_subscription = MagicMock(return_value=True)
            connector.get_active_challenge_for_asset = MagicMock(
                return_value={"challenge": {"id": "chal_cl_456", "asset": "CL"}}
            )

            # Mock HTTP 500 error from Headline Arena on duplicate submission
            mock_err = urllib.error.HTTPError(
                url="https://headlinearena.com/api/v1/eval/challenges/chal_cl_456/predict",
                code=500,
                msg="Internal Server Error",
                hdrs={},
                fp=None
            )
            with patch("urllib.request.urlopen", side_effect=mock_err):
                payload = {"asset": "CL", "direction": "bullish", "confidence": 0.85, "reasoning": "Model evaluation"}
                res = connector.submit_forecast(payload)
                self.assertEqual(res["status"], "ALREADY_SUBMITTED")
                self.assertEqual(res["mode"], "SKIPPED_ALREADY_PREDICTED")
                self.assertEqual(res["challenge_id"], "chal_cl_456")
                self.assertIn("already predicted", res["message"])

    def test_submit_forecast_no_active_challenge(self):
        with patch.dict(os.environ, {"TESTING": "0", "MIDGLEY_ENV": "dev"}, clear=True):
            connector = HeadlineArenaConnector(
                client_id="test_id",
                client_secret="test_secret",
                environment="dev"
            )
            connector.get_bearer_token = MagicMock(return_value="mock_bearer_token")
            connector.ensure_scope_subscription = MagicMock(return_value=True)
            connector.get_active_challenge_for_asset = MagicMock(return_value=None)

            payload = {"asset": "RB", "direction": "bullish", "confidence": 0.85}
            res = connector.submit_forecast(payload, live_in_dev=True)
            self.assertEqual(res["status"], "SKIPPED_NO_ACTIVE_CHALLENGE")
            self.assertIn("No active challenge found", res["message"])

    def test_ensure_scope_subscription_and_active_challenges(self):
        with patch.dict(os.environ, {"TESTING": "0"}, clear=True):
            connector = HeadlineArenaConnector(client_id="test_id", client_secret="test_secret")
            connector.get_bearer_token = MagicMock(return_value="mock_bearer_token")

            # Mock scope subscription POST and active challenges GET
            mock_sub_resp = MagicMock()
            mock_sub_resp.read.return_value = b'{"status": "subscribed"}'
            mock_sub_resp.__enter__.return_value = mock_sub_resp

            mock_active_resp1 = MagicMock()
            mock_active_resp1.read.return_value = b'{"challenges": [{"challenge": {"id": "chal_cl_999", "asset": "CL"}}]}'
            mock_active_resp1.__enter__.return_value = mock_active_resp1

            mock_active_resp2 = MagicMock()
            mock_active_resp2.read.return_value = b'{"challenges": [{"challenge": {"id": "chal_cl_999", "asset": "CL"}}]}'
            mock_active_resp2.__enter__.return_value = mock_active_resp2

            mock_active_resp3 = MagicMock()
            mock_active_resp3.read.return_value = b'{"challenges": [{"challenge": {"id": "chal_cl_999", "asset": "CL"}}]}'
            mock_active_resp3.__enter__.return_value = mock_active_resp3

            with patch("urllib.request.urlopen", side_effect=[mock_sub_resp, mock_active_resp1, mock_active_resp2, mock_active_resp3]):
                sub_res = connector.ensure_scope_subscription("CL")
                self.assertTrue(sub_res)
                self.assertIn("CL", connector._subscribed_scopes)

                challenges = connector.get_active_challenges()
                self.assertEqual(len(challenges), 1)
                
                cl_chal = connector.get_active_challenge_for_asset("CL")
                self.assertIsNotNone(cl_chal)
                self.assertEqual(cl_chal["challenge"]["id"], "chal_cl_999")

                rb_chal = connector.get_active_challenge_for_asset("RB")
                self.assertIsNone(rb_chal)

    def test_register_agent(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            connector = HeadlineArenaConnector()
            res = connector.register_agent(name="Test-Agent")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn("client_id", res)
            self.assertIn("client_secret", res)

    def test_submit_midgley_energy_forecasts_multi_asset(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            results = submit_midgley_energy_forecasts(
                rb_open_price=2.4500,
                rb_p50=2.5200,
                rb_p10=2.4100,
                rb_p90=2.6300,
                cl_open_price=78.50,
                cl_p50=77.20,
                cl_p10=74.80,
                cl_p90=79.60
            )
            self.assertIn("RB", results)
            self.assertIn("CL", results)
            self.assertEqual(results["RB"]["status"], "SUCCESS")
            self.assertEqual(results["CL"]["status"], "SUCCESS")

    def test_pending_forecast_cache_and_expiration(self):
        import tempfile
        import time
        from src.headline_arena_connector import (
            save_pending_forecast,
            load_pending_forecasts,
            clear_expired_pending_forecasts
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            # 1. Save active pending forecast (TTL: 24h)
            rec1 = save_pending_forecast(
                asset="RB",
                payload={"direction": "bullish", "confidence": 0.75},
                forecast_type="direction",
                ttl_hours=24.0,
                filepath=temp_path
            )
            self.assertEqual(rec1["asset"], "RB")

            # 2. Save expired pending forecast (negative TTL)
            rec2 = save_pending_forecast(
                asset="CL",
                payload={"direction": "bearish", "confidence": 0.65},
                forecast_type="direction",
                ttl_hours=-1.0,
                filepath=temp_path
            )

            # 3. Load active only (should return RB, not CL)
            active = load_pending_forecasts(active_only=True, filepath=temp_path)
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["asset"], "RB")

            # 4. Load all records (should return both)
            all_records = load_pending_forecasts(active_only=False, filepath=temp_path)
            self.assertEqual(len(all_records), 2)

            # 5. Clear expired
            purged = clear_expired_pending_forecasts(filepath=temp_path)
            self.assertEqual(purged, 1)

            # 6. Verify only active remains on disk
            after_purge = load_pending_forecasts(active_only=False, filepath=temp_path)
            self.assertEqual(len(after_purge), 1)
            self.assertEqual(after_purge[0]["asset"], "RB")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_submitted_ledger_idempotency(self):
        import tempfile
        from src.headline_arena_connector import (
            is_challenge_already_submitted,
            record_submitted_challenge,
            load_submitted_ledger
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            self.assertFalse(is_challenge_already_submitted("chal_test_101", filepath=temp_path))
            record_submitted_challenge("chal_test_101", "RB", {"status": "SUCCESS"}, filepath=temp_path)
            self.assertTrue(is_challenge_already_submitted("chal_test_101", filepath=temp_path))

            ledger = load_submitted_ledger(filepath=temp_path)
            self.assertIn("chal_test_101", ledger["submitted_challenges"])
            self.assertEqual(ledger["submitted_challenges"]["chal_test_101"]["asset"], "RB")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_eia_retail_civic_payload_formatting(self):
        connector = HeadlineArenaConnector()
        payload = connector.format_eia_retail_civic_payload(
            predicted_value=3.215,
            p10=3.120,
            p90=3.310
        )
        self.assertEqual(payload["asset"], "EIA_RETAIL_GASOLINE")
        self.assertEqual(payload["predicted_value"], 3.215)
        self.assertAlmostEqual(payload["predicted_std"], (3.310 - 3.120) / 2.5631, places=3)
        self.assertIn("EIA US Regular Gasoline", payload["reasoning"])
        self.assertIn("metadata", payload)
        self.assertEqual(payload["metadata"]["p50"], 3.215)

    def test_submit_macro_forecast_testing_mode(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            connector = HeadlineArenaConnector()
            payload = connector.format_eia_retail_civic_payload(
                predicted_value=3.185,
                p10=3.090,
                p90=3.280
            )
            res = connector.submit_macro_forecast(
                challenge_id="mock_civic_chal_555",
                payload=payload
            )
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["predicted_value"], 3.185)
            self.assertEqual(res["mode"], "TEST_MOCKED")

    def test_dispatch_pending_forecasts(self):
        import tempfile
        from src.headline_arena_connector import (
            save_pending_forecast,
            load_pending_forecasts
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_p:
            pending_path = tf_p.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_l:
            ledger_path = tf_l.name

        try:
            with patch.dict(os.environ, {"TESTING": "1"}):
                connector = HeadlineArenaConnector()
                # Seed pending forecast
                save_pending_forecast(
                    asset="CL",
                    payload={"direction": "bearish", "confidence": 0.70},
                    forecast_type="direction",
                    filepath=pending_path
                )

                # Dispatch (in TESTING mode, mock challenge matches CL)
                res = connector.dispatch_pending_forecasts(
                    pending_file=pending_path,
                    ledger_file=ledger_path
                )
                self.assertEqual(res["status"], "COMPLETED")
                self.assertEqual(res["dispatched"], 1)
                self.assertIn("CL", res["results"])

                # Second dispatch should recognize challenge as ALREADY_SUBMITTED
                res2 = connector.dispatch_pending_forecasts(
                    pending_file=pending_path,
                    ledger_file=ledger_path
                )
                self.assertEqual(res2["status"], "COMPLETED")
                self.assertEqual(res2["results"]["CL"]["status"], "ALREADY_SUBMITTED")
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)
            if os.path.exists(ledger_path):
                os.remove(ledger_path)

    def test_submit_midgley_energy_forecasts_with_eia_retail(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            results = submit_midgley_energy_forecasts(
                rb_open_price=2.4500,
                rb_p50=2.5200,
                rb_p10=2.4100,
                rb_p90=2.6300,
                cl_open_price=78.50,
                cl_p50=77.20,
                cl_p10=74.80,
                cl_p90=79.60,
                eia_retail_p50=3.215,
                eia_retail_p10=3.120,
                eia_retail_p90=3.310
            )
            self.assertIn("RB", results)
            self.assertIn("CL", results)
            self.assertIn("EIA_RETAIL_GASOLINE", results)
            self.assertEqual(results["RB"]["status"], "SUCCESS")
            self.assertEqual(results["CL"]["status"], "SUCCESS")


    def test_api_server_headline_arena_status(self):
        from fastapi.testclient import TestClient
        from src.api_server import app
        client = TestClient(app)
        with patch.dict(os.environ, {"TESTING": "1"}):
            res = client.get("/api/v1/connectors/headline-arena/status")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("settlement_rules", data)
            self.assertIn("RB", data["settlement_rules"])
            self.assertIn("CL", data["settlement_rules"])

    def test_api_server_headline_arena_submit(self):
        from fastapi.testclient import TestClient
        from src.api_server import app
        client = TestClient(app)
        with patch.dict(os.environ, {"TESTING": "1"}):
            res = client.post("/api/v1/connectors/headline-arena/submit", json={
                "asset": "RB",
                "open_price": 2.45,
                "p50": 2.52,
                "p10": 2.41,
                "p90": 2.63,
                "live_in_dev": False
            })
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("payload", data)
            self.assertIn("result", data)


    def test_dead_zones_ng_dxy(self):
        connector = HeadlineArenaConnector()
        self.assertEqual(connector.get_dead_zone("NG"), 0.0050)
        self.assertEqual(connector.get_dead_zone("DXY"), 0.0020)

    def test_synthesize_forecasting_rationale_ng(self):
        from src.headline_arena_connector import synthesize_forecasting_rationale
        rationale = synthesize_forecasting_rationale(
            asset="NG",
            open_price=2.850,
            p50=2.980,
            direction="bullish",
            confidence=0.760,
            probabilities={"bullish": 0.760, "neutral": 0.160, "bearish": 0.080},
            dead_zone=0.0050,
            t_upper=2.86425,
            t_lower=2.83575,
            p10=2.800,
            p90=3.100,
            sigma=0.117
        )
        self.assertIn("Henry Hub Natural Gas Futures (NG=F)", rationale)
        self.assertIn("$/MMBtu", rationale)
        self.assertIn("heating/cooling degree day", rationale)
        self.assertIn("BULLISH", rationale)

    def test_synthesize_forecasting_rationale_dxy(self):
        from src.headline_arena_connector import synthesize_forecasting_rationale
        rationale = synthesize_forecasting_rationale(
            asset="DXY",
            open_price=101.500,
            p50=101.100,
            direction="bearish",
            confidence=0.720,
            probabilities={"bullish": 0.090, "neutral": 0.190, "bearish": 0.720},
            dead_zone=0.0020,
            t_upper=101.703,
            t_lower=101.297,
            p10=100.800,
            p90=101.400
        )
        self.assertIn("US Dollar Index (DXY)", rationale)
        self.assertIn("pts", rationale)
        self.assertIn("Federal Reserve rate expectation", rationale)
        self.assertIn("BEARISH", rationale)

    def test_submit_midgley_energy_forecasts_with_ng_and_dxy(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            results = submit_midgley_energy_forecasts(
                rb_open_price=2.4500,
                rb_p50=2.5200,
                rb_p10=2.4100,
                rb_p90=2.6300,
                cl_open_price=78.50,
                cl_p50=77.20,
                cl_p10=74.80,
                cl_p90=79.60,
                ng_open_price=2.850,
                ng_p50=2.980,
                ng_p10=2.800,
                ng_p90=3.100,
                dxy_open_price=101.500,
                dxy_p50=101.100,
                dxy_p10=100.800,
                dxy_p90=101.400,
                eia_retail_p50=3.215,
                eia_retail_p10=3.120,
                eia_retail_p90=3.310
            )
            self.assertIn("RB", results)
            self.assertIn("CL", results)
            self.assertIn("NG", results)
            self.assertIn("DXY", results)
            self.assertIn("EIA_RETAIL_GASOLINE", results)
            self.assertEqual(results["RB"]["status"], "SUCCESS")
            self.assertEqual(results["CL"]["status"], "SUCCESS")
            self.assertEqual(results["NG"]["status"], "SUCCESS")
            self.assertEqual(results["DXY"]["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()

