"""
Bureau of Safety and Environmental Enforcement (BSEE) Gulf Shut-In Connector (src/bsee_shutins.py)
Ingests daily offshore Gulf of Mexico oil & gas production shut-in reports during tropical evacuations.
Primary source: direct official BSEE hurricane activity bulletin HTML parser (Issue #633).
Secondary: cached BSEE vintages. Tertiary emergency fallback: Google News RSS.
"""

import os
import re
import time
import urllib.request
import defusedxml.ElementTree as ET
import json
import logging
from html.parser import HTMLParser
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

USER_AGENT = "(MidgleyGasPriceForecaster, contact@example.com)"
BSEE_VINTAGE_FILE = os.path.join("data", "bsee_vintages.json")
BSEE_HURRICANE_URL = "https://www.bsee.gov/stats-facts/offshore-stats-by-topic/hurricane-activity"
BSEE_RSS_URL = "https://news.google.com/rss/search?q=BSEE+shut-in+Gulf+of+Mexico+when:7d&hl=en-US&gl=US&ceid=US:en"


class _HTMLTextExtractor(HTMLParser):
    """Stdlib HTMLParser that extracts visible text while ignoring script/style blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
            self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def _strip_html(html: str) -> str:
    """Strips HTML tags and normalizes whitespace for deterministic regex parsing."""
    parser = _HTMLTextExtractor()
    parser.feed(html)
    parser.close()
    return re.sub(r"\s+", " ", parser.get_text()).strip()


def parse_bsee_bulletin_html(html: str) -> Optional[Dict[str, Any]]:
    """
    Parses official BSEE Gulf of Mexico hurricane activity HTML tables and narrative bulletins.
    Extracts oil shut-in %, natural gas shut-in %, and evacuated platform counts.
    Returns None if no BSEE shut-in statistics are present in the HTML.
    """
    if not html or not html.strip():
        return None

    clean_text = _strip_html(html)
    text_lower = clean_text.lower()

    oil_pct: Optional[float] = None
    gas_pct: Optional[float] = None
    platforms: Optional[int] = None

    # 1. Oil production shut-in percentage (table or narrative formats)
    oil_patterns = [
        r"(?:percent(?:age)?\s+of\s+)?(?:current\s+)?oil\s+(?:production\s+)?shut[-\s]?in[^0-9.%]{0,30}(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?(?:current\s+)?)?(?:gulf\s+of\s+mexico\s+)?(?:oil|crude)\s+(?:production\s+)?(?:is\s+|has\s+been\s+)?shut[-\s]?in",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?(?:current\s+)?)?(?:oil|crude)",
    ]
    for pat in oil_patterns:
        m = re.search(pat, text_lower)
        if m:
            oil_pct = float(m.group(1))
            break

    # 2. Natural gas production shut-in percentage
    gas_patterns = [
        r"(?:percent(?:age)?\s+of\s+)?(?:current\s+)?(?:natural\s+)?gas\s+(?:production\s+)?shut[-\s]?in[^0-9.%]{0,30}(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?(?:current\s+)?)?(?:gulf\s+of\s+mexico\s+)?(?:natural\s+)?gas\s+(?:production\s+)?(?:is\s+|has\s+been\s+)?shut[-\s]?in",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?(?:current\s+)?)?(?:natural\s+gas|gas)",
    ]
    for pat in gas_patterns:
        m = re.search(pat, text_lower)
        if m:
            gas_pct = float(m.group(1))
            break

    # 3. Evacuated platforms count
    plat_patterns = [
        r"(?:production\s+)?platforms?\s+evacuated[^0-9]{0,30}(\d+)",
        r"evacuated\s+(?:production\s+)?platforms?[^0-9]{0,30}(\d+)",
        r"(\d+)\s*(?:production\s+)?platforms?\s*(?:have\s+been\s+|are\s+)?evacuated",
        r"personnel\s+have\s+been\s+evacuated\s+from\s+(?:a\s+total\s+of\s+)?(\d+)\s*(?:production\s+)?platforms?",
    ]
    for pat in plat_patterns:
        m = re.search(pat, text_lower)
        if m:
            platforms = int(m.group(1))
            break

    if oil_pct is None and gas_pct is None and platforms is None:
        return None

    oil_val = round(oil_pct, 2) if oil_pct is not None else 0.0
    gas_val = round(gas_pct, 2) if gas_pct is not None else 0.0
    plat_val = int(platforms) if platforms is not None else 0

    return {
        "bsee_gulf_oil_shutin_pct": oil_val,
        "bsee_gulf_gas_shutin_pct": gas_val,
        "bsee_evacuated_platforms_count": plat_val,
        "is_storm_evacuation_active": bool(oil_val > 0.0 or gas_val > 0.0 or plat_val > 0),
        "source_url": BSEE_HURRICANE_URL,
        "provenance": "BSEE_OFFICIAL_BULLETIN",
    }


def _record_connector_telemetry(status: str, latency_ms: float, http_status: Optional[int] = None) -> None:
    """Records BSEE connector latency and HTTP status in connector telemetry when available."""
    try:
        from src.telemetry import log_connector_call
        log_connector_call(
            connector="bsee_shutins",
            status=status,
            latency_ms=latency_ms,
            http_status=http_status,
        )
    except Exception:
        pass


def save_bsee_vintage_record(record: dict, filepath: Optional[str] = None) -> None:
    """Appends a point-in-time BSEE offshore shut-in vintage record."""
    fp = filepath or BSEE_VINTAGE_FILE
    if os.environ.get("TESTING") == "1" and os.path.abspath(fp) == os.path.abspath(os.path.join("data", "bsee_vintages.json")) and os.environ.get("TEST_PERSIST_RECORD") != "1":
        return
    try:
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        vintages = []
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    vintages = json.load(f)
            except Exception:
                vintages = []

        vintage_entry = {
            "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": record
        }
        vintages.append(vintage_entry)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(vintages, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to persist BSEE vintage record: {e}")


def get_bsee_vintages_as_of(as_of_date: str, filepath: str = BSEE_VINTAGE_FILE) -> Optional[dict]:
    """Retrieves the latest BSEE observation recorded on or before as_of_date."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            vintages = json.load(f)
        valid = [v for v in vintages if v.get("as_of", "")[:10] <= as_of_date]
        if valid:
            return valid[-1].get("data")
    except Exception as e:
        logger.debug(f"Error reading BSEE vintages: {e}")
    return None


