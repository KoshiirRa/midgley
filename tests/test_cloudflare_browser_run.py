"""
Unit Tests for Unified Cloudflare Browser Run Client (tests/test_cloudflare_browser_run.py)
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from src.cloudflare_browser_run import (
    resolve_cloudflare_account_id,
    resolve_cloudflare_api_token,
    CloudflareBrowserRunClient,
    fetch_markdown_via_browser_run,
)


def test_resolve_cloudflare_account_id_explicit():
    assert resolve_cloudflare_account_id("acc_123") == "acc_123"


def test_resolve_cloudflare_account_id_from_env():
    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "env_acc_456"}):
        assert resolve_cloudflare_account_id() == "env_acc_456"

    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "", "ACCOUNT_ID": "alt_acc_789"}):
        assert resolve_cloudflare_account_id() == "alt_acc_789"


def test_resolve_cloudflare_account_id_unconfigured():
    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "", "CLOUDFLARE_ACCOUNT": "", "ACCOUNT_ID": ""}):
        # Mock file non-existence to avoid reading local host default.toml
        with patch("os.path.exists", return_value=False):
            assert resolve_cloudflare_account_id(None) is None


def test_resolve_cloudflare_api_token_explicit():
    assert resolve_cloudflare_api_token("tok_123") == "tok_123"


def test_resolve_cloudflare_api_token_from_env():
    with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "token_abc"}):
        assert resolve_cloudflare_api_token() == "token_abc"

    with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "", "CLOUDFLARE_AUTH_TOKEN": "token_xyz"}):
        assert resolve_cloudflare_api_token() == "token_xyz"


def test_resolve_cloudflare_api_token_unconfigured():
    with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "", "CLOUDFLARE_AUTH_TOKEN": ""}):
        with patch("os.path.exists", return_value=False):
            assert resolve_cloudflare_api_token(None) is None


def test_client_is_configured():
    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "", "CLOUDFLARE_ACCOUNT": "", "ACCOUNT_ID": "", "CLOUDFLARE_API_TOKEN": "", "CLOUDFLARE_AUTH_TOKEN": ""}):
        with patch("os.path.exists", return_value=False):
            client_unconfigured = CloudflareBrowserRunClient(account_id=None, api_token=None)
            assert not client_unconfigured.is_configured

    client_configured = CloudflareBrowserRunClient(account_id="acc", api_token="tok")
    assert client_configured.is_configured


def test_fetch_markdown_success():
    client = CloudflareBrowserRunClient(account_id="acc_999", api_token="tok_888")

    with patch("src.cloudflare_browser_run.http_post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "result": "# Title\n\nScraped content in Markdown."
        }
        mock_post.return_value = mock_resp

        result = client.fetch_markdown("https://example.com/data")
        assert result == "# Title\n\nScraped content in Markdown."

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.cloudflare.com/client/v4/accounts/acc_999/browser-run/markdown"
        assert kwargs["json"] == {"url": "https://example.com/data"}
        assert "Bearer tok_888" in kwargs["headers"]["Authorization"]


def test_fetch_markdown_unconfigured_returns_none():
    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "", "CLOUDFLARE_ACCOUNT": "", "ACCOUNT_ID": "", "CLOUDFLARE_API_TOKEN": "", "CLOUDFLARE_AUTH_TOKEN": ""}):
        with patch("os.path.exists", return_value=False):
            client = CloudflareBrowserRunClient(account_id=None, api_token=None)
            assert client.fetch_markdown("https://example.com/data") is None


def test_fetch_markdown_http_error_returns_none():
    client = CloudflareBrowserRunClient(account_id="acc_999", api_token="tok_888")

    with patch("src.cloudflare_browser_run.http_post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        result = client.fetch_markdown("https://example.com/data")
        assert result is None


def test_fetch_markdown_via_browser_run_convenience():
    with patch("src.cloudflare_browser_run.http_post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "result": "## Rendered Markdown"
        }
        mock_post.return_value = mock_resp

        result = fetch_markdown_via_browser_run(
            "https://example.com/page",
            account_id="acc_custom",
            api_token="tok_custom"
        )
        assert result == "## Rendered Markdown"
