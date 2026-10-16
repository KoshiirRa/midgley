"""
Hindsight Episodic Context & Feedback Loop Engine (src/hindsight_context.py)

Provides closed-loop episodic memory grounding for Project Midgley:
1. Episodic Precedent Recall: Queries Hindsight memory bank ('Midgley') for historical
   analog shock episodes (refinery outages, pipeline disruptions, OPEC cuts, hurricane landfalls,
   river draft constraints, RVP transitions).
2. Prompt Context Formatting: Injects empirical historical duration, pass-through lags, and
   price reaction bounds into LLM analysis prompts.
3. Causal Reflection: Classifies post-settlement prediction anomalies (>2σ or directional misses)
   and records structured qualitative reflections back into episodic memory.
"""

from __future__ import annotations

import os
import re
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

from src.agent_memory import AgentMemoryManager
from src.db.client import get_db

logger = logging.getLogger(__name__)

# Core catalyst keywords triggering historical precedent recall
CATALYST_PATTERNS = [
    r"\brefin(?:ery|ing)?\b",
    r"\bfcc\b",
    r"\bcoker\b",
    r"\bhydrocracker\b",
    r"\bflar(?:e|ing)?\b",
    r"\boutage\b",
    r"\bfire\b",
    r"\bexplosion\b",
    r"\bpipeline\b",
    r"\bcolonial\b",
    r"\bexplorer\b",
    r"\bhurricane\b",
    r"\btropical\s+storm\b",
    r"\bopec(?:\+)?\b",
    r"\bproduction\s+cut\b",
    r"\bquota\b",
    r"\briver\b",
    r"\bbarge\b",
    r"\block\b",
    r"\bdraft\b",
    r"\bchokepoint\b",
    r"\bhormuz\b",
    r"\bsuez\b",
    r"\brvp\b",
    r"\bwaiver\b",
    r"\btariff\b",
    r"\bsanction(?:s)?\b",
    r"\bstrike\b",
    r"\bunplanned\s+shutdown\b"
]

CATALYST_REGEX = re.compile("|".join(CATALYST_PATTERNS), re.IGNORECASE)


def is_catalyst_headline(headline: str) -> bool:
    """Checks if a headline contains high-impact physical or qualitative catalyst keywords."""
    if not headline:
        return False
    return bool(CATALYST_REGEX.search(headline))


def extract_catalyst_tokens(headline: str) -> str:
    """Extracts dominant catalyst terms from headline for targeted episodic recall."""
    matches = [m.group(0).lower().strip() for m in CATALYST_REGEX.finditer(headline)]
    if matches:
        return " ".join(dict.fromkeys(matches))
    # Fallback to key words of length >= 4
    clean_words = [w for w in re.sub(r'[^\w\s]', ' ', headline).split() if len(w) >= 4]
    return " ".join(clean_words[:6])


def is_hindsight_prompt_injection_enabled() -> bool:
    """Checks if Hindsight episodic prompt injection into LLM prompts is enabled (Issue #576 N-4). Defaults to False."""
    val = os.getenv("MIDGLEY_ENABLE_HINDSIGHT_PROMPT_INJECTION", "0").strip().lower()
    return val in ("1", "true", "yes", "on")