class BSEEShutInConnector:
    """
    Zero-Cost BSEE Gulf Offshore Production Shut-In Connector.
    Primary: Direct official BSEE hurricane activity HTML bulletin parser (Issue #633).
    Secondary: Cached BSEE vintages. Tertiary emergency fallback: Google News RSS.
    """
    def __init__(self, vintage_file: str = BSEE_VINTAGE_FILE):
        self.is_free_alternative = True
        self.cost_per_query = 0.0
        self.vintage_file = vintage_file

    def _fetch_direct_bsee_bulletin(self) -> Optional[Dict[str, Any]]:
        """Fetches and parses the official BSEE hurricane activity bulletin HTML page."""
        t0 = time.monotonic()
        http_status: Optional[int] = None
        try:
            req = urllib.request.Request(BSEE_HURRICANE_URL, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as resp:
                http_status = getattr(resp, "status", 200)
                if http_status == 200:
                    html = resp.read().decode("utf-8", errors="replace")
                    parsed = parse_bsee_bulletin_html(html)
                    _record_connector_telemetry("success", (time.monotonic() - t0) * 1000.0, http_status)
                    return parsed
        except Exception as e:
            _record_connector_telemetry("error", (time.monotonic() - t0) * 1000.0, http_status)
            logger.debug(f"Direct BSEE bulletin fetch failed: {e}")
        return None

    def _fetch_rss_fallback(self) -> Optional[Dict[str, Any]]:
        """Emergency tertiary fallback: Google News RSS search for BSEE shut-in reports."""
        try:
            req = urllib.request.Request(BSEE_RSS_URL, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if getattr(resp, "status", 200) == 200:
                    xml_bytes = resp.read()
                    root = ET.fromstring(xml_bytes)
                    for item in root.findall(".//item"):
                        title = item.findtext("title", "")
                        desc = item.findtext("description", "")
                        text = f"{title} {desc}".lower()

                        if "shut-in" in text or "evacuat" in text or "bsee" in text:
                            out: Dict[str, Any] = {
                                "is_storm_evacuation_active": True,
                                "source_url": BSEE_RSS_URL,
                                "provenance": "GOOGLE_NEWS_RSS_FALLBACK",
                            }
                            oil_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?(?:current\s+)?)?(?:oil|crude)", text)
                            if oil_match:
                                out["bsee_gulf_oil_shutin_pct"] = float(oil_match.group(1))
                            gas_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?)?(?:gas|natural gas)", text)
                            if gas_match:
                                out["bsee_gulf_gas_shutin_pct"] = float(gas_match.group(1))
                            plat_match = re.search(r"(\d+)\s*(?:production\s*)?platforms?\s*(?:have\s*been\s*)?evacuated", text)
                            if plat_match:
                                out["bsee_evacuated_platforms_count"] = int(plat_match.group(1))
                            return out
        except Exception as e:
            logger.debug(f"BSEE emergency RSS fallback skipped: {e}")
        return None

    def fetch_gulf_shutin_data(self, html_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches daily BSEE offshore shut-in metrics with 12-hour lookup cache.
        Fallback order:
          1. Direct official BSEE hurricane activity bulletin HTML
          2. Cached BSEE vintage record
          3. Emergency Google News RSS fallback
        """
        day_bucket = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"bsee_gulf_shutin:{day_bucket}"
        if html_override is None:
            cached = global_cache.get(cache_key)
            if cached:
                logger.info("Loaded BSEE offshore shut-in data from lookup cache.")
                return cached

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result: Dict[str, Any] = {
            "source": "Bureau of Safety and Environmental Enforcement (BSEE Official Bulletin)",
            "source_url": BSEE_HURRICANE_URL,
            "provenance": "BASELINE_QUIET",
            "timestamp": timestamp_str,
            "bsee_gulf_oil_shutin_pct": 0.0,
            "bsee_gulf_gas_shutin_pct": 0.0,
            "bsee_evacuated_platforms_count": 0,
            "is_storm_evacuation_active": False,
            "status": "SUCCESS",
        }

        # 1. Primary: Direct official BSEE HTML bulletin (or injected mock HTML fixture)
        direct_parsed: Optional[Dict[str, Any]] = None
        if html_override is not None:
            direct_parsed = parse_bsee_bulletin_html(html_override)
        elif os.environ.get("TESTING") != "1":
            direct_parsed = self._fetch_direct_bsee_bulletin()

        if direct_parsed:
            result.update(direct_parsed)
        else:
            # 2. Secondary: Cached BSEE vintage record
            vintage = get_bsee_vintages_as_of(day_bucket, filepath=self.vintage_file)
            if vintage:
                result.update({
                    "bsee_gulf_oil_shutin_pct": vintage.get("bsee_gulf_oil_shutin_pct", 0.0),
                    "bsee_gulf_gas_shutin_pct": vintage.get("bsee_gulf_gas_shutin_pct", 0.0),
                    "bsee_evacuated_platforms_count": vintage.get("bsee_evacuated_platforms_count", 0),
                    "is_storm_evacuation_active": vintage.get("is_storm_evacuation_active", False),
                    "source_url": vintage.get("source_url", BSEE_HURRICANE_URL),
                    "provenance": "CACHED_VINTAGE",
                })
            elif os.environ.get("TESTING") != "1":
                # 3. Tertiary emergency fallback: Google News RSS
                rss_parsed = self._fetch_rss_fallback()
                if rss_parsed:
                    result.update(rss_parsed)

        save_bsee_vintage_record(result, filepath=self.vintage_file)
        if html_override is None:
            global_cache.set(cache_key, result, ttl_seconds=43200)
        return result
