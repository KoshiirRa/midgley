"""
Unit Test Suite for Dynamic Versioning & Model Badging Engine (Issue #298)
Tests src/version.py, badge generators, and API server version endpoints.
"""

import os
import pytest
from unittest.mock import patch
from src.version import (
    get_version,
    get_model_version,
    get_git_branch,
    is_release_branch,
    FALLBACK_PACKAGE_VERSION,
    FALLBACK_MODEL_VERSION
)
from src.dashboard_generator import get_release_badge, get_model_badge


class TestVersioningEngine:

    def test_get_version_env_override(self):
        """Verify MIDGLEY_VERSION environment variable takes top precedence."""
        with patch.dict(os.environ, {"MIDGLEY_VERSION": "v0.9.9"}):
            assert get_version() == "0.9.9"

        with patch.dict(os.environ, {"MIDGLEY_VERSION": "1.2.3"}):
            assert get_version() == "1.2.3"

    def test_get_version_dynamic_discovery(self):
        """Verify get_version returns a valid semver string in normal repository environment."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MIDGLEY_VERSION", None)
            ver = get_version()
            assert isinstance(ver, str)
            assert len(ver.split(".")) >= 2
            assert ver[0].isdigit()

    def test_get_model_version_env_override(self):
        """Verify MIDGLEY_MODEL_VERSION environment variable takes precedence."""
        with patch.dict(os.environ, {"MIDGLEY_MODEL_VERSION": "v2.0 Hubbert"}):
            assert get_model_version() == "v2.0 Hubbert"

    def test_get_model_version_default(self):
        """Verify get_model_version returns active model version."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MIDGLEY_MODEL_VERSION", None)
            model_ver = get_model_version()
            assert "v1.6" in model_ver or "Ipatieff" in model_ver

    def test_get_git_branch_resolution(self):
        """Verify git branch resolution hierarchy."""
        with patch.dict(os.environ, {"MIDGLEY_BRANCH": "main"}):
            assert get_git_branch() == "main"
            assert is_release_branch() is True

        with patch.dict(os.environ, {"MIDGLEY_BRANCH": "dev"}):
            assert get_git_branch() == "dev"
            assert is_release_branch() is False

        with patch.dict(os.environ, {"MIDGLEY_BRANCH": "", "GITHUB_REF_NAME": "release/v0.6.0"}):
            assert get_git_branch() == "release/v0.6.0"
            assert is_release_branch() is True

    def test_get_release_badge_html(self):
        """Verify HTML badges for dev vs release branches."""
        with patch.dict(os.environ, {"MIDGLEY_BRANCH": "main", "MIDGLEY_VERSION": "0.5.5"}):
            badge = get_release_badge()
            assert "Release v0.5.5" in badge
            assert "bg-orange-500/20" in badge

        with patch.dict(os.environ, {"MIDGLEY_BRANCH": "dev", "MIDGLEY_VERSION": "0.5.5"}):
            badge = get_release_badge()
            assert "Dev Branch v0.5.5-dev" in badge
            assert "bg-amber-500/20" in badge

    def test_get_model_badge_html(self):
        """Verify dynamic blue model badge HTML output."""
        with patch.dict(os.environ, {"MIDGLEY_MODEL_VERSION": "v1.6 Ipatieff"}):
            badge = get_model_badge()
            assert "Model v1.6 Ipatieff" in badge
            assert "bg-blue-500/20" in badge


class TestAPIServerVersionEndpoints:

    def test_api_server_health_version(self):
        """Verify /health endpoint returns dynamic version and model_version."""
        from fastapi.testclient import TestClient
        from src.api_server import app

        client = TestClient(app)
        with patch.dict(os.environ, {"MIDGLEY_VERSION": "0.5.5", "MIDGLEY_MODEL_VERSION": "v1.6 Ipatieff"}):
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "online"
            assert data["version"] == "0.5.5"
            assert data["model_version"] == "v1.6 Ipatieff"
