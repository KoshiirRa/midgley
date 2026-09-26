#!/usr/bin/env python3
"""
Headline Arena Sync Script (scripts/sync_headline_arena.py)

Periodically dispatches cached pending forecasts against active challenges
on Headline Arena (headlinearena.com) to decouple daily forecast generation
from challenge availability (Issue #418).

Usage:
  python scripts/sync_headline_arena.py
  python scripts/sync_headline_arena.py --live
  python scripts/sync_headline_arena.py --status
"""

import os
import sys
import json
import logging
import argparse

# Ensure repo root is on PYTHONPATH
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.headline_arena_connector import (
    HeadlineArenaConnector,
    load_pending_forecasts,
    load_submitted_ledger,
    clear_expired_pending_forecasts
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sync_headline_arena")


def main():
    parser = argparse.ArgumentParser(description="Headline Arena Sync & Dispatch Runner")
    parser.add_argument("--live", action="store_true", help="Enable live submission in development environment")
    parser.add_argument("--status", action="store_true", help="Display pending cache and ledger status without dispatching")
    args = parser.parse_args()

    connector = HeadlineArenaConnector()
    print("=" * 80)
    print("  HEADLINE ARENA ASYNCHRONOUS SYNC & DISPATCH RUNNER")
    print("=" * 80)
    print(f"Environment : {connector.environment} ({'Production' if connector.is_prod else 'Development'})")
    print(f"Configured  : {connector.is_configured}")
    print(f"Base URL    : {connector.base_url}")

    purged = clear_expired_pending_forecasts()
    if purged > 0:
        print(f"Purged {purged} expired pending forecasts (>24h).")

    pending = load_pending_forecasts(active_only=True)
    print(f"Active Pending Forecasts : {len(pending)}")
    for item in pending:
        asset = item.get("asset")
        f_type = item.get("forecast_type")
        exp = item.get("expires_at")
        print(f"  - [{asset}] type={f_type} expires={exp}")

    ledger = load_submitted_ledger()
    submitted = ledger.get("submitted_challenges", {})
    print(f"Submitted Ledger Entries : {len(submitted)}")

    if args.status:
        return

    print("\nExecuting dispatch...")
    result = connector.dispatch_pending_forecasts(live_in_dev=args.live)
    print("\nDispatch Results:")
    print(json.dumps(result, indent=2))
    print("=" * 80)


if __name__ == "__main__":
    main()
