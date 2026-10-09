"""
Hindsight-Driven Semantic Deduplication & Disambiguation Engine (src/hindsight_dedupe.py)

Scans incoming breaking energy headlines against recently active event memories (last 48-72h)
to detect potential cross-provider duplicates sharing the same core physical entity
(e.g., refinery, pipeline, operator) and incident type.

Supports:
- Jaccard & token-overlap semantic similarity
- Physical facility and corporate entity extraction
- Memory scanning across local intraday event records and Hindsight SaaS memory banks
- Holding candidate duplicates for human-in-the-loop operator review via Discord
"""

import os
import re
import json
import logging
import hashlib
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_HINDSIGHT_API_URL = "https://api.hindsight.vectorize.io"
DEFAULT_HINDSIGHT_BANK_ID = "midgley-event-dedupe"

# Specific physical refinery locations and regional infrastructure hubs (preferred over broad company names)
FACILITY_LOCATIONS = [
    "joliet", "baytown", "baton rouge", "beaumont",
    "delaware city", "el dorado", "tulsa", "west tulsa",
    "catlettsburg", "garyville", "sweeny", "bayway",
    "richmond refinery", "el segundo", "cushing",
    "colonial pipeline", "keystone pipeline", "explorer pipeline", "plantation pipeline",
    "strait of hormuz", "red sea", "bab el-mandeb"
]

CORE_OPERATOR_ENTITIES = [
    "exxonmobil", "exxon", "pbf energy", "pbf", "hf sinclair", "holly frontier",
    "marathon petroleum", "marathon", "valero", "phillips 66", "chevron"
]

CORE_ENERGY_ENTITIES = FACILITY_LOCATIONS + CORE_OPERATOR_ENTITIES

# Event Disruption Action Tokens
EVENT_ACTION_TOKENS = [
    "outage", "shutdown", "halt", "trip", "fire", "explosion", "flaring",
    "power outage", "unplanned", "force majeure", "leak", "spill",
    "strike", "attack", "tariff", "sanction", "quota cut"
]

STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "by", "for",
    "with", "about", "against", "after", "adds", "pressure", "over", "under",
    "is", "was", "are", "were", "be", "been", "reported", "breaking", "news"
}


