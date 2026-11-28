"""Unit tests for Cloudflare AI Gateway routing helper (Issue #764)."""

from __future__ import annotations

import sys
import types as pytypes
from unittest.mock import MagicMock, patch

from src.llm_gateway import (
    build_gateway_headers,
    create_gemini_client,
    get_ai_gateway_config,
    resolve_gemini_gateway_url,
)


def test_resolve_gateway_url_unconfigured_returns_none():
    assert resolve_gemini_gateway_url({}) is None
    assert resolve_gemini_gateway_url({"CLOUDFLARE_ACCOUNT_ID": "acct123"}) is None
    assert resolve_gemini_gateway_url({"CF_AI_GATEWAY_ID": "midgley-gw"}) is None


def test_resolve_gateway_url_from_account_and_gateway_id():
    url = resolve_gemini_gateway_url(
        {
            "CLOUDFLARE_ACCOUNT_ID": "acct123",
            "CF_AI_GATEWAY_ID": "midgley-gw",
        }
    )
    assert url == "https://gateway.ai.cloudflare.com/v1/acct123/midgley-gw/google-ai-studio"


def test_resolve_gateway_url_explicit_override_takes_precedence():
    url = resolve_gemini_gateway_url(
        {
            "CF_AI_GATEWAY_BASE_URL": "https://gateway.ai.cloudflare.com/v1/custom/gw/google-ai-studio/",
            "CLOUDFLARE_ACCOUNT_ID": "acct123",
            "CF_AI_GATEWAY_ID": "ignored-gw",
        }
    )
    assert url == "https://gateway.ai.cloudflare.com/v1/custom/gw/google-ai-studio"


def test_build_gateway_headers_auth_ttl_and_skip_cache():
    headers = build_gateway_headers(
        {
            "CF_AI_GATEWAY_TOKEN": "secret-gw-token",
            "CF_AI_GATEWAY_CACHE_TTL": "3600",
            "CF_AI_GATEWAY_SKIP_CACHE": "true",
        }
    )
    assert headers == {
        "cf-aig-authorization": "Bearer secret-gw-token",
        "cf-aig-cache-ttl": "3600",
        "cf-aig-skip-cache": "true",
    }


def test_get_ai_gateway_config_does_not_expose_raw_token():
    cfg = get_ai_gateway_config(
        {
            "CLOUDFLARE_ACCOUNT_ID": "acct123",
            "CF_AI_GATEWAY_ID": "midgley-gw",
            "CF_AI_GATEWAY_TOKEN": "super-secret-token",
            "CF_AI_GATEWAY_CACHE_TTL": "900",
        }
    )
    assert cfg.enabled is True
    assert cfg.has_auth_token is True
    assert cfg.cache_ttl_seconds == 900
    assert "super-secret-token" not in repr(cfg)


def _make_fake_genai_modules(mock_client: MagicMock):
    fake_genai = pytypes.ModuleType("google.genai")
    fake_types = pytypes.ModuleType("google.genai.types")

    class FakeHttpOptions:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    client_cls = MagicMock(return_value=mock_client)
    fake_genai.Client = client_cls  # type: ignore[attr-defined]
    fake_types.HttpOptions = FakeHttpOptions  # type: ignore[attr-defined]
    fake_genai.types = fake_types  # type: ignore[attr-defined]

    fake_google = pytypes.ModuleType("google")
    fake_google.genai = fake_genai  # type: ignore[attr-defined]
    return {
        "google": fake_google,
        "google.genai": fake_genai,
        "google.genai.types": fake_types,
    }, client_cls


def test_create_gemini_client_direct_fallback_when_unconfigured():
    mock_client = MagicMock()
    fake_mods, client_cls = _make_fake_genai_modules(mock_client)
    with patch.dict(sys.modules, fake_mods):
        client = create_gemini_client(api_key="test-key", env={})
        assert client is mock_client
        client_cls.assert_called_once_with(api_key="test-key")


def test_create_gemini_client_routes_through_ai_gateway_when_configured():
    mock_client = MagicMock()
    fake_mods, client_cls = _make_fake_genai_modules(mock_client)
    env = {
        "CLOUDFLARE_ACCOUNT_ID": "acct123",
        "CF_AI_GATEWAY_ID": "midgley-gw",
        "CF_AI_GATEWAY_TOKEN": "gw-tok",
        "CF_AI_GATEWAY_CACHE_TTL": "1800",
    }
    with patch.dict(sys.modules, fake_mods):
        client = create_gemini_client(api_key="test-key", env=env)
        assert client is mock_client
        assert client_cls.call_count == 1
        kwargs = client_cls.call_args.kwargs
        assert kwargs["api_key"] == "test-key"
        http_opts = kwargs["http_options"]
        assert http_opts.base_url == "https://gateway.ai.cloudflare.com/v1/acct123/midgley-gw/google-ai-studio"
        assert http_opts.headers["cf-aig-authorization"] == "Bearer gw-tok"
        assert http_opts.headers["cf-aig-cache-ttl"] == "1800"
