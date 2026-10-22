"""
Discord Webhook & Direct Message Notification Engine (src/discord_notifier.py)

Dispatches rich real-time Discord alerts when an intraday forecast revision is triggered
by the multi-agent intraday monitoring workflow, and manages multi-subscriber webhook
and Direct Message (DM) subscriptions (Issues #234, #235).

Features:
- Environment distinction (production vs dev)
- Comprehensive shock catalyst details (headline, source, URLs, target locales, impact scores)
- Color-coded severity thresholds
- Multi-subscriber registry (SQLite / Turso / Cloudflare D1) supporting both Incoming Webhooks
  and personal Discord Direct Message (`discord_dm`) subscriptions
- Fernet / HMAC-authenticated encryption at rest for stored webhook URLs
- Locale, minimum shock threshold, directional bias, and catalyst domain filtering
- Automatic circuit breaker (3 max failures, immediate deactivation on HTTP 404/410 or 50007 DM block)
- Test suite suppression (TESTING=1) and non-blocking timeout protection
"""

import os
import re
import json
import time
import hmac
import base64
import hashlib
import secrets
import sqlite3
import logging
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

# Valid Discord Incoming Webhook URL pattern
DISCORD_WEBHOOK_REGEX = re.compile(
    r"^https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/([0-9]+)/([A-Za-z0-9_-]+)(?:\?.*)?$"
)

# Canonical regional metro hub normalization map for subscription filtering
CANONICAL_LOCALE_ALIASES: Dict[str, str] = {
    "national": "National",
    "us": "National",
    "all": "National",
    "tulsa": "Tulsa",
    "tulsa_ok": "Tulsa",
    "newark": "Newark",
    "newark_de": "Newark",
    "cincinnati": "Cincinnati",
    "cincinnati_oh": "Cincinnati",
    "cincinnati_ky": "Cincinnati",
    "greenville": "Greenville",
    "greenville_nc": "Greenville",
    "charlotte": "Charlotte",
    "charlotte_nc": "Charlotte",
    "clt": "Charlotte",
    "oakland": "Oakland",
    "oakland_ca": "Oakland",
    "bay_area": "Oakland",
    "bayarea": "Oakland",
    "bayarea_ca": "Oakland",
    "sf": "Oakland",
    "san_francisco": "Oakland",
    "sanfrancisco_ca": "Oakland",
    "sanjose": "Oakland",
    "sanjose_ca": "Oakland",
    "port_st_lucie": "Port_St_Lucie",
    "port_st_lucie_fl": "Port_St_Lucie",
    "psl": "Port_St_Lucie",
    "chicago": "Chicago",
    "chicago_il": "Chicago",
    "chi": "Chicago",
    "houston": "Houston",
    "houston_tx": "Houston",
    "hou": "Houston",
    "los_angeles": "Los_Angeles",
    "los_angeles_ca": "Los_Angeles",
    "la": "Los_Angeles",
    "la_basin": "Los_Angeles",
    "socal": "Los_Angeles",
    "denver": "Denver",
    "denver_co": "Denver",
    "rocky_mountain": "Denver",
    "padd4": "Denver",
    "padd_4": "Denver",
    "new_york": "New_York",
    "new_york_ny": "New_York",
    "nyc": "New_York",
    "ny": "New_York",
    "ny_harbor": "New_York",
    "ny_state": "New_York",
    "new_york_metro": "New_York",
    "seattle": "Seattle",
    "seattle_wa": "Seattle",
    "puget_sound": "Seattle",
    "pnw": "Seattle",
    "sea": "Seattle",
    "phoenix": "Phoenix",
    "phoenix_az": "Phoenix",
    "phx": "Phoenix",
    "desert_southwest": "Phoenix",
    "anchorage": "Anchorage",
    "anchorage_ak": "Anchorage",
    "anc": "Anchorage",
    "alaska": "Anchorage",
    "honolulu": "Honolulu",
    "honolulu_hi": "Honolulu",
    "hnl": "Honolulu",
    "hawaii": "Honolulu",
    "oahu": "Honolulu",
    "guam": "Guam",
    "guam_gu": "Guam",
    "gu": "Guam",
    "hagatna": "Guam",
    "apra_harbor": "Guam",
    "san_juan": "San_Juan",
    "san_juan_pr": "San_Juan",
    "puerto_rico": "San_Juan",
    "pr": "San_Juan",
    "sju": "San_Juan",
    "boston": "Boston",
    "boston_ma": "Boston",
    "bos": "Boston",
    "new_england": "Boston",
}

SUPPORTED_LOCALES = [
    "National",
    "Tulsa",
    "Newark",
    "Cincinnati",
    "Greenville",
    "Charlotte",
    "Oakland",
    "Port_St_Lucie",
    "Chicago",
    "Houston",
    "Los_Angeles",
    "Denver",
    "New_York",
    "Seattle",
    "Phoenix",
    "Anchorage",
    "Honolulu",
    "Guam",
    "San_Juan",
    "Boston",
]

VALID_DIRECTION_FILTERS = {"all_shocks", "spikes_only", "drops_only"}
VALID_CATALYST_DOMAINS = {
    "refinery_pipeline",
    "weather_hurricane",
    "geopolitical_opec",
    "regulatory_tax",
}
VALID_DELIVERY_TYPES = {"webhook", "discord_dm"}
VALID_DELIVERY_MODES = {"realtime", "daily_digest"}
MAX_DISPATCH_FAILURES = 3


def normalize_locale_name(locale_str: str) -> Optional[str]:
    """Normalizes a user-supplied locale string to its canonical subscription hub name."""
    if not locale_str or not isinstance(locale_str, str):
        return None
    cleaned = locale_str.strip().lower().replace(" ", "_").replace(".", "").replace("-", "_")
    if cleaned in CANONICAL_LOCALE_ALIASES:
        return CANONICAL_LOCALE_ALIASES[cleaned]
    for canonical in SUPPORTED_LOCALES:
        if canonical.lower() == cleaned:
            return canonical
    return None


def normalize_locale_list(locales: Optional[List[str]]) -> List[str]:
    """Normalizes and deduplicates a list of target locales, defaulting to ['National'] if empty."""
    if not locales:
        return ["National"]
    normalized: List[str] = []
    for item in locales:
        canon = normalize_locale_name(item)
        if canon and canon not in normalized:
            normalized.append(canon)
    return normalized


def _looks_like_zip_code(val: str) -> bool:
    """Returns True if `val` is a 3-to-5 digit US ZIP code or ZIP+4 string."""
    if not val or not isinstance(val, str):
        return False
    base = val.strip().split("-")[0].strip()
    return base.isdigit() and 3 <= len(base) <= 5


