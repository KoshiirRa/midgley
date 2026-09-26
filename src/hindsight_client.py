"""
Hindsight Client Module (src/hindsight_client.py)
Lightweight, resilient HTTP client communicating with Vectorize Hindsight API
(deployed on Google Cloud Run or dev-vm) backed by Supabase pgvector.

Implements the core triad:
- Retain: Store experiential memory records, prediction anomalies, and physical shocks.
- Recall: Search for historical analogues and relevant episodic memories.
- Reflect: Agentic synthesis of root-cause post-mortems and parameter calibration.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.connector_telemetry import log_connector_event

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = float(os.environ.get("HINDSIGHT_TIMEOUT", "60.0"))  # 60-second timeout for Cloud Run scale-to-zero cold-start resilience
DEFAULT_WARMUP_TIMEOUT = float(os.environ.get("HINDSIGHT_WARMUP_TIMEOUT", "75.0"))  # 75-second warmup window for container cold boots


def _extract_error_detail(e: Exception) -> str:
    """Extracts a human-readable diagnostic message from HTTPError or general Exception."""
    if isinstance(e, urllib.error.HTTPError):
        try:
            err_body = e.read().decode("utf-8")
            err_json = json.loads(err_body)
            detail = err_json.get("detail", err_body)
            return f"HTTP {e.code}: {detail}"
        except Exception:
            return f"HTTP {e.code}: {e.reason}"
    return str(e)


class HindsightClient:
    """
    Client for interacting with Vectorize Hindsight REST API.
    Provides episodic agent memory integration (Retain-Recall-Reflect).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_id: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT
    ):
        if base_url is not None:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = os.environ.get("HINDSIGHT_API_URL", "").rstrip("/")
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("HINDSIGHT_API_KEY", "")
        if bank_id is not None:
            self.bank_id = bank_id
        else:
            self.bank_id = os.environ.get("HINDSIGHT_BANK_ID", "Midgley")
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Returns True if a valid Hindsight API URL is configured."""
        return bool(self.base_url and self.base_url.startswith("http"))

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Midgley-Hindsight-Client/2.0"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def ping(self) -> bool:
        """Checks if the Hindsight API service is reachable and responsive."""
        if not self.is_configured:
            return False
        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            return False
        start_time = time.time()
        try:
            url = f"{self.base_url}/health"
            req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                ok = resp.status in (200, 204)
                latency = (time.time() - start_time) * 1000.0
                log_connector_event(
                    connector_name="HindsightHosted",
                    target="health",
                    status="SUCCESS" if ok else f"HTTP_{resp.status}",
                    latency_ms=latency
                )
                return ok
        except Exception as e:
            latency = (time.time() - start_time) * 1000.0
            log_connector_event(
                connector_name="HindsightHosted",
                target="health",
                status="ERROR",
                latency_ms=latency,
                details=str(e)
            )
            logger.debug(f"Hindsight health ping failed: {e}")
            return False

    def warmup(self, max_wait_seconds: Optional[float] = None, retry_interval: float = 2.0) -> bool:
        """
        Proactively wakes up Cloud Run / Supabase Hindsight service from scale-to-zero.
        Polls health endpoint until responsive or max_wait_seconds elapses.
        """
        wait_seconds = max_wait_seconds if max_wait_seconds is not None else DEFAULT_WARMUP_TIMEOUT
        if not self.is_configured:
            logger.debug("Hindsight warmup skipped: service unconfigured.")
            return False
        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            logger.debug("TESTING=1: Suppressed Hindsight warmup network probe.")
            return False

        start_time = time.time()
        logger.info(f"Initiating Hindsight scale-to-zero warmup handshake (max_wait={wait_seconds}s)...")
        attempt = 1
        while (time.time() - start_time) < wait_seconds:
            try:
                url = f"{self.base_url}/health"
                req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
                with urllib.request.urlopen(req, timeout=min(self.timeout, 10.0)) as resp:
                    if resp.status in (200, 204):
                        elapsed = time.time() - start_time
                        logger.info(f"Hindsight service responsive after {elapsed:.2f}s (attempt {attempt}).")
                        log_connector_event(
                            connector_name="HindsightHosted",
                            target="warmup",
                            status="SUCCESS",
                            latency_ms=elapsed * 1000.0,
                            details=f"Warmup successful in attempt {attempt}"
                        )
                        return True
            except Exception as e:
                logger.debug(f"Hindsight warmup attempt {attempt} waiting: {e}")
            attempt += 1
            time.sleep(retry_interval)

        elapsed = time.time() - start_time
        log_connector_event(
            connector_name="HindsightHosted",
            target="warmup",
            status="TIMEOUT",
            latency_ms=elapsed * 1000.0,
            details=f"Warmup timed out after {wait_seconds}s"
        )
        logger.warning(f"Hindsight warmup timed out after {wait_seconds}s; downstream calls will use fallback.")
        return False

    def retain(
        self,
        content: str,
        region: str,
        memory_type: str = "experience",
        anomaly_type: Optional[str] = None,
        error_dollars: Optional[float] = None,
        predicted_price: Optional[float] = None,
        actual_price: Optional[float] = None,
        forecast_target_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retains a new memory record into the Hindsight agent memory bank.
        """
        if not self.is_configured:
            return {"status": "UNCONFIGURED", "message": "HINDSIGHT_API_URL not set."}

        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            return {"status": "TEST_SUPPRESSED", "message": "TESTING=1: Suppressed Hindsight network retain."}

        tags = [region]
        if anomaly_type:
            tags.append(anomaly_type)

        doc_id = f"exp_{region.lower()}_{(forecast_target_date or datetime.now().strftime('%Y%m%d')).replace('-', '')}"

        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
            "async": False,
            "items": [
                {
                    "content": content,
                    "context": f"Gas price forecasting record for region {region} (Error: ${error_dollars or 0.0:+.4f}/gal, Anomaly: {anomaly_type or 'NORMAL'})",
                    "document_id": doc_id,
                    "tags": tags,
                    "timestamp": now_utc
                }
            ]
        }

        url = f"{self.base_url}/v1/default/banks/{self.bank_id}/memories"
        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(1, 3):
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=self._get_headers(), method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    logger.info(f"Retained memory in Hindsight bank '{self.bank_id}' (region={region})")
                    return {"status": "SUCCESS", "data": res_data}
            except Exception as e:
                err_detail = _extract_error_detail(e)
                if attempt < 2:
                    logger.debug(f"Hindsight retain attempt {attempt} failed ({err_detail}); retrying...")
                    time.sleep(1.5)
                else:
                    logger.warning(f"Hindsight retain call failed after {attempt} attempts ({err_detail}). Falling back to local storage.")
                    return {"status": "ERROR", "error": err_detail}

        return {"status": "ERROR", "error": "Unknown retention failure"}

    def recall(
        self,
        query: str,
        region: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        top_k: int = 3,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-K relevant historical memories and analogies via semantic/hybrid search.
        """
        if not self.is_configured:
            return []

        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            return []

        tags = []
        if region:
            tags.append(region)
        if anomaly_type:
            tags.append(anomaly_type)

        payload = {
            "query": query,
            "budget": "mid",
            "tags": tags if tags else None
        }

        url = f"{self.base_url}/v1/default/banks/{self.bank_id}/memories/recall"
        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(1, 3):
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=self._get_headers(), method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    items = res_data.get("results", res_data.get("memories", []))
                    formatted = []
                    for it in items[:top_k]:
                        formatted.append({
                            "content": it.get("content", it.get("text", "")),
                            "region": region or "Unknown",
                            "score": it.get("score", 0.0),
                            "metadata": it
                        })
                    logger.info(f"Recalled {len(formatted)} memories from Hindsight bank '{self.bank_id}'")
                    return formatted
            except Exception as e:
                err_detail = _extract_error_detail(e)
                if attempt < 2:
                    logger.debug(f"Hindsight recall attempt {attempt} failed ({err_detail}); retrying...")
                    time.sleep(1.0)
                else:
                    logger.debug(f"Hindsight recall call failed after {attempt} attempts ({err_detail}).")
                    return []
        return []

    def reflect(
        self,
        anomalies: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Triggers agentic reflection on historical anomalies to generate qualitative post-mortems.
        """
        if not self.is_configured:
            return {"status": "UNCONFIGURED", "reflections": []}

        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            return {"status": "TEST_SUPPRESSED", "reflections": []}

        query = f"Reflect on these energy forecasting anomalies and summarize root causes: {json.dumps(anomalies)}"
        payload = {
            "query": query,
            "budget": "mid"
        }

        url = f"{self.base_url}/v1/default/banks/{self.bank_id}/reflect"
        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(1, 3):
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=self._get_headers(), method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout * 2) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    logger.info(f"Generated reflection via Hindsight bank '{self.bank_id}'")
                    return {"status": "SUCCESS", "reflections": res_data.get("reflections", [res_data])}
            except Exception as e:
                err_detail = _extract_error_detail(e)
                if attempt < 2:
                    logger.debug(f"Hindsight reflect attempt {attempt} failed ({err_detail}); retrying...")
                    time.sleep(2.0)
                else:
                    logger.warning(f"Hindsight reflect call failed after {attempt} attempts ({err_detail}).")
                    return {"status": "ERROR", "error": err_detail, "reflections": []}
        return {"status": "ERROR", "error": "Reflection failed", "reflections": []}

    def get_bank_stats(self, bank_id: Optional[str] = None) -> Optional[Dict[str, int]]:
        """
        Retrieves live memory, observation, and reflection counts from the remote Vectorize Hindsight service
        or Supabase pgvector backend.
        Returns:
            {"memories": int, "observations": int, "reflections": int} or None if unavailable/unconfigured.
        """
        if not self.is_configured:
            return None

        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            return None

        target_bank = bank_id or self.bank_id
        urls_to_try = [
            f"{self.base_url}/v1/default/banks/{target_bank}/stats",
            f"{self.base_url}/v1/default/banks/{target_bank}",
            f"{self.base_url}/banks/{target_bank}/stats"
        ]

        start_time = time.time()
        for url in urls_to_try:
            try:
                req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
                with urllib.request.urlopen(req, timeout=min(self.timeout, 5.0)) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        stats = data.get("stats", data.get("bank", data))
                        mem_count = (
                            stats.get("total_documents") or
                            stats.get("memories_count") or
                            stats.get("memories") or
                            stats.get("memory_count") or
                            stats.get("total_memories") or
                            stats.get("total_nodes") or 0
                        )
                        obs_count = (
                            stats.get("total_observations") or
                            stats.get("observations_count") or
                            stats.get("observations") or
                            stats.get("observation_count") or
                            stats.get("fact_count") or 0
                        )
                        ref_count = (
                            stats.get("reflections_count") or
                            stats.get("reflections") or
                            stats.get("reflection_count") or
                            stats.get("total_reflections") or 0
                        )
                        # If mem_count is 0 but generic count exists without separate observations
                        if mem_count == 0 and obs_count == 0 and ("memories" in stats or "total_memories" in stats):
                            mem_count = stats.get("memories", stats.get("total_memories", 0))

                        latency = (time.time() - start_time) * 1000.0
                        log_connector_event(
                            connector_name="HindsightHosted",
                            target=target_bank,
                            status="SUCCESS",
                            latency_ms=latency,
                            details=f"Stats: {mem_count} docs, {obs_count} obs, {ref_count} refs"
                        )
                        return {
                            "memories": int(mem_count),
                            "observations": int(obs_count),
                            "reflections": int(ref_count)
                        }
            except Exception as e:
                logger.debug(f"Hindsight bank stats query failed on {url}: {e}")
                continue

        latency = (time.time() - start_time) * 1000.0
        log_connector_event(
            connector_name="HindsightHosted",
            target=target_bank,
            status="ERROR",
            latency_ms=latency,
            details="Failed to query bank stats across endpoints"
        )
        return None

