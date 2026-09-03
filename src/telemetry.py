"""
System Telemetry & Observability Engine (src/telemetry.py)
Provides central operational telemetry logging, LLM token and cost tracking, API quota monitoring,
environment isolation (MIDGLEY_ENV dev vs prod), Prometheus metrics exporter formatting,
and multi-environment API call suppression rules (Issue #107 & Issue #108).
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

TELEMETRY_LEDGER_PATH = os.path.join("data", "telemetry_ledger.json")

# Model pricing estimates (USD per 1,000,000 tokens)
MODEL_PRICING = {
    "gemini-2.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "claude-3-5-haiku-20241022": {"prompt": 0.80, "completion": 4.00}
}


def get_current_environment() -> str:
    """
    Returns the active execution environment ('dev' or 'prod').
    Defaults to 'dev' for local/VM/test runs, 'prod' for cloud Action runners.
    """
    env = os.environ.get("MIDGLEY_ENV", "").lower()
    if env in ["prod", "production"]:
        return "prod"
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "prod"
    return "dev"


def calculate_llm_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates estimated USD cost for LLM invocations based on token counts."""
    pricing = MODEL_PRICING.get(model_name, {"prompt": 0.10, "completion": 0.40})
    prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
    completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
    return round(prompt_cost + completion_cost, 6)


def _load_telemetry_ledger() -> dict:
    """Loads the persistent telemetry JSON ledger from disk."""
    if os.path.exists(TELEMETRY_LEDGER_PATH):
        try:
            with open(TELEMETRY_LEDGER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error reading telemetry ledger: {e}")
    return {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "llm_totals": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "fallback_activations": 0
        },
        "llm_events": [],
        "api_events": []
    }


def _save_telemetry_ledger(ledger: dict) -> None:
    """Saves the persistent telemetry JSON ledger to disk."""
    os.makedirs(os.path.dirname(TELEMETRY_LEDGER_PATH), exist_ok=True)
    try:
        # Constrain event log size to rolling last 1,000 entries
        if len(ledger.get("llm_events", [])) > 1000:
            ledger["llm_events"] = ledger["llm_events"][-1000:]
        if len(ledger.get("api_events", [])) > 1000:
            ledger["api_events"] = ledger["api_events"][-1000:]
        with open(TELEMETRY_LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)
    except Exception as e:
        logger.debug(f"Error writing telemetry ledger: {e}")


def log_llm_usage(
    vendor: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    is_fallback: bool = False,
    environment: Optional[str] = None
) -> dict:
    """
    Logs an LLM API execution event and updates cumulative token/cost metrics.
    """
    if environment is None:
        environment = get_current_environment()

    # Suppress disk writes during unit testing unless explicitly tested
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_TELEMETRY_PERSIST"):
        return {"status": "TEST_SUPPRESSED"}

    total_tokens = prompt_tokens + completion_tokens
    cost_usd = calculate_llm_cost(model, prompt_tokens, completion_tokens)

    event_record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": environment,
        "vendor": vendor,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost_usd,
        "is_fallback": is_fallback
    }

    ledger = _load_telemetry_ledger()
    totals = ledger.setdefault("llm_totals", {
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0, "fallback_activations": 0
    })
    totals["prompt_tokens"] += prompt_tokens
    totals["completion_tokens"] += completion_tokens
    totals["total_tokens"] += total_tokens
    totals["estimated_cost_usd"] = round(totals["estimated_cost_usd"] + cost_usd, 6)
    if is_fallback:
        totals["fallback_activations"] += 1

    ledger["llm_events"].append(event_record)
    _save_telemetry_ledger(ledger)

    return event_record


