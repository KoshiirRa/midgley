"""
Wayback Machine Cloud Archiver Module (src/wayback_archiver.py)
Issue #197 & #491: Zero-Cost Internet Archive Wayback Machine Integration.

Features:
1. Availability API pre-flight check (https://archive.org/wayback/available?url={url}) to avoid redundant save requests.
2. Save Page Now 2 (SPN2) S3 authentication support (WAYBACK_ACCESS_KEY & WAYBACK_SECRET_KEY).
3. In-process rate limiting (3.0s minimum inter-request delay) & 15-minute circuit breaker on HTTP 429.
4. Dynamic cache with transient TTL on failure records to allow self-healing.
"""

import os
import time
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import requests

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join("data", "wayback_archive_cache.json")

# Module-level circuit breaker & rate limiter state
_LAST_REQUEST_TIME: float = 0.0
_CIRCUIT_BREAKER_UNTIL: float = 0.0
MIN_INTER_REQUEST_DELAY_SECONDS = 3.0
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 900.0  # 15 minutes


def _load_wayback_cache() -> dict:
    """Loads the local Wayback Machine submission cache."""
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error reading wayback archive cache: {e}")
    return {}


def _save_wayback_cache(cache: dict) -> None:
    """Saves the local Wayback Machine submission cache to disk."""
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_TELEMETRY_PERSIST"):
        return
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    try:
        from src.storage_io import atomic_write_json
        atomic_write_json(CACHE_PATH, cache)
    except Exception as e:
        logger.debug(f"Error saving wayback archive cache: {e}")


def is_google_news_redirect(url: str) -> bool:
    """Checks if a given URL is a Google News redirect wrapper."""
    if not url:
        return False
    lower = url.lower()
    return (
        "news.google.com/rss/articles/" in lower
        or "news.google.com/articles/" in lower
        or "news.google.com/__i/rss/rd/articles/" in lower
    )


def resolve_canonical_url(url: str, timeout: float = 5.0) -> str:
    """
    Resolves redirect wrapper URLs to canonical source publisher URLs.
    """
    if not url or not url.startswith(("http://", "https://")):
        return url

    if not is_google_news_redirect(url):
        return url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.head(url, headers=headers, allow_redirects=True, timeout=timeout)
        resolved = resp.url
        if resp.status_code in [405, 403, 400] or is_google_news_redirect(resolved):
            resp_get = requests.get(url, headers=headers, allow_redirects=True, stream=True, timeout=timeout)
            resolved = resp_get.url
            resp_get.close()

        if resolved and not is_google_news_redirect(resolved) and resolved.startswith(("http://", "https://")):
            logger.info(f"Resolved Google News redirect '{url}' -> canonical '{resolved}'")
            return resolved
    except Exception as e:
        logger.debug(f"Failed resolving canonical URL for '{url}': {e}")

    return url


def check_wayback_availability(url: str, timeout: float = 4.0) -> Optional[str]:
    """
    Queries the Wayback Availability API (https://archive.org/wayback/available?url={url}) (Issue #491).
    Returns existing snapshot URL if available, else None.
    """
    encoded_url = urllib.parse.quote(url, safe="")
    api_url = f"https://archive.org/wayback/available?url={encoded_url}"
    headers = {"User-Agent": "Midgley-Energy-Forecasting-Bot/1.0 (+https://github.com/KoshiirRa/midgley)"}

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read().decode("utf-8"))
                snapshots = data.get("archived_snapshots", {})
                closest = snapshots.get("closest", {})
                if closest.get("available") and closest.get("url"):
                    return str(closest["url"])
    except Exception as e:
        logger.debug(f"Wayback availability check notice for {url}: {e}")
    return None


