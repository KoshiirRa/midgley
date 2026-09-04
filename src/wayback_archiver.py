"""
Wayback Machine Cloud Archiver Module (src/wayback_archiver.py)
Issue #197: Zero-Cost Internet Archive Wayback Machine Integration

Submits breaking energy news, OPEC bulletins, and event URLs to the Internet Archive
Save API (https://web.archive.org/save/{url}) during intraday headline evaluations.
Provides 100% cloud-native, zero-infrastructure web archiving with local JSON caching.
"""

import os
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join("data", "wayback_archive_cache.json")


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
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.debug(f"Error saving wayback archive cache: {e}")


def archive_url_to_wayback(url: str, headline: str = "") -> Dict[str, Any]:
    """
    Submits a target article URL to the Internet Archive Wayback Machine Save API.
    Returns status record with archive_url or fallback status.
    """
    if not url or not url.startswith(("http://", "https://")):
        return {"status": "SKIPPED_INVALID_URL", "url": url}

    # Check local cache to avoid duplicate submissions
    cache = _load_wayback_cache()
    if url in cache:
        logger.info(f"Wayback Machine cache hit for URL: {url}")
        return cache[url]

    # Testing mode suppression
    if os.environ.get("TESTING") == "1" or os.environ.get("SUPPRESS_OUTBOUND_APIS") == "1":
        record = {
            "timestamp": datetime.now().isoformat(),
            "status": "TEST_SUPPRESSED",
            "url": url,
            "headline": headline,
            "archive_url": f"https://web.archive.org/web/*/{url}"
        }
        cache[url] = record
        _save_wayback_cache(cache)
        return record

    target_api = f"https://web.archive.org/save/{url}"
    headers = {
        "User-Agent": "Midgley-Energy-Forecasting-Bot/1.0 (+https://github.com/KoshiirRa/midgley)"
    }

    try:
        req = urllib.request.Request(target_api, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            archive_url = response.headers.get("Content-Location") or response.geturl()
            
            if not archive_url.startswith("https://web.archive.org"):
                archive_url = f"https://web.archive.org/web/*/{url}"

            record = {
                "timestamp": datetime.now().isoformat(),
                "status": "SUBMITTED" if status_code in [200, 302] else "PENDING",
                "http_status": status_code,
                "url": url,
                "headline": headline,
                "archive_url": archive_url
            }
            logger.info(f"🌐 Successfully archived URL to Wayback Machine: {archive_url}")

            cache[url] = record
            _save_wayback_cache(cache)
            return record

    except Exception as e:
        logger.warning(f"Wayback Machine submission warning for {url}: {e}")
        fallback_record = {
            "timestamp": datetime.now().isoformat(),
            "status": "FALLBACK_PENDING",
            "url": url,
            "headline": headline,
            "archive_url": f"https://web.archive.org/web/*/{url}",
            "error": str(e)
        }
        cache[url] = fallback_record
        _save_wayback_cache(cache)
        return fallback_record
