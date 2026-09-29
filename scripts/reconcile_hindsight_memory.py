#!/usr/bin/env python3
"""
Reconcile Hindsight Memory Script (scripts/reconcile_hindsight_memory.py)
Scans data/prediction_history.csv for evaluated prediction anomalies and reconciles
them into SQLite and Vectorize Hindsight episodic memory banks (Issue #557).
"""

import os
import sys
import argparse
import logging

# Ensure repo root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

from src.agent_memory import AgentMemoryManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("hindsight_reconcile")


def main():
    parser = argparse.ArgumentParser(description="Reconcile missing historical prediction anomalies into Hindsight memory.")
    parser.add_argument("--start-date", default="2026-09-25", help="Earliest forecast target date to reconcile (default: 2026-09-25)")
    parser.add_argument("--history-csv", default=os.path.join(PROJECT_ROOT, "data", "prediction_history.csv"), help="Path to prediction history CSV")
    args = parser.parse_args()

    print("=" * 80)
    print("      MIDGLEY HINDSIGHT EPISODIC MEMORY RECONCILIATION ENGINE (Issue #557)")
    print("=" * 80)
    print(f"  Target Start Date:  {args.start_date}")
    print(f"  History CSV Path:   {args.history_csv}")

    mem_mgr = AgentMemoryManager()
    is_online = mem_mgr.is_cloud_engine_active
    print(f"  Cloud Bank ID:      {mem_mgr.hindsight_client.bank_id}")
    print(f"  Cloud Connected:    {is_online} ({'Vectorize Hosted SaaS' if is_online else 'Local SQLite Fallback'})")
    print("-" * 80)

    res = mem_mgr.reconcile_unretained_prediction_anomalies(
        start_date=args.start_date,
        history_csv=args.history_csv
    )

    print(f"\n  Reconciliation Result: {res.get('status')}")
    print(f"  Synced Anomalies:      {res.get('synced_count', 0)}")
    
    if res.get("retained_anomalies"):
        print("\n  Retained Anomalies Breakdown:")
        for anom in res["retained_anomalies"]:
            print(f"    - [{anom['target_date']}] {anom['region']}: {anom['anomaly_type']} (Error: ${anom['error_dollars']:+.4f}/gal, Cloud: {anom['cloud_status']})")

    # Display post-reconciliation inventory
    inventory = mem_mgr.get_bank_inventory()
    print("\n" + "=" * 80)
    print("  POST-RECONCILIATION MEMORY INVENTORY")
    print("=" * 80)
    print(f"  Total Memories:     {inventory.get('memories_count', 0)}")
    print(f"  Total Observations: {inventory.get('observations_count', 0)}")
    print(f"  Total Reflections:  {inventory.get('reflections_count', 0)}")
    print(f"  Backend:            {inventory.get('backend')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