def resolve_subscription_locales_and_zips(
    target_locales: Optional[List[str]] = None,
    zip_codes: Optional[List[str]] = None,
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    """
    Resolves both named metro/PADD locales and 5-digit US ZIP codes (passed either in
    `target_locales` or `zip_codes`). Out-of-metro ZIPs automatically update the
    unmapped ZIP telemetry heatmap via `resolve_zip_code()`.
    """
    from src.zip_geocoding import resolve_zip_code

    normalized_locales: List[str] = []
    normalized_zips: List[str] = []
    zip_resolutions: List[Dict[str, Any]] = []

    raw_items: List[str] = []
    if target_locales:
        raw_items.extend(str(x).strip() for x in target_locales if x is not None and str(x).strip())

    raw_zips: List[str] = []
    if zip_codes:
        raw_zips.extend(str(z).strip() for z in zip_codes if z is not None and str(z).strip())

    for item in raw_items:
        if _looks_like_zip_code(item):
            raw_zips.append(item)
        else:
            canon = normalize_locale_name(item)
            if canon and canon not in normalized_locales:
                normalized_locales.append(canon)

    for z_item in raw_zips:
        res = resolve_zip_code(z_item)
        if res.get("resolution_tier") == "INVALID_INPUT_FALLBACK":
            continue
        clean_zip = str(res.get("zip_code") or "").strip()
        if clean_zip and clean_zip not in normalized_zips:
            normalized_zips.append(clean_zip)
            zip_resolutions.append(res)
        canon_hub = normalize_locale_name(str(res.get("locale_code") or "National"))
        if canon_hub and canon_hub not in normalized_locales:
            normalized_locales.append(canon_hub)

    return normalized_locales, normalized_zips, zip_resolutions



def validate_discord_webhook_url(webhook_url: Optional[str]) -> bool:
    """Validates that a URL is a well-formed HTTPS Discord Incoming Webhook URL."""
    if not webhook_url or not isinstance(webhook_url, str):
        return False
    try:
        parsed = urllib.parse.urlparse(webhook_url.strip())
        if parsed.scheme != "https":
            return False
        hostname = (parsed.hostname or "").lower()
        if hostname not in ("discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"):
            return False
        return bool(DISCORD_WEBHOOK_REGEX.match(webhook_url.strip()))
    except Exception:
        return False


def _get_encryption_secret() -> bytes:
    """Derives a 32-byte key from MIDGLEY_WEBHOOK_SECRET or fallback environment secret."""
    raw_secret = (
        os.environ.get("MIDGLEY_WEBHOOK_SECRET")
        or os.environ.get("MIDGLEY_ADMIN_SECRET")
        or os.environ.get("FLAG_SIGNING_KEY")
        or "midgley-default-local-webhook-encryption-key-v1"
    )
    return hashlib.sha256(raw_secret.encode("utf-8")).digest()


def encrypt_webhook_url(webhook_url: str) -> str:
    """
    Encrypts a Discord webhook URL at rest using cryptography.fernet if installed,
    or falls back to HMAC-SHA256 authenticated stream cipher (CTR-like keystream + MAC).
    """
    if not webhook_url:
        return ""
    key_32 = _get_encryption_secret()
    try:
        from cryptography.fernet import Fernet
        fernet_key = base64.urlsafe_b64encode(key_32)
        f = Fernet(fernet_key)
        token = f.encrypt(webhook_url.encode("utf-8")).decode("utf-8")
        return f"fernet:{token}"
    except Exception:
        nonce = secrets.token_bytes(16)
        plaintext = webhook_url.encode("utf-8")
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(plaintext):
            block = hmac.new(key_32, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
            keystream.extend(block)
            counter += 1
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream[: len(plaintext)]))
        mac = hmac.new(key_32, b"hmac_v1|" + nonce + ciphertext, hashlib.sha256).digest()[:16]
        blob = base64.urlsafe_b64encode(nonce + mac + ciphertext).decode("utf-8")
        return f"hmac_v1:{blob}"


def decrypt_webhook_url(encrypted_value: str) -> str:
    """Decrypts an encrypted Discord webhook URL stored in the subscription registry."""
    if not encrypted_value:
        return ""
    key_32 = _get_encryption_secret()
    if encrypted_value.startswith("fernet:"):
        token = encrypted_value[len("fernet:") :]
        from cryptography.fernet import Fernet
        fernet_key = base64.urlsafe_b64encode(key_32)
        f = Fernet(fernet_key)
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    elif encrypted_value.startswith("hmac_v1:"):
        blob = base64.urlsafe_b64decode(encrypted_value[len("hmac_v1:") :].encode("utf-8"))
        nonce = blob[:16]
        mac = blob[16:32]
        ciphertext = blob[32:]
        expected_mac = hmac.new(key_32, b"hmac_v1|" + nonce + ciphertext, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("Webhook URL decryption failed: HMAC authentication mismatch.")
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(ciphertext):
            block = hmac.new(key_32, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
            keystream.extend(block)
            counter += 1
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream[: len(ciphertext)]))
        return plaintext.decode("utf-8")
    raise ValueError("Unsupported encrypted webhook format.")


def infer_event_catalyst_domains(event_record: Dict[str, Any]) -> List[str]:
    """Classifies an intraday anomaly record into one or more catalyst domain tags."""
    headline = str(event_record.get("headline", "")).lower()
    scores = event_record.get("scores", {}) if isinstance(event_record.get("scores"), dict) else {}
    supply = float(scores.get("supply_disruption", 0.0))
    geopol = float(scores.get("geopolitical_risk", 0.0))
    opec = float(scores.get("opec_action", 0.0))

    domains = set()
    if any(k in headline for k in ("hurricane", "tropical", "tornado", "freeze", "storm", "weather", "flood", "nhc")):
        domains.add("weather_hurricane")
    if any(k in headline for k in ("tax", "excise", "carb", "lcfs", "epa", "rvp", "waiver", "regulatory", "cap-and-trade")):
        domains.add("regulatory_tax")
    if opec != 0.0 or geopol >= 0.30 or any(
        k in headline for k in ("opec", "tariff", "sanction", "hormuz", "embargo", "missile", "tanker", "war", "geopolitical")
    ):
        domains.add("geopolitical_opec")
    if supply >= 0.25 or any(
        k in headline for k in ("refinery", "pipeline", "outage", "explosion", "fire", "fcc", "cdu", "colonial", "shut", "halt", "8-k")
    ):
        domains.add("refinery_pipeline")

    if not domains:
        domains.add("refinery_pipeline")
    return sorted(domains)


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


