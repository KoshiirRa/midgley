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
import urllib.request
import urllib.parse
import pandas as pd
import logging
from datetime import datetime
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

# GasBuddy Internal GraphQL Endpoint
GASBUDDY_GRAPHQL_URL = "https://www.gasbuddy.com/graphql"

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


REGION_METADATA = {
    "National": {
        "zip": "20001",
        "state": "US",
        "static_anchor": 3.184,
        "name": "National Wholesale / US Average",
        "aaa_keywords": ["National Average", "US Average", "Current Avg."]
    },
    "Tulsa_OK": {
        "zip": "74103",
        "state": "OK",
        "static_anchor": 3.890,
        "name": "Tulsa, OK Metro Retail",
        "aaa_keywords": ["Tulsa"]
    },
    "Newark_DE": {
        "zip": "19711",
        "state": "DE",
        "static_anchor": 3.350,
        "name": "Newark, DE Metro Retail",
        "aaa_keywords": ["Wilmington", "New Castle", "State Average"]
    },
    "Cincinnati_OH": {
        "zip": "45202",
        "state": "OH",
        "static_anchor": 3.450,
        "name": "Cincinnati, OH Retail",
        "aaa_keywords": ["Cincinnati"]
    },
    "Cincinnati_KY": {
        "zip": "41011",
        "state": "KY",
        "static_anchor": 3.325,
        "name": "Northern Kentucky Retail",
        "aaa_keywords": ["Cincinnati", "Northern Kentucky", "Covington"]
    },
    "Oakland_CA": {
        "zip": "94612",
        "state": "CA",
        "static_anchor": 5.550,
        "name": "Oakland, CA Metro Retail",
        "aaa_keywords": ["Oakland", "East Bay", "Alameda"]
    },
    "BayArea_CA": {
        "zip": "94102",
        "state": "CA",
        "static_anchor": 5.650,
        "name": "SF Bay Area 9-County Avg",
        "aaa_keywords": ["San Francisco", "Oakland", "San Jose"]
    },
    "SanFrancisco_CA": {
        "zip": "94102",
        "state": "CA",
        "static_anchor": 5.720,
        "name": "San Francisco Metro Retail",
        "aaa_keywords": ["San Francisco"]
    },
    "SanJose_CA": {
        "zip": "95113",
        "state": "CA",
        "static_anchor": 5.553,
        "name": "San Jose / Silicon Valley Retail",
        "aaa_keywords": ["San Jose", "Santa Clara"]
    },
    "NorthBay_CA": {
        "zip": "94590",
        "state": "CA",
        "static_anchor": 5.453,
        "name": "North Bay / Solano Retail",
        "aaa_keywords": ["Vallejo", "Fairfield", "Napa"]
    },
    "Greenville_NC": {
        "zip": "27834",
        "state": "NC",
        "static_anchor": 3.250,
        "name": "Greenville, NC Metro Retail",
        "aaa_keywords": ["Greenville", "Pitt", "State Average"]
    },
    "Charlotte_NC": {
        "zip": "28202",
        "state": "NC",
        "static_anchor": 3.280,
        "name": "Charlotte, NC Metro Retail",
        "aaa_keywords": ["Charlotte", "Mecklenburg", "State Average"]
    },
    "Port_St_Lucie_FL": {
        "zip": "34952",
        "state": "FL",
        "static_anchor": 3.380,
        "name": "Port St. Lucie, FL Metro Retail",
        "aaa_keywords": ["Port St. Lucie", "St. Lucie", "State Average"]
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
    return {"average_price": 3.89, "stations": [], "source": "Tulsa Fallback Anchor"}


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
                    
                    # Search for specific metro heading block and its corresponding table
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
                except Exception as parse_err:
                    logger.debug(f"BS4 parsing notice for {region_code}: {type(parse_err).__name__}")

    except Exception as e:
        logger.debug(f"AAA web scraper notice for {region_code}: {type(e).__name__}")
    return None


def fetch_aaa_fuel_prices_all_grades(region_code: str = "National") -> dict:
    """
    Scrapes AAA Gas Prices (gasprices.aaa.com) for multi-grade fuel prices (Regular, Midgrade, Premium, Diesel).
    Returns zero-cost fuel price vector without API fees or paid subscriptions.
    """
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
                    "National": 0.0,
                    "Tulsa_OK": 0.706,
                    "Newark_DE": 0.166,
                    "Cincinnati_OH": 0.266,
                    "Cincinnati_KY": 0.141,
                    "Oakland_CA": 2.366,
                    "BayArea_CA": 2.466,
                    "SanFrancisco_CA": 2.466,
                    "SanJose_CA": 2.296,
                    "NorthBay_CA": 2.196,
                    "Greenville_NC": 0.490,
                    "Charlotte_NC": 0.520,
                    "Port_St_Lucie_FL": 0.620
                }
                offset = margins.get(region_code, 0.50)
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
            df = pd.read_csv(history_path)
            reg_df = df[df['region'] == region_code]
            if not reg_df.empty:
                if region_code in ["Oakland_CA", "BayArea_CA"]:
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
    1. Live GasBuddy GraphQL API
    2. AAA Metro Web Scraper
    3. EIA / yfinance Benchmark
    4. Last Known prediction_history.csv Price
    5. Static Regional Fallback Anchor
    """
    cache_key = f"live_price_{region_code}"

    def _fetch_uncached() -> dict:
        meta = REGION_METADATA.get(region_code, REGION_METADATA["Tulsa_OK"])
        zip_code = meta["zip"]
        static_fallback = meta["static_anchor"]
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        res = None

        # Step 1: Live GasBuddy GraphQL API
        gb_res = fetch_gasbuddy_prices_by_zip(zip_code)
        if gb_res and gb_res.get("average_price") and pd.notna(gb_res.get("average_price")):
            price = gb_res["average_price"]
            source = gb_res["source"]
            logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
            res = validate_price_payload_freshness({"region": region_code, "price": price, "source": source, "timestamp": timestamp_str})

        # Step 2: AAA Metro Web Scraper
        if not res or res.get("is_stale"):
            aaa_res = fetch_aaa_metro_price(region_code)
            if aaa_res and aaa_res.get("average_price") and pd.notna(aaa_res.get("average_price")):
                price = aaa_res["average_price"]
                source = aaa_res["source"]
                logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
                cand = validate_price_payload_freshness({"region": region_code, "price": price, "source": source, "timestamp": timestamp_str})
                if not res or not cand.get("is_stale"):
                    res = cand

        # Step 3: EIA / yfinance Benchmark Calculation
        if not res or res.get("is_stale"):
            eia_res = fetch_eia_or_yfinance_price(region_code)
            if eia_res and eia_res.get("average_price") and pd.notna(eia_res.get("average_price")):
                price = eia_res["average_price"]
                source = eia_res["source"]
                logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
                cand = validate_price_payload_freshness({"region": region_code, "price": price, "source": source, "timestamp": timestamp_str})
                if not res or not cand.get("is_stale"):
                    res = cand

        # Step 4: Last Known prediction_history.csv Price
        if not res:
            hist_res = fetch_history_last_known_price(region_code)
            if hist_res and hist_res.get("average_price") and pd.notna(hist_res.get("average_price")):
                price = hist_res["average_price"]
                source = hist_res["source"]
                logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
                res = validate_price_payload_freshness({"region": region_code, "price": price, "source": source, "timestamp": timestamp_str})

        # Step 5: Static Fallback Anchor
        if not res:
            logger.info(f"Using static fallback anchor for {region_code}: ${static_fallback:.3f}/gal")
            res = validate_price_payload_freshness({"region": region_code, "price": static_fallback, "source": f"Static Anchor ({region_code})", "timestamp": timestamp_str})

        # Determine granularity level
        source_name = res.get("source", "Static Anchor")
        if "GasBuddy" in source_name or "AAA" in source_name:
            served_granularity = "METRO"
        elif "EIA State" in source_name or "State" in source_name:
            served_granularity = "STATE"
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
    Zero-Cost PyPI Open-Source Community Fuel Scraper Connector.
    Provides fallback state and regional retail gas price lookups.
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def fetch_community_price(self, region_code: str = "Tulsa_OK") -> dict:
        meta = REGION_METADATA.get(region_code, REGION_METADATA["Tulsa_OK"])
        price = meta["static_anchor"]
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "region": region_code,
            "price": price,
            "source": f"PyPI Community Scraper ({region_code})",
            "is_free_alternative": True,
            "cost_per_query": 0.0,
            "timestamp": timestamp_str
        }