def get_all_quota_statuses() -> Dict[str, Any]:
    """
    Aggregates real-time quota status across Finlight, OilpriceAPI, AlphaVantage, and Gemini APIs.
    """
    quotas = {}
    
    # 1. Finlight Quota
    finlight_file = os.path.join("data", "finlight_quota.json")
    if os.path.exists(finlight_file):
        try:
            with open(finlight_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                calls = data.get("monthly_calls", 0)
                limit = data.get("monthly_limit", 150)
                quotas["finlight"] = {
                    "service": "Finlight.me",
                    "calls_used": calls,
                    "limit": limit,
                    "remaining": max(0, limit - calls),
                    "remaining_ratio": round(max(0.0, (limit - calls) / limit), 4),
                    "is_capped": data.get("is_capped", False)
                }
        except Exception as e:
            logger.debug(f"Error reading finlight quota: {e}")

    if "finlight" not in quotas:
        quotas["finlight"] = {
            "service": "Finlight.me", "calls_used": 0, "limit": 150, "remaining": 150, "remaining_ratio": 1.0, "is_capped": False
        }

    # 2. OilpriceAPI Quota
    oilprice_file = os.path.join("data", "oilpriceapi_quota.json")
    if os.path.exists(oilprice_file):
        try:
            with open(oilprice_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                calls = data.get("daily_calls", 0)
                limit = data.get("daily_limit", 25)
                quotas["oilpriceapi"] = {
                    "service": "OilpriceAPI",
                    "calls_used": calls,
                    "limit": limit,
                    "remaining": max(0, limit - calls),
                    "remaining_ratio": round(max(0.0, (limit - calls) / limit), 4),
                    "is_capped": data.get("is_capped", False)
                }
        except Exception as e:
            logger.debug(f"Error reading oilpriceapi quota: {e}")

    if "oilpriceapi" not in quotas:
        quotas["oilpriceapi"] = {
            "service": "OilpriceAPI", "calls_used": 0, "limit": 25, "remaining": 25, "remaining_ratio": 1.0, "is_capped": False
        }

    # 3. AlphaVantage Quota
    av_file = os.path.join("data", "alpha_vantage_quota.json")
    if os.path.exists(av_file):
        try:
            with open(av_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                calls = data.get("daily_calls", 0)
                limit = data.get("daily_limit", 25)
                quotas["alpha_vantage"] = {
                    "service": "AlphaVantage",
                    "calls_used": calls,
                    "limit": limit,
                    "remaining": max(0, limit - calls),
                    "remaining_ratio": round(max(0.0, (limit - calls) / limit), 4),
                    "is_capped": data.get("is_capped", False)
                }
        except Exception as e:
            logger.debug(f"Error reading alpha vantage quota: {e}")

    if "alpha_vantage" not in quotas:
        quotas["alpha_vantage"] = {
            "service": "AlphaVantage", "calls_used": 0, "limit": 25, "remaining": 25, "remaining_ratio": 1.0, "is_capped": False
        }

    # 4. Gemini API Quota (Cumulative LLM usage)
    ledger = _load_telemetry_ledger()
    totals = ledger.get("llm_totals", {})
    quotas["gemini_llm"] = {
        "service": "Google Gemini 2.5 Flash",
        "total_tokens_consumed": totals.get("total_tokens", 0),
        "estimated_cost_usd": totals.get("estimated_cost_usd", 0.0),
        "fallback_activations": totals.get("fallback_activations", 0)
    }

    return quotas


def format_prometheus_metrics(environment: Optional[str] = None) -> str:
    """
    Formats system telemetry metrics into Prometheus exposition text format for Grafana ingestion.
    """
    if environment is None:
        environment = get_current_environment()

    ledger = _load_telemetry_ledger()
    totals = ledger.get("llm_totals", {})
    quotas = get_all_quota_statuses()

    lines = []
    lines.append("# HELP llm_tokens_consumed_total Total LLM tokens consumed by extraction agents.")
    lines.append("# TYPE llm_tokens_consumed_total counter")
    lines.append(f'llm_tokens_consumed_total{{environment="{environment}",vendor="google",model="gemini-2.5-flash",type="prompt"}} {totals.get("prompt_tokens", 0)}')
    lines.append(f'llm_tokens_consumed_total{{environment="{environment}",vendor="google",model="gemini-2.5-flash",type="completion"}} {totals.get("completion_tokens", 0)}')
    lines.append(f'llm_tokens_consumed_total{{environment="{environment}",vendor="google",model="gemini-2.5-flash",type="total"}} {totals.get("total_tokens", 0)}')

    lines.append("# HELP llm_estimated_cost_usd_total Total estimated USD cost for LLM executions.")
    lines.append("# TYPE llm_estimated_cost_usd_total counter")
    lines.append(f'llm_estimated_cost_usd_total{{environment="{environment}",vendor="google",model="gemini-2.5-flash"}} {totals.get("estimated_cost_usd", 0.0):.6f}')

    lines.append("# HELP llm_tier_fallback_activations_total Total times extraction fell back to offline lexicon.")
    lines.append("# TYPE llm_tier_fallback_activations_total counter")
    lines.append(f'llm_tier_fallback_activations_total{{environment="{environment}",from_tier="gemini",to_tier="lexicon"}} {totals.get("fallback_activations", 0)}')

    lines.append("# HELP api_quota_remaining_ratio Percentage of API quota remaining before throttling.")
    lines.append("# TYPE api_quota_remaining_ratio gauge")
    for q_key in ["finlight", "oilpriceapi", "alpha_vantage"]:
        q_data = quotas.get(q_key, {})
        ratio = q_data.get("remaining_ratio", 1.0)
        lines.append(f'api_quota_remaining_ratio{{environment="{environment}",service="{q_key}"}} {ratio:.4f}')

    lines.append("# HELP api_quota_calls_used_total Total API calls used against quota safety valves.")
    lines.append("# TYPE api_quota_calls_used_total counter")
    for q_key in ["finlight", "oilpriceapi", "alpha_vantage"]:
        q_data = quotas.get(q_key, {})
        used = q_data.get("calls_used", 0)
        lines.append(f'api_quota_calls_used_total{{environment="{environment}",service="{q_key}"}} {used}')

    return "\n".join(lines) + "\n"


def is_api_call_suppressed_for_environment(service_name: str) -> bool:
    """
    Checks if outbound API calls should be suppressed based on active environment
    and availability of cached payloads (Issue #108).
    """
    env = get_current_environment()
    # In dev/test environments, if testing mode is set, suppress outbound calls
    if os.environ.get("TESTING") == "1" or os.environ.get("SUPPRESS_OUTBOUND_APIS") == "1":
        return True
    return False
