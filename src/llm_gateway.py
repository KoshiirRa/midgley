"""Cloudflare AI Gateway routing helper for Python LLM clients (Issue #764).

Provides an optional, zero-config-safe factory for Google Gemini (`google-genai`)
clients that transparently routes requests through Cloudflare AI Gateway when
configured via environment variables, while preserving direct API calls and
offline/test isolation when unconfigured.

Supported environment variables:
- ``CF_AI_GATEWAY_BASE_URL``: Full provider base URL override, e.g.
  ``https://gateway.ai.cloudflare.com/v1/<account_id>/<gateway_id>/google-ai-studio``
- ``CLOUDFLARE_ACCOUNT_ID`` + ``CF_AI_GATEWAY_ID``: Auto-constructs the
  ``google-ai-studio`` gateway URL when ``CF_AI_GATEWAY_BASE_URL`` is unset.
- ``CF_AI_GATEWAY_TOKEN``: Optional Authenticated Gateway token sent as
  ``cf-aig-authorization: Bearer <token>``.
- ``CF_AI_GATEWAY_CACHE_TTL``: Optional integer cache TTL in seconds sent as
  ``cf-aig-cache-ttl``.
- ``CF_AI_GATEWAY_SKIP_CACHE``: Optional truthy flag (``1``/``true``) sent as
  ``cf-aig-skip-cache: true``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CF_AI_GATEWAY_HOST = "https://gateway.ai.cloudflare.com/v1"
GOOGLE_AI_STUDIO_PROVIDER = "google-ai-studio"


@dataclass(frozen=True)
class AIGatewayConfig:
    """Resolved Cloudflare AI Gateway configuration (never stores raw secrets in repr)."""

    enabled: bool
    base_url: Optional[str] = None
    gateway_id: Optional[str] = None
    has_auth_token: bool = False
    cache_ttl_seconds: Optional[int] = None
    skip_cache: bool = False


def _is_truthy(val: Optional[str]) -> bool:
    return str(val or "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_gemini_gateway_url(env: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Resolve the Cloudflare AI Gateway base URL for Google AI Studio, or None."""
    source = env if env is not None else os.environ

    explicit = str(source.get("CF_AI_GATEWAY_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit

    account_id = str(
        source.get("CLOUDFLARE_ACCOUNT_ID") or source.get("CF_ACCOUNT_ID") or ""
    ).strip()
    gateway_id = str(
        source.get("CF_AI_GATEWAY_ID") or source.get("AI_GATEWAY_ID") or ""
    ).strip()

    if account_id and gateway_id:
        return (
            f"{DEFAULT_CF_AI_GATEWAY_HOST}/{account_id}/{gateway_id}"
            f"/{GOOGLE_AI_STUDIO_PROVIDER}"
        )

    return None


def get_ai_gateway_config(env: Optional[Dict[str, str]] = None) -> AIGatewayConfig:
    """Inspect current Cloudflare AI Gateway configuration without exposing secrets."""
    source = env if env is not None else os.environ
    base_url = resolve_gemini_gateway_url(source)
    gateway_id = str(
        source.get("CF_AI_GATEWAY_ID") or source.get("AI_GATEWAY_ID") or ""
    ).strip() or None
    has_token = bool(str(source.get("CF_AI_GATEWAY_TOKEN") or "").strip())

    raw_ttl = str(source.get("CF_AI_GATEWAY_CACHE_TTL") or "").strip()
    cache_ttl: Optional[int] = None
    if raw_ttl:
        try:
            parsed = int(raw_ttl)
            if parsed > 0:
                cache_ttl = parsed
        except ValueError:
            logger.warning("Ignoring invalid CF_AI_GATEWAY_CACHE_TTL value: %r", raw_ttl)

    return AIGatewayConfig(
        enabled=bool(base_url),
        base_url=base_url,
        gateway_id=gateway_id,
        has_auth_token=has_token,
        cache_ttl_seconds=cache_ttl,
        skip_cache=_is_truthy(source.get("CF_AI_GATEWAY_SKIP_CACHE")),
    )


def build_gateway_headers(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build optional Cloudflare AI Gateway HTTP headers (auth, cache TTL, skip-cache)."""
    source = env if env is not None else os.environ
    headers: Dict[str, str] = {}

    token = str(source.get("CF_AI_GATEWAY_TOKEN") or "").strip()
    if token:
        headers["cf-aig-authorization"] = f"Bearer {token}"

    raw_ttl = str(source.get("CF_AI_GATEWAY_CACHE_TTL") or "").strip()
    if raw_ttl:
        try:
            parsed = int(raw_ttl)
            if parsed > 0:
                headers["cf-aig-cache-ttl"] = str(parsed)
        except ValueError:
            pass

    if _is_truthy(source.get("CF_AI_GATEWAY_SKIP_CACHE")):
        headers["cf-aig-skip-cache"] = "true"

    return headers


def create_gemini_client(
    api_key: str,
    env: Optional[Dict[str, str]] = None,
) -> Any:
    """Create a ``google.genai.Client`` routed through Cloudflare AI Gateway when configured.

    When no AI Gateway URL/ID is configured, returns a standard direct
    ``genai.Client(api_key=api_key)``.
    """
    from google import genai
    from google.genai import types

    base_url = resolve_gemini_gateway_url(env)
    if not base_url:
        return genai.Client(api_key=api_key)

    headers = build_gateway_headers(env)
    http_options_kwargs: Dict[str, Any] = {"base_url": base_url}
    if headers:
        http_options_kwargs["headers"] = headers

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(**http_options_kwargs),
    )