def archive_url_to_wayback(url: str, headline: str = "") -> Dict[str, Any]:
    """
    Submits a target article URL to the Internet Archive Wayback Machine.
    Uses Availability API pre-flight check, SPN2 authentication if available,
    and adheres to circuit breaker & rate limits.
    """
    global _LAST_REQUEST_TIME, _CIRCUIT_BREAKER_UNTIL

    if not url or not url.startswith(("http://", "https://")):
        return {"status": "SKIPPED_INVALID_URL", "url": url}

    # Resolve canonical publisher URL if wrapped by Google News
    canonical_url = resolve_canonical_url(url)
    target_url = canonical_url if canonical_url else url

    # Check local cache
    cache = _load_wayback_cache()
    now_dt = datetime.now(timezone.utc)

    for lookup_key in [target_url, url]:
        if lookup_key in cache:
            cached_rec = cache[lookup_key]
            status = cached_rec.get("status")
            # If successfully archived or previously verified snapshot, return permanent cache
            if status in ["SUBMITTED", "AVAILABLE_SNAPSHOT", "TEST_SUPPRESSED"]:
                logger.info(f"Wayback Machine cache hit ({status}) for URL: {lookup_key}")
                return cached_rec

            # If failed/fallback record, check if it has aged past 1 hour (allow self-healing retry)
            rec_ts_str = cached_rec.get("timestamp", "")
            try:
                rec_dt = datetime.fromisoformat(rec_ts_str.replace("Z", "+00:00"))
                if (now_dt - rec_dt).total_seconds() < 3600.0:
                    return cached_rec
            except Exception:
                pass

    # Testing mode suppression
    if os.environ.get("TESTING") == "1" or os.environ.get("SUPPRESS_OUTBOUND_APIS") == "1":
        record = {
            "timestamp": now_dt.isoformat(),
            "status": "TEST_SUPPRESSED",
            "url": url,
            "canonical_url": target_url,
            "headline": headline,
            "archive_url": f"https://web.archive.org/web/*/{target_url}"
        }
        cache[target_url] = record
        _save_wayback_cache(cache)
        return record

    # Check circuit breaker
    now_time = time.time()
    if now_time < _CIRCUIT_BREAKER_UNTIL:
        remaining_cool = int(_CIRCUIT_BREAKER_UNTIL - now_time)
        logger.warning(f"Wayback Machine circuit breaker active (cool-down {remaining_cool}s remaining); skipping save for {target_url}")
        return {
            "timestamp": now_dt.isoformat(),
            "status": "CIRCUIT_BREAKER_ACTIVE",
            "url": url,
            "canonical_url": target_url,
            "headline": headline,
            "archive_url": f"https://web.archive.org/web/*/{target_url}"
        }

    # Pre-Flight: Query Availability API (Zero Write Load)
    existing_snapshot = check_wayback_availability(target_url)
    if existing_snapshot:
        logger.info(f"🌐 Found existing Wayback Machine snapshot for {target_url}: {existing_snapshot}")
        record = {
            "timestamp": now_dt.isoformat(),
            "status": "AVAILABLE_SNAPSHOT",
            "http_status": 200,
            "url": url,
            "canonical_url": target_url,
            "headline": headline,
            "archive_url": existing_snapshot
        }
        cache[target_url] = record
        _save_wayback_cache(cache)
        return record

    # Enforce minimum inter-request rate limit (3.0s)
    elapsed = now_time - _LAST_REQUEST_TIME
    if elapsed < MIN_INTER_REQUEST_DELAY_SECONDS:
        time.sleep(MIN_INTER_REQUEST_DELAY_SECONDS - elapsed)

    # Prepare Save Request
    target_api = f"https://web.archive.org/save/{target_url}"
    headers = {
        "User-Agent": "Midgley-Energy-Forecasting-Bot/1.0 (+https://github.com/KoshiirRa/midgley)"
    }

    # Optional SPN2 (Save Page Now 2) S3 Auth Keys
    access_key = os.getenv("WAYBACK_ACCESS_KEY") or os.getenv("INTERNET_ARCHIVE_ACCESS_KEY")
    secret_key = os.getenv("WAYBACK_SECRET_KEY") or os.getenv("INTERNET_ARCHIVE_SECRET_KEY")
    if access_key and secret_key:
        headers["Authorization"] = f"LOW {access_key}:{secret_key}"
        headers["Accept"] = "application/json"

    _LAST_REQUEST_TIME = time.time()

    try:
        req = urllib.request.Request(target_api, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=6) as response:
            status_code = response.getcode()
            archive_url = response.headers.get("Content-Location") or response.geturl()

            if not archive_url.startswith("https://web.archive.org"):
                archive_url = f"https://web.archive.org/web/*/{target_url}"

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "SUBMITTED" if status_code in [200, 302] else "PENDING",
                "http_status": status_code,
                "url": url,
                "canonical_url": target_url,
                "headline": headline,
                "archive_url": archive_url
            }
            logger.info(f"🌐 Successfully archived URL to Wayback Machine: {archive_url}")

            cache[target_url] = record
            _save_wayback_cache(cache)
            return record

    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning(f"Wayback Machine HTTP 429 Rate Limit encountered. Tripping circuit breaker for {CIRCUIT_BREAKER_COOLDOWN_SECONDS}s.")
            _CIRCUIT_BREAKER_UNTIL = time.time() + CIRCUIT_BREAKER_COOLDOWN_SECONDS

        fallback_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "FALLBACK_PENDING",
            "http_status": e.code,
            "url": url,
            "canonical_url": target_url,
            "headline": headline,
            "archive_url": f"https://web.archive.org/web/*/{target_url}",
            "error": str(e)
        }
        cache[target_url] = fallback_record
        _save_wayback_cache(cache)
        return fallback_record

    except Exception as e:
        logger.warning(f"Wayback Machine submission warning for {target_url}: {e}")
        fallback_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "FALLBACK_PENDING",
            "url": url,
            "canonical_url": target_url,
            "headline": headline,
            "archive_url": f"https://web.archive.org/web/*/{target_url}",
            "error": str(e)
        }
        cache[target_url] = fallback_record
        _save_wayback_cache(cache)
        return fallback_record
