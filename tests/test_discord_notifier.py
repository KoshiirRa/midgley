"""
Unit Tests for Discord Webhook Notification Engine (tests/test_discord_notifier.py)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from src.discord_notifier import (
    get_environment_label,
    format_intraday_discord_payload,
    send_intraday_discord_notification
)


class TestDiscordNotifier(unittest.TestCase):
    def setUp(self):
        self.sample_event = {
            "timestamp": "2026-09-10T21:00:00",
            "headline": "Massive Explosion Shuts Down Midwest Refinery Capacity",
            "source": "Cloudflare_Worker",
            "url": "https://energy.example.com/refinery-explosion",
            "archive_url": "https://web.archive.org/web/20260910/refinery-explosion",
            "is_anomaly": True,
            "target_locales": ["Tulsa", "Cincinnati"],
            "scores": {
                "overall_price_pressure": 0.45,
                "supply_disruption": 0.80,
                "geopolitical_risk": 0.10,
                "opec_action": 0.0
            }
        }

    def test_environment_resolution_dev(self):
        with patch.dict(os.environ, {"MIDGLEY_ENV": "dev"}, clear=True):
            self.assertEqual(get_environment_label(), "dev")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_environment_label(), "dev")

    def test_environment_resolution_prod(self):
        with patch.dict(os.environ, {"MIDGLEY_ENV": "prod"}, clear=True):
            self.assertEqual(get_environment_label(), "prod")
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            self.assertEqual(get_environment_label(), "prod")

    def test_format_payload_dev_structure(self):
        payload = format_intraday_discord_payload(self.sample_event, environment="dev")
        self.assertIn("embeds", payload)
        self.assertEqual(len(payload["embeds"]), 1)
        embed = payload["embeds"][0]

        self.assertIn("[DEVELOPMENT]", embed["title"])
        self.assertIn("Massive Explosion", embed["description"])
        # High supply disruption (0.80) -> Red color (15158332)
        self.assertEqual(embed["color"], 15158332)

        # Check fields
        field_names = [f["name"] for f in embed["fields"]]
        self.assertIn("🌐 Environment", field_names)
        self.assertIn("📡 Ingestion Source", field_names)
        self.assertIn("📍 Target Metro Hubs", field_names)
        self.assertIn("📊 Price Pressure (ΔP)", field_names)
        self.assertIn("🛢️ Supply Disruption (S)", field_names)
        self.assertIn("🌍 Geopolitical Risk (G)", field_names)
        self.assertIn("🔗 Intelligence Sources", field_names)

        # Check values
        env_field = next(f for f in embed["fields"] if f["name"] == "🌐 Environment")
        self.assertIn("Development", env_field["value"])

        locales_field = next(f for f in embed["fields"] if f["name"] == "📍 Target Metro Hubs")
        self.assertIn("Tulsa, Cincinnati", locales_field["value"])

        sources_field = next(f for f in embed["fields"] if f["name"] == "🔗 Intelligence Sources")
        self.assertIn("[Original Article](https://energy.example.com/refinery-explosion)", sources_field["value"])
        self.assertIn("[Wayback Machine Archive](https://web.archive.org/web/20260910/refinery-explosion)", sources_field["value"])

    def test_format_payload_prod_structure(self):
        payload = format_intraday_discord_payload(self.sample_event, environment="prod")
        embed = payload["embeds"][0]
        self.assertIn("[PRODUCTION]", embed["title"])

        env_field = next(f for f in embed["fields"] if f["name"] == "🌐 Environment")
        self.assertIn("Production", env_field["value"])

    def test_format_payload_color_coding(self):
        # 1. Bearish price pressure (<= -0.20) -> Green
        bearish_event = {
            "headline": "OPEC Floods Market with Unexpected Surplus",
            "scores": {"overall_price_pressure": -0.35, "supply_disruption": 0.0}
        }
        p_bear = format_intraday_discord_payload(bearish_event)
        self.assertEqual(p_bear["embeds"][0]["color"], 3066993)  # Green

        # 2. Bullish price spike (>= 0.40) -> Red
        bullish_event = {
            "headline": "Tariff War Hikes Crude Import Costs",
            "scores": {"overall_price_pressure": 0.42, "supply_disruption": 0.20}
        }
        p_bull = format_intraday_discord_payload(bullish_event)
        self.assertEqual(p_bull["embeds"][0]["color"], 15158332)  # Red

        # 3. Moderate shock -> Orange
        mod_event = {
            "headline": "Minor Pipeline Maintenance Delay",
            "scores": {"overall_price_pressure": 0.15, "supply_disruption": 0.25}
        }
        p_mod = format_intraday_discord_payload(mod_event)
        self.assertEqual(p_mod["embeds"][0]["color"], 15105570)  # Orange

    def test_send_notification_no_url(self):
        with patch.dict(os.environ, {}, clear=True):
            res = send_intraday_discord_notification(self.sample_event, webhook_url=None)
            self.assertFalse(res)

    def test_send_notification_testing_suppression(self):
        with patch.dict(os.environ, {"TESTING": "1"}, clear=True):
            res = send_intraday_discord_notification(
                self.sample_event,
                webhook_url="https://discord.com/api/webhooks/dummy/dummy"
            )
            # Should suppress HTTP dispatch and return True
            self.assertTrue(res)

    @patch("urllib.request.urlopen")
    def test_send_notification_http_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with patch.dict(os.environ, {"TEST_WEBHOOK_DISPATCH": "1"}, clear=True):
            res = send_intraday_discord_notification(
                self.sample_event,
                webhook_url="https://discord.com/api/webhooks/dummy/dummy",
                environment="prod"
            )
            self.assertTrue(res)
            mock_urlopen.assert_called_once()
            req_arg = mock_urlopen.call_args[0][0]
            self.assertEqual(req_arg.get_method(), "POST")
            self.assertEqual(req_arg.headers.get("Content-type"), "application/json")

    @patch("urllib.request.urlopen")
    def test_send_notification_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with patch.dict(os.environ, {"TEST_WEBHOOK_DISPATCH": "1"}, clear=True):
            res = send_intraday_discord_notification(
                self.sample_event,
                webhook_url="https://discord.com/api/webhooks/dummy/dummy"
            )
            self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
