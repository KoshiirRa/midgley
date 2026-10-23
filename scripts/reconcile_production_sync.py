"""
Pre-Audit Production Data Sync (scripts/reconcile_production_sync.py)
Automates the Friday afternoon reconciliation of production ground-truth actuals,
prediction histories, and telemetry from origin/main into dev before the Saturday weekly model review.
Dispatches a Discord notification upon completion.
"""

from __future__ import annotations

import os
import sys
import json
import logging
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconcile_production_sync")

INTRADAY_EVENTS_PATH = os.path.join("data", "intraday_events.json")


def run_git(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Executes a git command and returns the CompletedProcess object."""
    cmd = ["git"] + args
    logger.info(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def check_main_commits_ahead() -> Tuple[int, List[str]]:
    """
    Checks how many commits origin/main is ahead of dev.
    Returns (count, commit_summaries).
    """
    run_git(["fetch", "origin", "main", "dev"])
    res = run_git(["rev-list", "--count", "HEAD..origin/main"])
    count = int(res.stdout.strip() or "0")
    if count == 0:
        return 0, []

    log_res = run_git(["log", "--oneline", f"-n{min(count, 10)}", "HEAD..origin/main"])
    commits = [line.strip() for line in log_res.stdout.splitlines() if line.strip()]
    return count, commits


def reconcile_intraday_events_json() -> int:
    """
    Performs non-destructive 3-way merge on data/intraday_events.json.
    Merges newly discovered production events from origin/main while
    preserving review status annotations from dev (HEAD).
    Returns total merged count.
    """
    # Stage 1: merge base, Stage 2: HEAD (dev), Stage 3: incoming (main)
    try:
        s1 = subprocess.check_output(["git", "show", ":1:data/intraday_events.json"], text=True, encoding="utf-8")
        s2 = subprocess.check_output(["git", "show", ":2:data/intraday_events.json"], text=True, encoding="utf-8")
        s3 = subprocess.check_output(["git", "show", ":3:data/intraday_events.json"], text=True, encoding="utf-8")
        j1 = json.loads(s1)
        j2 = json.loads(s2)
        j3 = json.loads(s3)
    except Exception as e:
        logger.warning(f"Could not load 3-way git stages for intraday_events.json: {e}")
        # Fallback to local file if not in git conflict state
        if os.path.exists(INTRADAY_EVENTS_PATH):
            with open(INTRADAY_EVENTS_PATH, "r", encoding="utf-8") as f:
                return len(json.load(f))
        return 0

    def event_key(e: Dict[str, Any]) -> Any:
        return e.get("url") or (e.get("headline"), (e.get("timestamp") or "")[:19])

    d1 = {event_key(e): e for e in j1}
    d2 = {event_key(e): e for e in j2}
    d3 = {event_key(e): e for e in j3}

    merged_events = []
    seen_keys = set()

    # 1. Base events in order, updated by dev review status and main production scores
    for e in j1:
        k = event_key(e)
        seen_keys.add(k)
        item = dict(e)
        if k in d2:
            item.update(d2[k])
        if k in d3:
            for field, val in d3[k].items():
                if field not in ("duplicate_confirmed", "is_duplicate", "review_decision", "reviewed_at", "duplicate_review_notified"):
                    item[field] = val
        merged_events.append(item)

    # 2. Events added in dev
    for e in j2:
        k = event_key(e)
        if k not in seen_keys:
            seen_keys.add(k)
            item = dict(e)
            if k in d3:
                for field, val in d3[k].items():
                    if field not in ("duplicate_confirmed", "is_duplicate", "review_decision", "reviewed_at", "duplicate_review_notified"):
                        item[field] = val
            merged_events.append(item)

    # 3. Events added in main (production actuals)
    for e in j3:
        k = event_key(e)
        if k not in seen_keys:
            seen_keys.add(k)
            merged_events.append(e)

    os.makedirs(os.path.dirname(INTRADAY_EVENTS_PATH), exist_ok=True)
    with open(INTRADAY_EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_events, f, indent=2)

    logger.info(f"Reconciled {len(merged_events)} intraday events cleanly.")
    run_git(["add", INTRADAY_EVENTS_PATH])
    return len(merged_events)


def format_sync_discord_payload(
    status: str,
    commits_count: int,
    commits_summary: List[str],
    details: Optional[str] = None
) -> Dict[str, Any]:
    """Formats Discord webhook embed payload for pre-audit data sync."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if status == "SUCCESS":
        title = "🔄 Midgley Pre-Audit Data Sync: Dev Synchronized"
        color = 0x22c55e  # Green
        status_desc = f"Successfully merged **{commits_count} production commit(s)** from `main` into `dev`."
    elif status == "UP_TO_DATE":
        title = "✅ Midgley Pre-Audit Data Sync: Up to Date"
        color = 0x3b82f6  # Blue
        status_desc = "Branch `dev` is already fully synchronized with `origin/main`. No new production data commits."
    else:
        title = "🚨 Midgley Pre-Audit Data Sync: Failed"
        color = 0xef4444  # Red
        status_desc = f"Failed to reconcile `origin/main` into `dev`: {details or 'Unknown error'}"

    fields = [
        {"name": "Status", "value": f"`{status}`", "inline": True},
        {"name": "Branch", "value": "`dev` $\\leftarrow$ `origin/main`", "inline": True},
        {"name": "Saturday Review Readiness", "value": "✅ Ready for Saturday 08:12 AM CT audit" if status in ("SUCCESS", "UP_TO_DATE") else "⚠️ Manual intervention required", "inline": False}
    ]

    if commits_summary:
        sample_commits = "\n".join([f"• `{c}`" for c in commits_summary[:5]])
        fields.append({"name": f"Production Commits Reconciled ({min(len(commits_summary), 5)} of {commits_count})", "value": sample_commits, "inline": False})

    if details and status != "FAILED":
        fields.append({"name": "Details", "value": details, "inline": False})

    payload = {
        "username": "Midgley Pre-Audit MLOps",
        "avatar_url": "https://koshiirra.github.io/midgley/assets/icon.png",
        "embeds": [
            {
                "title": title,
                "description": status_desc,
                "color": color,
                "fields": fields,
                "footer": {
                    "text": "Midgley MLOps Automation • Friday Pre-Audit Sync"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }
    return payload


def send_sync_discord_notification(payload: Dict[str, Any], webhook_url: Optional[str] = None) -> bool:
    """Dispatches payload to Discord webhook URL."""
    if webhook_url is None:
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or os.environ.get("DISCORD_INTRADAY_WEBHOOK_URL")

    if not webhook_url:
        logger.info("No Discord webhook URL configured; skipping notification.")
        return False

    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_WEBHOOK_DISPATCH"):
        logger.info("TESTING=1: Suppressed Discord webhook notification HTTP POST.")
        return True

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "Midgley-MLOps/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            success = resp.status in (200, 204)
            if success:
                logger.info(f"Dispatched pre-audit sync Discord notification (HTTP {resp.status})")
            else:
                logger.warning(f"Discord responded with HTTP {resp.status}")
            return success
    except Exception as e:
        logger.warning(f"Failed to dispatch Discord webhook: {e}")
        return False


def execute_sync(dry_run: bool = False) -> int:
    """
    Main execution workflow for Friday pre-audit data sync.
    Returns process exit code (0 for success/up-to-date, 1 for failure).
    """
    logger.info("Starting Friday afternoon pre-audit production data sync...")

    try:
        count, commit_list = check_main_commits_ahead()
        logger.info(f"origin/main is {count} commit(s) ahead of HEAD.")

        if count == 0:
            logger.info("Branch is already up to date with origin/main.")
            payload = format_sync_discord_payload("UP_TO_DATE", 0, [])
            send_sync_discord_notification(payload)
            return 0

        if dry_run:
            logger.info(f"[DRY-RUN] Would merge {count} commit(s) from origin/main into dev.")
            payload = format_sync_discord_payload("SUCCESS", count, commit_list, details="Dry-run executed; no changes committed.")
            send_sync_discord_notification(payload)
            return 0

        # Attempt merge
        merge_res = run_git(["merge", "origin/main", "--no-commit"], check=False)
        if merge_res.returncode != 0:
            logger.info("Merge encountered unmerged files; resolving content conflicts...")
            # Check unmerged files
            diff_res = run_git(["diff", "--name-only", "--diff-filter=U"], check=False)
            unmerged = [f.strip() for f in diff_res.stdout.splitlines() if f.strip()]
            logger.info(f"Unmerged paths detected: {unmerged}")

            if "data/intraday_events.json" in unmerged:
                reconcile_intraday_events_json()
                unmerged.remove("data/intraday_events.json")

            if unmerged:
                error_msg = f"Unresolved merge conflicts remain in: {unmerged}"
                logger.error(error_msg)
                run_git(["merge", "--abort"], check=False)
                payload = format_sync_discord_payload("FAILED", count, commit_list, details=error_msg)
                send_sync_discord_notification(payload)
                return 1

        # Commit merge
        commit_msg = f"chore(merge): reconcile main production data into dev [skip ci]"
        run_git(["commit", "-m", commit_msg])

        # Push to dev with retry loop
        pushed = False
        for attempt in range(1, 4):
            push_res = run_git(["push", "origin", "HEAD:dev"], check=False)
            if push_res.returncode == 0:
                pushed = True
                logger.info(f"Successfully pushed reconciled dev branch on attempt {attempt}.")
                break
            logger.warning(f"Push attempt {attempt} failed; pulling rebase before retrying...")
            run_git(["pull", "--rebase", "origin", "dev"], check=False)

        if not pushed:
            error_msg = "Could not push reconciled dev branch after 3 attempts."
            logger.error(error_msg)
            payload = format_sync_discord_payload("FAILED", count, commit_list, details=error_msg)
            send_sync_discord_notification(payload)
            return 1

        payload = format_sync_discord_payload(
            "SUCCESS",
            count,
            commit_list,
            details=f"Reconciled ground-truth forecasts, prediction history, and intraday event streams."
        )
        send_sync_discord_notification(payload)
        logger.info("Friday pre-audit production data sync completed successfully.")
        return 0

    except Exception as e:
        logger.exception(f"Unexpected error during pre-audit sync: {e}")
        payload = format_sync_discord_payload("FAILED", 0, [], details=str(e))
        send_sync_discord_notification(payload)
        return 1


if __name__ == "__main__":
    is_dry_run = "--dry-run" in sys.argv
    sys.exit(execute_sync(dry_run=is_dry_run))
