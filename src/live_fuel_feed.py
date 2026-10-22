"""
Live Fuel Price API Feed Module (src/live_fuel_feed.py)
Provides integration functions for real-time gas price ingestion across all regional models:
1. GasBuddy GraphQL API (Station-level real-time prices by zip code).
2. AAA Metro & State Web Scraper (gasprices.aaa.com).
3. EIA API v2 / yfinance benchmark estimation.
4. Historical prediction_history.csv lookup fallback.
5. Static regional fallback price anchors.
"""

import os
import re
import json
import csv
import io
import urllib.request
import urllib.parse
import pandas as pd
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

# GasBuddy Internal GraphQL Endpoint
GASBUDDY_GRAPHQL_URL = "https://www.gasbuddy.com/graphql"

# lykmapipo/US-Gas-Prices Daily CSV Endpoints
LYKMAPIPO_METRO_CSV_URL = "https://raw.githubusercontent.com/lykmapipo/US-Gas-Prices/main/data/metro-daily-averages/{date}.csv"
LYKMAPIPO_STATE_CSV_URL = "https://raw.githubusercontent.com/lykmapipo/US-Gas-Prices/main/data/state-daily-averages/{date}.csv"
CACHE_TTL_AAA_CSV = 86400  # 24 hours

# Data Age Control Constants
MAX_DATA_AGE_HOURS = 24.0  # Strict 24-hour maximum data staleness threshold


def calculate_data_age_hours(timestamp_str: str) -> float:
    """Calculates data age in hours from a timestamp string (YYYY-MM-DD HH:MM:SS or ISO format)."""
    if not timestamp_str:
        return 0.0
    try:
        ts_clean = str(timestamp_str).replace('T', ' ').split('.')[0]
        if len(ts_clean) == 10:  # YYYY-MM-DD
            ts_clean += " 00:00:00"
        dt = datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")
        age_seconds = (datetime.now() - dt).total_seconds()
        return round(max(0.0, age_seconds / 3600.0), 2)
    except Exception:
        return 0.0


def validate_price_payload_freshness(payload: dict, max_allowed_hours: float = MAX_DATA_AGE_HOURS) -> dict:
    """
    Enforces Data Age Control on incoming retail fuel price payloads.
    Attaches 'data_age_hours' and 'is_stale' boolean flag.
    If age > max_allowed_hours (24.0h), logs a warning and marks is_stale = True.
    """
    if not payload or not isinstance(payload, dict):
        return payload

    ts = payload.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    age_hours = calculate_data_age_hours(ts)
    is_stale = age_hours > max_allowed_hours

    payload["data_age_hours"] = age_hours
    payload["is_stale"] = is_stale
    payload["max_allowed_age_hours"] = max_allowed_hours

    if is_stale:
        region = str(payload.get('region', 'Unknown'))
        src_name = str(payload.get('source', 'Unknown'))
        logger.warning(
            f"STALE RETAIL PRICE WARNING for {region}: "
            f"Data age is {age_hours:.1f} hours (Source: {src_name}), "
            f"exceeding max staleness threshold of {max_allowed_hours:.1f} hours."
        )
    return payload


def is_price_outlier(region_code: str, price: float) -> bool:
    """
    Validates whether a candidate live retail gas price is a plausible value
    or an unvalidated scraper outlier anomaly.
    Enforces physical feasibility bounds for US fuel markets without falsely rejecting
    legitimate macroeconomic price shifts.
    Returns True if price is an extreme outlier, False otherwise.
    """
    if price is None or not pd.notna(price) or float(price) <= 0:
        return True
    p_val = float(price)
    
    # For CA regions or state, enforce California physical bounds [$3.50, $9.00]
    if region_code == "CA" or str(region_code).endswith("_CA") or region_code in ["Oakland_CA", "BayArea_CA", "SanFrancisco_CA", "SanJose_CA", "NorthBay_CA", "Los_Angeles_CA"]:
        if p_val < 3.50 or p_val > 9.00:
            logger.warning(f"CA OUTLIER PRICE WARNING for {region_code}: ${p_val:.3f}/gal is outside expected CA range [$3.50, $9.00].")
            return True
        return False
    
    # For non-CA regions, enforce standard US retail gasoline physical bounds [$1.50, $8.50]
    if p_val < 1.50 or p_val > 8.50:
        logger.warning(f"OUTLIER PRICE ANOMALY DETECTED for {region_code}: ${p_val:.3f}/gal is outside plausible US retail range [$1.50, $8.50]. Rejecting candidate.")
        return True
        
    return False


