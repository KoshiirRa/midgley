"""
TokenTab Local LLM Token Accounting & Multi-Provider Quota Manager (Issue #189).
Parses LLM session logs and API call usage metrics, calculates provider-specific
token costs, enforces budget warning thresholds, and maintains a persistent ledger
at data/token_usage_ledger.json.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Standard Token & API Rate Cards (USD per 1,000,000 tokens / calls)
PROVIDER_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash": {"input_rate": 0.075, "output_rate": 0.300},
    "gemini": {"input_rate": 0.075, "output_rate": 0.300},
    "gpt-4o-mini": {"input_rate": 0.150, "output_rate": 0.600},
    "openai": {"input_rate": 0.150, "output_rate": 0.600},
    "claude-3-5-haiku": {"input_rate": 0.800, "output_rate": 4.000},
    "anthropic": {"input_rate": 0.800, "output_rate": 4.000},
    "finlight": {"input_rate": 0.000, "output_rate": 0.000},
    "offline_lexicon": {"input_rate": 0.000, "output_rate": 0.000},
    "unknown": {"input_rate": 0.100, "output_rate": 0.400}
}


class TokenTabAccountingManager:
    """
    Manages local LLM token accounting, cost estimation, budget threshold checks,
    and persistent ledger logging for midgley pipeline calls.
    """

    def __init__(self, ledger_path: str = "data/token_usage_ledger.json"):
        self.ledger_path = ledger_path
        self._ensure_ledger_exists()

    def _ensure_ledger_exists(self) -> None:
        """Create initial empty ledger JSON file if it does not exist."""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        if not os.path.exists(self.ledger_path):
            initial_data: Dict[str, Any] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "records": []
            }
            try:
                with open(self.ledger_path, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to initialize token usage ledger at {self.ledger_path}: {e}")

    def calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost in USD based on provider rate card.
        """
        key = provider.lower()
        pricing = PROVIDER_PRICING.get(key, PROVIDER_PRICING["unknown"])
        input_cost = (input_tokens / 1_000_000.0) * pricing["input_rate"]
        output_cost = (output_tokens / 1_000_000.0) * pricing["output_rate"]
        return round(input_cost + output_cost, 6)

    def record_usage(
        self,
        provider: str,
        call_type: str,
        input_tokens: int,
        output_tokens: int,
        status: str = "success",
        model_name: str = ""
    ) -> Dict[str, Any]:
        """
        Record a single LLM or API call usage entry into the persistent ledger.
        """
        total_tokens = input_tokens + output_tokens
        cost_usd = self.calculate_cost(provider, input_tokens, output_tokens)
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "timestamp": timestamp,
            "provider": provider.lower(),
            "model_name": model_name or provider,
            "call_type": call_type,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "status": status
        }

        try:
            with open(self.ledger_path, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {"created_at": timestamp, "records": []}
                
                if "records" not in data:
                    data["records"] = []
                
                data["records"].append(record)
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
        except Exception as e:
            logger.error(f"Failed to log token usage record to {self.ledger_path}: {e}")

        return record

    def get_ledger(self) -> List[Dict[str, Any]]:
        """Retrieve all recorded token usage records."""
        if not os.path.exists(self.ledger_path):
            return []
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("records", [])
        except Exception as e:
            logger.error(f"Failed to read ledger from {self.ledger_path}: {e}")
            return []

    def check_budget_warnings(
        self,
        records: Optional[List[Dict[str, Any]]] = None,
        monthly_cost_limit_usd: float = 10.0,
        daily_token_limit: int = 100_000
    ) -> List[Dict[str, Any]]:
        """
        Evaluate recorded usage against budget and token safety thresholds.
        """
        if records is None:
            records = self.get_ledger()

        now = datetime.now(timezone.utc)
        current_year_month = now.strftime("%Y-%m")
        today_str = now.strftime("%Y-%m-%d")

        monthly_cost = 0.0
        daily_tokens = 0

        for r in records:
            ts = r.get("timestamp", "")
            if ts.startswith(current_year_month):
                monthly_cost += r.get("cost_usd", 0.0)
            if ts.startswith(today_str):
                daily_tokens += r.get("total_tokens", 0)

        warnings: List[Dict[str, Any]] = []

        # Monthly cost warning checks
        cost_ratio = monthly_cost / monthly_cost_limit_usd if monthly_cost_limit_usd > 0 else 0.0
        if cost_ratio >= 1.0:
            warnings.append({
                "level": "critical",
                "code": "MONTHLY_COST_EXCEEDED",
                "message": f"Monthly LLM spend (${monthly_cost:.4f}) has exceeded cap (${monthly_cost_limit_usd:.2f})."
            })
        elif cost_ratio >= 0.8:
            warnings.append({
                "level": "warning",
                "code": "MONTHLY_COST_WARN",
                "message": f"Monthly LLM spend (${monthly_cost:.4f}) reached {cost_ratio*100:.1f}% of cap (${monthly_cost_limit_usd:.2f})."
            })

        # Daily token count warning checks
        token_ratio = daily_tokens / daily_token_limit if daily_token_limit > 0 else 0.0
        if token_ratio >= 1.0:
            warnings.append({
                "level": "warning",
                "code": "DAILY_TOKENS_EXCEEDED",
                "message": f"Daily token count ({daily_tokens:,}) exceeded threshold ({daily_token_limit:,})."
            })

        if not warnings:
            warnings.append({
                "level": "ok",
                "code": "BUDGET_NORMAL",
                "message": f"Token accounting within limits (${monthly_cost:.4f} / ${monthly_cost_limit_usd:.2f})."
            })

        return warnings

    def get_accounting_summary(
        self,
        monthly_cost_limit_usd: float = 10.0,
        daily_token_limit: int = 100_000
    ) -> Dict[str, Any]:
        """
        Generate complete TokenTab accounting summary object.
        """
        records = self.get_ledger()

        total_input = 0
        total_output = 0
        total_tokens = 0
        total_cost = 0.0
        total_calls = len(records)

        provider_summary: Dict[str, Dict[str, Any]] = {}
        daily_summary: Dict[str, Dict[str, Any]] = {}

        for r in records:
            prov = r.get("provider", "unknown").lower()
            inp = r.get("input_tokens", 0)
            outp = r.get("output_tokens", 0)
            toks = r.get("total_tokens", inp + outp)
            cost = r.get("cost_usd", 0.0)
            ts = r.get("timestamp", "")
            date_key = ts[:10] if len(ts) >= 10 else "unknown"

            # Aggregate overall
            total_input += inp
            total_output += outp
            total_tokens += toks
            total_cost += cost

            # Aggregate per provider
            if prov not in provider_summary:
                provider_summary[prov] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "calls": 0
                }
            provider_summary[prov]["input_tokens"] += inp
            provider_summary[prov]["output_tokens"] += outp
            provider_summary[prov]["total_tokens"] += toks
            provider_summary[prov]["cost_usd"] = round(provider_summary[prov]["cost_usd"] + cost, 6)
            provider_summary[prov]["calls"] += 1

            # Aggregate per day
            if date_key not in daily_summary:
                daily_summary[date_key] = {
                    "date": date_key,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "calls": 0
                }
            daily_summary[date_key]["input_tokens"] += inp
            daily_summary[date_key]["output_tokens"] += outp
            daily_summary[date_key]["total_tokens"] += toks
            daily_summary[date_key]["cost_usd"] = round(daily_summary[date_key]["cost_usd"] + cost, 6)
            daily_summary[date_key]["calls"] += 1

        daily_list = sorted(list(daily_summary.values()), key=lambda x: x["date"], reverse=True)
        warnings = self.check_budget_warnings(records, monthly_cost_limit_usd, daily_token_limit)

        return {
            "status": "success",
            "summary": {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 6),
                "total_calls": total_calls
            },
            "provider_breakdown": provider_summary,
            "daily_usage": daily_list,
            "budget_warnings": warnings,
            "pricing_rate_cards": PROVIDER_PRICING,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


# Global singleton instance for easy import across midgley modules
token_tab_manager = TokenTabAccountingManager()
