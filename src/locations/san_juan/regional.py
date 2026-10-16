"""
San Juan Metro & U.S. Caribbean Territories Regional Gas Price Forecasting Module (src/locations/san_juan/regional.py)
Fuses U.S. Caribbean Territories (PADD 6) petroleum market data, capturing the 100% maritime island
supply logistics anchored by Jones Act clean product tankers from the US Gulf Coast, closure of local refining
(CAPECO / Hovensa), Puerto Rico Department of Consumer Affairs (DACO) price regulation and metric survey conversion
(¢/L to $/gal), statutory Commonwealth petroleum taxes ($0.160/gal baseline arbitrio), and National Hurricane Center (NHC)
tropical cyclone / LUMA electrical grid vulnerability.
"""

import os
import re
import logging
import urllib.request
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union

from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

# Statutory metric conversion factor: 1 U.S. gallon = 3.785411784 liters
LITERS_PER_GALLON = 3.78541

# Jones Act clean product tanker marine freight differential (USGC Houston/Corpus Christi -> San Juan Harbor)
JONES_ACT_CLEAN_FREIGHT_DIFF = 0.145

# Puerto Rico Commonwealth statutory petroleum product tax (arbitrio)
PR_COMMONWEALTH_TAX_PER_GAL = 0.160
FEDERAL_EXCISE_TAX_PER_GAL = 0.184
TOTAL_REGULATORY_TAX_BURDEN = PR_COMMONWEALTH_TAX_PER_GAL + FEDERAL_EXCISE_TAX_PER_GAL  # 0.344 $/gal

# Baseline retail price in cents per liter (~$3.49/gal equivalent)
DEFAULT_DACO_CENTS_PER_LITER = 92.20
DEFAULT_SAN_JUAN_PUMP_PRICE = 3.490


def convert_cents_per_liter_to_dollars_per_gal(cents_per_liter: float) -> float:
    """
    Converts Puerto Rico retail fuel price in cents per liter (¢/L) to dollars per gallon ($/gal):
      $/gal = (¢/L / 100.0) * 3.78541
    """
    if cents_per_liter is None or float(cents_per_liter) <= 0:
        return DEFAULT_SAN_JUAN_PUMP_PRICE
    return round((float(cents_per_liter) / 100.0) * LITERS_PER_GALLON, 4)


def convert_dollars_per_gal_to_cents_per_liter(dollars_per_gal: float) -> float:
    """
    Converts retail fuel price in dollars per gallon ($/gal) to Puerto Rico cents per liter (¢/L):
      ¢/L = (dollars_per_gal / 3.78541) * 100.0
    """
    if dollars_per_gal is None or float(dollars_per_gal) <= 0:
        return DEFAULT_DACO_CENTS_PER_LITER
    return round((float(dollars_per_gal) / LITERS_PER_GALLON) * 100.0, 2)