def tokenize_headline(text: str) -> List[str]:
    """Tokenizes and normalizes headline for entity and semantic similarity comparison."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = [t for t in cleaned.split() if t and t not in STOP_WORDS]
    return tokens


def extract_matched_entity(text: str) -> Optional[str]:
    """Identifies if the headline explicitly mentions a known energy facility or operator."""
    text_lower = text.lower()
    # 1. Prioritize specific facility locations (e.g. Joliet over Exxon)
    for ent in FACILITY_LOCATIONS:
        if re.search(rf"\b{re.escape(ent)}\b", text_lower):
            return ent.title()
    # 2. Fall back to broader operator entities
    for ent in CORE_OPERATOR_ENTITIES:
        if re.search(rf"\b{re.escape(ent)}\b", text_lower):
            return ent.title()
    return None


def compute_token_similarity(text1: str, text2: str) -> float:
    """Computes Jaccard similarity across normalized token sets."""
    tokens1 = set(tokenize_headline(text1))
    tokens2 = set(tokenize_headline(text2))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


class HindsightEventDeduplicator:
    def __init__(
        self,
        event_log_path: str = os.path.join("data", "intraday_events.json"),
        similarity_threshold: float = 0.45,
        default_lookback_hours: float = 72.0
    ):
        self.event_log_path = event_log_path
        self.similarity_threshold = similarity_threshold
        self.default_lookback_hours = default_lookback_hours

    def get_recent_active_events(self, max_age_hours: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieves verified recent anomalies logged within max_age_hours."""
        lookback = max_age_hours or self.default_lookback_hours
        if not os.path.exists(self.event_log_path):
            return []

        active_events = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            with open(self.event_log_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                if not isinstance(records, list):
                    return []

                for r in records:
                    # Ignore non-anomalies or pending review records
                    if not r.get("is_anomaly") or r.get("pending_review"):
                        continue

                    ts_str = r.get("timestamp")
                    if ts_str:
                        try:
                            evt_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                            age_hours = (now - evt_dt).total_seconds() / 3600.0
                            if age_hours <= lookback:
                                r_copy = dict(r)
                                r_copy["age_hours"] = age_hours
                                active_events.append(r_copy)
                        except Exception:
                            # Fall back to including if recent without timestamp
                            active_events.append(r)
                    else:
                        active_events.append(r)
        except Exception as e:
            logger.warning(f"Could not read active events from {self.event_log_path}: {e}")

        return active_events

    def _get_hindsight_credentials(self) -> Tuple[str, str, str]:
        """Resolves Hindsight SaaS API URL, Bearer Token, and Bank ID."""
        api_url = os.environ.get("HINDSIGHT_API_URL", DEFAULT_HINDSIGHT_API_URL).rstrip("/")
        bank_id = os.environ.get("HINDSIGHT_DEDUPE_BANK_ID", DEFAULT_HINDSIGHT_BANK_ID)
        token = os.environ.get("HINDSIGHT_API_TOKEN", "")
        if not token:
            cfg_path = os.path.expanduser("~/.hindsight/coding-agent.json")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        token = cfg.get("apiToken", "")
                except Exception as e:
                    logger.debug(f"Could not read Hindsight config at {cfg_path}: {e}")
        return api_url, token, bank_id

    def retain_event_in_hindsight(self, event: Dict[str, Any]) -> bool:
        """
        Retains a verified high-impact intraday anomaly into the Hindsight SaaS memory bank.
        Provides durable cross-provider semantic indexing.
        Under TESTING=1, safely skips remote network calls unless FORCE_HINDSIGHT_SYNC is set.
        """
        if os.environ.get("TESTING") == "1" and not os.environ.get("FORCE_HINDSIGHT_SYNC"):
            return False

        api_url, token, bank_id = self._get_hindsight_credentials()
        if not token:
            logger.debug("Hindsight API token not found; skipping SaaS retention.")
            return False

        headline = event.get("headline", "")
        if not headline:
            return False

        entity = event.get("matched_entity") or extract_matched_entity(headline) or "Energy Infrastructure"
        doc_id = event.get("hash") or event.get("id") or hashlib.sha256(headline.encode("utf-8")).hexdigest()[:16]
        ts = event.get("timestamp") or datetime.now(timezone.utc).isoformat()
        locales = event.get("target_locales", ["National"])

        payload = {
            "items": [
                {
                    "content": f"{headline}. Impacted regional locales: {', '.join(locales)}. Impact scores: {event.get('scores', {})}",
                    "document_id": str(doc_id),
                    "entities": [{"text": entity, "type": "FACILITY"}],
                    "tags": ["intraday_anomaly", "petroleum_market", "disruption"],
                    "timestamp": ts,
                    "metadata": {
                        "source": str(event.get("source", "Unknown")),
                        "url": str(event.get("url", ""))
                    }
                }
            ]
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{api_url}/v1/default/banks/{bank_id}/memories",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            logger.debug(f"Notice retaining event in Hindsight bank '{bank_id}': {e}")
            return False

    def query_hindsight_candidates(self, headline: str) -> List[Dict[str, Any]]:
        """
        Queries Hindsight Cloud SaaS memories/recall for cross-provider semantic analogs.
        Under TESTING=1, safely skips remote calls unless FORCE_HINDSIGHT_SYNC is set.
        """
        if os.environ.get("TESTING") == "1" and not os.environ.get("FORCE_HINDSIGHT_SYNC"):
            return []

        api_url, token, bank_id = self._get_hindsight_credentials()
        if not token:
            return []

        payload = {
            "query": headline,
            "budget": "mid"
        }
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{api_url}/v1/default/banks/{bank_id}/memories/recall",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("results", [])
        except Exception as e:
            logger.debug(f"Hindsight recall query notice for '{headline[:40]}': {e}")
            return []
        return []

    def check_potential_duplicate(
        self,
        headline: str,
        source: str = "",
        url: str = "",
        max_age_hours: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates incoming headline against recent events.
        If an event within the lookback window shares the same physical entity and
        has high token/semantic similarity, returns match details for human review.
        Checks local rolling records and augments via Hindsight SaaS bank memory recall.
        """
        entity = extract_matched_entity(headline)
        recent_events = self.get_recent_active_events(max_age_hours)

        best_match = None
        highest_sim = 0.0

        if recent_events:
            for evt in recent_events:
                prev_hl = evt.get("headline", "")
                prev_url = evt.get("url", "")
                if prev_url and url and prev_url == url:
                    # Exact URL replay is a deterministic duplicate, not a candidate for disambiguation
                    return None

                prev_entity = extract_matched_entity(prev_hl)
                sim = compute_token_similarity(headline, prev_hl)

                # Match criteria:
                # 1. Exact shared physical facility/entity + (shared action token OR sim >= 0.30)
                # 2. Or high token similarity (>= 0.50) regardless of explicit named entity
                has_shared_entity = bool(entity and prev_entity and entity.lower() == prev_entity.lower())

                tokens_action_curr = {t for t in EVENT_ACTION_TOKENS if re.search(rf"\b{re.escape(t)}\b", headline.lower())}
                tokens_action_prev = {t for t in EVENT_ACTION_TOKENS if re.search(rf"\b{re.escape(t)}\b", prev_hl.lower())}
                has_shared_action = bool(tokens_action_curr and tokens_action_prev and (tokens_action_curr & tokens_action_prev))

                is_match = False
                if has_shared_entity and (has_shared_action or sim >= self.similarity_threshold or sim >= 0.30):
                    is_match = True
                elif sim >= 0.50:
                    is_match = True

                if is_match:
                    if sim > highest_sim or highest_sim == 0.0:
                        highest_sim = sim
                        matched_entity_name = entity or prev_entity or "Energy Infrastructure"
                        best_match = {
                            "is_potential_duplicate": True,
                            "similarity": round(sim, 2),
                            "matched_entity": matched_entity_name,
                            "prior_event": evt,
                            "incoming_headline": headline
                        }

        # 2. If no local match found or for cross-provider syndicated articles, consult Hindsight SaaS
        if not best_match:
            cloud_matches = self.query_hindsight_candidates(headline)
            for cm in cloud_matches:
                cm_text = cm.get("text", "")
                cm_entities = cm.get("entities", [])
                cm_id = cm.get("document_id") or cm.get("id")
                cm_meta = cm.get("metadata") or {}
                if cm_meta.get("url") and url and cm_meta.get("url") == url:
                    return None

                sim = compute_token_similarity(headline, cm_text)
                has_entity_overlap = bool(
                    entity and any(
                        entity.lower() in e.lower() or e.lower() in entity.lower()
                        for e in cm_entities
                    )
                )

                if (has_entity_overlap and sim >= 0.25) or sim >= 0.45:
                    matched_ent = entity or (cm_entities[0] if cm_entities else "Energy Facility")
                    best_match = {
                        "is_potential_duplicate": True,
                        "similarity": round(sim, 2),
                        "matched_entity": matched_ent,
                        "prior_event": {
                            "headline": cm_text,
                            "hash": cm_id,
                            "url": cm_meta.get("url", "")
                        },
                        "incoming_headline": headline,
                        "hindsight_saas_matched": True
                    }
                    break

        return best_match