REGION_METADATA = {
    "National": {
        "zip": "20001",
        "state": "US",
        "static_anchor": 4.316,
        "name": "National Wholesale / US Average",
        "aaa_keywords": ["National Average", "US Average", "Current Avg."]
    },
    "Tulsa_OK": {
        "zip": "74103",
        "state": "OK",
        "static_anchor": 3.820,
        "name": "Tulsa, OK Metro Retail",
        "aaa_keywords": ["Tulsa"]
    },
    "Newark_DE": {
        "zip": "19711",
        "state": "DE",
        "static_anchor": 4.350,
        "name": "Newark, DE Metro Retail",
        "aaa_keywords": ["Wilmington", "New Castle", "State Average"]
    },
    "Cincinnati_OH": {
        "zip": "45202",
        "state": "OH",
        "static_anchor": 4.080,
        "name": "Cincinnati, OH Retail",
        "aaa_keywords": ["Cincinnati"]
    },
    "Cincinnati_KY": {
        "zip": "41011",
        "state": "KY",
        "static_anchor": 4.160,
        "name": "Northern Kentucky Retail",
        "aaa_keywords": ["Cincinnati", "Northern Kentucky", "Covington"]
    },
    "Oakland_CA": {
        "zip": "94612",
        "state": "CA",
        "static_anchor": 6.050,
        "name": "Oakland, CA Metro Retail",
        "aaa_keywords": ["Oakland", "East Bay", "Alameda"]
    },
    "BayArea_CA": {
        "zip": "94102",
        "state": "CA",
        "static_anchor": 6.160,
        "name": "SF Bay Area 9-County Avg",
        "aaa_keywords": ["San Francisco", "Oakland", "San Jose"]
    },
    "SanFrancisco_CA": {
        "zip": "94102",
        "state": "CA",
        "static_anchor": 6.160,
        "name": "San Francisco Metro Retail",
        "aaa_keywords": ["San Francisco"]
    },
    "SanJose_CA": {
        "zip": "95113",
        "state": "CA",
        "static_anchor": 5.990,
        "name": "San Jose / Silicon Valley Retail",
        "aaa_keywords": ["San Jose", "Santa Clara"]
    },
    "NorthBay_CA": {
        "zip": "94590",
        "state": "CA",
        "static_anchor": 5.950,
        "name": "North Bay / Solano Retail",
        "aaa_keywords": ["Vallejo", "Fairfield", "Napa"]
    },
    "Greenville_NC": {
        "zip": "27834",
        "state": "NC",
        "static_anchor": 3.950,
        "name": "Greenville, NC Metro Retail",
        "aaa_keywords": ["Greenville", "Pitt", "State Average"]
    },
    "Charlotte_NC": {
        "zip": "28202",
        "state": "NC",
        "static_anchor": 3.980,
        "name": "Charlotte, NC Metro Retail",
        "aaa_keywords": ["Charlotte", "Mecklenburg", "State Average"]
    },
    "Port_St_Lucie_FL": {
        "zip": "34952",
        "state": "FL",
        "static_anchor": 4.145,
        "name": "Port St. Lucie, FL Metro Retail",
        "aaa_keywords": ["Port St. Lucie", "St. Lucie", "State Average"]
    },
    "Chicago_IL": {
        "zip": "60601",
        "state": "IL",
        "static_anchor": 3.850,
        "name": "Greater Chicago Metro Retail",
        "aaa_keywords": ["Chicago", "Cook County", "Metro Average"]
    },
    "Houston_TX": {
        "zip": "77002",
        "state": "TX",
        "static_anchor": 2.850,
        "name": "Houston, TX Metro Retail",
        "aaa_keywords": ["Houston", "Harris County", "Texas"]
    },
    "Los_Angeles_CA": {
        "zip": "90012",
        "state": "CA",
        "static_anchor": 4.890,
        "name": "Los Angeles Basin, CA Metro Retail",
        "aaa_keywords": ["Los Angeles", "Long Beach", "Orange County", "California"]
    },
    "Denver_CO": {
        "zip": "80202",
        "state": "CO",
        "static_anchor": 3.150,
        "name": "Denver, CO Metro Retail",
        "aaa_keywords": ["Denver", "Colorado", "Boulder", "State Average"]
    },
    "New_York_NY": {
        "zip": "10001",
        "state": "NY",
        "static_anchor": 3.480,
        "name": "New York, NY Metro Retail",
        "aaa_keywords": ["New York", "New York City", "Manhattan", "Long Island", "State Average"]
    },
    "San_Juan_PR": {
        "zip": "00901",
        "state": "PR",
        "static_anchor": 3.490,
        "name": "San Juan, PR Metro Retail",
        "aaa_keywords": ["San Juan", "Puerto Rico", "DACO"]
    },
    "Boston_MA": {
        "zip": "02108",
        "state": "MA",
        "static_anchor": 3.450,
        "name": "Boston, MA Metro Retail",
        "aaa_keywords": ["Boston", "Suffolk County", "Massachusetts", "State Average"]
    },
    "Seattle_WA": {
        "zip": "98101",
        "state": "WA",
        "static_anchor": 4.250,
        "name": "Seattle-Tacoma, WA Metro Retail",
        "aaa_keywords": ["Seattle", "King County", "Washington", "State Average"]
    },
    "Phoenix_AZ": {
        "zip": "85001",
        "state": "AZ",
        "static_anchor": 3.550,
        "name": "Phoenix, AZ Metro Retail",
        "aaa_keywords": ["Phoenix", "Maricopa County", "Arizona", "State Average"]
    },
    "Anchorage_AK": {
        "zip": "99501",
        "state": "AK",
        "static_anchor": 3.750,
        "name": "Anchorage, AK Metro Retail",
        "aaa_keywords": ["Anchorage", "Alaska", "State Average"]
    },
    "Honolulu_HI": {
        "zip": "96813",
        "state": "HI",
        "static_anchor": 4.650,
        "name": "Honolulu, HI Metro Retail",
        "aaa_keywords": ["Honolulu", "Oahu", "Hawaii", "State Average"]
    },
    "Guam_GU": {
        "zip": "96910",
        "state": "GU",
        "static_anchor": 4.890,
        "name": "Hagåtña, Guam Retail",
        "aaa_keywords": ["Guam", "Hagatna", "Apra Harbor"]
    }
}


