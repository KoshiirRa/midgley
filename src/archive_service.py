"""
ArchiveBox Historical News & Event Preservation Engine (src/archive_service.py)
Snapshots and preserves historical news articles, OPEC press releases, and refinery outage notices
to a self-hosted ArchiveBox instance (or persistent local fallback snapshot ledger).
Issue #97
"""

import os
import json
import hashlib
import logging
import threading
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

LEDGER_PATH = os.path.join("data", "archived_events_ledger.json")
ARCHIVES_DIR = os.path.join("data", "archives")


def is_testing_environment() -> bool:
    """Checks if running inside an automated test runner."""
    return (
        os.environ.get("TESTING") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("MIDGLEY_TEST_MODE") == "1"
    )


class ArchiveBoxClient:
    """
    Client for interacting with self-hosted ArchiveBox server or local fallback archive.
    """

    def __init__(self, archivebox_url: Optional[str] = None, api_key: Optional[str] = None):
        self.archivebox_url = (
            archivebox_url
            or os.environ.get("ARCHIVEBOX_URL")
            or os.environ.get("ARCHIVEBOX_SERVER")
        )
        self.api_key = api_key or os.environ.get("ARCHIVEBOX_API_KEY")
        self.ledger_file = LEDGER_PATH
        self.archives_dir = ARCHIVES_DIR

    def _get_url_hash(self, url: str) -> str:
        return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]

    def _load_ledger(self) -> Dict[str, Any]:
        """Loads persistent archive ledger from disk."""
        if os.path.exists(self.ledger_file):
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.debug(f"Error loading archive ledger: {e}")
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_archived": 0,
            "archives": {}
        }

    def _save_ledger(self, ledger: Dict[str, Any]):
        """Saves archive ledger to disk."""
        if is_testing_environment() and not os.environ.get("TEST_ARCHIVE_PERSIST"):
            return
        try:
            os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
            ledger["last_updated"] = datetime.now().isoformat()
            ledger["total_archived"] = len(ledger.get("archives", {}))
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
        except Exception as e:
            logger.debug(f"Error saving archive ledger: {e}")

    def is_url_archived(self, url: str) -> bool:
        """Checks if a URL has already been archived."""
        url_hash = self._get_url_hash(url)
        ledger = self._load_ledger()
        return url_hash in ledger.get("archives", {})

    def submit_url(
        self,
        url: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        content_snapshot: Optional[str] = None,
        async_dispatch: bool = False,
        timeout: float = 2.5
    ) -> Dict[str, Any]:
        """
        Submits target URL for historical snapshot archiving.
        If async_dispatch is True, runs submission in a background daemon thread.
        """
        if not url or not url.startswith("http"):
            return {"status": "SKIPPED", "url": url, "reason": "Invalid URL"}

        if async_dispatch:
            thread = threading.Thread(
                target=self._submit_url_sync,
                args=(url, title, tags, content_snapshot, timeout),
                daemon=True
            )
            thread.start()
            return {"status": "QUEUED_ASYNC", "url": url}

        return self._submit_url_sync(url, title, tags, content_snapshot, timeout)

    def _submit_url_sync(
        self,
        url: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        content_snapshot: Optional[str] = None,
        timeout: float = 2.5
    ) -> Dict[str, Any]:
        url_hash = self._get_url_hash(url)
        tag_list = tags or ["midgley-news", "energy-commodity"]
        timestamp = datetime.now().isoformat()

        # 1. Attempt ArchiveBox Server Dispatch if configured
        archivebox_res = None
        if self.archivebox_url and not is_testing_environment():
            endpoint = f"{self.archivebox_url.rstrip('/')}/api/v1/core/add/"
            payload = json.dumps({
                "url": url,
                "tag": ",".join(tag_list),
                "depth": 0
            }).encode("utf-8")

            headers = {
                "User-Agent": "Midgley-ArchiveBox-Client/1.0",
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            try:
                req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if 200 <= resp.getcode() < 300:
                        archivebox_res = "SUBMITTED_TO_ARCHIVEBOX"
                        logger.info(f"Successfully submitted {url} to ArchiveBox ({endpoint})")
            except Exception as e:
                logger.debug(f"ArchiveBox server notice for {url} ({e}). Falling back to local snapshot.")

        # 2. Local File & Ledger Preservation Fallback
        snapshot_file = None
        if content_snapshot:
            try:
                os.makedirs(self.archives_dir, exist_ok=True)
                snapshot_file = os.path.join(self.archives_dir, f"{url_hash}.md")
                if not is_testing_environment() or os.environ.get("TEST_ARCHIVE_PERSIST"):
                    with open(snapshot_file, "w", encoding="utf-8") as f:
                        f.write(f"# Snapshot: {title or url}\n# URL: {url}\n# Archived At: {timestamp}\n\n{content_snapshot}\n")
            except Exception as e:
                logger.debug(f"Could not write local snapshot file: {e}")

        # 3. Update Persistent Ledger
        ledger = self._load_ledger()
        record = {
            "url": url,
            "url_hash": url_hash,
            "title": title or url,
            "tags": tag_list,
            "archived_at": timestamp,
            "server_status": archivebox_res or "LOCAL_ONLY",
            "has_content_snapshot": bool(content_snapshot),
            "snapshot_file": snapshot_file
        }
        ledger.setdefault("archives", {})[url_hash] = record
        self._save_ledger(ledger)

        return {
            "status": "SUCCESS",
            "url": url,
            "url_hash": url_hash,
            "server_status": archivebox_res or "LOCAL_ONLY",
            "record": record
        }


def submit_url_to_archive(
    url: str,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    content_snapshot: Optional[str] = None,
    async_dispatch: bool = True
) -> Dict[str, Any]:
    """Global convenience helper to submit a URL for historical snapshot archiving."""
    client = ArchiveBoxClient()
    return client.submit_url(
        url=url,
        title=title,
        tags=tags,
        content_snapshot=content_snapshot,
        async_dispatch=async_dispatch
    )
