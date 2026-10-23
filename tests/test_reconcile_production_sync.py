"""
Unit tests for Friday pre-audit production data sync (scripts/reconcile_production_sync.py).
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

from scripts.reconcile_production_sync import (
    format_sync_discord_payload,
    send_sync_discord_notification,
    reconcile_intraday_events_json,
    execute_sync
)


class TestReconcileProductionSync(unittest.TestCase):

    def test_format_payload_success(self):
        payload = format_sync_discord_payload(
            status="SUCCESS",
            commits_count=5,
            commits_summary=["abc1234 feat: update", "def5678 chore: run"],
            details="Merged cleanly"
        )
        self.assertIn("embeds", payload)
        embed = payload["embeds"][0]
        self.assertIn("Synchronized", embed["title"])
        self.assertEqual(embed["color"], 0x22c55e)
        self.assertTrue(any(f["name"] == "Status" and f["value"] == "`SUCCESS`" for f in embed["fields"]))

    def test_format_payload_up_to_date(self):
        payload = format_sync_discord_payload(
            status="UP_TO_DATE",
            commits_count=0,
            commits_summary=[]
        )
        embed = payload["embeds"][0]
        self.assertIn("Up to Date", embed["title"])
        self.assertEqual(embed["color"], 0x3b82f6)

    def test_format_payload_failed(self):
        payload = format_sync_discord_payload(
            status="FAILED",
            commits_count=2,
            commits_summary=["abc1234"],
            details="Merge conflict error"
        )
        embed = payload["embeds"][0]
        self.assertIn("Failed", embed["title"])
        self.assertEqual(embed["color"], 0xef4444)

    def test_send_sync_discord_notification_testing_suppression(self):
        with patch.dict(os.environ, {"TESTING": "1", "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test"}):
            payload = format_sync_discord_payload("SUCCESS", 1, ["abc1234"])
            res = send_sync_discord_notification(payload)
            self.assertTrue(res)

    def test_send_sync_discord_notification_no_url(self):
        with patch.dict(os.environ, {"TESTING": "0"}, clear=True):
            payload = format_sync_discord_payload("SUCCESS", 1, ["abc1234"])
            res = send_sync_discord_notification(payload)
            self.assertFalse(res)

    def test_reconcile_intraday_events_json_logic(self, tmp_path=None):
        base_events = [
            {"headline": "Event 1", "timestamp": "2026-10-20T10:00:00", "url": "https://example.com/1", "scores": {"overall_price_pressure": 0.5}}
        ]
        dev_events = [
            {"headline": "Event 1", "timestamp": "2026-10-20T10:00:00", "url": "https://example.com/1", "scores": {"overall_price_pressure": 0.5}, "is_duplicate": True},
            {"headline": "Event Dev", "timestamp": "2026-10-21T10:00:00", "url": "https://example.com/dev", "scores": {"overall_price_pressure": 0.2}}
        ]
        main_events = [
            {"headline": "Event 1", "timestamp": "2026-10-20T10:00:00", "url": "https://example.com/1", "scores": {"overall_price_pressure": 0.8}},
            {"headline": "Event Main", "timestamp": "2026-10-22T10:00:00", "url": "https://example.com/main", "scores": {"overall_price_pressure": 0.4}}
        ]

        def mock_check_output(cmd, *args, **kwargs):
            stage = cmd[2]
            if stage == ":1:data/intraday_events.json":
                return json.dumps(base_events)
            elif stage == ":2:data/intraday_events.json":
                return json.dumps(dev_events)
            elif stage == ":3:data/intraday_events.json":
                return json.dumps(main_events)
            return "[]"

        with patch("subprocess.check_output", side_effect=mock_check_output), \
             patch("scripts.reconcile_production_sync.run_git"):
            count = reconcile_intraday_events_json()
            self.assertEqual(count, 3)

    def test_execute_sync_up_to_date(self):
        with patch("scripts.reconcile_production_sync.check_main_commits_ahead", return_value=(0, [])), \
             patch("scripts.reconcile_production_sync.send_sync_discord_notification", return_value=True):
            code = execute_sync()
            self.assertEqual(code, 0)

    def test_execute_sync_dry_run(self):
        with patch("scripts.reconcile_production_sync.check_main_commits_ahead", return_value=(3, ["c1", "c2", "c3"])), \
             patch("scripts.reconcile_production_sync.send_sync_discord_notification", return_value=True):
            code = execute_sync(dry_run=True)
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
