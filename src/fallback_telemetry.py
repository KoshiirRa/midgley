"""
Zero-Cost Fallback & Token Savings Telemetry Engine (src/fallback_telemetry.py)

Tracks and persists telemetry metrics for zero-cost event extraction fallbacks,
basic tier API key request routing, and saved LLM token costs.

Persists data to: data/fallback_telemetry.json
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

TELEMETRY_FILE = os.path.join("data", "fallback_telemetry.json")
DEFAULT_TOKENS_PER_EVENT = 350
DEFAULT_USD_PER_TOKEN = 0.0000003  # ~$0.000105 per 350 tokens (Gemini 2.5 Flash blend)

INITIAL_TELEMETRY_STRUCTURE = {
    "total_zero_cost_invocations": 0,
    "basic_tier_routed_count": 0,
    "provider_breakdown": {
        "lexicon": 0,
        "kaggle_llm_hook": 0,
        "spc_weather": 0,
        "physical_feed": 0
    },
    "tokens_saved": 0,
    "estimated_usd_saved": 0.0,
    "avg_zero_cost_latency_ms": 0.0,
    "last_updated": None,
    "history_log": []
}


class FallbackTelemetryLogger:
    def __init__(self, filepath: str = TELEMETRY_FILE):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Creates the data directory and telemetry JSON file if not present."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            self.save_telemetry(INITIAL_TELEMETRY_STRUCTURE)

    def load_telemetry(self) -> Dict[str, Any]:
        """Loads telemetry record from disk safely."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Backfill missing keys if schema expanded
                    for k, v in INITIAL_TELEMETRY_STRUCTURE.items():
                        if k not in data:
                            data[k] = v
                    return data
        except Exception as e:
            logger.warning(f"Failed to load fallback telemetry from {self.filepath}: {e}")
        return dict(INITIAL_TELEMETRY_STRUCTURE)

    def save_telemetry(self, data: Dict[str, Any]) -> bool:
        """Saves telemetry data to disk atomically."""
        try:
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            temp_path = f"{self.filepath}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, self.filepath)
            return True
        except Exception as e:
            logger.error(f"Failed to save fallback telemetry to {self.filepath}: {e}")
            return False

    def record_fallback_invocation(
        self,
        provider: str = "lexicon",
        is_basic_tier: bool = False,
        latency_ms: float = 0.0,
        tokens_saved: int = DEFAULT_TOKENS_PER_EVENT
    ) -> Dict[str, Any]:
        """
        Records a zero-cost fallback event invocation and updates token savings.
        """
        data = self.load_telemetry()

        data["total_zero_cost_invocations"] += 1
        if is_basic_tier:
            data["basic_tier_routed_count"] += 1

        # Provider breakdown
        clean_provider = provider.lower()
        if clean_provider not in data["provider_breakdown"]:
            data["provider_breakdown"][clean_provider] = 0
        data["provider_breakdown"][clean_provider] += 1

        # Token & USD savings calculation
        data["tokens_saved"] += tokens_saved
        usd_saved = round(tokens_saved * DEFAULT_USD_PER_TOKEN, 6)
        data["estimated_usd_saved"] = round(data.get("estimated_usd_saved", 0.0) + usd_saved, 4)

        # Average latency updating
        prev_total = data["total_zero_cost_invocations"]
        prev_avg = data.get("avg_zero_cost_latency_ms", 0.0)
        new_avg = ((prev_avg * (prev_total - 1)) + latency_ms) / prev_total
        data["avg_zero_cost_latency_ms"] = round(new_avg, 2)

        # Keep rolling 50 audit log entries
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": clean_provider,
            "is_basic_tier": is_basic_tier,
            "tokens_saved": tokens_saved,
            "latency_ms": round(latency_ms, 2)
        }
        data["history_log"] = ([log_entry] + data.get("history_log", []))[:50]

        self.save_telemetry(data)
        return data

    def get_summary(self) -> Dict[str, Any]:
        """Returns clean telemetry summary for API / Web Dashboard consumption."""
        data = self.load_telemetry()
        return {
            "total_zero_cost_invocations": data.get("total_zero_cost_invocations", 0),
            "basic_tier_routed_count": data.get("basic_tier_routed_count", 0),
            "provider_breakdown": data.get("provider_breakdown", {}),
            "tokens_saved": data.get("tokens_saved", 0),
            "estimated_usd_saved": data.get("estimated_usd_saved", 0.0),
            "avg_zero_cost_latency_ms": data.get("avg_zero_cost_latency_ms", 0.0),
            "last_updated": data.get("last_updated")
        }


# Global Singleton Instance
fallback_logger = FallbackTelemetryLogger()
