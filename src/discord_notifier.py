"""
Discord Webhook Notification Engine (src/discord_notifier.py)

Dispatches rich real-time Discord alerts when an intraday forecast revision is triggered
by the multi-agent intraday monitoring workflow.
Features:
- Environment distinction (production vs dev)
- Comprehensive shock catalyst details (headline, source, URLs, target locales, impact scores)
- Color-coded severity thresholds
- Test suite suppression (TESTING=1) and non-blocking timeout protection
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_environment_label(environment: Optional[str] = None) -> str:
    """Resolves the current execution environment label ('prod' or 'dev')."""
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


def format_intraday_discord_payload(event_record: Dict[str, Any], environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Constructs a rich Discord Embed payload representing an intraday forecast revision event.
    """
    env_label = get_environment_label(environment)
    is_prod = (env_label == "prod")
    env_badge = "[PRODUCTION]" if is_prod else "[DEVELOPMENT]"
    env_display = "Production (GitHub Actions / Cloud)" if is_prod else "Development (Local / dev-vm)"

    headline = event_record.get("headline", "Intraday Anomaly Trigger")
    source = event_record.get("source", "Intraday_Monitor")
    url = event_record.get("url", "").strip()
    archive_url = event_record.get("archive_url", "").strip()
    target_locales = event_record.get("target_locales", ["National"])
    locales_str = ", ".join(target_locales) if isinstance(target_locales, list) else str(target_locales)

    scores = event_record.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}

    price_pressure = float(scores.get("overall_price_pressure", 0.0))
    supply_disruption = float(scores.get("supply_disruption", 0.0))
    geopolitical_risk = float(scores.get("geopolitical_risk", 0.0))
    opec_action = float(scores.get("opec_action", 0.0))

    # Color selection based on market impact:
    # 🔴 Red: High supply shock (>= 0.50) or severe price hike (>= +0.40)
    # 🟢 Green: Substantial downward price pressure (<= -0.20)
    # 🟠 Orange: General volatility shock / tariff / geopolitical disruption
    if supply_disruption >= 0.50 or price_pressure >= 0.40:
        color = 15158332  # #E74C3C
    elif price_pressure <= -0.20:
        color = 3066993   # #2ECC71
    else:
        color = 15105570  # #E67E22

    fields = [
        {
            "name": "🌐 Environment",
            "value": f"`{env_display}`",
            "inline": True
        },
        {
            "name": "📡 Ingestion Source",
            "value": f"`{source}`",
            "inline": True
        },
        {
            "name": "📍 Target Metro Hubs",
            "value": f"`{locales_str}`",
            "inline": True
        },
        {
            "name": "📊 Price Pressure (ΔP)",
            "value": f"`{price_pressure:+.2f}/gal`",
            "inline": True
        },
        {
            "name": "🛢️ Supply Disruption (S)",
            "value": f"`{supply_disruption:.2f}`",
            "inline": True
        },
        {
            "name": "🌍 Geopolitical Risk (G)",
            "value": f"`{geopolitical_risk:.2f}`",
            "inline": True
        }
    ]

    if opec_action != 0.0:
        fields.append({
            "name": "🏛️ OPEC Action",
            "value": f"`{opec_action:+.2f}`",
            "inline": True
        })

    # Add source links if available
    links = []
    if url:
        links.append(f"[Original Article]({url})")
    if archive_url:
        links.append(f"[Wayback Machine Archive]({archive_url})")

    if links:
        fields.append({
            "name": "🔗 Intelligence Sources",
            "value": " • ".join(links),
            "inline": False
        })

    embed = {
        "title": f"🚨 {env_badge} Intraday Gas Price Forecast Revision",
        "description": f"**Trigger Catalyst:**\n> *\"{headline}\"*",
        "url": "https://koshiirra.github.io/midgley/",
        "color": color,
        "fields": fields,
        "footer": {
            "text": "Midgley Energy Complex Forecasting • Automated Intraday Anomaly Gateway"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    return {
        "username": "Midgley Intraday Monitor",
        "embeds": [embed]
    }


def send_intraday_discord_notification(
    event_record: Dict[str, Any],
    webhook_url: Optional[str] = None,
    environment: Optional[str] = None
) -> bool:
    """
    Dispatches a Discord webhook notification for an intraday forecast revision.
    
    Args:
        event_record: Dictionary containing headline, source, scores, target_locales, url, etc.
        webhook_url: Target Discord webhook URL (defaults to env vars DISCORD_INTRADAY_WEBHOOK_URL / DISCORD_WEBHOOK_URL).
        environment: Explicit environment override ('prod' or 'dev').
        
    Returns:
        bool: True if dispatched successfully or suppressed during test runs, False on error.
    """
    if webhook_url is None:
        webhook_url = os.environ.get("DISCORD_INTRADAY_WEBHOOK_URL") or os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.info("No Discord webhook URL configured (DISCORD_INTRADAY_WEBHOOK_URL unset); skipping notification.")
        return False

    # Unit testing suppression unless test dispatch is explicitly enabled
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_WEBHOOK_DISPATCH"):
        logger.info("TESTING=1: Suppressed Discord webhook notification HTTP POST.")
        return True

    payload = format_intraday_discord_payload(event_record, environment=environment)

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Midgley-Intraday-Notifier/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_ok = resp.status in (200, 204)
            if status_ok:
                logger.info(f"Successfully dispatched intraday Discord notification to webhook (HTTP {resp.status})")
            else:
                logger.warning(f"Discord webhook responded with unexpected status HTTP {resp.status}")
            return status_ok
    except Exception as e:
        logger.warning(f"Failed to dispatch intraday Discord webhook notification: {e}")
        return False
