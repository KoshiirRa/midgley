"""
Honolulu & Oahu Island Regional Gas Price Forecasting Module (src/locations/honolulu/regional.py)
Fuses Hawaii (PADD 5D) market data, modeling the isolated island archipelago refining system
anchored by Par Hawaii Kapolei Refinery (94k bpd), Barbers Point offshore tanker moorings,
inter-island ocean fuel barges (Young Brothers), composite state + county + GET taxes ($0.330/gal baseline),
and localized NOAA Weather Alerts for Oahu/Honolulu (HIZ002 / PHNL).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from src.noaa_weather import get_honolulu_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)


def fetch_honolulu_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Honolulu & Hawaii Regional Hub (PADD 5D)
    and dynamically calibrates the retail series to match live pump prices:
      - Hawaii Combined Motor Fuel Tax: $0.330/gal statutory baseline (state + Honolulu county + GET)
      - Par Hawaii Kapolei Refinery (94 kbpd) on Oahu
      - Trans-Pacific waterborne crude imports and inter-island marine barge delivery dynamics.
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("Honolulu_HI")["price"]
        except Exception:
            live_price = 4.650

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Honolulu & Hawaii region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_honolulu_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via EIA survey (Weekly Hawaii Regular Retail EMM_EPMR_PTE_SHI_DPG)
    market_df['honolulu_hi_retail_gasoline'] = get_regional_retail_history("Honolulu_HI", market_df['date'], live_price)
    market_df['honolulu_retail_gasoline'] = market_df['honolulu_hi_retail_gasoline']

    # Hawaii wholesale spot rack benchmark column
    if 'spot_oahu_rack' not in market_df.columns:
        market_df['spot_oahu_rack'] = market_df['gasoline_rbob'] + 0.220

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['honolulu_crack_spread'] = market_df['spot_oahu_rack'] - market_df['brent_crude_per_gal']
    market_df['kapolei_crack_spread'] = market_df['spot_oahu_rack'] - market_df['brent_crude_per_gal']
    market_df['honolulu_rack_margin'] = market_df['honolulu_retail_gasoline'] - market_df['spot_oahu_rack']
    market_df['total_regulatory_tax_burden'] = 0.330 + 0.184

    return market_df


def _generate_synthetic_honolulu_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = 4.650
) -> pd.DataFrame:
    """Generates synthetic historical business day series for Honolulu & Oahu Hub."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 82.0 + np.cumsum(np.random.normal(0, 1.20, n))
    wti_crude = brent_crude - 4.5 + np.random.normal(0, 0.35, n)
    rbob = (brent_crude / 42.0) * 1.36 + np.cumsum(np.random.normal(0, 0.025, n))
    spot_oahu = rbob + 0.220 + np.random.normal(0, 0.018, n)

    margin_honolulu = live_pump_price - spot_oahu[-1]
    var_honolulu = 0.14 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.020, n)
    var_honolulu -= var_honolulu[-1]

    honolulu_retail = spot_oahu + margin_honolulu + var_honolulu

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.60),
        'spot_oahu_rack': np.maximum(spot_oahu, 1.75),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 44.0),
        'honolulu_hi_retail_gasoline': np.maximum(honolulu_retail, 2.80),
        'honolulu_retail_gasoline': np.maximum(honolulu_retail, 2.80),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'honolulu_crack_spread': spot_oahu - (brent_crude / 42.0),
        'kapolei_crack_spread': spot_oahu - (brent_crude / 42.0),
        'honolulu_rack_margin': honolulu_retail - spot_oahu,
        'total_regulatory_tax_burden': 0.330 + 0.184
    })


def get_honolulu_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 5D Hawaii refining dynamics (Par Hawaii Kapolei 94 kbpd),
    Barbers Point offshore SPM tanker moorings, Young Brothers ocean fuel barges, statutory taxes ($0.330/gal),
    and localized Honolulu NOAA Weather alerts.
    """
    macro_events_df = get_historical_event_dataset()

    honolulu_events = [
        {"date": "2021-12-06", "headline": "Kona low storm brings torrential rainfall and 50 mph winds across Oahu, causing temporary marine mooring holds at Barbers Point offshore buoy.", "category": "Kona Low Marine Storm"},
        {"date": "2022-03-18", "headline": "Par Hawaii announces cessation of Russian crude imports following global sanctions, pivoting Kapolei refinery feedstock to Asia-Pacific and Latin American light sweet crudes.", "category": "Feedstock Geopolitical Pivot"},
        {"date": "2022-08-22", "headline": "Scheduled decoking turnaround on Kapolei refinery vacuum flasher proceeds with pre-loaded inter-island fuel barges stationed at Maui and Big Island.", "category": "Refinery Maintenance"},
        {"date": "2023-08-08", "headline": "Catastrophic Lahaina wildfire and high winds from Hurricane Dora disrupt electrical distribution on West Maui, prompting emergency fuel deliveries via Young Brothers barges.", "category": "Wildfire Emergency Response"},
        {"date": "2023-11-15", "headline": "Trans-Pacific product tanker offloads cargo at Honolulu Harbor, supplementing local Kapolei output during seasonal aviation jet fuel demand peak.", "category": "Waterborne Finished Import"},
        {"date": "2024-04-02", "headline": "Par Hawaii completes installation of renewable fuels processing unit at Kapolei, producing commercial sustainable aviation fuel and renewable diesel.", "category": "Biofuel Co-Processing Transition"},
        {"date": "2024-08-24", "headline": "Hurricane Hone passes south of Big Island; US Coast Guard sets Port Condition Yankee for Hilo and Kawaihae harbors, briefly pausing inter-island fuel barge transits.", "category": "Hurricane Marine Advisory"},
        {"date": "2024-11-20", "headline": "City and County of Honolulu maintains county fuel tax rate, keeping composite Oahu motor fuel tax burden steady at $0.330/gal.", "category": "Tax Policy Stability"}
    ]

    regional_df = pd.DataFrame(honolulu_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    noaa_hnl_df = get_honolulu_weather_dataset()
    noaa_formatted = noaa_hnl_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    frames = [macro_events_df, regional_df, noaa_formatted]

    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_hnl_df = load_live_regional_intraday_events("Honolulu")
        if not intraday_hnl_df.empty:
            frames.append(intraday_hnl_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for Honolulu: {e}")

    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
