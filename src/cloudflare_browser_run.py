"""
Cloudflare Browser Run Client & Markdown Extraction Library (src/cloudflare_browser_run.py)

Provides a unified, resilient interface to execute headless Chromium rendering and
extract structured Markdown via the Cloudflare Browser Run REST API:
POST https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-run/markdown
(https://developers.cloudflare.com/browser-run/)

Features:
- Headless, serverless dynamic page rendering into Markdown without running local browser instances.
- Automatic credential resolution (account ID & API token) from environment variables or local configs.
- Respects point-in-time constraints, mock modes under TESTING=1, and telemetry tracking.
- Standardized policy user-agent via MIDGLEY_AGENT_USER_AGENT.
"""

import os
import time
import logging
from typing import Optional, Dict, Any

from src.http_client import http_post, MIDGLEY_AGENT_USER_AGENT
from src.connector_telemetry import log_connector_event

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


def resolve_cloudflare_account_id(account_id: Optional[str] = None) -> Optional[str]:
    """
    Resolves Cloudflare Account ID from explicit argument, environment variables,
    or local configuration. Never falls back to hardcoded production IDs.
    """
    if account_id and account_id.strip():
        return account_id.strip()

    env_id = os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("CLOUDFLARE_ACCOUNT") or os.getenv("ACCOUNT_ID")
    if env_id and env_id.strip():
        return env_id.strip()

    # Check candidate local config files defensively
    candidate_paths = [
        os.path.expanduser("~/.config/.wrangler/config/default.toml"),
        os.path.expandvars(r"%APPDATA%\xdg.config\.wrangler\config\default.toml"),
    ]
    for cfg_path in candidate_paths:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("account_id"):
                            parts = line.split("=")
                            if len(parts) >= 2:
                                extracted = parts[1].strip().strip('"').strip("'")
                                if extracted:
                                    return extracted
            except Exception:
                pass
    return None


def resolve_cloudflare_api_token(api_token: Optional[str] = None) -> Optional[str]:
    """
    Resolves Cloudflare API / Auth token from explicit argument, environment variables,
    or local wrangler OAuth credentials.
    """
    if api_token and api_token.strip():
        return api_token.strip()

    token = os.getenv("CLOUDFLARE_API_TOKEN") or os.getenv("CLOUDFLARE_AUTH_TOKEN")
    if token and token.strip():
        return token.strip()

    # Check local wrangler config paths defensively (Linux / Windows)
    candidate_paths = [
        os.path.expanduser("~/.config/.wrangler/config/default.toml"),
        os.path.expandvars(r"%APPDATA%\xdg.config\.wrangler\config\default.toml"),
    ]
    for cfg_path in candidate_paths:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("oauth_token"):
                            parts = line.split("=")
                            if len(parts) >= 2:
                                extracted = parts[1].strip().strip('"').strip("'")
                                if extracted:
                                    return extracted
            except Exception:
                pass
    return None


class CloudflareBrowserRunClient:
    """
    Reusable client for executing Cloudflare Browser Run rendering calls.
    """

    def __init__(
        self,
        account_id: Optional[str] = None,
        api_token: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: float = 25.0
    ):
        self.account_id = resolve_cloudflare_account_id(account_id)
        self.api_token = resolve_cloudflare_api_token(api_token)
        self.user_agent = user_agent or MIDGLEY_AGENT_USER_AGENT
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Returns True if both Account ID and API Token are available."""
        return bool(self.account_id and self.api_token)

    def fetch_markdown(self, url: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        Executes a headless Browser Run session to render a page to Markdown.
        Returns the markdown text on success, or None on failure or missing credentials.
        """
        if not url:
            return None

        # Re-resolve in case env vars were set after client initialization
        acc_id = self.account_id or resolve_cloudflare_account_id()
        token = self.api_token or resolve_cloudflare_api_token()

        if not acc_id or not token:
            logger.debug(
                "Cloudflare Browser Run credentials (account_id or api_token) not configured; skipping call for %s",
                url
            )
            return None

        endpoint = f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/browser-run/markdown"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent
        }
        payload = {"url": url}
        t0 = time.time()
        effective_timeout = timeout or self.timeout

        try:
            resp = http_post(endpoint, json=payload, headers=headers, timeout=effective_timeout)
            latency_ms = (time.time() - t0) * 1000.0

            if resp is not None and resp.status_code == 200:
                data = resp.json()
                md_text = data.get("result") if isinstance(data, dict) else None
                if md_text and isinstance(md_text, str) and len(md_text.strip()) > 0:
                    log_connector_event(
                        "Cloudflare_Browser_Run",
                        url,
                        status="SUCCESS",
                        latency_ms=latency_ms,
                        details=f"Extracted {len(md_text)} chars"
                    )
                    return md_text
                else:
                    log_connector_event(
                        "Cloudflare_Browser_Run",
                        url,
                        status="EMPTY_RESULT",
                        latency_ms=latency_ms,
                        details="API returned empty markdown string"
                    )
                    return None
            else:
                status_code = resp.status_code if resp is not None else 0
                log_connector_event(
                    "Cloudflare_Browser_Run",
                    url,
                    status=f"HTTP_{status_code}",
                    latency_ms=latency_ms,
                    details=resp.text[:200] if resp is not None else "No response"
                )
                logger.debug("Cloudflare Browser Run returned status %s for %s", status_code, url)
                return None
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000.0
            log_connector_event(
                "Cloudflare_Browser_Run",
                url,
                status="ERROR",
                latency_ms=latency_ms,
                details=str(e)[:200]
            )
            logger.debug("Cloudflare Browser Run failed for %s: %s", url, e)
            return None


# Module-level convenience singleton / function
_DEFAULT_CLIENT: Optional[CloudflareBrowserRunClient] = None


def get_browser_run_client() -> CloudflareBrowserRunClient:
    """Returns a shared default CloudflareBrowserRunClient instance."""
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = CloudflareBrowserRunClient()
    return _DEFAULT_CLIENT


def fetch_markdown_via_browser_run(
    url: str,
    account_id: Optional[str] = None,
    api_token: Optional[str] = None,
    user_agent: Optional[str] = None,
    timeout: float = 25.0
) -> Optional[str]:
    """
    Convenience function to fetch a web page rendered to Markdown via Cloudflare Browser Run.
    """
    if account_id or api_token or user_agent:
        client = CloudflareBrowserRunClient(
            account_id=account_id,
            api_token=api_token,
            user_agent=user_agent,
            timeout=timeout
        )
        return client.fetch_markdown(url)
    return get_browser_run_client().fetch_markdown(url, timeout=timeout)
