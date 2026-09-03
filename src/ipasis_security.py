"""
IPASIS API Gateway Security & Telemetry Accounting (src/ipasis_security.py)

Provides real-time IP reputation checks, bot detection, and Tor/Proxy/Abuse filtering
for incoming webhook traffic (POST /api/v1/events/webhook).

Features:
- Free keyless tier / API key authentication (ipasis.com)
- In-memory 1-hour TTL cache to minimize external HTTP queries
- Zero-overhead local/private IP bypassing (127.0.0.1, ::1, 10.x, 192.168.x, testclient)
- Fail-open fallback when network or IPASIS API is unreachable
- Telemetry ledger at data/ipasis_telemetry.json tracking daily API quota usage (used / 1,000)
"""

import os
import json
import time
import logging
import ipaddress
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Default API Key from environment or fallback
IPASIS_API_KEY = os.environ.get("IPASIS_API_KEY", "ipasis_c92c28445c93_d65965edd3bfc851770b9573f777e152")
TELEMETRY_FILE = os.path.join("data", "ipasis_telemetry.json")

# In-memory TTL cache: {ip: (timestamp, result_dict)}
_IP_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour TTL

# Private/Local IP bypass definitions
LOCAL_BYPASS_HOSTS = {"testclient", "localhost", "test_runner", "test_suite"}