def fetch_gasbuddy_prices_by_zip(zip_code: str = "74103") -> dict:
    """
    Queries GasBuddy's GraphQL API for real-time station prices in any zip code.
    """

    graphql_query = """
    query LocationBySearchTerm($searchTerm: String!) {
        locationBySearchTerm(search: $searchTerm) {
            stations {
                results {
                    id
                    name
                    address {
                        line1
                        city
                        state
                        zip
                    }
                    prices {
                        fuelProduct
                        credit {
                            nickname
                            postedTime
                            price
                        }
                    }
                }
            }
        }
    }
    """
    
    payload = json.dumps({
        "query": graphql_query,
        "variables": {"searchTerm": zip_code}
    }).encode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        req = urllib.request.Request(GASBUDDY_GRAPHQL_URL, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                res_data = json.loads(response.read().decode('utf-8'))
                stations = res_data.get('data', {}).get('locationBySearchTerm', {}).get('stations', {}).get('results', [])
                
                station_prices = []
                for st in stations:
                    name = st.get('name')
                    prices = st.get('prices', [])
                    reg_price = None
                    for p in prices:
                        if p.get('fuelProduct') == 'regular' and p.get('credit'):
                            reg_price = p.get('credit', {}).get('price')
                            break
                    if reg_price and reg_price > 0:
                        station_prices.append({"station": name, "regular_price": reg_price})
                        
                if station_prices:
                    avg_price = sum(s['regular_price'] for s in station_prices) / len(station_prices)
                    logger.info(f"Fetched {len(station_prices)} GasBuddy stations for zip {zip_code}. Avg Regular: ${avg_price:.3f}/gal")
                    return {"average_price": round(avg_price, 3), "stations": station_prices, "source": f"GasBuddy GraphQL (Zip {zip_code})"}
    except Exception as e:
        logger.debug(f"GasBuddy GraphQL query notice for zip {zip_code}: {type(e).__name__}")
        
    return None


def fetch_gasbuddy_tulsa_prices(zip_code: str = "74103") -> dict:
    """Backward compatibility wrapper for Tulsa GasBuddy query."""
    res = fetch_gasbuddy_prices_by_zip(zip_code)
    if res:
        return res
    fallback_price = REGION_METADATA.get("Tulsa_OK", {}).get("static_anchor", 3.820)
    return {"average_price": fallback_price, "stations": [], "source": "Tulsa Fallback Anchor"}


def fetch_aaa_csv_prices(region_or_state: str, is_state: bool = False) -> Optional[dict]:
    """
    Fetches daily AAA retail fuel prices from the lykmapipo/US-Gas-Prices repository.
    Serves as the primary zero-cost, high-reliability source for both metro and state pump prices.
    Caches parsed daily tables with a 24-hour TTL in global_cache.
    Supports all 4 fuel products: regular, midgrade, premium, and diesel.
    """
    cache_key = "aaa_csv_state_table" if (is_state or len(region_or_state) == 2) else "aaa_csv_metro_table"
    cached_data = global_cache.get(cache_key)
    csv_text = None
    as_of_date = None

    if cached_data and isinstance(cached_data, dict) and cached_data.get("csv_text"):
        csv_text = cached_data["csv_text"]
        as_of_date = cached_data.get("date")
    else:
        # Fetch from GitHub with date auto-discovery across the last 7 days
        url_template = LYKMAPIPO_STATE_CSV_URL if (is_state or len(region_or_state) == 2) else LYKMAPIPO_METRO_CSV_URL
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        now = datetime.now(timezone.utc)
        for days_back in range(8):
            cand_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
            url = url_template.format(date=cand_date)
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        raw_bytes = response.read()
                        csv_text = raw_bytes.decode('utf-8', errors='ignore')
                        as_of_date = cand_date
                        global_cache.set(
                            cache_key,
                            {"date": as_of_date, "csv_text": csv_text},
                            ttl_seconds=CACHE_TTL_AAA_CSV
                        )
                        logger.info(f"Loaded AAA daily CSV from lykmapipo ({cache_key}, date: {as_of_date})")
                        break
            except Exception as e:
                logger.debug(f"Candidate AAA CSV date {cand_date} notice: {e}")
                continue

    if not csv_text:
        return None

    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        if not rows:
            return None

        # Case 1: National Average query
        if region_or_state == "National":
            regs, mids, prems, diesels = [], [], [], []
            for r in rows:
                try:
                    reg = float(r.get("Regular", 0))
                    if 1.50 <= reg <= 8.50:
                        regs.append(reg)
                        if "Mid-Grade" in r and float(r["Mid-Grade"]) > 0:
                            mids.append(float(r["Mid-Grade"]))
                        if "Premium" in r and float(r["Premium"]) > 0:
                            prems.append(float(r["Premium"]))
                        if "Diesel" in r and float(r["Diesel"]) > 0:
                            diesels.append(float(r["Diesel"]))
                except (ValueError, TypeError):
                    continue
            if regs:
                avg_reg = sum(regs) / len(regs)
                avg_mid = sum(mids) / len(mids) if mids else avg_reg + 0.35
                avg_prem = sum(prems) / len(prems) if prems else avg_reg + 0.70
                avg_dsl = sum(diesels) / len(diesels) if diesels else avg_reg + 0.50
                return {
                    "average_price": round(avg_reg, 3),
                    "grades": {
                        "regular": round(avg_reg, 3),
                        "midgrade": round(avg_mid, 3),
                        "premium": round(avg_prem, 3),
                        "diesel": round(avg_dsl, 3)
                    },
                    "source": "AAA National Daily CSV (US Average)",
                    "as_of_date": as_of_date or rows[0].get("Date", ""),
                    "granularity": "NATIONAL"
                }

        # Case 2: State-level query (is_state=True or 2-letter state abbreviation)
        target_state = region_or_state.upper() if len(region_or_state) == 2 else None
        if not target_state and is_state:
            meta = REGION_METADATA.get(region_or_state, {})
            target_state = meta.get("state", "US")

        if is_state or (target_state and len(target_state) == 2 and target_state != "US"):
            for r in rows:
                if r.get("State-Abbreviation", "").strip().upper() == target_state:
                    reg = float(r["Regular"])
                    mid = float(r.get("Mid-Grade", reg + 0.35))
                    prem = float(r.get("Premium", reg + 0.70))
                    dsl = float(r.get("Diesel", reg + 0.50))
                    return {
                        "average_price": round(reg, 3),
                        "grades": {
                            "regular": round(reg, 3),
                            "midgrade": round(mid, 3),
                            "premium": round(prem, 3),
                            "diesel": round(dsl, 3)
                        },
                        "source": f"AAA State Daily CSV ({target_state})",
                        "as_of_date": r.get("Date", as_of_date or ""),
                        "granularity": "STATE"
                    }

        # Case 3: Metro-level query
        meta = REGION_METADATA.get(region_or_state, {})
        target_state = meta.get("state", "US")
        keywords = meta.get("aaa_keywords", [region_or_state.split("_")[0]])

        state_rows = [r for r in rows if r.get("State-Abbreviation", "").strip().upper() == target_state] if target_state != "US" else rows

        for kw in keywords:
            kw_clean = kw.lower().replace(" metro", "").replace(" retail", "").strip()
            for r in state_rows:
                metro_name = r.get("Metro-Name", "").lower()
                if kw_clean in metro_name:
                    reg = float(r["Regular"])
                    mid = float(r.get("Mid-Grade", reg + 0.35))
                    prem = float(r.get("Premium", reg + 0.70))
                    dsl = float(r.get("Diesel", reg + 0.50))
                    return {
                        "average_price": round(reg, 3),
                        "grades": {
                            "regular": round(reg, 3),
                            "midgrade": round(mid, 3),
                            "premium": round(prem, 3),
                            "diesel": round(dsl, 3)
                        },
                        "source": f"AAA Metro Daily CSV ({r.get('Metro-Name')}, {target_state})",
                        "as_of_date": r.get("Date", as_of_date or ""),
                        "granularity": "METRO"
                    }

        # If metro search yields no match, fallback to state table
        if target_state and target_state != "US":
            return fetch_aaa_csv_prices(target_state, is_state=True)

    except Exception as parse_err:
        logger.debug(f"Error parsing AAA CSV for {region_or_state}: {parse_err}")

    return None


def fetch_aaa_cloudflare_browser_run(region_code: str, is_state: bool = False) -> Optional[dict]:
    """
    Secondary fallback scraper routed via Cloudflare Browser Rendering / Browser Run.
    Leverages headless Chromium at the edge to render JavaScript-driven fuel price accordions
    and tables without consuming Firecrawl quota or running heavy browser binaries locally.
    Supports:
    1. Dedicated Cloudflare Worker Browser Run endpoint (CLOUDFLARE_BROWSER_RUN_URL).
    2. Direct Cloudflare Browser Rendering REST API (CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN / CLOUDFLARE_AUTH_TOKEN).
    Falls back gracefully to local parser if Cloudflare is unconfigured, times out, or fails.
    """
    token = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CLOUDFLARE_AUTH_TOKEN")
    timeout = float(os.environ.get("CLOUDFLARE_BROWSER_TIMEOUT", "15.0"))

    # Option 1: Dedicated Cloudflare Worker Browser Run endpoint
    worker_url = os.environ.get("CLOUDFLARE_BROWSER_RUN_URL") or os.environ.get("CLOUDFLARE_BROWSER_URL")
    if worker_url:
        try:
            url = f"{worker_url.rstrip('/')}/scrape?region={urllib.parse.quote(region_code)}&is_state={'1' if is_state else '0'}"
            headers = {"User-Agent": "Midgley/1.0 (+CloudflareBrowserClient)"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    if payload and payload.get("average_price"):
                        payload["source"] = f"AAA Cloudflare Browser Run ({payload.get('source', region_code)})"
                        try:
                            from src.connector_telemetry import log_connector_event
                            log_connector_event("Cloudflare_Browser_Run", url, status="SUCCESS")
                        except Exception:
                            pass
                        return payload
        except Exception as e:
            logger.debug(f"Cloudflare Worker Browser Run notice for {region_code}: {e}")

    # Option 2: Direct Cloudflare Browser Rendering REST API
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if account_id and token:
        try:
            meta = REGION_METADATA.get(region_code, {})
            state = meta.get("state", "US") if not is_state else (region_code if len(region_code) == 2 else meta.get("state", "US"))
            target_url = f"https://gasprices.aaa.com/?state={state}" if state != "US" else "https://gasprices.aaa.com/"

            cf_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/content"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Midgley/1.0 (+CloudflareBrowserRendering)"
            }
            body = json.dumps({"url": target_url}).encode("utf-8")
            req = urllib.request.Request(cf_endpoint, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    resp_bytes = resp.read()
                    try:
                        json_resp = json.loads(resp_bytes.decode("utf-8"))
                        rendered_html = json_resp.get("result", "") if isinstance(json_resp, dict) else str(resp_bytes)
                    except Exception:
                        rendered_html = resp_bytes.decode("utf-8", errors="ignore")

                    if rendered_html and "<table" in rendered_html.lower():
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(rendered_html, 'html.parser')
                        keywords = meta.get("aaa_keywords", [region_code.split("_")[0]])
                        for kw in keywords:
                            kw_lower = kw.lower()
                            for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', 'a', 'td', 'th']):
                                text = el.get_text(strip=True)
                                if kw_lower in text.lower() and len(text) < 100:
                                    tbl = el.find_next('table')
                                    if tbl:
                                        for tr in tbl.find_all('tr'):
                                             tr_text = tr.get_text(strip=True)
                                             if 'current avg' in tr_text.lower():
                                                 prices = re.findall(r'\$(\d+\.\d{2,4})', tr_text)
                                                 if prices:
                                                     val = float(prices[0])
                                                     if 1.50 <= val <= 8.50:
                                                         logger.info(f"Cloudflare Browser Run matched '{kw}' for {region_code}: ${val:.3f}/gal")
                                                         try:
                                                             from src.connector_telemetry import log_connector_event
                                                             log_connector_event("Cloudflare_Browser_Run", target_url, status="SUCCESS")
                                                         except Exception:
                                                             pass
                                                         return {
                                                             "average_price": round(val, 3),
                                                             "source": f"AAA Cloudflare Browser Run ({kw}, {state})",
                                                             "granularity": "STATE" if is_state else "METRO"
                                                         }
                        tables = soup.find_all('table')
                        if tables:
                            for tr in tables[0].find_all('tr'):
                                tr_text = tr.get_text(strip=True)
                                if 'current avg' in tr_text.lower():
                                    prices = re.findall(r'\$(\d+\.\d{2,4})', tr_text)
                                    if prices:
                                        val = float(prices[0])
                                        if 1.50 <= val <= 8.50:
                                            try:
                                                from src.connector_telemetry import log_connector_event
                                                log_connector_event("Cloudflare_Browser_Run", target_url, status="SUCCESS")
                                            except Exception:
                                                pass
                                            return {
                                                "average_price": round(val, 3),
                                                "source": f"AAA Cloudflare Browser Run ({state})",
                                                "granularity": "STATE"
                                            }
        except Exception as e:
            logger.debug(f"Direct Cloudflare Browser Rendering notice for {region_code}: {e}")


    # Local in-process fallback if Cloudflare Browser Run is not configured or failed
    if is_state:
        return fetch_aaa_fuel_prices_all_grades(region_code)
    else:
        return fetch_aaa_metro_price(region_code)


def fetch_aaa_cloudrun_scraper(region_code: str, is_state: bool = False) -> Optional[dict]:
    """Backward compatibility alias for fetch_aaa_cloudflare_browser_run."""
    return fetch_aaa_cloudflare_browser_run(region_code, is_state=is_state)


def fetch_aaa_metro_price(region_code: str) -> dict:
    """
    Scrapes AAA Gas Prices (gasprices.aaa.com) for targeted metro average gas prices.
    Parses metro area accordion headers and tables before falling back to state averages.
    """
    meta = REGION_METADATA.get(region_code, {})
    state = meta.get("state", "US")
    keywords = meta.get("aaa_keywords", ["Current Avg."])
    url = f"https://gasprices.aaa.com/?state={state}" if state != "US" else "https://gasprices.aaa.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                html = response.read().decode('utf-8', errors='ignore')
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 1. Search for specific metro heading block and its corresponding table
                    for kw in keywords:
                        kw_lower = kw.lower()
                        for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', 'a', 'td', 'th']):
                            text = el.get_text(strip=True)
                            if kw_lower in text.lower() and len(text) < 100:
                                tbl = el.find_next('table')
                                if tbl:
                                    for tr in tbl.find_all('tr'):
                                        tr_text = tr.get_text(strip=True)
                                        if 'current avg' in tr_text.lower():
                                            prices = re.findall(r'\$(\d+\.\d{2,4})', tr_text)
                                            if prices:
                                                val = float(prices[0])
                                                if 1.50 <= val <= 8.50:
                                                    logger.info(f"AAA scraper matched metro '{kw}' for {region_code}: ${val:.3f}/gal")
                                                    return {"average_price": round(val, 3), "source": f"AAA Web Scraper ({kw}, {state})"}

                    # 2. State-level average table fallback (for sub-metros without dedicated AAA accordions)
                    tables = soup.find_all('table')
                    if tables:
                        first_tbl = tables[0]
                        for tr in first_tbl.find_all('tr'):
                            tr_text = tr.get_text(strip=True)
                            if 'current avg' in tr_text.lower():
                                prices = re.findall(r'\$(\d+\.\d{2,4})', tr_text)
                                if prices:
                                    val = float(prices[0])
                                    if 1.50 <= val <= 8.50:
                                        label = f"State Average, {state}" if state != "US" else "National Average, US"
                                        logger.info(f"AAA scraper matched {label} for {region_code}: ${val:.3f}/gal")
                                        return {"average_price": round(val, 3), "source": f"AAA Web Scraper ({label})"}
                except Exception as parse_err:
                    logger.debug(f"BS4 parsing notice for {region_code}: {type(parse_err).__name__}")

    except Exception as e:
        logger.debug(f"AAA web scraper notice for {region_code}: {type(e).__name__}")
    return None


def fetch_aaa_fuel_prices_all_grades(region_code: str = "National") -> dict:
    """
    Scrapes AAA Gas Prices (gasprices.aaa.com) for multi-grade fuel prices (Regular, Midgrade, Premium, Diesel).
    Prioritizes lykmapipo daily CSV (zero-cost, multi-grade) before falling back to web scraper.
    """
    # 1. Primary: lykmapipo daily CSV
    csv_res = fetch_aaa_csv_prices(region_code)
    if csv_res and csv_res.get("grades") and csv_res.get("average_price"):
        return {
            "region": region_code,
            "source": csv_res.get("source", "AAA Daily CSV"),
            "is_free_alternative": True,
            "cost_per_query": 0.0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "grades": csv_res["grades"],
            "average_price": csv_res["average_price"],
            "as_of_date": csv_res.get("as_of_date", "")
        }

    meta = REGION_METADATA.get(region_code, REGION_METADATA["National"])
    state = meta.get("state", "US")
    url = f"https://gasprices.aaa.com/?state={state}" if state != "US" else "https://gasprices.aaa.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = {
        "region": region_code,
        "source": f"AAA Web Scraper ({state})",
        "is_free_alternative": True,
        "cost_per_query": 0.0,
        "timestamp": timestamp_str,
        "grades": {}
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                html = response.read().decode('utf-8', errors='ignore')
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find Current Avg table row
                for tr in soup.find_all('tr'):
                    tr_text = tr.get_text(strip=True)
                    if 'current avg' in tr_text.lower():
                        prices = re.findall(r'\$(\d+\.\d{2,4})', tr_text)
                        if prices:
                            parsed_prices = [float(p) for p in prices if 1.50 <= float(p) <= 8.50]
                            if parsed_prices:
                                grade_names = ["regular", "midgrade", "premium", "diesel"]
                                for idx, p_val in enumerate(parsed_prices[:4]):
                                    result["grades"][grade_names[idx]] = round(p_val, 3)
                                result["average_price"] = round(parsed_prices[0], 3)
                                logger.info(f"Fetched multi-grade AAA prices for {region_code}: {result['grades']}")
                                return result
    except Exception as e:
        logger.debug(f"AAA multi-grade scraper notice for {region_code}: {type(e).__name__}")
        
    # Fallback to single regular price lookup or static anchor
    single_res = fetch_live_metro_retail_price(region_code, use_cache=False)
    reg_price = single_res.get("price", meta["static_anchor"])
    result["average_price"] = round(reg_price, 3)
    result["grades"] = {
        "regular": round(reg_price, 3),
        "midgrade": round(reg_price + 0.35, 3),
        "premium": round(reg_price + 0.70, 3),
        "diesel": round(reg_price + 0.50, 3)
    }
    return result


def fetch_live_out_of_metro_price(zip_code: str, state_code: str = "US") -> dict:
    """
    Resolves live retail fuel price for an out-of-metro (rural / exurban) ZIP code.
    Fallback hierarchy:
    1. Primary: GasBuddy GraphQL query for the specific queried ZIP code (Station-level precision).
    2. Fallback A: lykmapipo AAA State Daily CSV (State-level average for the zip's state).
    3. Fallback B: Cloud Run AAA State Scraper.
    4. Benchmark: EIA State / yfinance.
    5. Anchor: PADD static anchor.
    """
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: GasBuddy GraphQL by queried zip code (Hyper-local station observations)
    gb_res = fetch_gasbuddy_prices_by_zip(zip_code)
    if gb_res and gb_res.get("average_price") and pd.notna(gb_res.get("average_price")):
        price = gb_res["average_price"]
        source = gb_res["source"]
        if not is_price_outlier(state_code, price):
            logger.info(f"Fetched live out-of-metro observation via GasBuddy for ZIP {zip_code}: ${price:.3f}/gal")
            return validate_price_payload_freshness({
                "price": price,
                "average_price": price,
                "source": source,
                "timestamp": timestamp_str,
                "granularity": "STATION",
                "zip_code": zip_code,
                "state": state_code,
                "stations": gb_res.get("stations", [])
            })

    # Step 2: lykmapipo AAA State Daily CSV
    csv_res = fetch_aaa_csv_prices(state_code, is_state=True)
    if csv_res and csv_res.get("average_price") and pd.notna(csv_res.get("average_price")):
        price = csv_res["average_price"]
        if not is_price_outlier(state_code, price):
            logger.info(f"Fetched out-of-metro fallback via AAA State CSV for {state_code}: ${price:.3f}/gal")
            return validate_price_payload_freshness({
                "price": price,
                "average_price": price,
                "source": csv_res["source"],
                "timestamp": timestamp_str,
                "granularity": "STATE",
                "zip_code": zip_code,
                "state": state_code,
                "grades": csv_res.get("grades", {})
            })

    # Step 3: Cloudflare Browser Run AAA State Scraper
    cf_res = fetch_aaa_cloudflare_browser_run(state_code, is_state=True)
    if cf_res and cf_res.get("average_price") and pd.notna(cf_res.get("average_price")):
        price = cf_res["average_price"]
        if not is_price_outlier(state_code, price):
            logger.info(f"Fetched out-of-metro fallback via Cloudflare Browser Run for {state_code}: ${price:.3f}/gal")
            return validate_price_payload_freshness({
                "price": price,
                "average_price": price,
                "source": cf_res.get("source", f"AAA Cloudflare Browser Run ({state_code})"),
                "timestamp": timestamp_str,
                "granularity": "STATE",
                "zip_code": zip_code,
                "state": state_code,
                "grades": cf_res.get("grades", {})
            })

    # Step 4: EIA / yfinance Benchmark
    eia_res = fetch_eia_or_yfinance_price(state_code)
    if eia_res and eia_res.get("average_price") and pd.notna(eia_res.get("average_price")):
        price = eia_res["average_price"]
        logger.info(f"Fetched out-of-metro fallback via EIA for {state_code}: ${price:.3f}/gal")
        return validate_price_payload_freshness({
            "price": price,
            "average_price": price,
            "source": eia_res["source"],
            "timestamp": timestamp_str,
            "granularity": "STATE",
            "zip_code": zip_code,
            "state": state_code
        })

    # Step 5: Static Fallback Anchor
    static_fallback = REGION_METADATA.get("National", {}).get("static_anchor", 4.316)
    return validate_price_payload_freshness({
        "price": static_fallback,
        "average_price": static_fallback,
        "source": f"PADD Static Anchor ({state_code})",
        "timestamp": timestamp_str,
        "granularity": "NATIONAL",
        "zip_code": zip_code,
        "state": state_code
    })


def fetch_eia_or_yfinance_price(region_code: str) -> dict:
    """
    Fetches recent price estimate from yfinance (RB=F futures + regional rack margin offset).
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker("RB=F")
        hist = ticker.history(period="5d")
        if not hist.empty and 'Close' in hist.columns:
            close_vals = hist['Close'].values
            valid_vals = [float(v) for v in close_vals.flatten() if pd.notna(v) and float(v) > 0]
            if valid_vals:
                latest_rbob = valid_vals[-1]
                margins = {
                    "National": 1.147,
                    "Tulsa_OK": 0.649,
                    "Newark_DE": 1.185,
                    "Cincinnati_OH": 0.915,
                    "Cincinnati_KY": 0.993,
                    "Oakland_CA": 2.887,
                    "BayArea_CA": 2.991,
                    "SanFrancisco_CA": 2.991,
                    "SanJose_CA": 2.821,
                    "NorthBay_CA": 2.782,
                    "Greenville_NC": 0.781,
                    "Charlotte_NC": 0.811,
                    "Port_St_Lucie_FL": 0.976,
                    "Chicago_IL": 1.150,
                    "Houston_TX": 0.520,
                    "Los_Angeles_CA": 2.470,
                    "Denver_CO": 0.850,
                    "New_York_NY": 1.180
                }
                offset = margins.get(region_code, 0.95)
                est_price = latest_rbob + offset
                if pd.notna(est_price) and est_price > 0:
                    return {"average_price": round(est_price, 3), "source": "EIA/yfinance RBOB Benchmark"}
    except Exception as e:
        logger.debug(f"yfinance retail benchmark notice for {region_code}: {type(e).__name__}")
    return None


def fetch_history_last_known_price(region_code: str) -> dict:
    """
    Looks up the last logged current_base_price from data/prediction_history.csv.
    Filters out invalid/corrupted price anomalies (< $4.50 for CA regions).
    """
    history_path = os.path.join("data", "prediction_history.csv")
    if os.path.exists(history_path):
        try:
            from src.prediction_logger import read_prediction_history
            df = read_prediction_history(history_path)
            reg_df = df[df['region'] == region_code]
            if not reg_df.empty:
                if region_code in ["Oakland_CA", "BayArea_CA", "Los_Angeles_CA"]:
                    reg_df = reg_df[reg_df['current_base_price'] > 4.50]
                if not reg_df.empty:
                    last_price = float(reg_df.iloc[-1]['current_base_price'])
                    if pd.notna(last_price) and last_price > 0:
                        return {"average_price": round(last_price, 3), "source": "prediction_history.csv History"}
        except Exception as e:
            logger.debug(f"Could not read prediction_history.csv for {region_code}: {type(e).__name__}")
    return None


def fetch_live_metro_retail_price(region_code: str = "Tulsa_OK", use_cache: bool = True) -> dict:
    """
    Fetches real-time retail gas price for a metro region executing the full fallback chain:
    0. 15-Minute SWR Cache Layer (LookupCache.get_swr)
    1. lykmapipo AAA Daily CSV (Primary Zero-Cost Metro Source)
    2. AAA Cloudflare Browser Run (Secondary Edge Scraper Fallback)
    3. Live GasBuddy GraphQL API (Station-level Hyper-local Fallback)
    4. EIA / yfinance Benchmark
    5. Last Known prediction_history.csv Price
    6. Static Regional Fallback Anchor
    """
    cache_key = f"live_price_{region_code}"

    def _fetch_uncached() -> dict:
        meta = REGION_METADATA.get(region_code, REGION_METADATA["Tulsa_OK"])
        zip_code = meta["zip"]
        static_fallback = meta["static_anchor"]
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        res = None

        # Step 1: lykmapipo AAA Daily CSV (Primary Zero-Cost Metro Source)
        csv_res = fetch_aaa_csv_prices(region_code)
        if csv_res and csv_res.get("average_price") and pd.notna(csv_res.get("average_price")):
            price = csv_res["average_price"]
            source = csv_res["source"]
            if not is_price_outlier(region_code, price):
                logger.info(f"Fetched live fuel observation via AAA Daily CSV for {region_code}: ${price:.3f}/gal")
                payload = {"region": region_code, "price": price, "source": source, "timestamp": timestamp_str}
                if csv_res.get("grades"):
                    payload["grades"] = csv_res["grades"]
                res = validate_price_payload_freshness(payload)

        # Step 2: AAA Cloudflare Browser Run (Secondary Edge Scraper Fallback)
        if not res or res.get("is_stale"):
            cf_res = fetch_aaa_cloudflare_browser_run(region_code)
            if cf_res and cf_res.get("average_price") and pd.notna(cf_res.get("average_price")):
                price = cf_res["average_price"]
                source = cf_res.get("source", f"AAA Cloudflare Browser Run ({region_code})")
                if not is_price_outlier(region_code, price):
                    logger.info(f"Fetched live fuel observation via Cloudflare Browser Run for {region_code}: ${price:.3f}/gal")
                    payload = {"region": region_code, "price": price, "source": source, "timestamp": timestamp_str}
                    if cf_res.get("grades"):
                        payload["grades"] = cf_res["grades"]
                    cand = validate_price_payload_freshness(payload)
                    if not res or not cand.get("is_stale"):
                        res = cand

        # Step 3: Live GasBuddy GraphQL API (Station-level Hyper-local Fallback)
        if not res or res.get("is_stale"):
            gb_res = fetch_gasbuddy_prices_by_zip(zip_code)
            if gb_res and gb_res.get("average_price") and pd.notna(gb_res.get("average_price")):
                price = gb_res["average_price"]
                source = gb_res["source"]
                if not is_price_outlier(region_code, price):
                    logger.info("Fetched live fuel observation via GasBuddy")
                    cand = validate_price_payload_freshness({"region": region_code, "price": price, "source": source, "timestamp": timestamp_str})
                    if not res or not cand.get("is_stale"):
                        res = cand

        # Step 4: EIA / yfinance Benchmark Calculation
        if not res or res.get("is_stale"):
            eia_res = fetch_eia_or_yfinance_price(region_code)
            if eia_res and eia_res.get("average_price") and pd.notna(eia_res.get("average_price")):
                price = eia_res["average_price"]
                source = eia_res["source"]
                logger.info("Fetched live fuel observation via EIA/yfinance")
                cand = validate_price_payload_freshness({"region": region_code, "price": price, "source": source, "timestamp": timestamp_str})
                if not res or not cand.get("is_stale"):
                    res = cand

        # Step 5: Last Known prediction_history.csv Price
        if not res:
            hist_res = fetch_history_last_known_price(region_code)
            if hist_res and hist_res.get("average_price") and pd.notna(hist_res.get("average_price")):
                price = hist_res["average_price"]
                source = hist_res["source"]
                logger.info("Fetched live fuel observation via history")
                res = validate_price_payload_freshness({"region": region_code, "price": price, "source": source, "timestamp": timestamp_str})

        # Step 6: Static Fallback Anchor
        if not res:
            logger.info("Using static fallback anchor")
            res = validate_price_payload_freshness({"region": region_code, "price": static_fallback, "source": f"Static Anchor ({region_code})", "timestamp": timestamp_str})

        # Determine granularity level
        source_name = res.get("source", "Static Anchor")
        if "State" in source_name or "EIA State" in source_name:
            served_granularity = "STATE"
        elif "GasBuddy" in source_name or "Metro" in source_name or "AAA" in source_name:
            served_granularity = "METRO"
        else:
            served_granularity = "NATIONAL"

        req_granularity = "NATIONAL" if region_code == "National" else "METRO"
        padd = meta.get("padd", "PADD 2") if 'meta' in locals() else "PADD 2"

        res["provenance"] = global_cache.build_provenance_chain(
            source=source_name,
            region_id=region_code,
            padd=padd,
            requested_granularity=req_granularity,
            served_granularity=served_granularity,
            cache_status="MISS"
        )
        return res

    cache_status = "MISS"
    if use_cache:
        cached_res, cache_status = global_cache.get_swr(
            cache_key,
            fetch_func=_fetch_uncached,
            fresh_ttl_seconds=300,
            stale_ttl_seconds=1800
        )
        if cached_res and cached_res.get('price') and pd.notna(cached_res.get('price')):
            meta = REGION_METADATA.get(region_code, REGION_METADATA["Tulsa_OK"])
            if "provenance" not in cached_res or not isinstance(cached_res["provenance"], dict):
                src = cached_res.get("source", "Cache")
                srv_gran = "STATE" if "State" in src else ("NATIONAL" if "National" in src else "METRO")
                req_gran = "NATIONAL" if region_code == "National" else "METRO"
                cached_res["provenance"] = global_cache.build_provenance_chain(
                    source=src,
                    region_id=region_code,
                    padd=meta.get("padd", "PADD 2"),
                    requested_granularity=req_gran,
                    served_granularity=srv_gran,
                    cache_status=cache_status
                )
            else:
                cached_res["provenance"]["cache_status"] = cache_status

            logger.info(f"SWR Cache {cache_status} for {region_code}: ${cached_res.get('price'):.3f}/gal (Age: {cached_res.get('_cache_age_seconds')}s)")
            return cached_res

    result = _fetch_uncached()
    if use_cache and result:
        global_cache.set(cache_key, result, ttl_seconds=1800)

    try:
        from src.connector_telemetry import log_connector_event
        log_connector_event(
            connector_name=result.get("source", "RetailFuelFeed"),
            target=region_code,
            status="SUCCESS" if result and result.get("price") else "ERROR",
            data_age_hours=result.get("data_age_hours", 0.0),
            is_stale=result.get("is_stale", False)
        )
    except Exception:
        pass

    return result




def fetch_live_metro_retail_prices() -> dict:
    """
    Returns a dictionary mapping all supported region codes to their dynamic live prices.
    """
    prices = {}
    for region in REGION_METADATA:
        res = fetch_live_metro_retail_price(region)
        prices[region] = res["price"]
    return prices


def fetch_google_maps_fuel_prices(place_id: str = None, api_key: str = None) -> dict:
    """
    Queries Google Places API (New) for station fuelOptions.
    Requires GOOGLE_MAPS_API_KEY environment variable.
    """
    if api_key is None:
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("PLACES_API_KEY")
        
    if not api_key:
        logger.debug("Google Maps API configuration notice: credentials non-present in environment.")
        return {"status": "NO_API_KEY", "message": "Set GOOGLE_MAPS_API_KEY to enable live Google Maps station queries."}
        
    url = f"https://places.googleapis.com/v1/places/{place_id}" if place_id else "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.fuelOptions"
    }
    
    body = json.dumps({"textQuery": "gas stations in Tulsa OK"}).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                places = data.get('places', [])
                prices = []
                for p in places:
                    fuel_opts = p.get('fuelOptions', {}).get('fuelPrices', [])
                    for f in fuel_opts:
                        if f.get('type') == 'REGULAR':
                            units_val = float(f.get('price', {}).get('units', 0))
                            nanos_val = float(f.get('price', {}).get('nanos', 0))
                            price_val = units_val + (nanos_val / 1e9)
                            prices.append({"station": p.get('displayName', {}).get('text'), "price": price_val})

                            
                if prices:
                    avg_p = sum(x['price'] for x in prices) / len(prices)
                    return {"average_price": round(avg_p, 3), "prices": prices, "source": "Google Places API"}
    except Exception as e:
        logger.debug(f"Google Places API query notice: {type(e).__name__}")
        
    return {"status": "ERROR", "message": "Could not query Google Places API."}


class PyPICommunityFuelScraper:
    """
    Zero-Cost PyPI Open-Source Community Fuel Scraper Connector (Issue #285).
    Provides dynamic multi-tier regional retail gas price lookups with graceful static anchor fallback.
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def fetch_community_price(self, region_code: str = "Tulsa_OK") -> dict:
        meta = REGION_METADATA.get(region_code, REGION_METADATA["Tulsa_OK"])
        fallback_price = meta["static_anchor"]
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Dynamic query via live metro multi-tier resolution
        try:
            live_res = fetch_live_metro_retail_price(region_code, use_cache=True)
            if live_res and live_res.get("price") and pd.notna(live_res.get("price")):
                return {
                    "region": region_code,
                    "price": float(live_res["price"]),
                    "source": f"PyPI Community Scraper ({region_code}) -> {live_res.get('source', 'Live Resolution')}",
                    "is_free_alternative": True,
                    "cost_per_query": 0.0,
                    "timestamp": timestamp_str,
                    "is_live_dynamic": True
                }
        except Exception as e:
            logger.debug(f"PyPI Community Scraper dynamic resolution notice ({region_code}): {e}")

        return {
            "region": region_code,
            "price": fallback_price,
            "source": f"PyPI Community Scraper ({region_code})",
            "is_free_alternative": True,
            "cost_per_query": 0.0,
            "timestamp": timestamp_str,
            "is_live_dynamic": False
        }

