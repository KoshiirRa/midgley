"""
Unit Tests for Release Reconciliation Manifest & Migration Protocol (Issue #299)
Tests generate_release_manifest(), REST API endpoint, and check_updates reconciler.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.release_manifest import generate_release_manifest, save_release_manifest, MANIFEST_SCHEMA_VERSION
from scripts.check_updates import fetch_upstream_manifest, check_environment_variables, reconcile_upgrades


def test_generate_release_manifest_structure():
    manifest = generate_release_manifest()
    
    assert "version" in manifest
    assert "model_version" in manifest
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert "compatibility" in manifest
    assert "environment_changes" in manifest
    assert "model_engine" in manifest
    assert "database_migrations" in manifest
    assert "agent_action_items" in manifest
    assert len(manifest["agent_action_items"]) > 0
    assert "feature_matrix_columns" in manifest["model_engine"]


def test_save_release_manifest(tmp_path):
    dest = str(tmp_path / "RELEASE_MANIFEST.json")
    out = save_release_manifest(filepath=dest)
    assert os.path.exists(out)

    with open(out, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema_version"] == MANIFEST_SCHEMA_VERSION


def test_check_environment_variables():
    manifest = {
        "environment_changes": {
            "added": [
                {"name": "MOCK_VAR_CONFIGURED", "required": True},
                {"name": "MOCK_VAR_MISSING", "required": False}
            ]
        }
    }
    with patch.dict(os.environ, {"MOCK_VAR_CONFIGURED": "value123"}, clear=False):
        audit = check_environment_variables(manifest)
        assert "MOCK_VAR_CONFIGURED" in audit["configured"]
        assert any(item["name"] == "MOCK_VAR_MISSING" for item in audit["missing"])


def test_reconcile_upgrades_dry_run(capsys):
    manifest = generate_release_manifest()
    success = reconcile_upgrades(manifest, dry_run=True)
    assert success is True
    
    captured = capsys.readouterr()
    assert "Midgley Upstream Release & Schema Compatibility Reconciler" in captured.out
    assert "AI Agent Action Items" in captured.out