def query_episodic_precedents(
    query_text: str,
    region: Optional[str] = None,
    top_k: int = 2,
    as_of: Optional[str] = None,
    memory_manager: Optional[AgentMemoryManager] = None
) -> List[Dict[str, Any]]:
    """
    Queries Hindsight memory bank for matching historical shock episodes.
    Returns normalized structured precedent entries, applying point-in-time as_of filtering (Issue #576 N-4/N-5, Issue #580 N-9).
    """
    if not query_text:
        return []

    mgr = memory_manager or AgentMemoryManager()
    t0 = time.time()
    raw_memories = []

    try:
        raw_memories = mgr.recall(query=query_text, region=region, top_k=top_k * 2 if as_of else top_k)
    except Exception as e:
        logger.debug(f"Hindsight precedent recall notice: {e}")

    latency_ms = (time.time() - t0) * 1000.0
    precedents = []

    for item in raw_memories:
        content = item.get("content", "")
        metadata = item.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        # Parse structured fields from reflection or memory content
        anom = item.get("anomaly_type") or metadata.get("anomaly_type") or "HISTORICAL_SHOCK"
        reg = item.get("region") or region or "National"
        target_d = item.get("forecast_target_date") or metadata.get("target_date")

        # Point-in-time as_of filtering (Issue #580 N-9, Issue #586 N-4/N-5)
        if as_of:
            if not target_d:
                continue
            try:
                if str(target_d)[:10] > str(as_of)[:10]:
                    continue
            except Exception:
                continue

        # Derive duration, lag, and price reaction without synthetic default hallucination (Issue #576 N-5, #586)
        duration = metadata.get("outage_duration_days") or metadata.get("duration") or ""
        lag = metadata.get("pass_through_lag_days") or metadata.get("lag") or ""
        price_shock = metadata.get("price_shock_dollars") or metadata.get("realized_price_reaction") or ""
        lesson = metadata.get("lesson") or metadata.get("calibration_suggestion") or ""
        if not lesson and len(content) > 10:
            lesson = content[:160]

        precedents.append({
            "memory_id": item.get("memory_id", ""),
            "catalyst": content[:120].strip(),
            "region": reg,
            "target_date": target_d,
            "anomaly_type": anom,
            "duration": str(duration),
            "pass_through_lag": str(lag),
            "price_shock": str(price_shock),
            "lesson": lesson.strip() if isinstance(lesson, str) else "",
            "score": float(item.get("score", 1.0))
        })
        if len(precedents) >= top_k:
            break

    # Log telemetry to relational database
    try:
        db = get_db()
        log_id = hashlib.sha256(f"recall_{query_text}_{time.time()}".encode("utf-8")).hexdigest()[:32]
        sql = """
        INSERT INTO hindsight_telemetry (log_id, operation, context_key, query_or_doc, result_summary, latency_ms, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        summary = f"Found {len(precedents)} precedents"
        db.execute(sql, (log_id, "RECALL", region or "GLOBAL", query_text[:200], summary, latency_ms, "SUCCESS"))
    except Exception as err:
        logger.debug(f"Could not record hindsight telemetry: {err}")

    return precedents


def format_hindsight_precedent_prompt_block(precedents: List[Dict[str, Any]]) -> str:
    """
    Formats structured episodic precedents into a Markdown context block for LLM prompts.
    Omits missing or empty fields without inserting synthetic place-holders (Issue #576 N-5).
    """
    if not precedents:
        return ""

    lines = ["\n[HISTORICAL EPISODIC MEMORY PRECEDENT & REALIZED ANALOGS]"]
    for i, p in enumerate(precedents, 1):
        reg_info = f" ({p['region']})" if p.get("region") else ""
        date_info = f" [{p['target_date']}]" if p.get("target_date") else ""
        lines.append(f"• Precedent {i}: {p['catalyst']}{reg_info}{date_info}")
        if p.get("duration"):
            lines.append(f"   - Historical Outage Duration: {p['duration']}")
        if p.get("pass_through_lag"):
            lines.append(f"   - Empirical Pass-Through Lag: {p['pass_through_lag']}")
        if p.get("price_shock"):
            lines.append(f"   - Realized Price Reaction: {p['price_shock']}")
        if p.get("lesson"):
            lines.append(f"   - Key Econometric Takeaway: {p['lesson']}")

    lines.append("Use these empirical historical bounds to anchor and calibrate your qualitative impact scores.\n")
    return "\n".join(lines)


def inject_hindsight_context(
    headline: str,
    region: Optional[str] = None,
    top_k: int = 2,
    as_of: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Inspects headline for energy catalysts, retrieves relevant Hindsight memory precedents,
    and returns the formatted prompt block and structured precedent list.
    Gated behind MIDGLEY_ENABLE_HINDSIGHT_PROMPT_INJECTION (Issue #576 N-4).
    """
    if not is_hindsight_prompt_injection_enabled():
        return "", []

    if not is_catalyst_headline(headline):
        return "", []

    query_tokens = extract_catalyst_tokens(headline)
    precedents = query_episodic_precedents(query_tokens, region=region, top_k=top_k, as_of=as_of)
    prompt_block = format_hindsight_precedent_prompt_block(precedents)
    return prompt_block, precedents


def classify_causal_anomaly(
    predicted_price: float,
    actual_price: float,
    error_dollars: float,
    directional_hit: Optional[float | bool] = None,
    active_events_count: int = 0
) -> str:
    """
    Classifies root cause of out-of-sample forecast anomaly.
    Robustly handles directional misses for float 0.0 or boolean False (Issue #580 N-10).
    """
    diff = predicted_price - actual_price
    
    d_miss = False
    if directional_hit is not None:
        if isinstance(directional_hit, bool):
            d_miss = not directional_hit
        else:
            try:
                d_miss = (float(directional_hit) == 0.0)
            except Exception:
                d_miss = False

    if diff >= 0.20:
        if active_events_count > 0:
            return "OVERESTIMATED_SHOCK"
        return "LARGE_OVERESTIMATE"
    elif diff <= -0.20:
        if active_events_count > 0:
            return "UNDERESTIMATED_SHOCK"
        return "LARGE_UNDERESTIMATE"
    elif d_miss and abs(diff) >= 0.05:
        return "DIRECTIONAL_FLIP"
    elif abs(diff) >= 0.15:
        return "BASIS_DIVERGENCE"
    return "NORMAL"


def evaluate_and_reflect_settled_anomalies(
    eval_df: pd.DataFrame,
    memory_manager: Optional[AgentMemoryManager] = None
) -> List[Dict[str, Any]]:
    """
    Scans settled evaluation records for significant forecasting anomalies (>2σ or directional misses),
    synthesizes qualitative post-mortems, and retains durable reflections in Hindsight memory.
    """
    if eval_df is None or eval_df.empty:
        return []

    mgr = memory_manager or AgentMemoryManager()
    anomalies_to_reflect = []

    for _, row in eval_df.iterrows():
        pred = float(row.get("predicted_5d_price") or row.get("predicted_price", 0.0))
        act = float(row.get("actual_5d_price") or row.get("actual_price", 0.0))
        err = float(row.get("error_dollars") or (pred - act))
        reg = str(row.get("region", "National"))
        target_d = str(row.get("forecast_target_date") or row.get("target_date", ""))
        d_hit = row.get("directional_hit") if ("directional_hit" in row and pd.notna(row.get("directional_hit"))) else row.get("directional_correct")

        if pred <= 0 or act <= 0:
            continue

        directional_val = None
        if pd.notna(d_hit):
            try:
                directional_val = float(d_hit)
            except Exception:
                directional_val = bool(d_hit)

        anom_type = classify_causal_anomaly(
            predicted_price=pred,
            actual_price=act,
            error_dollars=err,
            directional_hit=directional_val
        )

        if anom_type != "NORMAL":
            anomalies_to_reflect.append({
                "region": reg,
                "forecast_target_date": target_d,
                "predicted_price": pred,
                "actual_price": act,
                "error_dollars": err,
                "anomaly_type": anom_type,
                "title": f"Forecast Anomaly: {reg} on {target_d} ({anom_type})",
                "content": f"Resolved forecast for {reg} targeting {target_d}: Predicted ${pred:.4f}/gal, Realized ${act:.4f}/gal, Deviation ${err:+.4f}/gal ({anom_type})."
            })

    if not anomalies_to_reflect:
        return []

    logger.info(f"Identified {len(anomalies_to_reflect)} forecast anomalies for Hindsight episodic reflection.")
    reflections = []

    try:
        reflections = mgr.reflect_on_anomalies(anomalies_to_reflect)
        # Log reflection telemetry
        db = get_db()
        for r in reflections:
            log_id = hashlib.sha256(f"reflect_{r.get('title')}_{time.time()}".encode("utf-8")).hexdigest()[:32]
            sql = """
            INSERT INTO hindsight_telemetry (log_id, operation, context_key, query_or_doc, result_summary, latency_ms, status)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """
            db.execute(sql, (
                log_id, "REFLECT", r.get("region", "GLOBAL"),
                r.get("title", "Reflection")[:200],
                r.get("root_cause", "")[:200],
                50.0, "SUCCESS"
            ))
    except Exception as e:
        logger.warning(f"Failed to reflect on anomalies in Hindsight: {e}")

    return reflections
