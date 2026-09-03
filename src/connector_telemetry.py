"""
Connector Telemetry & Freshness Audit Logger Module (src/connector_telemetry.py)
Provides persistent structured health and performance tracking for all zero-cost data connectors
and retail gas price ingestion feeds. Logs calls, success rates, response latencies, data ages,
and staleness warnings to data/connector_telemetry.json.
"""

import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

TELEMETRY_FILE_PATH = os.path.join("data", "connector_telemetry.json")


def _load_telemetry_ledger() -> dict:
    """Loads the persistent telemetry JSON ledger from disk."""
    if os.path.exists(TELEMETRY_FILE_PATH):
        try:
            with open(TELEMETRY_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error loading telemetry ledger: {e}")
    return {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_events": 0,
        "events": []
    }


def _save_telemetry_ledger(ledger: dict) -> None:
    """Saves the persistent telemetry JSON ledger to disk."""
    os.makedirs(os.path.dirname(TELEMETRY_FILE_PATH), exist_ok=True)
    try:
        # Keep rolling last 1,000 telemetry events to constrain file size
        if len(ledger.get("events", [])) > 1000:
            ledger["events"] = ledger["events"][-1000:]
        ledger["total_events"] = len(ledger["events"])
        ledger["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(TELEMETRY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)
    except Exception as e:
        logger.debug(f"Error saving telemetry ledger: {e}")


def log_connector_event(
    connector_name: str,
    target: str,
    status: str = "SUCCESS",
    latency_ms: float = 0.0,
    data_age_hours: float = 0.0,
    is_stale: bool = False,
    details: str = None
) -> dict:
    """
    Logs a single connector or retail fuel feed execution event to data/connector_telemetry.json.
    """
    # Suppress disk writes during unit testing
    if os.environ.get("TESTING") == "1" or connector_name.startswith("Test_"):
        return {"status": "TEST_SUPPRESSED"}

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_record = {
        "timestamp": timestamp_str,
        "connector_name": connector_name,
        "target": target,
        "status": status.upper(),
        "latency_ms": round(float(latency_ms), 2),
        "data_age_hours": round(float(data_age_hours), 2),
        "is_stale": bool(is_stale),
        "details": details or ""
    }

    ledger = _load_telemetry_ledger()
    ledger["events"].append(event_record)
    _save_telemetry_ledger(ledger)

    logger.debug(f"Logged connector telemetry for {connector_name} ({target}): {status}")
    return event_record


def get_telemetry_summary(days: int = 7) -> dict:
    """
    Computes summary telemetry statistics (success rate %, avg latency, avg data age, stale count)
    across all connectors over a rolling N-day window.
    """
    ledger = _load_telemetry_ledger()
    events = ledger.get("events", [])

    cutoff_dt = datetime.now() - timedelta(days=days)
    recent_events = []
    for ev in events:
        try:
            dt = datetime.strptime(ev["timestamp"], "%Y-%m-%d %H:%M:%S")
            if dt >= cutoff_dt:
                recent_events.append(ev)
        except Exception:
            recent_events.append(ev)

    total_calls = len(recent_events)
    if total_calls == 0:
        return {
            "window_days": days,
            "total_calls": 0,
            "success_rate_pct": 100.0,
            "avg_latency_ms": 0.0,
            "avg_data_age_hours": 0.0,
            "stale_payload_count": 0,
            "connectors": {}
        }

    success_count = sum(1 for e in recent_events if e.get("status") == "SUCCESS")
    stale_count = sum(1 for e in recent_events if e.get("is_stale"))
    avg_latency = sum(e.get("latency_ms", 0.0) for e in recent_events) / total_calls
    avg_age = sum(e.get("data_age_hours", 0.0) for e in recent_events) / total_calls

    connector_breakdown = {}
    for e in recent_events:
        c_name = e.get("connector_name", "Unknown")
        if c_name not in connector_breakdown:
            connector_breakdown[c_name] = {
                "total_calls": 0,
                "success_calls": 0,
                "stale_calls": 0,
                "latencies": [],
                "data_ages": []
            }
        cb = connector_breakdown[c_name]
        cb["total_calls"] += 1
        if e.get("status") == "SUCCESS":
            cb["success_calls"] += 1
        if e.get("is_stale"):
            cb["stale_calls"] += 1
        cb["latencies"].append(e.get("latency_ms", 0.0))
        cb["data_ages"].append(e.get("data_age_hours", 0.0))

    formatted_connectors = {}
    for c_name, cb in connector_breakdown.items():
        c_tot = cb["total_calls"]
        formatted_connectors[c_name] = {
            "total_calls": c_tot,
            "success_rate_pct": round((cb["success_calls"] / c_tot) * 100.0, 1),
            "stale_calls": cb["stale_calls"],
            "avg_latency_ms": round(sum(cb["latencies"]) / c_tot, 2) if c_tot else 0.0,
            "avg_data_age_hours": round(sum(cb["data_ages"]) / c_tot, 2) if c_tot else 0.0
        }

    return {
        "window_days": days,
        "total_calls": total_calls,
        "success_rate_pct": round((success_count / total_calls) * 100.0, 1),
        "avg_latency_ms": round(avg_latency, 2),
        "avg_data_age_hours": round(avg_age, 2),
        "stale_payload_count": stale_count,
        "connectors": formatted_connectors
    }


def generate_telemetry_report(days: int = 7) -> str:
    """Generates a human-readable Markdown telemetry performance report."""
    summary = get_telemetry_summary(days=days)
    lines = [
        f"# Connector Performance & Data Freshness Audit Report ({days}-Day Window)",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Total Connector Calls:** `{summary['total_calls']}`",
        f"- **Overall Success Rate:** `{summary['success_rate_pct']}%`",
        f"- **Average Response Latency:** `{summary['avg_latency_ms']} ms`",
        f"- **Average Data Age:** `{summary['avg_data_age_hours']} hours`",
        f"- **Stale Payloads Flagged (>24h):** `{summary['stale_payload_count']}`",
        "",
        "### Connector Breakdown Table",
        "| Connector Name | Total Calls | Success Rate (%) | Stale Calls (>24h) | Avg Latency (ms) | Avg Data Age (h) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]

    connectors = summary.get("connectors", {})
    if not connectors:
        lines.append("| *No telemetry events logged yet* | - | - | - | - | - |")
    else:
        for c_name, meta in connectors.items():
            lines.append(
                f"| `{c_name}` | {meta['total_calls']} | {meta['success_rate_pct']}% | "
                f"{meta['stale_calls']} | {meta['avg_latency_ms']} ms | {meta['avg_data_age_hours']} h |"
            )

    return "\n".join(lines)