def scrape_daco_retail_prices() -> Dict[str, Any]:
    """
    Scrapes the daily retail fuel price survey from the Puerto Rico Department of Consumer
    Affairs (DACO - Departamento de Asuntos del Consumidor, daco.pr.gov).
    DACO surveys pump prices across Puerto Rico in cents per liter (¢/L) for regular, premium,
    and diesel across wholesale distributors (Puma, TotalEnergies, Sol/Shell, Mobil, Toral).
    
    Under TESTING=1 or when remote networks are inaccessible, provides validated,
    metric-converted fallback observations with full provenance.
    """
    cache_key = "daco_daily_survey_pr"
    cached = global_cache.get(cache_key)
    if cached and isinstance(cached, dict):
        return cached

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Enforce test isolation
    if os.environ.get("TESTING") == "1":
        cents_reg = DEFAULT_DACO_CENTS_PER_LITER
        dollars_reg = convert_cents_per_liter_to_dollars_per_gal(cents_reg)
        payload = {
            "source": "DACO Daily Fuel Survey (Testing Fallback)",
            "timestamp": now_str,
            "region": "San_Juan_PR",
            "cents_per_liter": {
                "regular": cents_reg,
                "premium": round(cents_reg * 1.082, 2),
                "diesel": round(cents_reg * 1.131, 2)
            },
            "dollars_per_gal": {
                "regular": dollars_reg,
                "premium": round(convert_cents_per_liter_to_dollars_per_gal(cents_reg * 1.082), 3),
                "diesel": round(convert_cents_per_liter_to_dollars_per_gal(cents_reg * 1.131), 3)
            },
            "price": dollars_reg,
            "margin_cap_enforced": False,
            "currency": "USD",
            "unit": "¢/L to $/gal",
            "is_live": False
        }
        return payload

    daco_url = "https://www.daco.pr.gov/estudios-y-publicaciones/precios-de-gasolina/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        req = urllib.request.Request(daco_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                html = response.read().decode('utf-8', errors='ignore')
                # Extract cents per liter values typically formatted as XX.X or XX.XX ¢/L
                matches = re.findall(r'(\d{2}\.\d{1,2})\s*(?:¢|cent|c\/l)', html, re.IGNORECASE)
                if matches:
                    valid_cents = [float(m) for m in matches if 60.0 <= float(m) <= 150.0]
                    if valid_cents:
                        avg_cents = float(np.mean(valid_cents[:5]))
                        dollars_reg = convert_cents_per_liter_to_dollars_per_gal(avg_cents)
                        res = {
                            "source": "DACO Daily Fuel Survey (daco.pr.gov)",
                            "timestamp": now_str,
                            "region": "San_Juan_PR",
                            "cents_per_liter": {
                                "regular": round(avg_cents, 2),
                                "premium": round(avg_cents * 1.082, 2),
                                "diesel": round(avg_cents * 1.131, 2)
                            },
                            "dollars_per_gal": {
                                "regular": dollars_reg,
                                "premium": round(convert_cents_per_liter_to_dollars_per_gal(avg_cents * 1.082), 3),
                                "diesel": round(convert_cents_per_liter_to_dollars_per_gal(avg_cents * 1.131), 3)
                            },
                            "price": dollars_reg,
                            "margin_cap_enforced": False,
                            "currency": "USD",
                            "unit": "¢/L to $/gal",
                            "is_live": True
                        }
                        global_cache.set(cache_key, res, ttl_seconds=1800)
                        return res
    except Exception as e:
        logger.debug(f"DACO scraping notice for San Juan: {type(e).__name__} - {e}")

    # Fallback to static anchor
    cents_reg = DEFAULT_DACO_CENTS_PER_LITER
    dollars_reg = convert_cents_per_liter_to_dollars_per_gal(cents_reg)
    res = {
        "source": "DACO Daily Fuel Survey (Historical Anchor)",
        "timestamp": now_str,
        "region": "San_Juan_PR",
        "cents_per_liter": {
            "regular": cents_reg,
            "premium": round(cents_reg * 1.082, 2),
            "diesel": round(cents_reg * 1.131, 2)
        },
        "dollars_per_gal": {
            "regular": dollars_reg,
            "premium": round(convert_cents_per_liter_to_dollars_per_gal(cents_reg * 1.082), 3),
            "diesel": round(convert_cents_per_liter_to_dollars_per_gal(cents_reg * 1.131), 3)
        },
        "price": dollars_reg,
        "margin_cap_enforced": False,
        "currency": "USD",
        "unit": "¢/L to $/gal",
        "is_live": False
    }
    global_cache.set(cache_key, res, ttl_seconds=300)
    return res


def fetch_san_juan_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to San Juan Metro & U.S. Caribbean Territories Hub (PADD 6)
    and dynamically calibrates the retail series to match live pump prices:
      - Puerto Rico Commonwealth Petroleum Product Tax: $0.160/gal (arbitrio) baseline
      - Landed Wholesale Benchmark: US Gulf Coast Conventional Cargo ('spot_gulf_coast')
        plus Jones Act clean product tanker marine freight differential ($0.145/gal)
      - Retail Ground Truth: DACO Daily Survey metric prices converted from ¢/L to $/gal
      - 100% Maritime Island Supply Logistics via deepwater berths in San Juan Bay.
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("San_Juan_PR")["price"]
        except Exception:
            live_price = DEFAULT_SAN_JUAN_PUMP_PRICE

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for San Juan & PADD 6 region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_san_juan_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via DACO / EIA Caribbean feed
    market_df['san_juan_pr_retail_gasoline'] = get_regional_retail_history("San_Juan_PR", market_df['date'], live_price)
    market_df['san_juan_retail_gasoline'] = market_df['san_juan_pr_retail_gasoline']
    market_df['daco_retail_cents_per_liter'] = market_df['san_juan_retail_gasoline'].apply(convert_dollars_per_gal_to_cents_per_liter)

    # Wholesale USGC benchmark + Jones Act clean tanker freight differential
    usgc_col = 'spot_gulf_coast' if 'spot_gulf_coast' in market_df.columns else 'gasoline_rbob'
    market_df['spot_caribbean_waterborne'] = market_df[usgc_col] + JONES_ACT_CLEAN_FREIGHT_DIFF
    market_df['jones_act_freight_differential'] = JONES_ACT_CLEAN_FREIGHT_DIFF

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['san_juan_crack_spread'] = market_df['spot_caribbean_waterborne'] - market_df['brent_crude_per_gal']
    market_df['caribbean_crack_spread'] = market_df['spot_caribbean_waterborne'] - market_df['brent_crude_per_gal']
    market_df['san_juan_rack_margin'] = market_df['san_juan_retail_gasoline'] - market_df['spot_caribbean_waterborne']
    market_df['total_regulatory_tax_burden'] = TOTAL_REGULATORY_TAX_BURDEN

    return market_df


