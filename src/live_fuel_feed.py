"""
Live Fuel Price API Feed Module (src/live_fuel_feed.py)
Provides integration functions for:
1. GasBuddy GraphQL API (Station-level real-time prices in Tulsa Metro).
2. Google Places API (New Places API fuelOptions endpoint).
3. EIA API v2 (Official Energy Information Administration Oklahoma retail gas price series).
"""

import os
import json
import urllib.request
import urllib.parse
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# GasBuddy Internal GraphQL Endpoint
GASBUDDY_GRAPHQL_URL = "https://www.gasbuddy.com/graphql"

def fetch_gasbuddy_tulsa_prices(zip_code: str = "74103") -> dict:
    """
    Queries GasBuddy's GraphQL API for real-time station prices in Tulsa, OK.
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
                    logger.info(f"Fetched {len(station_prices)} GasBuddy stations in Tulsa ({zip_code}). Avg Regular: ${avg_price:.3f}/gal")
                    return {"average_price": round(avg_price, 3), "stations": station_prices, "source": "GasBuddy GraphQL"}
    except Exception as e:
        logger.debug(f"GasBuddy GraphQL query notice: {e}")
        
    return {"average_price": 3.89, "stations": [], "source": "Tulsa Fallback Anchor"}


def fetch_google_maps_fuel_prices(place_id: str = None, api_key: str = None) -> dict:
    """
    Queries Google Places API (New) for station fuelOptions (Regular, Midgrade, Premium, Diesel).
    Requires GOOGLE_MAPS_API_KEY environment variable.
    """
    if api_key is None:
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("PLACES_API_KEY")
        
    if not api_key:
        logger.debug("GOOGLE_MAPS_API_KEY not found in environment.")
        return {"status": "NO_API_KEY", "message": "Set GOOGLE_MAPS_API_KEY to enable live Google Maps station queries."}
        
    # Endpoint for Google Places API (New)
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
