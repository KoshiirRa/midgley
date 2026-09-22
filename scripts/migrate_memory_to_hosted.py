#!/usr/bin/env python3
"""
Migrate Agent Memory to Hindsight-Hosted SaaS (scripts/migrate_memory_to_hosted.py)
Transfers pre-existing episodic memory records, anomaly post-mortems, and reflections
from local SQLite (data/agent_memory.sqlite) to the managed Vectorize Hindsight cloud service.
"""

import os
import sys
import json
import sqlite3
import logging
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure repo root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.hindsight_client import HindsightClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("hindsight_migration")


def run_migration(batch_size: int = 25, reset_sync: bool = False):
    db_path = os.path.join(PROJECT_ROOT, "data", "agent_memory.sqlite")
    if not os.path.exists(db_path):
        logger.error(f"Memory database not found at {db_path}")
        return

    bank_id = os.environ.get("HINDSIGHT_BANK_ID", "Midgley")
    client = HindsightClient(bank_id=bank_id)

    if not client.is_configured:
        logger.error("HINDSIGHT_API_URL or HINDSIGHT_API_KEY is not configured.")
        return

    logger.info("=" * 70)
    logger.info("STARTING MIGRATION TO HINDSIGHT-HOSTED SAAS")
    logger.info(f"Target URL:  {client.base_url}")
    logger.info(f"Target Bank: {client.bank_id}")
    logger.info("=" * 70)

    # Health check
    if not client.ping():
        logger.error("Failed to reach Hindsight API endpoint. Please check URL and network.")
        return
    logger.info("Endpoint ping succeeded!")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if reset_sync:
        logger.info("Resetting cloud_synced flag for all records...")
        conn.execute("UPDATE memories SET cloud_synced = 0")
        conn.commit()

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories WHERE cloud_synced = 0 ORDER BY forecast_target_date ASC, id ASC")
    pending_memories = cursor.fetchall()
    logger.info(f"Pending unsynced memories: {len(pending_memories)}")

    if not pending_memories:
        logger.info("No pending memories to migrate. Use --reset to force re-sync.")
        conn.close()
        return

    total_migrated = 0
    total_tokens_used = 0

    for i in range(0, len(pending_memories), batch_size):
        batch = pending_memories[i:i + batch_size]
        items_payload = []
        synced_ids = []

        for row in batch:
            region = row["region"]
            anomaly_type = row["anomaly_type"]
            content = row["content"]
            error_dollars = row["error_dollars"] or 0.0
            target_date = row["forecast_target_date"] or datetime.now().strftime("%Y-%m-%d")
            doc_id = f"exp_{region.lower()}_{target_date.replace('-', '')}"

            tags = [region]
            if anomaly_type:
                tags.append(anomaly_type)

            items_payload.append({
                "content": content,
                "context": f"Gas price forecasting record for region {region} (Error: ${error_dollars:+.4f}/gal, Anomaly: {anomaly_type or 'NORMAL'})",
                "document_id": doc_id,
                "tags": tags,
                "timestamp": row["created_at"] or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            })
            synced_ids.append(row["id"])

        payload = {
            "async": False,
            "items": items_payload
        }

        url = f"{client.base_url}/v1/default/banks/{client.bank_id}/memories"
        data_bytes = json.dumps(payload).encode("utf-8")

        try:
            import urllib.request
            req = urllib.request.Request(url, data=data_bytes, headers=client._get_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=client.timeout * 2) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                usage = res_data.get("usage", {})
                batch_tokens = usage.get("total_tokens", 0)
                total_tokens_used += batch_tokens

                placeholders = ",".join("?" for _ in synced_ids)
                conn.execute(f"UPDATE memories SET cloud_synced = 1 WHERE id IN ({placeholders})", synced_ids)
                conn.commit()

                total_migrated += len(synced_ids)
                logger.info(
                    f"Batch {i // batch_size + 1}/{(len(pending_memories) + batch_size - 1) // batch_size}: "
                    f"Synced {len(synced_ids)} records | Batch Tokens: {batch_tokens:,} | Total Migrated: {total_migrated}/{len(pending_memories)}"
                )
        except Exception as e:
            logger.error(f"Failed migrating batch starting at index {i}: {e}", exc_info=True)
            time.sleep(2.0)

    conn.close()

    stats = client.get_bank_stats()
    logger.info("=" * 70)
    logger.info("MIGRATION COMPLETED!")
    logger.info(f"Total Records Migrated:  {total_migrated}")
    logger.info(f"Total Retain Tokens:     {total_tokens_used:,}")
    estimated_cost = (total_tokens_used / 1_000_000) * 10.0
    logger.info(f"Estimated Balance Used:  ${estimated_cost:.4f} (from free credits)")
    logger.info(f"Final Bank Stats:        {stats}")
    logger.info("=" * 70)


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    run_migration(batch_size=25, reset_sync=reset)
