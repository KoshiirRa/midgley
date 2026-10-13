"""
Unit & Integration Tests for Multi-Subscriber Discord Webhooks, Direct Message (DM)
Subscriptions, and `/midgley` Slash Command Manifests (tests/test_discord_subscriptions.py).
Covers Issue #235.
"""

import os
import json
import urllib.error
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.discord_notifier import (
    DiscordSubscriptionRegistry,
    get_subscription_registry,
    validate_discord_webhook_url,
    encrypt_webhook_url,
    decrypt_webhook_url,
    normalize_locale_list,
    infer_event_catalyst_domains,
    dispatch_to_matching_subscribers,
    create_discord_dm_channel,
    send_discord_dm_payload,
)
from src.api_server import app
from scripts.register_discord_commands import (
    build_midgley_command_manifest,
    register_discord_commands,
)


class TestDiscordSubscriptionsUnit:
    def test_webhook_url_validation(self):
        valid_url = "https://discord.com/api/webhooks/123456789012345678/AbCdEfGhIjKlMnOpQrStUvWxYz_0123456789"
        valid_canary = "https://canary.discord.com/api/webhooks/987654321/token_abc-123"
        assert validate_discord_webhook_url(valid_url) is True
        assert validate_discord_webhook_url(valid_canary) is True
        assert validate_discord_webhook_url("http://discord.com/api/webhooks/123/abc") is False
        assert validate_discord_webhook_url("https://example.com/api/webhooks/123/abc") is False
        assert validate_discord_webhook_url("") is False
        assert validate_discord_webhook_url(None) is False

    def test_webhook_encryption_roundtrip(self, monkeypatch):
        monkeypatch.setenv("MIDGLEY_WEBHOOK_SECRET", "unit-test-secret-encryption-key-235")
        raw_url = "https://discord.com/api/webhooks/111222333444555666/SecretWebhookToken_XYZ123"
        encrypted = encrypt_webhook_url(raw_url)
        assert encrypted != raw_url
        assert "SecretWebhookToken_XYZ123" not in encrypted
        decrypted = decrypt_webhook_url(encrypted)
        assert decrypted == raw_url

    def test_locale_normalization_and_catalyst_domains(self):
        locales = normalize_locale_list(["tulsa_ok", "BayArea_CA", "port st. lucie", "tulsa", "National"])
        assert locales == ["Tulsa", "Oakland", "Port_St_Lucie", "National"]

        domains_refinery = infer_event_catalyst_domains({
            "headline": "Major fire and unplanned FCC outage at Chevron Richmond refinery",
            "scores": {"supply_disruption": 0.75, "overall_price_pressure": 0.45}
        })
        assert "refinery_pipeline" in domains_refinery

        domains_weather = infer_event_catalyst_domains({
            "headline": "Category 4 Hurricane enters Gulf Coast refining corridor",
            "scores": {"supply_disruption": 0.60, "overall_price_pressure": 0.50}
        })
        assert "weather_hurricane" in domains_weather

    def test_registry_webhook_and_dm_crud_and_filtering(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TESTING", "1")
        db_file = str(tmp_path / "test_subscribers.sqlite")
        reg = DiscordSubscriptionRegistry(db_path=db_file)

        # 1. Register a Tulsa + National webhook subscriber (spikes_only, threshold 0.30)
        sub_wh = reg.register_subscription(
            target_locales=["Tulsa", "National"],
            minimum_shock_threshold=0.30,
            delivery_type="webhook",
            webhook_url="https://discord.com/api/webhooks/100000001/webhook_token_tulsa",
            direction_filter="spikes_only",
            client_label="Tulsa Fleet Ops",
            verify_handshake=True
        )
        assert sub_wh["subscription_id"].startswith("sub_")
        assert sub_wh["delivery_type"] == "webhook"
        assert sub_wh["target_locales"] == ["Tulsa", "National"]
        assert sub_wh["handshake_verified"] is True

        # 2. Register a Discord Direct Message (discord_dm) subscriber for Oakland & Tulsa
        sub_dm = reg.register_subscription(
            target_locales=["Oakland", "Tulsa"],
            minimum_shock_threshold=0.20,
            delivery_type="discord_dm",
            discord_user_id="998877665544332211",
            direction_filter="all_shocks",
            client_label="@bay_area_driver",
            verify_handshake=True
        )
        assert sub_dm["delivery_type"] == "discord_dm"
        assert sub_dm["discord_user_id"] == "998877665544332211"
        assert sub_dm["dm_channel_id"] == "dm_test_998877665544332211"

        # 3. Check status summary
        summary = reg.get_status_summary()
        assert summary["active_subscriptions"] == 2
        assert summary["by_delivery_type"]["webhook"] == 1
        assert summary["by_delivery_type"]["discord_dm"] == 1
        assert summary["by_locale"]["Tulsa"] == 2
        assert summary["by_locale"]["Oakland"] == 1

        # 4. Query matching subscribers for a Tulsa +0.42 spike -> both should match
        matched_spike = reg.get_matching_subscribers(
            event_locales=["Tulsa"],
            price_pressure=0.42
        )
        assert len(matched_spike) == 2

        # 5. Query matching subscribers for a Tulsa -0.35 price drop -> only sub_dm (all_shocks) matches
        matched_drop = reg.get_matching_subscribers(
            event_locales=["Tulsa"],
            price_pressure=-0.35
        )
        assert len(matched_drop) == 1
        assert matched_drop[0]["subscription_id"] == sub_dm["subscription_id"]

        # 6. Partial locale unsubscribe for DM user
        unsub_part = reg.unsubscribe_by_discord_user("998877665544332211", locale="Oakland")
        assert unsub_part["removed"] is True
        assert unsub_part["remaining_locales"] == ["Tulsa"]

        # 7. Token-verified unsubscribe for webhook
        assert reg.unsubscribe(sub_wh["subscription_id"], manage_token="wrong_token") is False
        assert reg.unsubscribe(sub_wh["subscription_id"], manage_token=sub_wh["manage_token"]) is True

    def test_circuit_breaker_on_dead_webhook_and_blocked_dm(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TESTING", "1")
        db_file = str(tmp_path / "cb_subscribers.sqlite")
        reg = DiscordSubscriptionRegistry(db_path=db_file)

        sub_wh = reg.register_subscription(
            target_locales=["National"],
            minimum_shock_threshold=0.20,
            delivery_type="webhook",
            webhook_url="https://discord.com/api/webhooks/200000002/dead_webhook_token",
            verify_handshake=False
        )
        sub_dm = reg.register_subscription(
            target_locales=["National"],
            minimum_shock_threshold=0.20,
            delivery_type="discord_dm",
            discord_user_id="123456789012345678",
            dm_channel_id="dm_chan_123",
            verify_handshake=False
        )

        event = {
            "headline": "Colonial Pipeline Line 1 unplanned shutdown",
            "source": "Intraday_Monitor",
            "target_locales": ["National"],
            "scores": {"overall_price_pressure": 0.45, "supply_disruption": 0.80}
        }

        # Simulate HTTP 404 on webhook and HTTP 403 (50007 DM blocked) on DM
        with patch("src.discord_notifier._post_webhook_payload", return_value=(False, 404, "HTTP 404: Unknown Webhook")), \
             patch("src.discord_notifier.send_discord_dm_payload", return_value=(False, "dm_chan_123", 403, "HTTP 403: 50007 Cannot send messages to this user")):
            dispatch_res = dispatch_to_matching_subscribers(event, registry=reg)
            assert dispatch_res["matched_subscribers"] == 2
            assert dispatch_res["failed"] == 2
            assert dispatch_res["deactivated"] == 2

        status = reg.get_status_summary()
        assert status["active_subscriptions"] == 0
        assert status["inactive_subscriptions"] == 2

    def test_slash_command_manifest_structure(self, monkeypatch):
        monkeypatch.setenv("TESTING", "1")
        manifest = build_midgley_command_manifest()
        assert len(manifest) == 1
        cmd = manifest[0]
        assert cmd["name"] == "midgley"
        assert cmd["integration_types"] == [0, 1]
        assert cmd["contexts"] == [0, 1, 2]
        sub_names = [opt["name"] for opt in cmd["options"]]
        assert sub_names == ["subscribe", "unsubscribe", "status", "forecast", "test-alert"]

        dry_res = register_discord_commands(dry_run=True)
        assert dry_res["status"] == "dry_run"
        assert dry_res["commands_count"] == 1


class TestDiscordSubscriptionsAPIEndpoints:
    def test_api_subscribe_webhook_and_dm_flow(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TESTING", "1")
        db_file = str(tmp_path / "api_subscribers.sqlite")
        monkeypatch.setenv("MIDGLEY_SUBSCRIBERS_DB_PATH", db_file)
        get_subscription_registry(db_path=db_file, reset=True)

        client = TestClient(app)

        # 1. Subscribe via webhook
        resp_wh = client.post(
            "/api/v1/notifications/discord/subscribe",
            json={
                "delivery_type": "webhook",
                "webhook_url": "https://discord.com/api/webhooks/333444555666/ValidToken_ABC",
                "target_locales": ["Tulsa", "National"],
                "minimum_shock_threshold": 0.35,
                "direction_filter": "spikes_only",
                "client_label": "Tulsa Municipal Fleet"
            }
        )
        assert resp_wh.status_code == 200
        data_wh = resp_wh.json()
        assert data_wh["status"] == "subscribed"
        sub_id_wh = data_wh["subscription"]["subscription_id"]
        manage_token_wh = data_wh["subscription"]["manage_token"]

        # 2. Subscribe via Discord Direct Message (discord_dm)
        resp_dm = client.post(
            "/api/v1/notifications/discord/subscribe",
            json={
                "delivery_type": "discord_dm",
                "discord_user_id": "445566778899001122",
                "target_locales": ["Cincinnati", "Chicago"],
                "minimum_shock_threshold": 0.25,
                "direction_filter": "all_shocks",
                "client_label": "Discord Server Member"
            }
        )
        assert resp_dm.status_code == 200
        data_dm = resp_dm.json()
        assert data_dm["subscription"]["delivery_type"] == "discord_dm"
        assert data_dm["subscription"]["discord_user_id"] == "445566778899001122"

        # 3. Check subscription status endpoint
        resp_status = client.get("/api/v1/notifications/discord/subscriptions/status")
        assert resp_status.status_code == 200
        summary = resp_status.json()["summary"]
        assert summary["active_subscriptions"] == 2
        assert summary["by_delivery_type"]["webhook"] == 1
        assert summary["by_delivery_type"]["discord_dm"] == 1
        assert summary["by_locale"]["Tulsa"] == 1
        assert summary["by_locale"]["Cincinnati"] == 1

        # 4. Self-service test endpoint (both webhook and DM)
        resp_test_dm = client.post(
            "/api/v1/notifications/discord/test",
            json={
                "delivery_type": "discord_dm",
                "discord_user_id": "445566778899001122",
                "target_locales": ["Cincinnati"]
            }
        )
        assert resp_test_dm.status_code == 200
        assert resp_test_dm.json()["status"] == "delivered"

        # 5. Unsubscribe webhook with manage_token
        resp_del = client.delete(
            f"/api/v1/notifications/discord/subscriptions/{sub_id_wh}",
            params={"manage_token": manage_token_wh}
        )
        assert resp_del.status_code == 200
        assert resp_del.json()["status"] == "unsubscribed"
