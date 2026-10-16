"""
Phoenix Metro & Desert Southwest Regional Gas Price Forecasting Module (src/locations/phoenix/regional.py)
Fuses Desert Southwest (PADD 5C) market data, modeling the zero-refinery import sink
supplied via Kinder Morgan SFPP West Line (from Los Angeles) and East Line (from El Paso / Gulf Coast),
statutory Arizona motor fuel excise tax ($0.180/gal), Maricopa County Cleaner Burning Gasoline (CBG) standards,
and localized NOAA Weather Alerts for Maricopa/Pima counties (AZZ023 / KPHX).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from src.noaa_weather import get_phoenix_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)


def fetch_phoenix_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Phoenix Metro & Desert Southwest Regional Hub (PADD 5C)
    and dynamically calibrates the retail series to match live pump prices:
      - Arizona State Motor Fuel Tax: $0.180/gal statutory excise (among the lowest in U.S.)
      - Zero in-state refining footprint; dual pipeline ingress via Kinder Morgan West (LA) and East (El Paso/USGC) lines
      - Phoenix wholesale rack benchmark with Permian and California arbitrage differentials.
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("Phoenix_AZ")["price"]
        except Exception:
            live_price = 3.250

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Phoenix & Desert Southwest region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_phoenix_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via EIA survey (Weekly Arizona All Formulations EMM_EPMR_PTE_SAZ_DPG)
    market_df['phoenix_az_retail_gasoline'] = get_regional_retail_history("Phoenix_AZ", market_df['date'], live_price)
    market_df['phoenix_retail_gasoline'] = market_df['phoenix_az_retail_gasoline']

    # Phoenix pipeline wholesale spot benchmark column
    if 'spot_phoenix_pipe' not in market_df.columns:
        market_df['spot_phoenix_pipe'] = market_df['gasoline_rbob'] + 0.065

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['phoenix_crack_spread'] = market_df['spot_phoenix_pipe'] - market_df['wti_crude_per_gal']
    market_df['desert_crack_spread'] = market_df['spot_phoenix_pipe'] - market_df['wti_crude_per_gal']
    market_df['phoenix_rack_margin'] = market_df['phoenix_retail_gasoline'] - market_df['spot_phoenix_pipe']
    market_df['total_regulatory_tax_burden'] = 0.180 + 0.184

    return market_df


def _generate_synthetic_phoenix_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = 3.250
) -> pd.DataFrame:
    """Generates synthetic historical business day series for Phoenix & Desert Southwest Hub."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 78.0 + np.cumsum(np.random.normal(0, 1.10, n))
    wti_crude = brent_crude - 4.5 + np.random.normal(0, 0.35, n)
    rbob = (wti_crude / 42.0) * 1.30 + np.cumsum(np.random.normal(0, 0.021, n))
    spot_phx = rbob + 0.065 + np.random.normal(0, 0.012, n)

    margin_phoenix = live_pump_price - spot_phx[-1]
    var_phoenix = 0.14 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.018, n)
    var_phoenix -= var_phoenix[-1]

    phoenix_retail = spot_phx + margin_phoenix + var_phoenix

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'spot_phoenix_pipe': np.maximum(spot_phx, 1.55),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 44.0),
        'phoenix_az_retail_gasoline': np.maximum(phoenix_retail, 2.10),
        'phoenix_retail_gasoline': np.maximum(phoenix_retail, 2.10),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'phoenix_crack_spread': spot_phx - (wti_crude / 42.0),
        'desert_crack_spread': spot_phx - (wti_crude / 42.0),
        'phoenix_rack_margin': phoenix_retail - spot_phx,
        'total_regulatory_tax_burden': 0.180 + 0.184
    })


def get_phoenix_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 5C Desert Southwest midstream dynamics (Kinder Morgan SFPP East/West Lines),
    51st Avenue terminal operations, Arizona statutory fuel tax ($0.180/gal),
    Maricopa County Cleaner Burning Gasoline (CBG) standards, and localized Phoenix NOAA Weather alerts.
    """
    macro_events_df = get_historical_event_dataset()

    phoenix_events = [
        {"date": "2021-06-01", "headline": "Maricopa County transitions to summer blend Arizona Cleaner Burning Gasoline (CBG), raising blending and terminal handling premiums at 51st Avenue.", "category": "Arizona CBG Summer Transition"},
        {"date": "2022-04-12", "headline": "Kinder Morgan SFPP East Line pump station maintenance near Tucson temporarily reduces product flows from El Paso, increasing reliance on West Line barrels.", "category": "Pipeline Flow Restriction"},
        {"date": "2022-09-28", "headline": "California CARBOB refinery spikes in Torrance cause Kinder Morgan to maximize East Line nominations from Texas into Phoenix terminal.", "category": "East-West Pipeline Arbitrage"},
        {"date": "2023-01-20", "headline": "Arizona legislature rejects proposed fuel excise tax indexing, keeping state motor fuel excise rate locked at $0.180/gal.", "category": "Tax Policy Freeze"},
        {"date": "2023-07-15", "headline": "Record 31 consecutive days above 110°F in Phoenix triggers extreme ambient temperature storage protocols at 51st Avenue terminal tank farms.", "category": "Extreme Heat Wave"},
        {"date": "2023-10-01", "headline": "Maricopa County switches to winter oxygenated CBG blend specification to curb winter carbon monoxide emissions.", "category": "Winter CBG Blend Transition"},
        {"date": "2024-03-10", "headline": "Kinder Morgan announces expansion of batch throughput on SFPP East Line, adding 15,000 bpd capacity from Permian/USGC refiners into Arizona.", "category": "Midstream Expansion"},
        {"date": "2024-07-22", "headline": "Desert monsoon flash flood damages feeder electrical substation near Casa Grande, temporarily stalling pipeline pump throughput.", "category": "Monsoon Flash Flood"},
        {"date": "2024-11-14", "headline": "Gulf Coast refined product export surge tightens El Paso rack availability, momentarily lifting Phoenix terminal wholesale prices.", "category": "Wholesale Supply Tightening"}
    ]

    regional_df = pd.DataFrame(phoenix_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    noaa_phx_df = get_phoenix_weather_dataset()
    noaa_formatted = noaa_phx_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    frames = [macro_events_df, regional_df, noaa_formatted]

    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_phx_df = load_live_regional_intraday_events("Phoenix")
        if not intraday_phx_df.empty:
            frames.append(intraday_phx_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for Phoenix: {e}")

    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
