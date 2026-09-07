"""
Healthchecks Cron & Pipeline Monitoring Engine (src/healthcheck_monitor.py)
Provides execution heartbeat pings (start, success, fail/error, logs) to Healthchecks.io
or self-hosted Healthchecks instances to monitor pipeline reliability.
"""

import os
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)


def is_testing_environment() -> bool:
    """Checks if running inside an automated test runner."""
    return (
        os.environ.get("TESTING") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("MIDGLEY_TEST_MODE") == "1"
    )


def resolve_healthcheck_url(url_or_uuid: Optional[str] = None) -> Optional[str]:
    """
    Resolves the target Healthchecks base ping URL from argument or environment variables.
    Supports full URLs (e.g. https://hc-ping.com/<uuid>) or bare UUID strings.
    """
    target = (
        url_or_uuid
        or os.environ.get("HEALTHCHECKS_DAILY_PING_URL")
        or os.environ.get("HEALTHCHECKS_WEEKLY_PING_URL")
        or os.environ.get("HEALTHCHECKS_PING_URL")
        or os.environ.get("HEALTHCHECKS_UUID")
    )
    if not target:
        return None

    target = target.strip()
    if target.startswith("http://") or target.startswith("https://"):
        return target.rstrip("/")
    
    # Bare UUID format
    return f"https://hc-ping.com/{target}"


def send_healthcheck_ping(
    url_or_uuid: Optional[str] = None,
    state: str = "success",
    log_message: Optional[str] = None,
    timeout: float = 3.0,
    force_send: bool = False
) -> bool:
    """
    Sends an HTTP heartbeat ping to Healthchecks.

    Args:
        url_or_uuid: Base ping URL or UUID. If None, checks environment variables.
        state: Ping state in ['start', 'success', 'fail', 'log'].
               - 'start': appends /start
               - 'success': base URL (HEAD/GET or POST with log body)
               - 'fail': appends /fail
               - 'log': appends /log
        log_message: Optional diagnostic text/log payload to send in the request body.
        timeout: Network timeout in seconds (default: 3.0s).
        force_send: If True, bypasses test environment suppression.

    Returns:
        bool: True if ping was successful or simulated in test mode, False otherwise.
    """
    base_url = resolve_healthcheck_url(url_or_uuid)
    if not base_url:
        logger.debug("No Healthchecks URL/UUID configured. Skipping heartbeat ping.")
        return False

    if is_testing_environment() and not force_send:
        logger.debug(f"[TEST MODE] Suppressed Healthchecks ping ({state}) to {base_url}")
        return True

    endpoint = base_url
    if state == "start":
        endpoint = f"{base_url}/start"
    elif state in ("fail", "error"):
        endpoint = f"{base_url}/fail"
    elif state == "log":
        endpoint = f"{base_url}/log"

    try:
        data = log_message.encode("utf-8") if log_message else None
        headers = {"User-Agent": "Midgley-Healthchecks-Monitor/1.0"}
        if data:
            headers["Content-Type"] = "text/plain; charset=utf-8"

        req = urllib.request.Request(endpoint, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.getcode()
            logger.info(f"Healthchecks ping ({state}) dispatched to {endpoint} [HTTP {status_code}]")
            return 200 <= status_code < 300

    except urllib.error.HTTPError as e:
        logger.warning(f"Healthchecks ping ({state}) failed with HTTP {e.code}: {e.reason}")
        return False
    except Exception as e:
        logger.warning(f"Healthchecks ping ({state}) error: {e}")
        return False


def ping_healthcheck_start(url_or_uuid: Optional[str] = None, log_message: Optional[str] = None, force_send: bool = False) -> bool:
    """Helper to dispatch a job start heartbeat signal."""
    return send_healthcheck_ping(url_or_uuid, state="start", log_message=log_message, force_send=force_send)


def ping_healthcheck_success(url_or_uuid: Optional[str] = None, log_message: Optional[str] = None, force_send: bool = False) -> bool:
    """Helper to dispatch a job success heartbeat signal."""
    return send_healthcheck_ping(url_or_uuid, state="success", log_message=log_message, force_send=force_send)


def ping_healthcheck_failure(url_or_uuid: Optional[str] = None, log_message: Optional[str] = None, force_send: bool = False) -> bool:
    """Helper to dispatch a job failure heartbeat signal."""
    return send_healthcheck_ping(url_or_uuid, state="fail", log_message=log_message, force_send=force_send)