class IPASISSecurityVerifier:
    def __init__(self, daily_allowance: int = 1000, timeout: float = 2.0):
        self.daily_allowance = daily_allowance
        self.timeout = timeout

    @staticmethod
    def is_private_or_local_ip(ip_str: str) -> bool:
        """Determines if an IP string is a local loopback, private RFC 1918 subnet, or test runner."""
        if not ip_str or ip_str.lower() in LOCAL_BYPASS_HOSTS:
            return True
            
        clean_ip = ip_str.split(",")[0].strip()
        try:
            ip_obj = ipaddress.ip_address(clean_ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError:
            # If string cannot be parsed as IP, treat as internal test identifier
            return True

    def check_ip_reputation(self, client_ip: str) -> Dict[str, Any]:
        """
        Inspects client IP reputation against IPASIS API or local cache.
        Returns result dict with 'is_blocked', 'trust_score', 'privacy_flags', and 'provider'.
        """
        clean_ip = client_ip.split(",")[0].strip() if client_ip else "127.0.0.1"

        # 1. Check local/private IP bypass
        if self.is_private_or_local_ip(clean_ip):
            self._update_telemetry_counters(private_bypass=True, allowed=True)
            return {
                "ip": clean_ip,
                "is_blocked": False,
                "reason": "Private/Local IP Bypass",
                "privacy": {"Tor": False, "Proxy": False, "VPN": False, "Abuse": False},
                "cached": False,
                "provider": "IPASIS_Bypass"
            }

        # 2. Check 1-hour TTL cache
        now = time.time()
        if clean_ip in _IP_CACHE:
            cached_time, cached_res = _IP_CACHE[clean_ip]
            if (now - cached_time) < CACHE_TTL_SECONDS:
                self._update_telemetry_counters(cache_hit=True, allowed=not cached_res.get("is_blocked", False))
                res = dict(cached_res)
                res["cached"] = True
                return res

        # 3. Query external IPASIS API
        api_key = os.environ.get("IPASIS_API_KEY", IPASIS_API_KEY)
        url = f"https://api.ipasis.com/v1/lookup?ip={clean_ip}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Midgley-GasPriceEngine/1.4",
            "X-API-Key": api_key,
            "Accept": "application/json"
        })

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    privacy = data.get("privacy", {})
                    
                    is_tor = bool(privacy.get("Tor", False))
                    is_proxy = bool(privacy.get("Proxy", False))
                    is_abuse = bool(privacy.get("Abuse", False))
                    
                    # Block if Tor or malicious Proxy/Abuse origin
                    is_blocked = is_tor or (is_proxy and is_abuse)
                    reason = "High-Risk Tor/Abuse Origin" if is_blocked else "Clean Origin"

                    result = {
                        "ip": clean_ip,
                        "is_blocked": is_blocked,
                        "reason": reason,
                        "privacy": privacy,
                        "cached": False,
                        "provider": "IPASIS"
                    }

                    _IP_CACHE[clean_ip] = (now, result)
                    self._update_telemetry_counters(api_call=True, allowed=not is_blocked, blocked=is_blocked)
                    return result

        except Exception as err:
            logger.warning(f"IPASIS API lookup failed for IP '{clean_ip}' (fail-open fallback): {err}")

        # Fail-open fallback on error or timeout
        fallback_res = {
            "ip": clean_ip,
            "is_blocked": False,
            "reason": "Fail-Open Fallback (API Unreachable)",
            "privacy": {"Tor": False, "Proxy": False, "VPN": False, "Abuse": False},
            "cached": False,
            "provider": "IPASIS_FailOpen"
        }
        self._update_telemetry_counters(allowed=True)
        return fallback_res

    def _update_telemetry_counters(self, private_bypass: bool = False, cache_hit: bool = False, api_call: bool = False, allowed: bool = False, blocked: bool = False):
        """Updates persistent telemetry ledger at data/ipasis_telemetry.json."""
        os.makedirs("data", exist_ok=True)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        ledger = {
            "date": today_str,
            "daily_requests_used": 0,
            "daily_allowance": self.daily_allowance,
            "total_checks": 0,
            "private_bypasses": 0,
            "cache_hits": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        if os.path.exists(TELEMETRY_FILE):
            try:
                with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if isinstance(existing, dict):
                        # Reset daily counter if date changed
                        if existing.get("date") == today_str:
                            ledger["daily_requests_used"] = existing.get("daily_requests_used", 0)
                        ledger["total_checks"] = existing.get("total_checks", 0)
                        ledger["private_bypasses"] = existing.get("private_bypasses", 0)
                        ledger["cache_hits"] = existing.get("cache_hits", 0)
                        ledger["allowed_requests"] = existing.get("allowed_requests", 0)
                        ledger["blocked_requests"] = existing.get("blocked_requests", 0)
            except Exception as e:
                logger.debug(f"Could not load existing IPASIS telemetry ledger: {e}")

        ledger["total_checks"] += 1
        if private_bypass:
            ledger["private_bypasses"] += 1
        if cache_hit:
            ledger["cache_hits"] += 1
        if api_call:
            ledger["daily_requests_used"] += 1
        if allowed:
            ledger["allowed_requests"] += 1
        if blocked:
            ledger["blocked_requests"] += 1

        ledger["last_updated"] = datetime.now(timezone.utc).isoformat()

        try:
            with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save IPASIS telemetry ledger: {e}")


def get_ipasis_telemetry() -> Dict[str, Any]:
    """Returns current IPASIS security and request accounting telemetry summary."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    default_summary = {
        "date": today_str,
        "daily_requests_used": 0,
        "daily_allowance": 1000,
        "quota_remaining": 1000,
        "status": "OK",
        "total_checks": 0,
        "private_bypasses": 0,
        "cache_hits": 0,
        "allowed_requests": 0,
        "blocked_requests": 0,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "security_enabled": os.environ.get("MIDGLEY_IP_SECURITY_ENABLED", "1") != "0"
    }

    if os.path.exists(TELEMETRY_FILE):
        try:
            with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    used = data.get("daily_requests_used", 0)
                    allowance = data.get("daily_allowance", 1000)
                    default_summary.update({
                        "date": data.get("date", today_str),
                        "daily_requests_used": used,
                        "daily_allowance": allowance,
                        "quota_remaining": max(0, allowance - used),
                        "status": "CAP_EXCEEDED" if used >= allowance else "OK",
                        "total_checks": data.get("total_checks", 0),
                        "private_bypasses": data.get("private_bypasses", 0),
                        "cache_hits": data.get("cache_hits", 0),
                        "allowed_requests": data.get("allowed_requests", 0),
                        "blocked_requests": data.get("blocked_requests", 0)
                    })
        except Exception as e:
            logger.debug(f"Failed to read IPASIS telemetry ledger: {e}")

    return default_summary