def format_intraday_discord_payload(
    event_record: Dict[str, Any],
    environment: Optional[str] = None,
    include_components: Optional[bool] = None,
    role_mention: Optional[str] = None
) -> Dict[str, Any]:
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

    event_hash = event_record.get("hash")
    if not event_hash:
        event_hash = hashlib.sha256(headline.encode("utf-8", errors="ignore")).hexdigest()[:16]

    safe_headline_param = (headline[:120] + "...") if len(headline) > 120 else headline
    safe_url_param = (url[:200] + "...") if len(url) > 200 else url

    signing_secret = (
        os.getenv("FLAG_SIGNING_KEY")
        or os.getenv("ADMIN_TOKEN")
        or os.getenv("CLOUDFLARE_AUTH_TOKEN")
        or ""
    )
    exp_time = int(time.time()) + (72 * 3600)  # 72 hours validity
    sig_param = ""
    if signing_secret:
        headline_hash = hashlib.sha256(safe_headline_param.encode("utf-8", errors="ignore")).hexdigest()[:16]
        msg = f"flag_fp:v2|{event_hash}|{headline_hash}|{exp_time}".encode("utf-8")
        sig_param = hmac.new(signing_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:32]
    else:
        logger.warning(
            "Neither FLAG_SIGNING_KEY, ADMIN_TOKEN, nor CLOUDFLARE_AUTH_TOKEN is configured in environment. "
            "Discord flag link will be generated without HMAC signature and will be rejected by Cloudflare Worker."
        )
    flag_params = urllib.parse.urlencode({
        "id": event_hash,
        "exp": str(exp_time),
        "sig": sig_param,
        "headline": safe_headline_param,
        "source": source,
        "p": f"{price_pressure:+.2f}",
        "s": f"{supply_disruption:.2f}",
        "g": f"{geopolitical_risk:.2f}",
        "url": safe_url_param
    })
    flag_url = f"https://midgley-intraday-monitor.m-cubed-3.workers.dev/flag?{flag_params}"
    tracking_url = "https://github.com/KoshiirRa/midgley/issues/258"

    fields.append({
        "name": "🚩 Feedback & Review",
        "value": f"[🚩 Flag False Positive]({flag_url}) • [📋 Tracking Thread #258]({tracking_url})",
        "inline": False
    })

    # Strict Discord embed character limit sanitization (max 256 for title/field names, 1024 for field values)
    sanitized_fields = []
    for f in fields:
        fname = str(f.get("name", ""))
        fval = str(f.get("value", ""))
        if len(fname) > 256:
            fname = fname[:253] + "..."
        if len(fval) > 1024:
            fval = fval[:1020] + "..."
        sanitized_fields.append({
            "name": fname,
            "value": fval,
            "inline": bool(f.get("inline", True))
        })

    safe_title = f"🚨 {env_badge} Intraday Gas Price Forecast Revision"
    if len(safe_title) > 256:
        safe_title = safe_title[:253] + "..."

    safe_desc = f"**Trigger Catalyst:**\n> *\"{headline}\"*"
    if len(safe_desc) > 4096:
        safe_desc = safe_desc[:4090] + "...\"*"

    embed = {
        "title": safe_title,
        "description": safe_desc,
        "url": "https://koshiirRa.github.io/midgley/",
        "color": color,
        "fields": sanitized_fields,
        "footer": {
            "text": f"Midgley Energy Complex Forecasting • Anomaly ID: {event_hash}"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload: Dict[str, Any] = {
        "username": "Midgley Intraday Monitor",
        "embeds": [embed]
    }

    # Optional role/user mention escalation on high-severity shocks (S >= 0.80 or |ΔP| >= 0.50)
    if role_mention and (supply_disruption >= 0.80 or abs(price_pressure) >= 0.50):
        payload["content"] = f"🚨 **High-Severity Energy Shock Alert** {role_mention.strip()}"

    # Top-level interactive Action Row buttons are only attached when explicitly requested
    # (e.g. Discord Bot Applications). Standard incoming Discord webhooks reject top-level components with HTTP 400.
    if include_components is None:
        include_components = os.environ.get("DISCORD_INCLUDE_COMPONENTS", "0").lower() in ("1", "true")

    if include_components:
        components = [
            {
                "type": 1,  # Action Row
                "components": [
                    {
                        "type": 2,  # Button
                        "style": 5,  # Link button
                        "label": "🚩 Flag False Positive",
                        "url": flag_url
                    },
                    {
                        "type": 2,  # Button
                        "style": 5,  # Link button
                        "label": "📋 Tracking Thread #258",
                        "url": tracking_url
                    }
                ]
            }
        ]
        payload["components"] = components

    return payload


def create_discord_dm_channel(discord_user_id: str, bot_token: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Opens or retrieves a Discord Direct Message (DM) channel with `discord_user_id`
    via `POST https://discord.com/api/v10/users/@me/channels`.

    Returns:
        Tuple[Optional[str], Optional[str]]: (dm_channel_id, error_message)
    """
    if not discord_user_id or not str(discord_user_id).strip().isdigit():
        return None, "Invalid Discord user snowflake ID (must be numeric string)."

    clean_user_id = str(discord_user_id).strip()
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_WEBHOOK_DISPATCH"):
        return f"dm_test_{clean_user_id}", None

    token = (bot_token or os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    if not token:
        return None, "DISCORD_BOT_TOKEN is not configured on the server."

    url = "https://discord.com/api/v10/users/@me/channels"
    body = json.dumps({"recipient_id": clean_user_id}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "Midgley-Intraday-Notifier/1.0"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            channel_id = data.get("id")
            if channel_id:
                return str(channel_id), None
            return None, "Discord API response did not contain a DM channel ID."
    except urllib.error.HTTPError as he:
        err_body = ""
        try:
            err_body = he.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return None, f"Discord DM channel creation failed (HTTP {he.code}): {err_body or he.reason}"
    except Exception as e:
        return None, f"Discord DM channel creation error: {e}"


def send_discord_dm_payload(
    payload: Dict[str, Any],
    discord_user_id: Optional[str] = None,
    dm_channel_id: Optional[str] = None,
    bot_token: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[int], Optional[str]]:
    """
    Sends a Discord message payload to a user's Direct Message channel using `DISCORD_BOT_TOKEN`.

    Returns:
        Tuple[bool, Optional[str], Optional[int], Optional[str]]:
        (success, resolved_dm_channel_id, http_status, error_message)
    """
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_WEBHOOK_DISPATCH"):
        resolved_ch = dm_channel_id or (f"dm_test_{discord_user_id}" if discord_user_id else "dm_test_channel")
        return True, resolved_ch, 200, None

    token = (bot_token or os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    if not token:
        return False, dm_channel_id, None, "DISCORD_BOT_TOKEN is not configured."

    resolved_channel_id = (dm_channel_id or "").strip()
    if not resolved_channel_id:
        if not discord_user_id:
            return False, None, None, "Either dm_channel_id or discord_user_id is required."
        resolved_channel_id, err = create_discord_dm_channel(discord_user_id, bot_token=token)
        if not resolved_channel_id:
            return False, None, None, err

    # Discord Bot API POST /channels/{id}/messages does not accept webhook-only 'username' top-level field
    bot_payload = {k: v for k, v in payload.items() if k != "username"}
    url = f"https://discord.com/api/v10/channels/{resolved_channel_id}/messages"
    data_bytes = json.dumps(bot_payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "Midgley-Intraday-Notifier/1.0"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            return status in (200, 201, 204), resolved_channel_id, status, None
    except urllib.error.HTTPError as he:
        err_body = ""
        try:
            err_body = he.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return False, resolved_channel_id, he.code, f"HTTP {he.code}: {err_body or he.reason}"
    except Exception as e:
        return False, resolved_channel_id, None, str(e)


def format_welcome_verification_payload(
    target_locales: List[str],
    min_shock_threshold: float,
    direction_filter: str = "all_shocks",
    delivery_type: str = "webhook",
    client_label: Optional[str] = None,
    subscription_id: Optional[str] = None,
    zip_codes: Optional[List[str]] = None,
    zip_resolutions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Formats a handshake/welcome verification embed sent upon subscription registration or test."""
    locales_str = ", ".join(target_locales) if target_locales else "National"
    delivery_badge = "💬 Direct Message (Private DM)" if delivery_type == "discord_dm" else "🪝 Channel Incoming Webhook"
    embed = {
        "title": "✅ Midgley Intraday Alert Subscription Verified",
        "description": (
            "Your Discord alert subscription has been registered and verified. "
            "You will receive real-time notifications when intraday forecast revisions match your filters."
        ),
        "url": "https://koshiirRa.github.io/midgley/",
        "color": 3066993,  # #2ECC71 Green
        "fields": [
            {"name": "📡 Delivery Mode", "value": f"`{delivery_badge}`", "inline": True},
            {"name": "📍 Subscribed Hubs", "value": f"`{locales_str}`", "inline": True},
            {"name": "⚡ Shock Threshold (|ΔP|)", "value": f"`>= ${min_shock_threshold:.2f}/gal`", "inline": True},
            {"name": "🧭 Direction Filter", "value": f"`{direction_filter}`", "inline": True},
        ],
        "footer": {
            "text": f"Midgley Notification Gateway • Subscription ID: {subscription_id or 'test-handshake'}"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if zip_resolutions:
        zip_lines = []
        departure_warnings = []
        tracking_issues = []
        for zr in zip_resolutions[:5]:
            zc = zr.get("zip_code", "")
            loc_name = zr.get("location_name") or f"ZIP {zc}"
            st = zr.get("state", "US")
            padd = zr.get("padd_region", "PADD 2")
            hub = normalize_locale_name(str(zr.get("locale_code") or "National")) or "National"
            tax = float(zr.get("state_tax_rate_per_gal", 0.25))
            hub_tax = float(zr.get("hub_baseline_tax_rate", 0.25))
            tax_delta = float(zr.get("tax_delta_per_gal", 0.0))
            is_dep = bool(zr.get("is_significant_departure"))
            tier_badge = "Direct Metro Cluster" if zr.get("is_metro_cluster_hit") else f"{padd} Corridor Fallback"
            
            tax_note = f"State Tax: `${tax:.3f}/gal`"
            if tax_delta != 0:
                tax_note += f" (Hub Base: `${hub_tax:.3f}/gal` • Wedge: `${tax_delta:+.3f}/gal`)"
            
            zip_lines.append(f"**{loc_name}** (`{zc}` {st} • {tier_badge} → `{hub}` | {tax_note})")
            
            if is_dep:
                est_basis = float(zr.get("estimated_basis_delta", tax_delta))
                departure_warnings.append(
                    f"State fuel taxes in **{st}** (`${tax:.3f}/gal`) depart from `{hub}` coastal rack base (`${hub_tax:.3f}/gal`) by `{tax_delta:+.3f}/gal`. "
                    f"Retail pump prices trade at an estimated `{est_basis:+.2f}/gal` basis differential over coastal rack benchmarks due to state taxes and regional distribution logistics. Shocks (|ΔP|) will track wholesale transmission from `{padd}`."
                )
            if zr.get("tracking_issue_number"):
                tracking_issues.append(f"[#{zr.get('tracking_issue_number')}](https://github.com/KoshiirRa/midgley/issues/{zr.get('tracking_issue_number')})")

        embed["fields"].append({
            "name": "📮 Subscribed ZIP Code Routing",
            "value": "\n".join(zip_lines),
            "inline": False,
        })
        if departure_warnings:
            embed["fields"].append({
                "name": "⚠️ Regional Basis & Tax Departure",
                "value": "\n\n".join(departure_warnings),
                "inline": False
            })
        if tracking_issues:
            embed["fields"].append({
                "name": "🏛️ Regional Calibration Hub Tracking",
                "value": f"A dedicated calibration hub tracking issue is open on the Midgley repository: {', '.join(tracking_issues)}",
                "inline": False
            })
    elif zip_codes:
        embed["fields"].append({
            "name": "📮 Subscribed ZIP Codes",
            "value": f"`{', '.join(zip_codes)}`",
            "inline": True,
        })
    if client_label:
        embed["fields"].append({"name": "🏷️ Client Label", "value": f"`{client_label}`", "inline": True})
    return {
        "username": "Midgley Intraday Monitor",
        "embeds": [embed]
    }


class DiscordSubscriptionRegistry:
    """
    Persistent registry for multi-subscriber Discord Webhook and Direct Message (DM)
    alert subscriptions (Issue #235).
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("MIDGLEY_SUBSCRIBERS_DB_PATH") or os.path.join("data", "subscribers.sqlite")
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_schema(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discord_subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    delivery_type TEXT NOT NULL DEFAULT 'webhook',
                    webhook_url_hash TEXT,
                    encrypted_webhook_url TEXT,
                    discord_user_id TEXT,
                    dm_channel_id TEXT,
                    target_locales TEXT NOT NULL,
                    zip_codes TEXT NOT NULL DEFAULT '[]',
                    min_shock_threshold REAL DEFAULT 0.25,
                    direction_filter TEXT NOT NULL DEFAULT 'all_shocks',
                    catalyst_domains TEXT,
                    delivery_mode TEXT NOT NULL DEFAULT 'realtime',
                    role_mention TEXT,
                    client_label TEXT,
                    manage_token_hash TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    muted_until TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_notified_at TEXT,
                    failure_count INTEGER DEFAULT 0
                )
            """)
            try:
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(discord_subscriptions)").fetchall()]
                if "zip_codes" not in cols:
                    conn.execute("ALTER TABLE discord_subscriptions ADD COLUMN zip_codes TEXT NOT NULL DEFAULT '[]';")
            except Exception:
                pass
            conn.execute("CREATE INDEX IF NOT EXISTS idx_discord_subs_active ON discord_subscriptions (is_active, delivery_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_discord_subs_webhook_hash ON discord_subscriptions (webhook_url_hash);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_discord_subs_user_id ON discord_subscriptions (discord_user_id);")
            conn.commit()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def register_subscription(
        self,
        target_locales: Optional[List[str]] = None,
        minimum_shock_threshold: float = 0.25,
        delivery_type: str = "webhook",
        webhook_url: Optional[str] = None,
        discord_user_id: Optional[str] = None,
        dm_channel_id: Optional[str] = None,
        direction_filter: str = "all_shocks",
        catalyst_domains: Optional[List[str]] = None,
        delivery_mode: str = "realtime",
        role_mention: Optional[str] = None,
        client_label: Optional[str] = None,
        verify_handshake: bool = True,
        zip_codes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Registers or updates a Discord webhook or DM alert subscription.
        Supports both regional metro/PADD hub names and 5-digit US ZIP codes.
        Out-of-metro ZIP codes automatically update the unmapped ZIP query heatmap.
        Returns subscription metadata including `subscription_id` and `manage_token`.
        """
        delivery_type_norm = (delivery_type or "webhook").strip().lower()
        if delivery_type_norm not in VALID_DELIVERY_TYPES:
            raise ValueError(f"Invalid delivery_type '{delivery_type}'. Must be one of {sorted(VALID_DELIVERY_TYPES)}.")

        if not target_locales and not zip_codes:
            locales_norm = ["National"]
            zips_norm: List[str] = []
            zip_resolutions: List[Dict[str, Any]] = []
        else:
            locales_norm, zips_norm, zip_resolutions = resolve_subscription_locales_and_zips(
                target_locales=target_locales,
                zip_codes=zip_codes,
            )
            if not locales_norm:
                raise ValueError("At least one valid target locale or 5-digit US ZIP code is required.")

        threshold_val = max(0.0, min(5.0, float(minimum_shock_threshold)))
        dir_norm = (direction_filter or "all_shocks").strip().lower()
        if dir_norm not in VALID_DIRECTION_FILTERS:
            raise ValueError(f"Invalid direction_filter '{direction_filter}'. Must be one of {sorted(VALID_DIRECTION_FILTERS)}.")

        mode_norm = (delivery_mode or "realtime").strip().lower()
        if mode_norm not in VALID_DELIVERY_MODES:
            raise ValueError(f"Invalid delivery_mode '{delivery_mode}'. Must be one of {sorted(VALID_DELIVERY_MODES)}.")

        domains_norm: Optional[List[str]] = None
        if catalyst_domains:
            domains_norm = [d.strip().lower() for d in catalyst_domains if d and d.strip().lower() in VALID_CATALYST_DOMAINS]
            if not domains_norm:
                raise ValueError(f"Invalid catalyst_domains. Supported domains: {sorted(VALID_CATALYST_DOMAINS)}.")

        webhook_hash: Optional[str] = None
        encrypted_url: Optional[str] = None
        clean_user_id: Optional[str] = None
        resolved_dm_channel: Optional[str] = dm_channel_id

        if delivery_type_norm == "webhook":
            if not validate_discord_webhook_url(webhook_url):
                raise ValueError("Invalid Discord webhook URL. Must match https://discord.com/api/webhooks/{id}/{token}.")
            clean_url = webhook_url.strip()
            webhook_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
            encrypted_url = encrypt_webhook_url(clean_url)
        else:
            if not discord_user_id or not str(discord_user_id).strip().isdigit():
                raise ValueError("Valid numeric discord_user_id is required when delivery_type is 'discord_dm'.")
            clean_user_id = str(discord_user_id).strip()

        sub_id = f"sub_{secrets.token_hex(8)}"
        manage_token = f"mgt_{secrets.token_urlsafe(24)}"
        manage_token_hash = self._hash_token(manage_token)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_conn() as conn:
            existing = None
            if delivery_type_norm == "webhook" and webhook_hash:
                existing = conn.execute(
                    "SELECT subscription_id FROM discord_subscriptions WHERE webhook_url_hash = ?",
                    (webhook_hash,)
                ).fetchone()
            elif delivery_type_norm == "discord_dm" and clean_user_id:
                existing = conn.execute(
                    "SELECT subscription_id, dm_channel_id FROM discord_subscriptions WHERE discord_user_id = ? AND delivery_type = 'discord_dm'",
                    (clean_user_id,)
                ).fetchone()

            if existing:
                sub_id = existing["subscription_id"]
                if delivery_type_norm == "discord_dm" and not resolved_dm_channel:
                    resolved_dm_channel = existing["dm_channel_id"]

        # Optional handshake verification ping
        handshake_sent = False
        if verify_handshake:
            welcome_payload = format_welcome_verification_payload(
                target_locales=locales_norm,
                min_shock_threshold=threshold_val,
                direction_filter=dir_norm,
                delivery_type=delivery_type_norm,
                client_label=client_label,
                subscription_id=sub_id,
                zip_codes=zips_norm,
                zip_resolutions=zip_resolutions,
            )
            if delivery_type_norm == "webhook" and webhook_url:
                ok, status, err = _post_webhook_payload(webhook_url.strip(), welcome_payload)
                if not ok:
                    raise RuntimeError(f"Webhook handshake verification failed: {err or f'HTTP {status}'}")
                handshake_sent = True
            elif delivery_type_norm == "discord_dm" and clean_user_id:
                ok, ch_id, status, err = send_discord_dm_payload(
                    welcome_payload,
                    discord_user_id=clean_user_id,
                    dm_channel_id=resolved_dm_channel
                )
                if not ok:
                    raise RuntimeError(f"Discord DM handshake verification failed: {err or f'HTTP {status}'}")
                resolved_dm_channel = ch_id or resolved_dm_channel
                handshake_sent = True

        with self._get_conn() as conn:
            if existing:
                conn.execute(
                    """
                    UPDATE discord_subscriptions
                    SET delivery_type = ?,
                        webhook_url_hash = ?,
                        encrypted_webhook_url = ?,
                        discord_user_id = ?,
                        dm_channel_id = ?,
                        target_locales = ?,
                        zip_codes = ?,
                        min_shock_threshold = ?,
                        direction_filter = ?,
                        catalyst_domains = ?,
                        delivery_mode = ?,
                        role_mention = ?,
                        client_label = ?,
                        manage_token_hash = ?,
                        is_active = 1,
                        muted_until = NULL,
                        failure_count = 0
                    WHERE subscription_id = ?
                    """,
                    (
                        delivery_type_norm,
                        webhook_hash,
                        encrypted_url,
                        clean_user_id,
                        resolved_dm_channel,
                        json.dumps(locales_norm),
                        json.dumps(zips_norm),
                        threshold_val,
                        dir_norm,
                        json.dumps(domains_norm) if domains_norm else None,
                        mode_norm,
                        role_mention,
                        client_label,
                        manage_token_hash,
                        sub_id,
                    )
                )
            else:
                conn.execute(
                    """
                    INSERT INTO discord_subscriptions (
                        subscription_id, delivery_type, webhook_url_hash, encrypted_webhook_url,
                        discord_user_id, dm_channel_id, target_locales, zip_codes, min_shock_threshold,
                        direction_filter, catalyst_domains, delivery_mode, role_mention,
                        client_label, manage_token_hash, is_active, created_at, failure_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
                    """,
                    (
                        sub_id,
                        delivery_type_norm,
                        webhook_hash,
                        encrypted_url,
                        clean_user_id,
                        resolved_dm_channel,
                        json.dumps(locales_norm),
                        json.dumps(zips_norm),
                        threshold_val,
                        dir_norm,
                        json.dumps(domains_norm) if domains_norm else None,
                        mode_norm,
                        role_mention,
                        client_label,
                        manage_token_hash,
                        now_iso,
                    )
                )
            conn.commit()

        return {
            "subscription_id": sub_id,
            "manage_token": manage_token,
            "delivery_type": delivery_type_norm,
            "discord_user_id": clean_user_id,
            "dm_channel_id": resolved_dm_channel,
            "target_locales": locales_norm,
            "zip_codes": zips_norm,
            "zip_resolutions": zip_resolutions,
            "minimum_shock_threshold": threshold_val,
            "direction_filter": dir_norm,
            "catalyst_domains": domains_norm,
            "delivery_mode": mode_norm,
            "client_label": client_label,
            "handshake_verified": handshake_sent,
            "is_active": True,
            "created_at": now_iso,
        }

    def unsubscribe(self, subscription_id: str, manage_token: Optional[str] = None, is_admin: bool = False) -> bool:
        """Deactivates/deletes a subscription by ID after verifying its `manage_token` (or admin override)."""
        if not subscription_id:
            return False
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT subscription_id, manage_token_hash FROM discord_subscriptions WHERE subscription_id = ?",
                (subscription_id,)
            ).fetchone()
            if not row:
                return False
            if not is_admin:
                if not manage_token:
                    return False
                expected_hash = row["manage_token_hash"]
                supplied_hash = self._hash_token(manage_token.strip())
                if not hmac.compare_digest(expected_hash, supplied_hash):
                    return False
            conn.execute("DELETE FROM discord_subscriptions WHERE subscription_id = ?", (subscription_id,))
            conn.commit()
            return True

    def unsubscribe_by_discord_user(self, discord_user_id: str, locale: Optional[str] = None) -> Dict[str, Any]:
        """
        Unsubscribes a Discord user from DM alerts (either a specific locale/ZIP or all locales).
        Used by `/midgley unsubscribe`.
        """
        clean_uid = str(discord_user_id or "").strip()
        if not clean_uid:
            return {"removed": False, "remaining_locales": [], "remaining_zip_codes": []}

        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT subscription_id, target_locales, zip_codes FROM discord_subscriptions WHERE discord_user_id = ? AND delivery_type = 'discord_dm' AND is_active = 1",
                (clean_uid,)
            ).fetchone()
            if not row:
                return {"removed": False, "remaining_locales": [], "remaining_zip_codes": []}

            sub_id = row["subscription_id"]
            current_locales = json.loads(row["target_locales"] or '["National"]')
            try:
                current_zips = json.loads(row["zip_codes"] or "[]")
            except Exception:
                current_zips = []

            if not locale or locale.strip().lower() == "all":
                conn.execute("DELETE FROM discord_subscriptions WHERE subscription_id = ?", (sub_id,))
                conn.commit()
                return {"removed": True, "subscription_id": sub_id, "remaining_locales": [], "remaining_zip_codes": []}

            raw_loc = locale.strip()
            if _looks_like_zip_code(raw_loc):
                clean_zip = raw_loc.split("-")[0].strip().zfill(5)[:5]
                if clean_zip in current_zips:
                    remaining_zips = [z for z in current_zips if z != clean_zip]
                    conn.execute(
                        "UPDATE discord_subscriptions SET zip_codes = ? WHERE subscription_id = ?",
                        (json.dumps(remaining_zips), sub_id)
                    )
                    conn.commit()
                    return {
                        "removed": True,
                        "subscription_id": sub_id,
                        "remaining_locales": current_locales,
                        "remaining_zip_codes": remaining_zips,
                    }

            canon_target = normalize_locale_name(raw_loc)
            if not canon_target or canon_target not in current_locales:
                return {
                    "removed": False,
                    "subscription_id": sub_id,
                    "remaining_locales": current_locales,
                    "remaining_zip_codes": current_zips,
                }

            remaining = [loc for loc in current_locales if loc != canon_target]
            if not remaining:
                conn.execute("DELETE FROM discord_subscriptions WHERE subscription_id = ?", (sub_id,))
                conn.commit()
                return {"removed": True, "subscription_id": sub_id, "remaining_locales": [], "remaining_zip_codes": []}
            else:
                conn.execute(
                    "UPDATE discord_subscriptions SET target_locales = ? WHERE subscription_id = ?",
                    (json.dumps(remaining), sub_id)
                )
                conn.commit()
                return {
                    "removed": True,
                    "subscription_id": sub_id,
                    "remaining_locales": remaining,
                    "remaining_zip_codes": current_zips,
                }

    def get_user_subscription(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        """Returns the active DM subscription record for a given `discord_user_id`, if any."""
        clean_uid = str(discord_user_id or "").strip()
        if not clean_uid:
            return None
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM discord_subscriptions WHERE discord_user_id = ? AND delivery_type = 'discord_dm'",
                (clean_uid,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_dict(row, include_decrypted_url=False)

    def mute_subscription(self, subscription_id: str, hours: int = 24) -> bool:
        """Snoozes/mutes a subscription for `hours` hours (Issue #235 Enhancement 1)."""
        muted_until = (datetime.now(timezone.utc) + timedelta(hours=max(1, hours))).isoformat()
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE discord_subscriptions SET muted_until = ? WHERE subscription_id = ?",
                (muted_until, subscription_id)
            )
            conn.commit()
            return cur.rowcount > 0

    def _row_to_dict(self, row: sqlite3.Row, include_decrypted_url: bool = False) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["target_locales"] = json.loads(d.get("target_locales") or '["National"]')
        except Exception:
            d["target_locales"] = ["National"]
        try:
            d["zip_codes"] = json.loads(d.get("zip_codes") or "[]")
        except Exception:
            d["zip_codes"] = []
        try:
            d["catalyst_domains"] = json.loads(d["catalyst_domains"]) if d.get("catalyst_domains") else None
        except Exception:
            d["catalyst_domains"] = None
        d["is_active"] = bool(d.get("is_active", 0))
        if include_decrypted_url and d.get("encrypted_webhook_url"):
            try:
                d["webhook_url"] = decrypt_webhook_url(d["encrypted_webhook_url"])
            except Exception as e:
                logger.warning(f"Failed to decrypt webhook URL for subscription {d.get('subscription_id')}: {e}")
                d["webhook_url"] = None
        return d

    def sync_edge_subscriptions(self, force: bool = False) -> int:
        """
        Pulls edge Discord DM subscriptions registered via Cloudflare Worker slash commands
        (/midgley subscribe) from the edge worker and merges them into the local subscription registry.
        """
        if os.environ.get("TESTING") == "1" and not force:
            return 0

        auth_token = os.environ.get("DISCORD_BOT_TOKEN") or os.environ.get("ADMIN_TOKEN") or os.environ.get("CLOUDFLARE_AUTH_TOKEN")
        if not auth_token:
            return 0

        worker_base = os.environ.get(
            "MIDGLEY_WORKER_BASE_URL",
            "https://midgley-intraday-monitor.m-cubed-3.workers.dev"
        ).rstrip("/")

        synced_count = 0
        try:
            req = urllib.request.Request(
                f"{worker_base}/discord/subscriptions",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "User-Agent": "Midgley-Subscription-Sync/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    subs = payload.get("subscriptions", [])
                    with self._get_conn() as conn:
                        for s in subs:
                            user_id = s.get("discord_user_id")
                            sub_id = s.get("subscription_id")
                            if not user_id or not sub_id:
                                continue
                            target_locales = json.dumps(s.get("target_locales") or ["National"])
                            zip_codes = json.dumps(s.get("zip_codes") or [])
                            min_shock = float(s.get("min_shock_threshold", 0.25))
                            direction = s.get("direction_filter", "all_shocks")
                            delivery_mode = s.get("delivery_mode", "realtime")
                            dm_channel = s.get("dm_channel_id")
                            is_active = 1 if s.get("is_active", True) else 0
                            muted_until = s.get("muted_until")
                            created_at = s.get("created_at") or datetime.now(timezone.utc).isoformat()
                            dummy_token_hash = self._hash_token(f"edge_{sub_id}")

                            conn.execute("""
                                INSERT INTO discord_subscriptions (
                                    subscription_id, delivery_type, discord_user_id, dm_channel_id,
                                    target_locales, zip_codes, min_shock_threshold, direction_filter,
                                    delivery_mode, manage_token_hash, is_active, muted_until, created_at
                                ) VALUES (?, 'discord_dm', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(subscription_id) DO UPDATE SET
                                    target_locales = excluded.target_locales,
                                    zip_codes = excluded.zip_codes,
                                    min_shock_threshold = excluded.min_shock_threshold,
                                    direction_filter = excluded.direction_filter,
                                    dm_channel_id = COALESCE(excluded.dm_channel_id, discord_subscriptions.dm_channel_id),
                                    is_active = excluded.is_active,
                                    muted_until = excluded.muted_until
                            """, (
                                sub_id, user_id, dm_channel,
                                target_locales, zip_codes, min_shock, direction,
                                delivery_mode, dummy_token_hash, is_active, muted_until, created_at
                            ))
                            synced_count += 1
                        conn.commit()
        except Exception as err:
            logger.debug(f"Edge Discord subscription sync skipped or failed: {err}")

        return synced_count

    def get_matching_subscribers(
        self,
        event_locales: List[str],
        price_pressure: float,
        catalyst_domains: Optional[List[str]] = None,
        delivery_mode: str = "realtime"
    ) -> List[Dict[str, Any]]:
        """
        Queries active subscribers matching:
        locales(s) ∩ event_locales ≠ ∅  AND  |ΔP| >= threshold(s)  AND  direction_matches(s, ΔP)
        """
        if os.environ.get("TESTING") != "1":
            try:
                self.sync_edge_subscriptions()
            except Exception:
                pass

        norm_event_locales = set(normalize_locale_list(event_locales))
        abs_dp = abs(float(price_pressure))
        now_iso = datetime.now(timezone.utc).isoformat()
        matched: List[Dict[str, Any]] = []

        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM discord_subscriptions WHERE is_active = 1 AND delivery_mode = ?",
                (delivery_mode,)
            ).fetchall()

        for row in rows:
            sub = self._row_to_dict(row, include_decrypted_url=True)
            muted_until = sub.get("muted_until")
            if muted_until and str(muted_until) > now_iso:
                continue

            sub_locales = set(sub.get("target_locales") or ["National"])
            # Match if intersection is non-empty
            if not (sub_locales & norm_event_locales):
                continue

            threshold = float(sub.get("min_shock_threshold", 0.25))
            if abs_dp < threshold:
                continue

            direction = sub.get("direction_filter", "all_shocks")
            if direction == "spikes_only" and price_pressure <= 0.0:
                continue
            if direction == "drops_only" and price_pressure >= 0.0:
                continue

            sub_domains = sub.get("catalyst_domains")
            if sub_domains and catalyst_domains:
                if not (set(sub_domains) & set(catalyst_domains)):
                    continue

            matched.append(sub)

        return matched

    def record_dispatch_outcome(
        self,
        subscription_id: str,
        success: bool,
        permanent_failure: bool = False,
        resolved_dm_channel_id: Optional[str] = None
    ) -> None:
        """
        Updates subscriber telemetry after a notification attempt.
        Enforces circuit breaking: marks subscription `is_active = 0` immediately on permanent failure
        (HTTP 404/410 dead webhook or HTTP 403 error 50007 blocked DM) or when `failure_count >= 3`.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            if success:
                if resolved_dm_channel_id:
                    conn.execute(
                        "UPDATE discord_subscriptions SET last_notified_at = ?, failure_count = 0, dm_channel_id = ? WHERE subscription_id = ?",
                        (now_iso, resolved_dm_channel_id, subscription_id)
                    )
                else:
                    conn.execute(
                        "UPDATE discord_subscriptions SET last_notified_at = ?, failure_count = 0 WHERE subscription_id = ?",
                        (now_iso, subscription_id)
                    )
            else:
                row = conn.execute(
                    "SELECT failure_count FROM discord_subscriptions WHERE subscription_id = ?",
                    (subscription_id,)
                ).fetchone()
                if row:
                    new_count = int(row["failure_count"] or 0) + 1
                    should_deactivate = permanent_failure or (new_count >= MAX_DISPATCH_FAILURES)
                    conn.execute(
                        "UPDATE discord_subscriptions SET failure_count = ?, is_active = ? WHERE subscription_id = ?",
                        (new_count, 0 if should_deactivate else 1, subscription_id)
                    )
            conn.commit()

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns active subscription counts grouped by regional metro hub, delivery type, and ZIP codes."""
        by_locale: Dict[str, int] = {loc: 0 for loc in SUPPORTED_LOCALES}
        by_delivery_type: Dict[str, int] = {"webhook": 0, "discord_dm": 0}
        by_zip_code: Dict[str, int] = {}
        active_count = 0
        inactive_count = 0

        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM discord_subscriptions").fetchall()

        for row in rows:
            sub = self._row_to_dict(row, include_decrypted_url=False)
            if sub["is_active"]:
                active_count += 1
                dtype = sub.get("delivery_type", "webhook")
                by_delivery_type[dtype] = by_delivery_type.get(dtype, 0) + 1
                for loc in sub.get("target_locales", []):
                    by_locale[loc] = by_locale.get(loc, 0) + 1
                for zc in sub.get("zip_codes", []):
                    by_zip_code[zc] = by_zip_code.get(zc, 0) + 1
            else:
                inactive_count += 1

        return {
            "total_subscriptions": active_count + inactive_count,
            "active_subscriptions": active_count,
            "inactive_subscriptions": inactive_count,
            "by_delivery_type": by_delivery_type,
            "by_locale": by_locale,
            "by_zip_code": by_zip_code,
        }



_global_subscription_registry: Optional[DiscordSubscriptionRegistry] = None


def get_subscription_registry(db_path: Optional[str] = None, reset: bool = False) -> DiscordSubscriptionRegistry:
    """Returns or initializes the singleton DiscordSubscriptionRegistry."""
    global _global_subscription_registry
    if reset or _global_subscription_registry is None or (db_path and _global_subscription_registry.db_path != db_path):
        _global_subscription_registry = DiscordSubscriptionRegistry(db_path=db_path)
    return _global_subscription_registry


def _post_webhook_payload(webhook_url: str, payload: Dict[str, Any], timeout: int = 10) -> Tuple[bool, Optional[int], Optional[str]]:
    """Internal helper to POST a JSON payload to a Discord Incoming Webhook URL."""
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_WEBHOOK_DISPATCH"):
        return True, 204, None

    if not validate_discord_webhook_url(webhook_url):
        return False, None, "Invalid or unauthorized Discord webhook URL"

    try:
        parsed = urllib.parse.urlparse(webhook_url.strip())
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in (
            "discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"
        ):
            return False, None, "Invalid or unauthorized Discord webhook host"
        safe_url = urllib.parse.urlunparse(parsed)

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            safe_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Midgley-Intraday-Notifier/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_ok = resp.status in (200, 204)
            return status_ok, resp.status, None if status_ok else f"HTTP {resp.status}"
    except urllib.error.HTTPError as he:
        return False, he.code, f"HTTP {he.code}: {he.reason}"
    except Exception as e:
        return False, None, str(e)


def dispatch_to_matching_subscribers(
    event_record: Dict[str, Any],
    environment: Optional[str] = None,
    registry: Optional[DiscordSubscriptionRegistry] = None
) -> Dict[str, Any]:
    """
    Locale-filtered multiplex dispatch engine (Issue #235).
    Queries active webhook and Direct Message (`discord_dm`) subscribers matching the anomaly's
    `target_locales`, `overall_price_pressure`, direction filter, and catalyst domain, and
    dispatches concurrently with dead-webhook (HTTP 404/410) & blocked-DM (HTTP 403/50007) circuit breaking.
    """
    reg = registry or get_subscription_registry()
    target_locales = event_record.get("target_locales", ["National"])
    if isinstance(target_locales, str):
        target_locales = [target_locales]

    scores = event_record.get("scores", {}) if isinstance(event_record.get("scores"), dict) else {}
    price_pressure = float(scores.get("overall_price_pressure", 0.0))
    domains = infer_event_catalyst_domains(event_record)

    subscribers = reg.get_matching_subscribers(
        event_locales=target_locales,
        price_pressure=price_pressure,
        catalyst_domains=domains,
        delivery_mode="realtime"
    )

    if not subscribers:
        return {
            "matched_subscribers": 0,
            "succeeded": 0,
            "failed": 0,
            "deactivated": 0,
            "results": []
        }

    def _deliver_single(sub: Dict[str, Any]) -> Dict[str, Any]:
        sub_id = sub["subscription_id"]
        dtype = sub.get("delivery_type", "webhook")
        role_mention = sub.get("role_mention")

        if dtype == "discord_dm":
            payload = format_intraday_discord_payload(
                event_record,
                environment=environment,
                include_components=True,
                role_mention=role_mention
            )
            ok, resolved_ch, status, err = send_discord_dm_payload(
                payload,
                discord_user_id=sub.get("discord_user_id"),
                dm_channel_id=sub.get("dm_channel_id")
            )
            permanent = status in (403, 404)
            reg.record_dispatch_outcome(
                sub_id,
                success=ok,
                permanent_failure=permanent,
                resolved_dm_channel_id=resolved_ch
            )
            return {
                "subscription_id": sub_id,
                "delivery_type": "discord_dm",
                "success": ok,
                "status": status,
                "deactivated": (not ok) and (permanent or (int(sub.get("failure_count", 0)) + 1 >= MAX_DISPATCH_FAILURES)),
                "error": err
            }
        else:
            webhook_url = sub.get("webhook_url")
            if not webhook_url:
                reg.record_dispatch_outcome(sub_id, success=False, permanent_failure=True)
                return {
                    "subscription_id": sub_id,
                    "delivery_type": "webhook",
                    "success": False,
                    "status": None,
                    "deactivated": True,
                    "error": "Missing or undecryptable webhook URL"
                }
            payload = format_intraday_discord_payload(
                event_record,
                environment=environment,
                include_components=False,
                role_mention=role_mention
            )
            ok, status, err = _post_webhook_payload(webhook_url, payload)
            permanent = status in (404, 410)
            reg.record_dispatch_outcome(sub_id, success=ok, permanent_failure=permanent)
            return {
                "subscription_id": sub_id,
                "delivery_type": "webhook",
                "success": ok,
                "status": status,
                "deactivated": (not ok) and (permanent or (int(sub.get("failure_count", 0)) + 1 >= MAX_DISPATCH_FAILURES)),
                "error": err
            }

    results = []
    max_workers = min(8, len(subscribers))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_deliver_single, s) for s in subscribers]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                logger.warning(f"Subscriber dispatch worker exception: {exc}")

    succeeded = sum(1 for r in results if r.get("success"))
    failed = len(results) - succeeded
    deactivated = sum(1 for r in results if r.get("deactivated"))

    return {
        "matched_subscribers": len(subscribers),
        "succeeded": succeeded,
        "failed": failed,
        "deactivated": deactivated,
        "results": results
    }


def send_intraday_discord_notification(
    event_record: Dict[str, Any],
    webhook_url: Optional[str] = None,
    environment: Optional[str] = None,
    include_components: Optional[bool] = None,
    dispatch_subscribers: bool = True
) -> bool:
    """
    Dispatches a Discord webhook notification for an intraday forecast revision to the primary
    channel webhook AND fans out to any locale-filtered subscribers (webhooks + DMs).
    
    Args:
        event_record: Dictionary containing headline, source, scores, target_locales, url, etc.
        webhook_url: Target Discord webhook URL (defaults to env vars DISCORD_INTRADAY_WEBHOOK_URL / DISCORD_WEBHOOK_URL).
        environment: Explicit environment override ('prod' or 'dev').
        include_components: Whether to attach top-level action button components (default: False).
        dispatch_subscribers: Whether to also fan out to registered multi-subscribers (default: True).
        
    Returns:
        bool: True if dispatched successfully or suppressed during test runs, False on error.
    """
    primary_explicit = webhook_url is not None
    if webhook_url is None:
        webhook_url = os.environ.get("DISCORD_INTRADAY_WEBHOOK_URL") or os.environ.get("DISCORD_WEBHOOK_URL")

    # Fan out to multi-subscriber registry unless caller passed an explicit single webhook override
    sub_succeeded = 0
    if dispatch_subscribers and not primary_explicit:
        try:
            sub_summary = dispatch_to_matching_subscribers(event_record, environment=environment)
            sub_succeeded = sub_summary.get("succeeded", 0)
        except Exception as e:
            logger.debug(f"Subscriber multiplex dispatch notice: {e}")

    if not webhook_url:
        if sub_succeeded > 0:
            return True
        logger.info("No Discord webhook URL configured (DISCORD_INTRADAY_WEBHOOK_URL unset); skipping notification.")
        return False

    # Unit testing suppression unless test dispatch is explicitly enabled
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_WEBHOOK_DISPATCH"):
        logger.info("TESTING=1: Suppressed Discord webhook notification HTTP POST.")
        return True

    payload = format_intraday_discord_payload(
        event_record,
        environment=environment,
        include_components=include_components
    )

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
            return status_ok or (sub_succeeded > 0)
    except Exception as e:
        logger.warning(f"Failed to dispatch intraday Discord webhook notification: {e}")
        return sub_succeeded > 0


def format_duplicate_review_discord_payload(
    new_event: Dict[str, Any],
    prior_event: Dict[str, Any],
    matched_entity: str,
    similarity: float,
    environment: Optional[str] = None,
    include_components: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Constructs an interactive Discord Embed payload alerting operators to a potential
    event duplicate or follow-up report on the same physical facility/entity.
    """
    env_label = get_environment_label(environment)
    is_prod = (env_label == "prod")
    env_badge = "[PRODUCTION]" if is_prod else "[DEVELOPMENT]"

    new_headline = new_event.get("headline", "New Breaking Headline")
    prior_headline = prior_event.get("headline", "Prior Active Event")
    new_url = new_event.get("url", "").strip()
    prior_url = prior_event.get("url", "").strip()

    target_locales = new_event.get("target_locales", ["National"])
    locales_str = ", ".join(target_locales) if isinstance(target_locales, list) else str(target_locales)

    scores = new_event.get("scores", {})
    price_pressure = float(scores.get("overall_price_pressure", 0.0))
    supply_disruption = float(scores.get("supply_disruption", 0.0))

    new_hash = new_event.get("hash") or hashlib.sha256(new_headline.encode("utf-8", errors="ignore")).hexdigest()[:16]
    prior_hash = prior_event.get("hash") or hashlib.sha256(prior_headline.encode("utf-8", errors="ignore")).hexdigest()[:16]

    age_hours = float(prior_event.get("age_hours", 0.0))
    age_str = f"Logged {age_hours:.1f}h ago" if age_hours > 0 else "Recently active"

    signing_secret = (
        os.getenv("FLAG_SIGNING_KEY")
        or os.getenv("ADMIN_TOKEN")
        or os.getenv("CLOUDFLARE_AUTH_TOKEN")
        or ""
    )
    exp_time = int(time.time()) + (72 * 3600)
    sig_dup = ""
    sig_dist = ""
    if signing_secret:
        msg_dup = f"review_dup:v1|{new_hash}|{prior_hash}|duplicate|{exp_time}".encode("utf-8")
        sig_dup = hmac.new(signing_secret.encode("utf-8"), msg_dup, hashlib.sha256).hexdigest()[:32]
        msg_dist = f"review_dist:v1|{new_hash}|{prior_hash}|distinct|{exp_time}".encode("utf-8")
        sig_dist = hmac.new(signing_secret.encode("utf-8"), msg_dist, hashlib.sha256).hexdigest()[:32]
    else:
        logger.warning(
            "Neither FLAG_SIGNING_KEY, ADMIN_TOKEN, nor CLOUDFLARE_AUTH_TOKEN is configured in environment. "
            "Duplicate review links will be generated without HMAC signature and will be rejected by Cloudflare Worker."
        )

    base_worker = "https://midgley-intraday-monitor.m-cubed-3.workers.dev"
    dup_params = urllib.parse.urlencode({
        "id": new_hash,
        "prior_id": prior_hash,
        "decision": "duplicate",
        "exp": str(exp_time),
        "sig": sig_dup,
        "headline": new_headline[:120]
    })
    dist_params = urllib.parse.urlencode({
        "id": new_hash,
        "prior_id": prior_hash,
        "decision": "distinct",
        "exp": str(exp_time),
        "sig": sig_dist,
        "headline": new_headline[:120]
    })
    flag_params = urllib.parse.urlencode({
        "id": new_hash,
        "exp": str(exp_time),
        "sig": sig_dup,
        "headline": new_headline[:120],
        "source": new_event.get("source", "Intraday_Monitor"),
        "p": f"{price_pressure:+.2f}",
        "s": f"{supply_disruption:.2f}",
        "g": "0.00",
        "url": new_url[:200]
    })

    dup_url = f"{base_worker}/review?{dup_params}"
    dist_url = f"{base_worker}/review?{dist_params}"
    flag_url = f"{base_worker}/flag?{flag_params}"

    fields = [
        {
            "name": "📌 Matched Entity",
            "value": f"`{matched_entity}`",
            "inline": True
        },
        {
            "name": "🔍 Hindsight Similarity",
            "value": f"`{similarity * 100:.0f}% Overlap`",
            "inline": True
        },
        {
            "name": "📍 Target Metro Hubs",
            "value": f"`{locales_str}`",
            "inline": True
        },
        {
            "name": "📊 Tentative Impact (ΔP)",
            "value": f"`{price_pressure:+.2f}/gal`",
            "inline": True
        },
        {
            "name": "🛢️ Supply Disruption (S)",
            "value": f"`{supply_disruption:.2f}`",
            "inline": True
        }
    ]

    links = []
    if new_url:
        links.append(f"[Incoming Article]({new_url})")
    if prior_url:
        links.append(f"[Prior Incident Article]({prior_url})")
    if links:
        fields.append({
            "name": "🔗 Intelligence Sources",
            "value": " • ".join(links),
            "inline": False
        })

    fields.append({
        "name": "⚡ Operator Disambiguation Actions",
        "value": f"[🔗 Confirm Duplicate (Suppress)]({dup_url}) • [⚡ Confirm New Incident (Apply)]({dist_url}) • [🚩 Flag False Positive]({flag_url})",
        "inline": False
    })

    desc = (
        f"**Incoming Catalyst (Held in Staging):**\n> *\"{new_headline}\"*\n\n"
        f"**Prior Active Incident on File ({age_str}):**\n> *\"{prior_headline}\"*"
    )

    embed = {
        "title": f"⚠️ {env_badge} Potential Event Duplicate / Follow-Up Review Needed",
        "description": desc,
        "url": "https://koshiirRa.github.io/midgley/",
        "color": 15960850,  # Amber #F39C12
        "fields": fields,
        "footer": {
            "text": f"Midgley Event Deduplication Engine • Candidate ID: {new_hash}"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload: Dict[str, Any] = {
        "username": "Midgley Intraday Monitor",
        "embeds": [embed]
    }

    if include_components is None:
        include_components = os.environ.get("DISCORD_INCLUDE_COMPONENTS", "0").lower() in ("1", "true")

    if include_components:
        payload["components"] = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "🔗 Confirm Duplicate",
                        "url": dup_url
                    },
                    {
                        "type": 2,
                        "style": 5,
                        "label": "⚡ Confirm New Incident",
                        "url": dist_url
                    },
                    {
                        "type": 2,
                        "style": 5,
                        "label": "🚩 Flag False Positive",
                        "url": flag_url
                    }
                ]
            }
        ]

    return payload


def send_duplicate_review_discord_notification(
    new_event: Dict[str, Any],
    prior_event: Dict[str, Any],
    matched_entity: str,
    similarity: float,
    webhook_url: Optional[str] = None,
    environment: Optional[str] = None,
    include_components: Optional[bool] = None
) -> bool:
    """Dispatches a duplicate review alert to Discord for operator disambiguation."""
    if not webhook_url:
        webhook_url = os.environ.get("DISCORD_INTRADAY_WEBHOOK_URL")

    if not webhook_url:
        logger.info("No Discord webhook URL configured; skipping duplicate review notification.")
        return False

    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_WEBHOOK_DISPATCH"):
        logger.info("TESTING=1: Suppressed Discord duplicate review notification HTTP POST.")
        return True

    payload = format_duplicate_review_discord_payload(
        new_event=new_event,
        prior_event=prior_event,
        matched_entity=matched_entity,
        similarity=similarity,
        environment=environment,
        include_components=include_components
    )

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
                logger.info(f"Successfully dispatched duplicate review notification to Discord (HTTP {resp.status})")
            return status_ok
    except Exception as e:
        logger.warning(f"Failed to dispatch duplicate review Discord notification: {e}")
        return False
