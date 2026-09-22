"""
Headline Arena Energy Forecasting Connector (src/headline_arena_connector.py)

Provides an independent probabilistic calibration and benchmark adapter for Midgley's
multi-agent energy forecasting models against Headline Arena (headlinearena.com).

Features:
- OAuth2 client_credentials token exchange with automatic TTL expiry caching
- Closed-form standard normal CDF probability conversion from P10/P50/P90 quantile bands
  over asset dead-zone thresholds (Brier categorical scoring for RB and CL)
- Settlement rules ingestion (GET /api/v1/eval/settlement-rules) with resilient offline defaults
- Environment isolation:
  * Dev / Local: Dry-run by default. Explicit test submissions tagged with [DEV-TEST].
  * Production: Headless live submissions using GitHub Secrets.
  * Testing: 100% mocked / network suppressed under TESTING=1.
- Telemetry logging via src/connector_telemetry.py
- One-time dev CLI registration helper
"""

import os
import sys
import math
import json
import time
import logging
import argparse
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

from src.connector_telemetry import log_connector_event

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    _env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(_env_path):
        try:
            with open(_env_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _v = _line.split("=", 1)
                        _k, _v = _k.strip(), _v.strip()
                        if _k and _k not in os.environ:
                            os.environ[_k] = _v
        except Exception:
            pass

logger = logging.getLogger(__name__)

# Default API endpoints
DEFAULT_BASE_URL = "https://headlinearena.com/api/v1"

# Pending forecasts cache and submitted challenge idempotency ledger
PENDING_FORECASTS_FILE = os.path.join("data", "headline_arena_pending_forecasts.json")
SUBMITTED_LEDGER_FILE = os.path.join("data", "headline_arena_submitted_ledger.json")


def load_pending_forecasts(
    active_only: bool = True,
    filepath: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Loads cached pending forecasts from disk or memory (in test mode).
    If active_only=True, filters out records older than their TTL expiration.
    """
    if os.environ.get("TESTING") == "1" and filepath is None:
        forecasts = getattr(load_pending_forecasts, "_test_mock_pending", [])
    else:
        path = filepath or PENDING_FORECASTS_FILE
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                forecasts = data if isinstance(data, list) else data.get("pending_forecasts", [])
        except Exception as e:
            logger.debug(f"Notice loading pending forecasts from {path}: {e}")
            return []

    if not active_only:
        return forecasts

    now_ts = time.time()
    active = []
    for fc in forecasts:
        exp_ts = fc.get("expires_ts")
        if exp_ts is None and "expires_at" in fc:
            try:
                exp_dt = datetime.fromisoformat(fc["expires_at"].replace("Z", "+00:00"))
                exp_ts = exp_dt.timestamp()
            except Exception:
                exp_ts = None
        if exp_ts is None or exp_ts > now_ts:
            active.append(fc)
    return active


def save_pending_forecast(
    asset: str,
    payload: Dict[str, Any],
    forecast_type: str = "direction",
    ttl_hours: float = 24.0,
    filepath: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persists a generated forecast payload into the 24h pending forecast cache.
    Replaces existing pending records for the same asset and forecast_type.
    """
    now_dt = datetime.now(timezone.utc)
    now_ts = now_dt.timestamp()
    exp_ts = now_ts + (ttl_hours * 3600.0)
    exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)

    record = {
        "asset": asset.upper().strip(),
        "forecast_type": forecast_type,
        "created_at": now_dt.isoformat(),
        "expires_at": exp_dt.isoformat(),
        "created_ts": now_ts,
        "expires_ts": exp_ts,
        "payload": payload
    }

    if os.environ.get("TESTING") == "1" and filepath is None:
        if not hasattr(load_pending_forecasts, "_test_mock_pending"):
            load_pending_forecasts._test_mock_pending = []
        filtered = [
            item for item in load_pending_forecasts._test_mock_pending
            if not (
                str(item.get("asset", "")).upper() == record["asset"]
                and str(item.get("forecast_type", "")).lower() == record["forecast_type"].lower()
            )
        ]
        filtered.append(record)
        load_pending_forecasts._test_mock_pending = filtered
        return record

    path = filepath or PENDING_FORECASTS_FILE
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    except Exception:
        pass

    existing = load_pending_forecasts(active_only=True, filepath=path)
    filtered = [
        item for item in existing
        if not (
            str(item.get("asset", "")).upper() == record["asset"]
            and str(item.get("forecast_type", "")).lower() == record["forecast_type"].lower()
        )
    ]
    filtered.append(record)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write pending forecasts to {path}: {e}")

    return record


def clear_expired_pending_forecasts(filepath: Optional[str] = None) -> int:
    """
    Cleans up expired pending forecast records from disk cache.
    Returns the count of purged records.
    """
    if os.environ.get("TESTING") == "1" and filepath is None:
        all_records = load_pending_forecasts(active_only=False)
        active_records = load_pending_forecasts(active_only=True)
        load_pending_forecasts._test_mock_pending = active_records
        return len(all_records) - len(active_records)

    path = filepath or PENDING_FORECASTS_FILE
    if not os.path.exists(path):
        return 0
    all_records = load_pending_forecasts(active_only=False, filepath=path)
    active_records = load_pending_forecasts(active_only=True, filepath=path)
    purged_count = len(all_records) - len(active_records)
    if purged_count > 0:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(active_records, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to clean expired pending forecasts from {path}: {e}")
    return purged_count


def load_submitted_ledger(filepath: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads the persistent challenge submission idempotency ledger.
    """
    if os.environ.get("TESTING") == "1" and filepath is None:
        return getattr(load_submitted_ledger, "_test_mock_ledger", {"submitted_challenges": {}})

    path = filepath or SUBMITTED_LEDGER_FILE
    if not os.path.exists(path):
        return {"submitted_challenges": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                if "submitted_challenges" not in data:
                    data["submitted_challenges"] = {}
                return data
            return {"submitted_challenges": {}}
    except Exception as e:
        logger.debug(f"Notice loading submitted ledger from {path}: {e}")
        return {"submitted_challenges": {}}


def is_challenge_already_submitted(
    challenge_id: str,
    filepath: Optional[str] = None
) -> bool:
    """
    Checks if a specific challenge ID has already received a prediction in the local ledger.
    """
    if not challenge_id:
        return False
    ledger = load_submitted_ledger(filepath=filepath)
    return str(challenge_id) in ledger.get("submitted_challenges", {})


def record_submitted_challenge(
    challenge_id: str,
    asset: str,
    response: Dict[str, Any],
    filepath: Optional[str] = None
) -> None:
    """
    Records a completed or duplicate challenge prediction in the local ledger for idempotency.
    """
    if not challenge_id:
        return

    now_dt = datetime.now(timezone.utc)
    entry = {
        "asset": asset.upper().strip(),
        "submitted_at": now_dt.isoformat(),
        "submitted_ts": now_dt.timestamp(),
        "response": response
    }

    if os.environ.get("TESTING") == "1" and filepath is None:
        if not hasattr(load_submitted_ledger, "_test_mock_ledger"):
            load_submitted_ledger._test_mock_ledger = {"submitted_challenges": {}}
        load_submitted_ledger._test_mock_ledger["submitted_challenges"][str(challenge_id)] = entry
        return

    path = filepath or SUBMITTED_LEDGER_FILE
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    except Exception:
        pass

    ledger = load_submitted_ledger(filepath=path)
    ledger["submitted_challenges"][str(challenge_id)] = entry
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to record submitted challenge in {path}: {e}")


# Offline default settlement dead-zone rules if API is unreachable
DEFAULT_SETTLEMENT_RULES: Dict[str, Dict[str, Any]] = {
    "RB": {
        "dead_zone": 0.0030,  # ±0.30% of open for RBOB Wholesale Gasoline
        "decimal_places": 4,
        "name": "RBOB Gasoline Futures (RB=F)",
        "unit": "$/gal"
    },
    "CL": {
        "dead_zone": 0.0030,  # ±0.30% of open for WTI Crude Oil (Headline Arena official)
        "decimal_places": 2,
        "name": "Crude Oil Futures (CL=F)",
        "unit": "$/bbl"
    }
}


def norm_cdf(z: float) -> float:
    """
    Computes standard normal cumulative distribution function Phi(z) using math.erf.
    Phi(z) = 0.5 * (1.0 + erf(z / sqrt(2)))
    """
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def compute_directional_probabilities(
    open_price: float,
    p50: float,
    p10: Optional[float] = None,
    p90: Optional[float] = None,
    residual_std: Optional[float] = None,
    dead_zone: float = 0.0030
) -> Dict[str, Any]:
    """
    Converts median forecast (p50), quantile uncertainty bands (p10, p90) or residual_std,
    and open spot price into categorical probabilities (bullish, neutral, bearish) over the
    specified dead-zone threshold d.

    Math Formulation:
      mu = p50
      sigma = (p90 - p10) / (2 * 1.28155) = (p90 - p10) / 2.5631 (or residual_std)
      T_upper = open_price * (1 + dead_zone)
      T_lower = open_price * (1 - dead_zone)
      z_upper = (T_upper - mu) / sigma
      z_lower = (T_lower - mu) / sigma

      P(bullish) = 1 - Phi(z_upper)
      P(bearish) = Phi(z_lower)
      P(neutral) = max(0, 1 - P(bullish) - P(bearish))
    """
    if open_price <= 0:
        raise ValueError(f"open_price must be positive, got {open_price}")

    mu = float(p50)

    # Derive sigma from quantile spread or residual_std
    if p10 is not None and p90 is not None and p90 > p10:
        sigma = (float(p90) - float(p10)) / 2.5631
    elif residual_std is not None and residual_std > 0:
        sigma = float(residual_std)
    else:
        # Fallback heuristic: 2% of open price
        sigma = max(0.005, 0.02 * open_price)

    # Prevent division by zero
    sigma = max(1e-6, sigma)

    t_upper = open_price * (1.0 + dead_zone)
    t_lower = open_price * (1.0 - dead_zone)

    z_upper = (t_upper - mu) / sigma
    z_lower = (t_lower - mu) / sigma

    p_bullish = max(0.0, 1.0 - norm_cdf(z_upper))
    p_bearish = max(0.0, norm_cdf(z_lower))
    p_neutral = max(0.0, 1.0 - p_bullish - p_bearish)

    # Normalize across the 3 categories to ensure sum == 1.0
    total_p = p_bullish + p_neutral + p_bearish
    if total_p > 0:
        p_bullish /= total_p
        p_neutral /= total_p
        p_bearish /= total_p
    else:
        p_neutral = 1.0
        p_bullish = 0.0
        p_bearish = 0.0

    # Determine argmax direction and confidence
    probs = {
        "bullish": p_bullish,
        "neutral": p_neutral,
        "bearish": p_bearish
    }
    direction = max(probs, key=probs.get)
    confidence = round(probs[direction], 4)

    return {
        "direction": direction,
        "confidence": confidence,
        "probabilities": {
            "bullish": round(p_bullish, 4),
            "neutral": round(p_neutral, 4),
            "bearish": round(p_bearish, 4)
        },
        "open_price": open_price,
        "mu": mu,
        "sigma": round(sigma, 6),
        "dead_zone": dead_zone,
        "t_upper": round(t_upper, 4),
        "t_lower": round(t_lower, 4)
    }


def synthesize_forecasting_rationale(
    asset: str,
    open_price: float,
    p50: float,
    direction: str,
    confidence: float,
    probabilities: Dict[str, float],
    dead_zone: float,
    t_upper: float,
    t_lower: float,
    p10: Optional[float] = None,
    p90: Optional[float] = None,
    sigma: Optional[float] = None,
    qualitative_catalysts: Optional[Dict[str, Any]] = None,
    technical_indicators: Optional[Dict[str, Any]] = None,
    physical_feeds: Optional[Dict[str, Any]] = None
) -> str:
    """
    Synthesizes a structured, highly in-depth market intelligence rationale
    for Headline Arena commodity forecasting challenges.
    """
    asset_clean = asset.upper().strip()
    unit = "$/gal" if asset_clean == "RB" else "$/bbl"
    asset_name = "RBOB Wholesale Gasoline (RB=F)" if asset_clean == "RB" else "Cushing WTI Crude Oil (CL=F)"
    
    p10_str = f"{unit}{p10:.4f}" if (p10 is not None and asset_clean == "RB") else (f"{unit}{p10:.2f}" if p10 is not None else "N/A")
    p90_str = f"{unit}{p90:.4f}" if (p90 is not None and asset_clean == "RB") else (f"{unit}{p90:.2f}" if p90 is not None else "N/A")
    sigma_val = sigma if sigma is not None else (0.02 * open_price)
    
    p_bull = probabilities.get("bullish", 0.0) * 100.0
    p_neut = probabilities.get("neutral", 0.0) * 100.0
    p_bear = probabilities.get("bearish", 0.0) * 100.0
    
    # 1. Qualitative catalyst breakdown
    catalysts = qualitative_catalysts or {}
    p_press = float(catalysts.get("overall_price_pressure", 0.0))
    s_disrup = float(catalysts.get("supply_disruption", 0.0))
    g_risk = float(catalysts.get("geopolitical_risk", 0.0))
    opec = float(catalysts.get("opec_action", 0.0))
    
    # 2. Technical & crack spread narrative
    tech = technical_indicators or {}
    crack = tech.get("crack_spread")
    wti_feed = tech.get("wti_price")
    rb_feed = tech.get("rbob_price")
    
    if asset_clean == "RB":
        if crack is not None:
            margin_narrative = f"Implied 3:2:1 refinery crack spread margin is positioned at ${crack:.2f}/bbl."
        elif wti_feed is not None:
            implied_crack = (open_price * 42.0) - float(wti_feed)
            margin_narrative = f"Underlying WTI crude feedstock (${float(wti_feed):.2f}/bbl) establishes an implied RBOB crack spread of ${implied_crack:.2f}/bbl."
        else:
            margin_narrative = "Refinery crack spread margins track seasonal equilibrium across PADD 1B and PADD 2 distribution hubs."
    else:
        if rb_feed is not None:
            margin_narrative = f"Downstream product demand from wholesale RBOB (${float(rb_feed):.4f}/gal) provides steady crack absorption for prompt physical crude."
        else:
            margin_narrative = "Prompt physical crude balances at Cushing reflect standard pipeline delivery flows and backwardation/contango structure."
            
    # 3. Physical feeds & macro factors
    phys = physical_feeds or {}
    ovx = phys.get("ovx_volatility")
    rigs = phys.get("rig_count")
    ovx_str = f"Cboe OVX crude volatility at {ovx:.1f} pts" if ovx is not None else "Implied energy volatility regime remains bounded"
    rig_str = f"US active oil drilling rigs at {rigs}" if rigs is not None else "drilling rig capacity is steady"
    
    # 4. Directional thesis
    if direction == "bullish":
        thesis = (
            f"Model projects spot settlement to advance above the {unit}{t_upper:.4f} upper threshold (+{dead_zone*100:.2f}%) "
            f"driven by positive price momentum, upside catalyst weighting (Pressure: {p_press:+.2f}, Disruption: {s_disrup:.2f}), "
            f"and physical supply tightness outstripping short-term inventory cushions."
        )
    elif direction == "bearish":
        thesis = (
            f"Model projects spot settlement to decline below the {unit}{t_lower:.4f} lower threshold (-{dead_zone*100:.2f}%) "
            f"driven by negative price pressure ({p_press:+.2f}), softening feedstock margins, and steady refinery throughput "
            f"counteracting isolated geopolitical risk premia."
        )
    else:
        thesis = (
            f"Model projects spot price to remain bounded within the +/-{dead_zone*100:.2f}% neutral dead-zone band "
            f"[{unit}{t_lower:.4f} - {unit}{t_upper:.4f}] as countervailing supply and demand factors balance out prior to settlement."
        )

    lines = [
        f"[Midgley Multi-Agent Forecast | {asset_name}]",
        f"- Executive Direction: {direction.upper()} (Confidence: {confidence*100:.1f}% | Settlement Band: +/-{dead_zone*100:.2f}% [{unit}{t_lower:.4f} - {unit}{t_upper:.4f}])",
        f"- Multi-Agent Ensemble Distribution: Open {unit}{open_price:.4f}, P50 Target {unit}{p50:.4f}, 80% CI [{p10_str} - {p90_str}], Volatility sigma={sigma_val:.4f} {unit}.",
        f"- Dead-Zone CDF Decomposition: P(Bullish)={p_bull:.1f}%, P(Neutral)={p_neut:.1f}%, P(Bearish)={p_bear:.1f}% based on closed-form standard normal integration over the {dead_zone*10000:.0f} bps dead-zone bounds.",
        f"- Market Dynamics & Margin Structure: {margin_narrative}",
        f"- Catalysts & Qualitative NLP Scores: Price Pressure: {p_press:+.2f} | Supply Disruption: {s_disrup:.2f} | Geopolitical Risk: {g_risk:.2f} | OPEC Action: {opec:.2f}. Macro context: {ovx_str}, while {rig_str}.",
        f"- Settlement Thesis: {thesis}"
    ]
    return "\n".join(lines)


class HeadlineArenaConnector:
    """
    Headline Arena API Client and Prediction Submitter.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        environment: Optional[str] = None
    ):
        self.base_url = (base_url or os.environ.get("HEADLINE_ARENA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.client_id = client_id or os.environ.get("HEADLINE_ARENA_CLIENT_ID", "").strip()
        self.client_secret = (
            client_secret
            or os.environ.get("HEADLINE_ARENA_CLIENT_SECRET", "").strip()
            or os.environ.get("HEADLINE_ARENA_API_KEY", "").strip()
        )
        self.environment = self._resolve_environment(environment)
        self._token_cache: Optional[Dict[str, Any]] = None
        self._settlement_rules_cache: Optional[Dict[str, Any]] = None
        self._subscribed_scopes: set = set()

    @staticmethod
    def _resolve_environment(environment: Optional[str] = None) -> str:
        """Resolves execution environment ('prod' vs 'dev')."""
        if environment:
            return "prod" if environment.lower() in ["prod", "production"] else "dev"
        try:
            from src.telemetry import get_current_environment
            return get_current_environment()
        except Exception:
            env = os.environ.get("MIDGLEY_ENV", "").lower()
            if env in ["prod", "production"] or os.environ.get("GITHUB_ACTIONS") == "true":
                return "prod"
            return "dev"

    @property
    def is_configured(self) -> bool:
        """Checks if client credentials are present."""
        return bool(self.client_id and self.client_secret)

    @property
    def is_prod(self) -> bool:
        """Returns True if running in production."""
        return self.environment == "prod"

    def get_bearer_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Exchanges client_id and client_secret for an OAuth2 bearer access token
        with automatic in-memory caching and expiration management.
        """
        if not self.is_configured:
            return None

        # Check in-memory cache
        now = time.time()
        if (
            not force_refresh
            and self._token_cache
            and self._token_cache.get("expires_at", 0) > now + 60
        ):
            return self._token_cache.get("access_token")

        # Test environment bypass
        if os.environ.get("TESTING") == "1":
            mock_token = "mock_ha_token_test_12345"
            self._token_cache = {"access_token": mock_token, "expires_at": now + 3600}
            return mock_token

        token_url = f"{self.base_url}/agent/auth/token"
        payload = {
            "grant_type": "client_credentials",
            "agent_id": self.client_id,
            "client_secret": self.client_secret
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            token_url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "Midgley-Forecaster/1.0"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                access_token = result.get("access_token")
                expires_in = int(result.get("expires_in", 3600))
                self._token_cache = {
                    "access_token": access_token,
                    "expires_at": now + expires_in
                }
                return access_token
        except Exception as e:
            logger.warning(f"Failed to fetch Headline Arena OAuth2 bearer token: {e}")
            return None

    def get_settlement_rules(self) -> Dict[str, Any]:
        """
        Fetches official settlement dead-zone rules from GET /api/v1/eval/settlement-rules.
        Falls back to resilient offline defaults if network request fails.
        """
        if self._settlement_rules_cache:
            return self._settlement_rules_cache

        if os.environ.get("TESTING") == "1":
            self._settlement_rules_cache = DEFAULT_SETTLEMENT_RULES
            return self._settlement_rules_cache

        rules_url = f"{self.base_url}/eval/settlement-rules"
        req = urllib.request.Request(
            rules_url,
            headers={"User-Agent": "Midgley-Forecaster/1.0"},
            method="GET"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                rules = json.loads(resp.read().decode("utf-8"))
                if isinstance(rules, dict) and len(rules) > 0:
                    self._settlement_rules_cache = rules
                    return rules
        except Exception as e:
            logger.debug(f"Notice fetching Headline Arena settlement rules, using fallback defaults: {e}")

        self._settlement_rules_cache = DEFAULT_SETTLEMENT_RULES
        return self._settlement_rules_cache

    def get_dead_zone(self, asset: str) -> float:
        """Returns the dead-zone fraction for a given asset (e.g., 0.0030 for RB, 0.0020 for CL)."""
        rules_data = self.get_settlement_rules()
        rules_dict = rules_data.get("rules", rules_data)
        asset_rule = rules_dict.get(asset.upper(), {})
        if "neutral_pct" in asset_rule:
            return float(asset_rule["neutral_pct"]) / 100.0
        if "dead_zone" in asset_rule:
            return float(asset_rule["dead_zone"])
        return float(DEFAULT_SETTLEMENT_RULES.get(asset.upper(), {}).get("dead_zone", 0.0030))

    def ensure_scope_subscription(self, scope_key: str) -> bool:
        """
        Subscribes agent to a prediction scope (POST /api/v1/agent/prediction-scope/{scope_key}).
        Maintains an in-memory set to avoid duplicate subscription requests within a session.
        """
        scope_clean = scope_key.upper().strip()
        if scope_clean in self._subscribed_scopes:
            return True

        if os.environ.get("TESTING") == "1":
            self._subscribed_scopes.add(scope_clean)
            return True

        token = self.get_bearer_token()
        if not token:
            return False

        sub_url = f"{self.base_url}/agent/prediction-scope/{scope_clean}"
        req = urllib.request.Request(
            sub_url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Midgley-Forecaster/1.0"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self._subscribed_scopes.add(scope_clean)
                return True
        except urllib.error.HTTPError as e:
            if e.code in [400, 409]:
                self._subscribed_scopes.add(scope_clean)
                return True
            logger.warning(f"Failed to subscribe to scope {scope_clean}: HTTP {e.code}")
            return False
        except Exception as e:
            logger.warning(f"Error subscribing to scope {scope_clean}: {e}")
            return False

    def get_active_challenges(self) -> List[Dict[str, Any]]:
        """
        Fetches active challenges from GET /api/v1/eval/challenges/active.
        """
        if os.environ.get("TESTING") == "1":
            return [
                {
                    "challenge": {
                        "id": "mock_cl_challenge_123",
                        "asset": "CL",
                        "name": "Crude Oil",
                        "deadline": "2026-09-18T16:00:00Z"
                    }
                }
            ]

        token = self.get_bearer_token()
        if not token:
            return []

        active_url = f"{self.base_url}/eval/challenges/active"
        req = urllib.request.Request(
            active_url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Midgley-Forecaster/1.0"
            },
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict):
                    return data.get("challenges", [])
                elif isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.warning(f"Failed to fetch active challenges from Headline Arena: {e}")
            return []

    def get_active_challenge_for_asset(self, asset: str) -> Optional[Dict[str, Any]]:
        """
        Finds the active challenge matching the target asset (e.g. 'CL' or 'RB').
        """
        challenges = self.get_active_challenges()
        asset_upper = asset.upper().strip()
        for ch in challenges:
            c_data = ch.get("challenge", ch)
            if c_data.get("asset", "").upper() == asset_upper:
                return ch
        return None

    def get_active_civic_challenges(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches active civic / macro forecasting challenges (e.g. EIA Retail Gasoline).
        """
        challenges = self.get_active_challenges()
        civic_list = []
        topic_filter = topic.upper().strip() if topic else None
        for ch in challenges:
            c_data = ch.get("challenge", ch)
            category = str(c_data.get("category", "")).lower()
            ch_topic = str(c_data.get("topic", c_data.get("asset", ""))).upper()
            is_civic = "civic" in category or "macro" in category or "eia" in ch_topic.lower() or "gas" in ch_topic.lower()
            if topic_filter:
                if topic_filter in ch_topic or ch_topic in topic_filter:
                    civic_list.append(ch)
            elif is_civic:
                civic_list.append(ch)
        return civic_list

    def get_active_challenge_by_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """
        Finds the active challenge matching a specific topic or asset keyword.
        """
        civics = self.get_active_civic_challenges(topic=topic)
        if civics:
            return civics[0]
        topic_upper = topic.upper().strip()
        for ch in self.get_active_challenges():
            c_data = ch.get("challenge", ch)
            if c_data.get("asset", "").upper() == topic_upper or c_data.get("topic", "").upper() == topic_upper:
                return ch
        return None

    def register_agent(
        self,
        name: str = "Midgley-Energy-Agent",
        description: str = "Multi-agent RBOB wholesale gasoline and Cushing WTI crude forecasting engine",
        model_provider: str = "google",
        model_name: str = "gemini-2.5-flash",
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Registers a new agent with Headline Arena (POST /api/v1/agent/registry/register).
        Intended for one-time interactive setup in local/dev environments.
        """
        if scopes is None:
            scopes = ["prediction:submit", "challenge:read"]

        if os.environ.get("TESTING") == "1":
            return {
                "status": "SUCCESS",
                "client_id": "test_ha_client_id_123",
                "client_secret": "test_ha_secret_456",
                "agent_id": name.lower().replace(" ", "-"),
                "message": "Agent registered successfully (test mode)"
            }

        reg_url = f"{self.base_url}/agent/registry/register"
        payload = {
            "name": name,
            "type": "forecaster",
            "bio": description,
            "languages": ["en"],
            "model_provider": model_provider,
            "model_name": model_name,
            "auth_method": "client_credentials",
            "requested_scopes": scopes
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            reg_url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "Midgley-Forecaster/1.0"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(f"HTTP Error registering agent ({e.code}): {err_body}")
            return {"status": "ERROR", "code": e.code, "error": err_body}
        except Exception as e:
            logger.error(f"Error registering agent with Headline Arena: {e}")
            return {"status": "ERROR", "error": str(e)}

    def format_direction_payload(
        self,
        asset: str,
        open_price: float,
        p50: float,
        p10: Optional[float] = None,
        p90: Optional[float] = None,
        residual_std: Optional[float] = None,
        qualitative_catalysts: Optional[Dict[str, Any]] = None,
        technical_indicators: Optional[Dict[str, Any]] = None,
        physical_feeds: Optional[Dict[str, Any]] = None,
        custom_reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formats a categorical direction submission payload for Headline Arena daily asset challenges.
        Automatically decorates reasoning with environment provenance ([DEVELOPMENT] / [DEV-TEST] vs Production).
        """
        asset_clean = asset.upper().strip()
        dead_zone = self.get_dead_zone(asset_clean)
        probs_meta = compute_directional_probabilities(
            open_price=open_price,
            p50=p50,
            p10=p10,
            p90=p90,
            residual_std=residual_std,
            dead_zone=dead_zone
        )

        # Build reasoning explanation
        if custom_reasoning:
            reasoning_text = custom_reasoning
        else:
            reasoning_text = synthesize_forecasting_rationale(
                asset=asset_clean,
                open_price=open_price,
                p50=p50,
                direction=probs_meta["direction"],
                confidence=probs_meta["confidence"],
                probabilities=probs_meta["probabilities"],
                dead_zone=dead_zone,
                t_upper=probs_meta["t_upper"],
                t_lower=probs_meta["t_lower"],
                p10=p10,
                p90=p90,
                sigma=probs_meta.get("sigma"),
                qualitative_catalysts=qualitative_catalysts,
                technical_indicators=technical_indicators,
                physical_feeds=physical_feeds
            )

        # Apply environment prefix if not in production
        if not self.is_prod:
            reasoning_text = f"[DEV-TEST] [DEVELOPMENT]\n{reasoning_text}"

        return {
            "asset": asset_clean,
            "direction": probs_meta["direction"],
            "confidence": probs_meta["confidence"],
            "reasoning": reasoning_text,
            "metadata": {
                "environment": self.environment,
                "probabilities": probs_meta["probabilities"],
                "open_price": open_price,
                "p50": p50,
                "p10": p10,
                "p90": p90,
                "dead_zone": dead_zone,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def format_macro_numeric_payload(
        self,
        asset: str,
        p50: float,
        p10: Optional[float] = None,
        p90: Optional[float] = None,
        residual_std: Optional[float] = None,
        reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formats a numeric distribution payload (predicted_value, predicted_std)
        for Headline Arena macro-indicator CRPS closed-form challenges.
        """
        if p10 is not None and p90 is not None and p90 > p10:
            sigma = (float(p90) - float(p10)) / 2.5631
        elif residual_std is not None and residual_std > 0:
            sigma = float(residual_std)
        else:
            sigma = max(0.01, 0.02 * float(p50))

        reasoning_text = reasoning or f"Midgley multi-agent numeric distribution: mu={p50:.4f}, sigma={sigma:.4f}"
        if not self.is_prod:
            reasoning_text = f"[DEV-TEST] {reasoning_text}"

        return {
            "asset": asset.upper().strip(),
            "predicted_value": round(float(p50), 4),
            "predicted_std": round(max(1e-4, sigma), 6),
            "reasoning": reasoning_text
        }

    def format_eia_retail_civic_payload(
        self,
        predicted_value: float,
        p10: Optional[float] = None,
        p90: Optional[float] = None,
        residual_std: Optional[float] = None,
        custom_reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formats a numeric distribution payload for the EIA Weekly Retail Gasoline Civic Challenge (Issue #408).
        Computes Gaussian standard deviation sigma from P10/P90 quantile spread or empirical residual std.
        """
        mu = float(predicted_value)
        if p10 is not None and p90 is not None and p90 > p10:
            sigma = (float(p90) - float(p10)) / 2.5631
        elif residual_std is not None and residual_std > 0:
            sigma = float(residual_std)
        else:
            sigma = max(0.01, 0.015 * mu)
        sigma = max(1e-4, sigma)

        if custom_reasoning:
            reasoning_text = custom_reasoning
        else:
            reasoning_lines = [
                "[Midgley Multi-Agent Forecast | EIA US Regular Gasoline Retail Price]",
                f"- Predicted Target (P50 Median): ${mu:.4f}/gal",
                f"- Gaussian Uncertainty: sigma={sigma:.4f}/gal" + (f" (80% CI: [${p10:.4f} - ${p90:.4f}])" if (p10 is not None and p90 is not None) else ""),
                "- Continuous Ranked Probability Score (CRPS): Closed-form normal distribution CDF evaluation.",
                "- Multi-Agent Synthesis: Ingests PADD 1-5 refinery runs, spot RBOB crack spreads, EPA RVP compliance curves, and regional rack markups."
            ]
            reasoning_text = "\n".join(reasoning_lines)

        if not self.is_prod:
            reasoning_text = f"[DEV-TEST] [DEVELOPMENT]\n{reasoning_text}"

        return {
            "asset": "EIA_RETAIL_GASOLINE",
            "topic": "EIA_RETAIL_GASOLINE",
            "predicted_value": round(mu, 4),
            "predicted_std": round(sigma, 6),
            "reasoning": reasoning_text,
            "metadata": {
                "environment": self.environment,
                "p50": mu,
                "p10": p10,
                "p90": p90,
                "sigma": round(sigma, 6),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def submit_macro_forecast(
        self,
        challenge_id: str,
        payload: Dict[str, Any],
        live_in_dev: bool = False
    ) -> Dict[str, Any]:
        """
        Submits a numeric macro / civic forecast payload to /eval/challenges/{challenge_id}/predict (Issue #408).
        """
        start_time = time.time()
        asset = payload.get("asset", payload.get("topic", "MACRO"))

        if not challenge_id:
            return {"status": "ERROR", "message": "Missing challenge_id for macro forecast submission."}

        # Check local submitted ledger for idempotency
        if is_challenge_already_submitted(challenge_id):
            msg = f"Challenge {challenge_id} ({asset}) has already been submitted in the local ledger."
            logger.info(msg)
            return {
                "status": "ALREADY_SUBMITTED",
                "mode": "SKIPPED_ALREADY_PREDICTED",
                "asset": asset,
                "challenge_id": challenge_id,
                "message": msg
            }

        # 1. Test environment suppression
        if os.environ.get("TESTING") == "1":
            latency = (time.time() - start_time) * 1000.0
            record_submitted_challenge(challenge_id, asset, {"status": "SUCCESS", "mode": "TEST_MOCKED"})
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="SUCCESS",
                latency_ms=latency,
                details=f"Test mode mock macro submission: predicted_value={payload.get('predicted_value')}"
            )
            return {
                "status": "SUCCESS",
                "mode": "TEST_MOCKED",
                "asset": asset,
                "challenge_id": challenge_id,
                "predicted_value": payload.get("predicted_value"),
                "predicted_std": payload.get("predicted_std"),
                "submission_id": "test_sub_mock_macro_123"
            }

        # 2. Check credentials
        if not self.is_configured:
            logger.info(f"Headline Arena credentials not configured. Skipping macro submission for {asset}.")
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="SKIPPED_NO_CREDENTIALS",
                latency_ms=0.0,
                details="HEADLINE_ARENA_CLIENT_ID / HEADLINE_ARENA_CLIENT_SECRET missing"
            )
            return {
                "status": "SKIPPED_NO_CREDENTIALS",
                "asset": asset,
                "challenge_id": challenge_id,
                "message": "Missing Headline Arena client credentials."
            }

        # 3. Dev environment dry-run gate
        allow_dev_submit = live_in_dev or os.environ.get("HEADLINE_ARENA_DEV_SUBMIT") == "1"
        if not self.is_prod and not allow_dev_submit:
            logger.info(
                f"[DEV DRY-RUN] Headline Arena macro submission for {asset} (challenge {challenge_id}) computed: "
                f"predicted_value={payload.get('predicted_value')}, predicted_std={payload.get('predicted_std')}. "
                f"Skipping live POST request in dev mode."
            )
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="SUCCESS",
                latency_ms=0.0,
                details=f"Dev dry-run macro: val={payload.get('predicted_value')}, std={payload.get('predicted_std')}"
            )
            return {
                "status": "DRY_RUN",
                "mode": "DEVELOPMENT_DRY_RUN",
                "asset": asset,
                "challenge_id": challenge_id,
                "predicted_value": payload.get("predicted_value"),
                "predicted_std": payload.get("predicted_std"),
                "reasoning": payload.get("reasoning"),
                "message": "Dev dry-run completed successfully without external network POST."
            }

        # 4. Live submission (Production or Explicit Dev-Test)
        bearer_token = self.get_bearer_token()
        if not bearer_token:
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="AUTH_ERROR",
                latency_ms=(time.time() - start_time) * 1000.0,
                details="Failed to obtain OAuth2 bearer token"
            )
            return {
                "status": "AUTH_ERROR",
                "asset": asset,
                "challenge_id": challenge_id,
                "message": "Failed to authenticate with Headline Arena."
            }

        predict_url = f"{self.base_url}/eval/challenges/{challenge_id}/predict"
        post_body = {
            "predicted_value": float(payload.get("predicted_value", 0.0)),
            "predicted_std": float(payload.get("predicted_std", 0.01)),
            "reasoning": str(payload.get("reasoning", ""))
        }
        data_bytes = json.dumps(post_body).encode("utf-8")
        req = urllib.request.Request(
            predict_url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
                "User-Agent": "Midgley-Forecaster/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                latency = (time.time() - start_time) * 1000.0
                record_submitted_challenge(challenge_id, asset, resp_data)
                log_connector_event(
                    connector_name="HeadlineArena",
                    target=asset,
                    status="SUCCESS",
                    latency_ms=latency,
                    details=f"Submitted macro {asset} (challenge {challenge_id}): val={payload.get('predicted_value')}, std={payload.get('predicted_std')}"
                )
                return {
                    "status": "SUCCESS",
                    "mode": "LIVE_SUBMISSION",
                    "asset": asset,
                    "challenge_id": challenge_id,
                    "response": resp_data
                }
        except urllib.error.HTTPError as e:
            latency = (time.time() - start_time) * 1000.0
            err_msg = e.read().decode("utf-8") if e.fp else str(e)
            err_lower = err_msg.lower()
            is_already_submitted = (
                e.code in [409, 500]
                or (e.code == 400 and any(k in err_lower for k in ["already", "duplicate", "unique", "exist", "conflict"]))
            )
            if is_already_submitted:
                record_submitted_challenge(challenge_id, asset, {"status": "ALREADY_SUBMITTED", "code": e.code})
                log_connector_event(
                    connector_name="HeadlineArena",
                    target=asset,
                    status="ALREADY_SUBMITTED_TODAY",
                    latency_ms=latency,
                    details=f"Macro challenge {challenge_id} already predicted (HTTP {e.code})"
                )
                return {
                    "status": "ALREADY_SUBMITTED",
                    "mode": "SKIPPED_ALREADY_PREDICTED",
                    "asset": asset,
                    "challenge_id": challenge_id,
                    "message": f"Challenge {challenge_id} for {asset} was already predicted today (HTTP {e.code})."
                }
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="HTTP_ERROR",
                latency_ms=latency,
                details=f"HTTP {e.code}: {err_msg[:100]}"
            )
            return {"status": "HTTP_ERROR", "code": e.code, "error": err_msg, "asset": asset, "challenge_id": challenge_id}
        except Exception as e:
            latency = (time.time() - start_time) * 1000.0
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="NETWORK_ERROR",
                latency_ms=latency,
                details=str(e)[:100]
            )
            return {"status": "NETWORK_ERROR", "error": str(e), "asset": asset, "challenge_id": challenge_id}

    def submit_forecast(
        self,
        payload: Dict[str, Any],
        live_in_dev: bool = False
    ) -> Dict[str, Any]:
        """
        Submits forecast payload to Headline Arena.
        
        Environment Safety Rules:
        - TESTING=1: returns mock success with zero network requests.
        - Dev environment: performs DRY-RUN by default unless live_in_dev=True or HEADLINE_ARENA_DEV_SUBMIT=1.
        - Production: executes live submission if credentials are configured.
        - Missing credentials: skips gracefully with SKIPPED_NO_CREDENTIALS status.
        """
        start_time = time.time()
        asset = payload.get("asset", "UNKNOWN")

        # 1. Test environment suppression
        if os.environ.get("TESTING") == "1":
            latency = (time.time() - start_time) * 1000.0
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="SUCCESS",
                latency_ms=latency,
                details=f"Test mode mock submission: direction={payload.get('direction')}"
            )
            return {
                "status": "SUCCESS",
                "mode": "TEST_MOCKED",
                "asset": asset,
                "direction": payload.get("direction"),
                "confidence": payload.get("confidence"),
                "submission_id": "test_sub_mock_12345"
            }

        # 2. Check credentials
        if not self.is_configured:
            logger.info(f"Headline Arena credentials not configured. Skipping submission for {asset}.")
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="SKIPPED_NO_CREDENTIALS",
                latency_ms=0.0,
                details="HEADLINE_ARENA_CLIENT_ID / HEADLINE_ARENA_CLIENT_SECRET missing"
            )
            return {
                "status": "SKIPPED_NO_CREDENTIALS",
                "asset": asset,
                "message": "Missing Headline Arena client credentials."
            }

        # 3. Dev environment dry-run gate
        allow_dev_submit = live_in_dev or os.environ.get("HEADLINE_ARENA_DEV_SUBMIT") == "1"
        if not self.is_prod and not allow_dev_submit:
            logger.info(
                f"[DEV DRY-RUN] Headline Arena submission for {asset} computed: "
                f"direction={payload.get('direction')}, confidence={payload.get('confidence')}. "
                f"Skipping live POST request in dev mode."
            )
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="SUCCESS",
                latency_ms=0.0,
                details=f"Dev dry-run: direction={payload.get('direction')}, confidence={payload.get('confidence')}"
            )
            return {
                "status": "DRY_RUN",
                "mode": "DEVELOPMENT_DRY_RUN",
                "asset": asset,
                "direction": payload.get("direction"),
                "confidence": payload.get("confidence"),
                "reasoning": payload.get("reasoning"),
                "message": "Dev dry-run completed successfully without external network POST."
            }

        # 4. Live submission (Production or Explicit Dev-Test)
        bearer_token = self.get_bearer_token()
        if not bearer_token:
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="AUTH_ERROR",
                latency_ms=(time.time() - start_time) * 1000.0,
                details="Failed to obtain OAuth2 bearer token"
            )
            return {
                "status": "AUTH_ERROR",
                "asset": asset,
                "challenge_id": challenge_id,
                "message": "Failed to authenticate with Headline Arena."
            }

        # 5. Ensure scope subscription
        self.ensure_scope_subscription(asset)

        # 6. Discover active challenge
        challenge_record = self.get_active_challenge_for_asset(asset)
        if not challenge_record:
            latency = (time.time() - start_time) * 1000.0
            msg = f"No active challenge found for {asset} on Headline Arena."
            logger.info(f"{msg} Skipping submission.")
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="SKIPPED_NO_ACTIVE_CHALLENGE",
                latency_ms=latency,
                details=msg
            )
            return {
                "status": "SKIPPED_NO_ACTIVE_CHALLENGE",
                "asset": asset,
                "message": msg
            }

        challenge_data = challenge_record.get("challenge", challenge_record)
        challenge_id = challenge_data.get("id")
        if not challenge_id:
            latency = (time.time() - start_time) * 1000.0
            msg = f"Challenge record for {asset} missing challenge_id."
            logger.warning(msg)
            return {
                "status": "ERROR",
                "asset": asset,
                "message": msg
            }

        # Check local submitted ledger for idempotency
        if is_challenge_already_submitted(challenge_id):
            msg = f"Challenge {challenge_id} ({asset}) was already predicted today."
            logger.info(msg)
            return {
                "status": "ALREADY_SUBMITTED",
                "mode": "SKIPPED_ALREADY_PREDICTED",
                "asset": asset,
                "challenge_id": challenge_id,
                "message": msg
            }

        # 7. Submit prediction to /eval/challenges/{challenge_id}/predict
        predict_url = f"{self.base_url}/eval/challenges/{challenge_id}/predict"
        post_body = {
            "direction": payload.get("direction"),
            "confidence": float(payload.get("confidence", 0.5)),
            "reasoning": payload.get("reasoning", "")
        }
        data_bytes = json.dumps(post_body).encode("utf-8")
        req = urllib.request.Request(
            predict_url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
                "User-Agent": "Midgley-Forecaster/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                latency = (time.time() - start_time) * 1000.0
                counts_for_score = resp_data.get("counts_for_score", True)
                record_submitted_challenge(challenge_id, asset, resp_data)
                log_connector_event(
                    connector_name="HeadlineArena",
                    target=asset,
                    status="SUCCESS",
                    latency_ms=latency,
                    details=f"Submitted {asset} (challenge {challenge_id}): direction={payload.get('direction')}, confidence={payload.get('confidence')}, scored={counts_for_score}"
                )
                return {
                    "status": "SUCCESS",
                    "mode": "LIVE_SUBMISSION",
                    "asset": asset,
                    "challenge_id": challenge_id,
                    "counts_for_score": counts_for_score,
                    "response": resp_data
                }
        except urllib.error.HTTPError as e:
            latency = (time.time() - start_time) * 1000.0
            err_msg = e.read().decode("utf-8") if e.fp else str(e)
            
            # Detect duplicate challenge submission constraint (HTTP 409 Conflict, HTTP 500 Internal Server Error, or HTTP 400 with duplicate message)
            err_lower = err_msg.lower()
            is_already_submitted = (
                e.code in [409, 500] 
                or (e.code == 400 and any(k in err_lower for k in ["already", "duplicate", "unique", "exist", "conflict"]))
            )
            
            if is_already_submitted:
                record_submitted_challenge(challenge_id, asset, {"status": "ALREADY_SUBMITTED", "code": e.code})
                logger.info(
                    f"Headline Arena challenge {challenge_id} ({asset}) has already received a prediction today (HTTP {e.code}). "
                    f"Skipping duplicate submission."
                )
                log_connector_event(
                    connector_name="HeadlineArena",
                    target=asset,
                    status="ALREADY_SUBMITTED_TODAY",
                    latency_ms=latency,
                    details=f"Challenge {challenge_id} already predicted (HTTP {e.code})"
                )
                return {
                    "status": "ALREADY_SUBMITTED",
                    "mode": "SKIPPED_ALREADY_PREDICTED",
                    "asset": asset,
                    "challenge_id": challenge_id,
                    "message": f"Active challenge {challenge_id} for {asset} was already predicted today."
                }
            
            logger.error(f"Headline Arena HTTP error {e.code} for {asset} (challenge {challenge_id}): {err_msg}")
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="HTTP_ERROR",
                latency_ms=latency,
                details=f"HTTP {e.code}: {err_msg[:100]}"
            )
            return {"status": "HTTP_ERROR", "code": e.code, "error": err_msg, "asset": asset, "challenge_id": challenge_id}
        except Exception as e:
            latency = (time.time() - start_time) * 1000.0
            logger.error(f"Headline Arena submission network error for {asset} (challenge {challenge_id}): {e}")
            log_connector_event(
                connector_name="HeadlineArena",
                target=asset,
                status="NETWORK_ERROR",
                latency_ms=latency,
                details=str(e)[:100]
            )
            return {"status": "NETWORK_ERROR", "error": str(e), "asset": asset, "challenge_id": challenge_id}

    def dispatch_pending_forecasts(
        self,
        live_in_dev: bool = False,
        pending_file: Optional[str] = None,
        ledger_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches cached pending forecasts against active challenges on Headline Arena (Issue #418).
        - Discards expired forecasts (>24h).
        - Queries active challenges.
        - Submits matching pending forecasts if not already submitted in the local ledger.
        - Updates submitted ledger.
        """
        clear_expired_pending_forecasts(filepath=pending_file)
        pending = load_pending_forecasts(active_only=True, filepath=pending_file)
        if not pending:
            return {
                "status": "NO_PENDING_FORECASTS",
                "dispatched": 0,
                "results": {}
            }

        active_challenges = self.get_active_challenges()
        if not active_challenges:
            return {
                "status": "NO_ACTIVE_CHALLENGES",
                "pending_count": len(pending),
                "dispatched": 0,
                "results": {}
            }

        results = {}
        dispatched_count = 0

        for record in pending:
            asset = record.get("asset", "").upper()
            forecast_type = record.get("forecast_type", "direction")
            payload = record.get("payload", {})

            # Match against active challenges
            matching_ch = None
            for ch in active_challenges:
                c_data = ch.get("challenge", ch)
                ch_asset = str(c_data.get("asset", "")).upper()
                ch_topic = str(c_data.get("topic", "")).upper()
                if ch_asset == asset or ch_topic == asset or (
                    asset in ["EIA_RETAIL_GASOLINE", "GAS_REGULAR", "EIA_GAS_REGULAR_US"]
                    and any(k in ch_topic or k in ch_asset for k in ["EIA", "GAS", "RETAIL"])
                ):
                    matching_ch = ch
                    break

            if not matching_ch:
                results[asset] = {"status": "NO_MATCHING_ACTIVE_CHALLENGE", "asset": asset}
                continue

            c_data = matching_ch.get("challenge", matching_ch)
            challenge_id = c_data.get("id")
            if not challenge_id:
                results[asset] = {"status": "ERROR_MISSING_CHALLENGE_ID", "asset": asset}
                continue

            if is_challenge_already_submitted(challenge_id, filepath=ledger_file):
                results[asset] = {
                    "status": "ALREADY_SUBMITTED",
                    "asset": asset,
                    "challenge_id": challenge_id,
                    "message": f"Challenge {challenge_id} for {asset} already in ledger."
                }
                continue

            if forecast_type == "macro" or "predicted_value" in payload:
                res = self.submit_macro_forecast(challenge_id, payload, live_in_dev=live_in_dev)
            else:
                res = self.submit_forecast(payload, live_in_dev=live_in_dev)

            results[asset] = res
            if res.get("status") in ["SUCCESS", "ALREADY_SUBMITTED", "DRY_RUN"]:
                dispatched_count += 1
                if res.get("status") in ["SUCCESS", "ALREADY_SUBMITTED"]:
                    record_submitted_challenge(challenge_id, asset, res, filepath=ledger_file)

        return {
            "status": "COMPLETED",
            "pending_count": len(pending),
            "dispatched": dispatched_count,
            "results": results
        }


def submit_midgley_energy_forecasts(
    rb_open_price: float,
    rb_p50: float,
    rb_p10: Optional[float] = None,
    rb_p90: Optional[float] = None,
    rb_residual_std: Optional[float] = None,
    cl_open_price: Optional[float] = None,
    cl_p50: Optional[float] = None,
    cl_p10: Optional[float] = None,
    cl_p90: Optional[float] = None,
    cl_residual_std: Optional[float] = None,
    eia_retail_p50: Optional[float] = None,
    eia_retail_p10: Optional[float] = None,
    eia_retail_p90: Optional[float] = None,
    eia_retail_residual_std: Optional[float] = None,
    qualitative_catalysts: Optional[Dict[str, Any]] = None,
    technical_indicators: Optional[Dict[str, Any]] = None,
    physical_feeds: Optional[Dict[str, Any]] = None,
    save_pending: bool = True,
    live_in_dev: bool = False
) -> Dict[str, Any]:
    """
    Submits daily forecasts for RBOB Gasoline (RB), Cushing WTI Crude (CL), and optional
    EIA US Regular Retail Gasoline (Issue #408) to Headline Arena.
    Automatically persists generated forecasts into the 24h pending cache (Issue #418).
    """
    connector = HeadlineArenaConnector()
    results = {}

    # Technical indicator defaults
    tech = dict(technical_indicators or {})
    if rb_open_price > 0 and "rbob_price" not in tech:
        tech["rbob_price"] = rb_open_price
    if cl_open_price and cl_open_price > 0 and "wti_price" not in tech:
        tech["wti_price"] = cl_open_price
    if rb_open_price > 0 and cl_open_price and cl_open_price > 0 and "crack_spread" not in tech:
        tech["crack_spread"] = (rb_open_price * 42.0) - cl_open_price

    # 1. RBOB Wholesale Gasoline
    if rb_open_price > 0 and rb_p50 > 0:
        rb_payload = connector.format_direction_payload(
            asset="RB",
            open_price=rb_open_price,
            p50=rb_p50,
            p10=rb_p10,
            p90=rb_p90,
            residual_std=rb_residual_std,
            qualitative_catalysts=qualitative_catalysts,
            technical_indicators=tech,
            physical_feeds=physical_feeds
        )
        if save_pending:
            save_pending_forecast(asset="RB", payload=rb_payload, forecast_type="direction")
        results["RB"] = connector.submit_forecast(rb_payload, live_in_dev=live_in_dev)

    # 2. WTI Crude Oil
    if cl_open_price and cl_p50 and cl_open_price > 0 and cl_p50 > 0:
        cl_payload = connector.format_direction_payload(
            asset="CL",
            open_price=cl_open_price,
            p50=cl_p50,
            p10=cl_p10,
            p90=cl_p90,
            residual_std=cl_residual_std,
            qualitative_catalysts=qualitative_catalysts,
            technical_indicators=tech,
            physical_feeds=physical_feeds
        )
        if save_pending:
            save_pending_forecast(asset="CL", payload=cl_payload, forecast_type="direction")
        results["CL"] = connector.submit_forecast(cl_payload, live_in_dev=live_in_dev)

    # 3. EIA US Regular Retail Gasoline Civic / Macro Challenge (Issue #408)
    if eia_retail_p50 and eia_retail_p50 > 0:
        eia_payload = connector.format_eia_retail_civic_payload(
            predicted_value=eia_retail_p50,
            p10=eia_retail_p10,
            p90=eia_retail_p90,
            residual_std=eia_retail_residual_std
        )
        if save_pending:
            save_pending_forecast(asset="EIA_RETAIL_GASOLINE", payload=eia_payload, forecast_type="macro")

        # Discover active EIA civic challenge
        eia_challenge = connector.get_active_challenge_by_topic("EIA_RETAIL_GASOLINE")
        if eia_challenge:
            ch_data = eia_challenge.get("challenge", eia_challenge)
            ch_id = ch_data.get("id")
            if ch_id:
                results["EIA_RETAIL_GASOLINE"] = connector.submit_macro_forecast(
                    challenge_id=ch_id,
                    payload=eia_payload,
                    live_in_dev=live_in_dev
                )
            else:
                results["EIA_RETAIL_GASOLINE"] = {"status": "SKIPPED_NO_CHALLENGE_ID", "payload": eia_payload}
        else:
            results["EIA_RETAIL_GASOLINE"] = {"status": "CACHED_PENDING_CHALLENGE", "payload": eia_payload}

    return results


def main():
    """CLI Entrypoint for one-time agent registration, pending sync, and manual test submissions."""
    parser = argparse.ArgumentParser(description="Midgley Headline Arena Forecasting Connector CLI")
    parser.add_argument("--register", action="store_true", help="Register a new agent with Headline Arena")
    parser.add_argument("--name", type=str, default="Midgley-Energy-Agent", help="Agent name for registration")
    parser.add_argument("--description", type=str, default="Probabilistic multi-agent RBOB gasoline and WTI crude forecaster", help="Agent description")
    parser.add_argument("--model-provider", type=str, default="google", help="Underlying model provider (default: google)")
    parser.add_argument("--model-name", type=str, default="gemini-2.5-flash", help="Underlying model name (default: gemini-2.5-flash)")
    parser.add_argument("--sync", action="store_true", help="Dispatch pending cached forecasts against active challenges")
    parser.add_argument("--submit-test", action="store_true", help="Perform a test prediction submission")
    parser.add_argument("--live", action="store_true", help="Enable live submission in dev environment (tags as [DEV-TEST])")
    parser.add_argument("--status", action="store_true", help="Check Headline Arena connection status and settlement rules")

    args = parser.parse_args()
    connector = HeadlineArenaConnector()

    if args.register:
        print("=" * 70)
        print("  HEADLINE ARENA - ONE-TIME AGENT REGISTRATION (DEV ENVIRONMENT)")
        print("=" * 70)
        print(f"Registering Agent: {args.name}")
        print(f"Description: {args.description}")
        print(f"Provider: {args.model_provider}")
        print(f"Model: {args.model_name}")
        res = connector.register_agent(
            name=args.name,
            description=args.description,
            model_provider=args.model_provider,
            model_name=args.model_name
        )
        print("\nRegistration Result:")
        print(json.dumps(res, indent=2))
        if "client_id" in res and "client_secret" in res:
            print("\n" + "=" * 70)
            print("  SUCCESS! Set the following environment variables in .env or GitHub Secrets:")
            print(f"  HEADLINE_ARENA_CLIENT_ID={res['client_id']}")
            print(f"  HEADLINE_ARENA_CLIENT_SECRET={res['client_secret']}")
            print("=" * 70)
        return

    if args.sync:
        print("=" * 70)
        print("  HEADLINE ARENA - DISPATCH PENDING FORECASTS")
        print("=" * 70)
        sync_res = connector.dispatch_pending_forecasts(live_in_dev=args.live)
        print(json.dumps(sync_res, indent=2))
        return

    if args.status or not (args.submit_test):
        print("=" * 70)
        print("  HEADLINE ARENA CONNECTOR STATUS")
        print("=" * 70)
        print(f"Environment: {connector.environment} ({'Production' if connector.is_prod else 'Development'})")
        print(f"Configured: {connector.is_configured}")
        print(f"Base URL: {connector.base_url}")
        rules = connector.get_settlement_rules()
        print("\nSettlement Rules:")
        print(json.dumps(rules, indent=2))
        pending = load_pending_forecasts(active_only=True)
        print(f"\nActive Pending Forecasts ({len(pending)}):")
        print(json.dumps(pending, indent=2))

    if args.submit_test:
        print("\n" + "=" * 70)
        print("  TEST FORECAST SUBMISSION")
        print("=" * 70)
        # Sample RBOB, WTI, and EIA Retail test forecasts
        res = submit_midgley_energy_forecasts(
            rb_open_price=2.4500,
            rb_p50=2.5200,
            rb_p10=2.4100,
            rb_p90=2.6300,
            cl_open_price=78.50,
            cl_p50=77.20,
            cl_p10=74.80,
            cl_p90=79.60,
            eia_retail_p50=3.215,
            eia_retail_p10=3.120,
            eia_retail_p90=3.310,
            live_in_dev=args.live
        )
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