def _generate_synthetic_san_juan_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = DEFAULT_SAN_JUAN_PUMP_PRICE
) -> pd.DataFrame:
    """Generates synthetic historical business day series for San Juan Metro & Caribbean Hub."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 80.0 + np.cumsum(np.random.normal(0, 1.15, n))
    wti_crude = brent_crude - 4.2 + np.random.normal(0, 0.30, n)
    rbob = (brent_crude / 42.0) * 1.35 + np.cumsum(np.random.normal(0, 0.022, n))
    spot_usgc = rbob - 0.040 + np.random.normal(0, 0.015, n)
    spot_caribbean = spot_usgc + JONES_ACT_CLEAN_FREIGHT_DIFF

    margin_sj = live_pump_price - spot_caribbean[-1]
    var_sj = 0.10 * np.sin(np.linspace(0, 3.5 * np.pi, n)) + np.random.normal(0, 0.015, n)
    var_sj -= var_sj[-1]

    sj_retail = spot_caribbean + margin_sj + var_sj

    cents_per_liter = (sj_retail / LITERS_PER_GALLON) * 100.0

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.60),
        'spot_gulf_coast': np.maximum(spot_usgc, 1.55),
        'spot_caribbean_waterborne': np.maximum(spot_caribbean, 1.70),
        'jones_act_freight_differential': np.full(n, JONES_ACT_CLEAN_FREIGHT_DIFF),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 44.0),
        'san_juan_pr_retail_gasoline': np.maximum(sj_retail, 2.50),
        'san_juan_retail_gasoline': np.maximum(sj_retail, 2.50),
        'daco_retail_cents_per_liter': np.maximum(cents_per_liter, 65.0),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'san_juan_crack_spread': spot_caribbean - (brent_crude / 42.0),
        'caribbean_crack_spread': spot_caribbean - (brent_crude / 42.0),
        'san_juan_rack_margin': sj_retail - spot_caribbean,
        'total_regulatory_tax_burden': np.full(n, TOTAL_REGULATORY_TAX_BURDEN)
    })


def get_san_juan_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 6 Caribbean Territories dynamics:
    Jones Act coastal tanker deliveries from USGC, DACO regulatory price monitoring and margin caps,
    LUMA energy electrical grid outages, NHC tropical alerts (Hurricanes Maria, Fiona, Ernesto),
    and deepwater terminal logistics across San Juan Bay.
    """
    macro_events_df = get_historical_event_dataset()

    from src.noaa_weather import get_san_juan_weather_dataset
    noaa_sju_df = get_san_juan_weather_dataset()

    san_juan_events = [
        {"date": "2022-04-18", "headline": "Jones Act compliant coastal clean product tanker discharges 240,000 barrels of regular conventional gasoline at San Juan Bay Puerto Nuevo terminal from Corpus Christi.", "category": "Product Tanker Ingestion"},
        {"date": "2022-06-25", "headline": "DACO (Departamento de Asuntos del Consumidor) issues daily fuel survey monitoring report noting stable wholesaler profit margins across Puma, Total, and Sol Shell stations.", "category": "DACO Regulatory Survey"},
        {"date": "2022-09-18", "headline": "Category 1 Hurricane Fiona causes catastrophic islandwide electrical blackout across LUMA Energy grid; fuel stations experience surging lines for emergency diesel generator supply.", "category": "Grid Blackout Emergency"},
        {"date": "2022-09-22", "headline": "DACO issues emergency price freeze order under statutory emergency powers, capping distributor and retailer fuel margins following Hurricane Fiona recovery.", "category": "DACO Margin Cap Freeze"},
        {"date": "2023-03-10", "headline": "Puerto Rico Department of Treasury (Hacienda) confirms enforcement of Commonwealth petroleum product excise tax (arbitrio) baseline at $0.160 per gallon.", "category": "Tax Policy Compliance"},
        {"date": "2023-08-14", "headline": "Tightening Atlantic Jones Act coastal tanker freight market increases clean shipping charter premiums from US Gulf Coast to Caribbean petroleum terminals.", "category": "Jones Act Freight Differential"},
        {"date": "2023-11-05", "headline": "Puma Energy Caribe completes terminal modernization and vapor recovery enhancements at Bayamón storage hub, boosting San Juan distribution throughput.", "category": "Terminal Infrastructure"},
        {"date": "2024-04-12", "headline": "LUMA Energy substation fire triggers localized blackouts in San Juan metro area, briefly elevating commercial generator diesel burn at hospital and data center nodes.", "category": "LUMA Grid Outage"},
        {"date": "2024-08-14", "headline": "Tropical Storm Ernesto tracks east of Puerto Rico; US Coast Guard Sector San Juan directs marine tanker vessels to secure harbor moorings.", "category": "Tropical Storm Advisory"}
    ]

    regional_df = pd.DataFrame(san_juan_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    noaa_formatted = noaa_sju_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    frames = [macro_events_df, regional_df, noaa_formatted]

    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_sju_df = load_live_regional_intraday_events("San_Juan")
        if not intraday_sju_df.empty:
            frames.append(intraday_sju_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for San Juan: {e}")

    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
