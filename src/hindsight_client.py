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
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0  # Strict 5-second timeout for scale-to-zero / network resilience


class HindsightClient:
    """
    REST API Client for Vectorize Hindsight Agent Memory Service.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_id: str = "midgley-gas-forecasting",
        timeout: float = DEFAULT_TIMEOUT
    ):
        self.base_url = (base_url or os.environ.get("HINDSIGHT_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("HINDSIGHT_API_KEY", "")
        self.bank_id = bank_id
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
        try:
            url = f"{self.base_url}/health"
            req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.debug(f"Hindsight health ping failed: {e}")
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

        payload = {
            "bank_id": self.bank_id,
            "memory_type": memory_type,
            "region": region,
            "content": content,
            "anomaly_type": anomaly_type,
            "error_dollars": error_dollars,
            "predicted_price": predicted_price,
            "actual_price": actual_price,
            "forecast_target_date": forecast_target_date,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        try:
            url = f"{self.base_url}/v1/memories/retain"
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=self._get_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Retained memory in Hindsight bank '{self.bank_id}' (region={region})")
                return res_data
        except Exception as e:
            logger.warning(f"Hindsight retain call failed ({e}). Falling back to local storage.")
            return {"status": "ERROR", "error": str(e)}

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

        payload = {
            "bank_id": self.bank_id,
            "query": query,
            "region": region,
            "anomaly_type": anomaly_type,
            "top_k": top_k,
            "threshold": threshold
        }

        try:
            url = f"{self.base_url}/v1/memories/recall"
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=self._get_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                memories = res_data.get("memories", [])
                logger.info(f"Recalled {len(memories)} memories from Hindsight bank '{self.bank_id}'")
                return memories
        except Exception as e:
            logger.debug(f"Hindsight recall call failed ({e}).")
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

        payload = {
            "bank_id": self.bank_id,
            "anomalies": anomalies,
            "context": context or "Weekly Saturday Gas Price Model Review & Anomaly Post-Mortem"
        }

        try:
            url = f"{self.base_url}/v1/memories/reflect"
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=self._get_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout * 2) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Generated {len(res_data.get('reflections', []))} reflections via Hindsight.")
                return res_data
        except Exception as e:
            logger.warning(f"Hindsight reflect call failed ({e}).")
            return {"status": "ERROR", "error": str(e), "reflections": []}
