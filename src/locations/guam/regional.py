"""
Guam & Pacific Island Territories Regional Gas Price Forecasting Module (src/locations/guam/regional.py)
Fuses U.S. Pacific Island Territories (PADD 7) market data, modeling the isolated Western Pacific
refined product import system anchored by trans-Pacific MR product tankers from Asian refining hubs
(Singapore, South Korea), Apra Harbor Cabras Island fuel storage terminals, territorial liquid fuel taxes
($0.190/gal total baseline), retail oligopoly margins (Mobil, IP&E Shell, SPPC 76), and Joint Typhoon Warning
Center (JTWC) / WFO Guam weather alerts.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from src.noaa_weather import get_guam_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)


def fetch_guam_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Hagåtña / Apra Harbor, Guam (PADD 7)
    and dynamically calibrates the retail series to match live pump prices:
      - Guam Territorial Liquid Fuel Tax: $0.150/gal + $0.040/gal Mass Transit surcharge = $0.190/gal baseline
      - Mean of Platts Singapore (MOPS) 92 RON Mogas landed wholesale benchmark
      - Trans-Pacific Medium Range (MR) product tanker shipping from Singapore / South Korea to Apra Harbor
      - Retail distribution oligopoly: Mobil Oil Guam, IP&E (Shell), and SPPC (76).
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("Guam_GU")["price"]
        except Exception:
            live_price = 4.890

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Guam & PADD 7 region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_guam_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via Guam Energy Office (GEO) or regional fallback
    market_df['guam_gu_retail_gasoline'] = get_regional_retail_history("Guam_GU", market_df['date'], live_price)
    market_df['guam_retail_gasoline'] = market_df['guam_gu_retail_gasoline']

    # Mean of Platts Singapore (MOPS) 92 RON Mogas landed wholesale benchmark at Apra Harbor
    if 'spot_mops_92_rack' not in market_df.columns:
        market_df['spot_mops_92_rack'] = market_df['gasoline_rbob'] + 0.350

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['guam_crack_spread'] = market_df['spot_mops_92_rack'] - market_df['brent_crude_per_gal']
    market_df['mops_crack_spread'] = market_df['spot_mops_92_rack'] - market_df['brent_crude_per_gal']
    market_df['guam_rack_margin'] = market_df['guam_retail_gasoline'] - market_df['spot_mops_92_rack']
    market_df['total_regulatory_tax_burden'] = 0.190 + 0.184

    return market_df


def _generate_synthetic_guam_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = 4.890
) -> pd.DataFrame:
    """Generates synthetic historical business day series for Hagåtña / Apra Harbor Hub."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 82.0 + np.cumsum(np.random.normal(0, 1.20, n))
    wti_crude = brent_crude - 4.5 + np.random.normal(0, 0.35, n)
    rbob = (brent_crude / 42.0) * 1.36 + np.cumsum(np.random.normal(0, 0.025, n))
    spot_mops = rbob + 0.350 + np.random.normal(0, 0.020, n)

    margin_guam = live_pump_price - spot_mops[-1]
    var_guam = 0.12 * np.sin(np.linspace(0, 3 * np.pi, n)) + np.random.normal(0, 0.018, n)
    var_guam -= var_guam[-1]

    guam_retail = spot_mops + margin_guam + var_guam

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.60),
        'spot_mops_92_rack': np.maximum(spot_mops, 1.85),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 44.0),
        'guam_gu_retail_gasoline': np.maximum(guam_retail, 3.20),
        'guam_retail_gasoline': np.maximum(guam_retail, 3.20),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'guam_crack_spread': spot_mops - (brent_crude / 42.0),
        'mops_crack_spread': spot_mops - (brent_crude / 42.0),
        'guam_rack_margin': guam_retail - spot_mops,
        'total_regulatory_tax_burden': 0.190 + 0.184
    })


def get_guam_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 7 Pacific Island Territories dynamics:
    trans-Pacific MR product tankers from Singapore / South Korea, Cabras Island terminal operations,
    statutory liquid fuel taxes ($0.190/gal), retail oligopoly adjustments, and localized JTWC / WFO Guam typhoon alerts.
    """
    macro_events_df = get_historical_event_dataset()

    guam_events = [
        {"date": "2022-04-12", "headline": "Trans-Pacific Medium Range clean product tanker discharges 280,000 barrels of Mogas 92 at Cabras Island fuel pier from Singapore Jurong refinery.", "category": "Product Tanker Ingestion"},
        {"date": "2022-09-08", "headline": "Joint Typhoon Warning Center issues advisory for Tropical Storm Muifa passing north of Guam; commercial vessels directed to secure Apra Harbor moorings.", "category": "Tropical Storm Advisory"},
        {"date": "2023-01-20", "headline": "Defense Logistics Agency (DLA) Energy awards bulk commercial fuel support contract for Western Pacific defense installations including Andersen AFB and Naval Base Guam.", "category": "Military Procurement"},
        {"date": "2023-05-24", "headline": "Category 4 Super Typhoon Mawar makes direct landfall on northern Guam; US Coast Guard sets Port Condition Zulu, shutting Apra Harbor and prompting post-storm fuel ration lines.", "category": "Typhoon Disaster Emergency"},
        {"date": "2023-06-02", "headline": "Port Authority of Guam reopens Cabras commercial tanker berths with priority offloading for Mobil and Shell relief fuel shipments following Typhoon Mawar.", "category": "Port Recovery Operation"},
        {"date": "2023-10-10", "headline": "Typhoon Bolaven intensifies into super typhoon as it passes through the Rota Channel; maritime harbor traffic suspended across Mariana Islands.", "category": "Super Typhoon Warning"},
        {"date": "2024-03-15", "headline": "Mean of Platts Singapore (MOPS) 92 RON spot Mogas benchmark surges on Asian refinery turnaround season in South Korea and Japan, widening landed fuel acquisition costs at Apra Harbor.", "category": "MOPS Benchmark Shift"},
        {"date": "2024-07-28", "headline": "Guam Energy Office (GEO) Monthly Petroleum Monitor reports stable commercial retail gas margins among Mobil, IP&E Shell, and SPPC 76 across Hagåtña and Tamuning stations.", "category": "Territorial Market Monitor"},
        {"date": "2024-11-12", "headline": "Western Pacific tropical disturbance 94W generates heavy surf and gale warnings for Guam coastal marine waters, delaying inbound product tanker pilotage.", "category": "Marine Gale Advisory"}
    ]

    regional_df = pd.DataFrame(guam_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    noaa_gum_df = get_guam_weather_dataset()
    noaa_formatted = noaa_gum_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    frames = [macro_events_df, regional_df, noaa_formatted]

    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_gum_df = load_live_regional_intraday_events("Guam")
        if not intraday_gum_df.empty:
            frames.append(intraday_gum_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for Guam: {e}")

    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
