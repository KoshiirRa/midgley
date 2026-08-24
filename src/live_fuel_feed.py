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

REGION_METADATA = {
    "National": {
        "zip": "20001",
        "state": "US",
        "static_anchor": 3.184,
        "name": "National Wholesale / US Average"
    },
    "Tulsa_OK": {
        "zip": "74103",
        "state": "OK",
        "static_anchor": 3.890,
        "name": "Tulsa, OK Metro Retail"
    },
    "Newark_DE": {
        "zip": "19711",
        "state": "DE",
        "static_anchor": 3.350,
        "name": "Newark, DE Metro Retail"
    },
    "Cincinnati_OH": {
        "zip": "45202",
        "state": "OH",
        "static_anchor": 3.450,
        "name": "Cincinnati, OH Retail"
    },
    "Cincinnati_KY": {
        "zip": "41011",
        "state": "KY",
        "static_anchor": 3.325,
        "name": "Northern Kentucky Retail"
    },
    "Oakland_CA": {
        "zip": "94612",
        "state": "CA",
        "static_anchor": 5.550,
        "name": "Oakland, CA Metro Retail"
    },
    "BayArea_CA": {
        "zip": "94102",
        "state": "CA",
        "static_anchor": 5.650,
        "name": "SF Bay Area 9-County Avg"
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
        logger.debug(f"GasBuddy GraphQL query notice for zip {zip_code}: {e}")
        
    return None


def fetch_gasbuddy_tulsa_prices(zip_code: str = "74103") -> dict:
    """Backward compatibility wrapper for Tulsa GasBuddy query."""
    res = fetch_gasbuddy_prices_by_zip(zip_code)
    if res:
        return res
    return {"average_price": 3.89, "stations": [], "source": "Tulsa Fallback Anchor"}


def fetch_aaa_metro_price(region_code: str) -> dict:
    """
    Scrapes AAA Gas Prices (gasprices.aaa.com) for state/metro average gas prices.
    """
    meta = REGION_METADATA.get(region_code, {})
    state = meta.get("state", "US")
    url = f"https://gasprices.aaa.com/?state={state}" if state != "US" else "https://gasprices.aaa.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                html = response.read().decode('utf-8', errors='ignore')
                matches = re.findall(r'\$(\d+\.\d{2,3})', html)
                if matches:
                    valid_prices = [float(m) for m in matches if 1.50 <= float(m) <= 7.50]
                    if valid_prices:
                        avg_p = valid_prices[0]
                        return {"average_price": round(avg_p, 3), "source": f"AAA Web Scraper ({state})"}
    except Exception as e:
        logger.debug(f"AAA web scraper notice for {region_code}: {e}")
    return None


def fetch_eia_or_yfinance_price(region_code: str) -> dict:
    """
    Fetches recent price estimate from yfinance (RB=F futures + regional rack margin offset).
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker("RB=F")
        hist = ticker.history(period="5d")
        if not hist.empty and 'Close' in hist.columns:
            latest_rbob = float(hist['Close'].iloc[-1])
            margins = {
                "National": 0.0,
                "Tulsa_OK": 0.706,
                "Newark_DE": 0.166,
                "Cincinnati_OH": 0.266,
                "Cincinnati_KY": 0.141,
                "Oakland_CA": 2.366,
                "BayArea_CA": 2.466
            }
            offset = margins.get(region_code, 0.50)
            est_price = latest_rbob + offset
            return {"average_price": round(est_price, 3), "source": "EIA/yfinance RBOB Benchmark"}
    except Exception as e:
        logger.debug(f"yfinance retail benchmark notice for {region_code}: {e}")
    return None


def fetch_history_last_known_price(region_code: str) -> dict:
    """
    Looks up the last logged current_base_price from data/prediction_history.csv.
    """
    history_path = os.path.join("data", "prediction_history.csv")
    if os.path.exists(history_path):
        try:
            df = pd.read_csv(history_path)
            reg_df = df[df['region'] == region_code]
            if not reg_df.empty:
                last_price = float(reg_df.iloc[-1]['current_base_price'])
                if last_price > 0:
                    return {"average_price": round(last_price, 3), "source": "prediction_history.csv History"}
        except Exception as e:
            logger.debug(f"Could not read prediction_history.csv for {region_code}: {e}")
    return None


def fetch_live_metro_retail_price(region_code: str = "Tulsa_OK", use_cache: bool = True) -> dict:
    """
    Fetches real-time retail gas price for a metro region executing the full fallback chain:
    0. 15-Minute SQLite/In-Memory Cache (LookupCache)
    1. Live GasBuddy GraphQL API
    2. AAA Metro Web Scraper
    3. EIA / yfinance Benchmark
    4. Last Known prediction_history.csv Price
    5. Static Regional Fallback Anchor
    """
    cache_key = f"live_price_{region_code}"
    if use_cache:
        cached_res = global_cache.get(cache_key)
        if cached_res:
            logger.info(f"Cache hit for {region_code}: ${cached_res.get('price'):.3f}/gal (Age: {cached_res.get('_cache_age_seconds')}s)")
            return cached_res

    meta = REGION_METADATA.get(region_code, REGION_METADATA["Tulsa_OK"])
    zip_code = meta["zip"]
    static_fallback = meta["static_anchor"]
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = None

    # Step 1: Live GasBuddy GraphQL API
    gb_res = fetch_gasbuddy_prices_by_zip(zip_code)
    if gb_res and gb_res.get("average_price"):
        price = gb_res["average_price"]
        source = gb_res["source"]
        logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
        result = {"region": region_code, "price": price, "source": source, "timestamp": timestamp_str}

    # Step 2: AAA Metro Web Scraper
    if not result:
        aaa_res = fetch_aaa_metro_price(region_code)
        if aaa_res and aaa_res.get("average_price"):
            price = aaa_res["average_price"]
            source = aaa_res["source"]
            logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
            result = {"region": region_code, "price": price, "source": source, "timestamp": timestamp_str}

    # Step 3: EIA / yfinance Benchmark Calculation
    if not result:
        eia_res = fetch_eia_or_yfinance_price(region_code)
        if eia_res and eia_res.get("average_price"):
            price = eia_res["average_price"]
            source = eia_res["source"]
            logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
            result = {"region": region_code, "price": price, "source": source, "timestamp": timestamp_str}

    # Step 4: Last Known prediction_history.csv Price
    if not result:
        hist_res = fetch_history_last_known_price(region_code)
        if hist_res and hist_res.get("average_price"):
            price = hist_res["average_price"]
            source = hist_res["source"]
            logger.info(f"Fetched live fuel price for {region_code} via {source}: ${price:.3f}/gal")
            result = {"region": region_code, "price": price, "source": source, "timestamp": timestamp_str}

    # Step 5: Static Fallback Anchor
    if not result:
        logger.info(f"Using static fallback anchor for {region_code}: ${static_fallback:.3f}/gal")
        result = {"region": region_code, "price": static_fallback, "source": f"Static Anchor ({region_code})", "timestamp": timestamp_str}

    # Cache successful result
    if use_cache and result:
        global_cache.set(cache_key, result, ttl_seconds=900)

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
        logger.debug("GOOGLE_MAPS_API_KEY not found in environment.")
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
                            price_val = f.get('price', {}).get('units') + f.get('price', {}).get('nanos', 0) / 1e9
                            prices.append({"station": p.get('displayName', {}).get('text'), "price": price_val})
                            
                if prices:
                    avg_p = sum(x['price'] for x in prices) / len(prices)
                    return {"average_price": round(avg_p, 3), "prices": prices, "source": "Google Places API"}
    except Exception as e:
        logger.debug(f"Google Places API query notice: {e}")
        
    return {"status": "ERROR", "message": "Could not query Google Places API."}
