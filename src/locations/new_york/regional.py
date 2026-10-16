"""
New York Harbor & New York State Regional Gas Price Forecasting Module (src/locations/new_york/regional.py)
Fuses New York Harbor & New York State (PADD 1B) market data, modeling the New York Harbor RBOB barge complex,
Phillips 66 Bayway Refinery (258 kbpd), midstream distribution via Buckeye Pipeline & Colonial Pipeline Line 1
terminus, Hudson River / Long Island Sound barge distribution, statutory New York State fuel tax ($0.472/gal baseline),
EPA NYC/Long Island summer RFG rules vs 9.0 psi Upstate conventional standards, and localized NOAA Weather Alerts
for NYC Metro and Hudson Valley (NYZ072 / KNYC / KLGA / KJFK).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from src.noaa_weather import get_new_york_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)


def fetch_new_york_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to New York Harbor & New York State Regional Hub (PADD 1B)
    and dynamically calibrates the retail series to match live pump prices:
      - New York State Motor Fuel Tax: $0.472/gal statutory baseline (excise + PBT + state sales tax)
      - Phillips 66 Bayway Refinery (258 kbpd) and NY Harbor barge pricing dynamics
      - New York Harbor RBOB spot benchmark with Buckeye Pipeline midstream delivery tariffs.
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("New_York_NY")["price"]
        except Exception:
            live_price = 3.480

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for New York region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_new_york_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via EIA survey (Weekly NYC All Formulations EMM_EPMR_PTE_Y35NY_DPG / State EMM_EPMR_PTE_SNY_DPG)
    market_df['new_york_ny_retail_gasoline'] = get_regional_retail_history("New_York_NY", market_df['date'], live_price)
    market_df['new_york_retail_gasoline'] = market_df['new_york_ny_retail_gasoline']

    # New York Harbor wholesale spot benchmark column
    if 'spot_ny_harbor' not in market_df.columns:
        market_df['spot_ny_harbor'] = market_df['gasoline_rbob']

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['new_york_crack_spread'] = market_df['spot_ny_harbor'] - market_df['brent_crude_per_gal']
    market_df['bayway_crack_spread'] = market_df['spot_ny_harbor'] - market_df['brent_crude_per_gal']
    market_df['new_york_rack_margin'] = market_df['new_york_retail_gasoline'] - market_df['spot_ny_harbor']

    return market_df


def _generate_synthetic_new_york_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = 3.480
) -> pd.DataFrame:
    """Generates synthetic historical business day series for New York Harbor & NY State Hub."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 80.0 + np.cumsum(np.random.normal(0, 1.15, n))
    wti_crude = brent_crude - 4.2 + np.random.normal(0, 0.30, n)
    rbob = (brent_crude / 42.0) * 1.35 + np.cumsum(np.random.normal(0, 0.024, n))
    spot_ny = rbob + np.random.normal(0, 0.008, n)

    margin_ny = live_pump_price - spot_ny[-1]
    var_ny = 0.12 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.018, n)
    var_ny -= var_ny[-1]

    ny_retail = spot_ny + margin_ny + var_ny

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.60),
        'spot_ny_harbor': np.maximum(spot_ny, 1.60),
        'wti_crude': np.maximum(wti_crude, 42.0),
        'brent_crude': np.maximum(brent_crude, 46.0),
        'new_york_ny_retail_gasoline': np.maximum(ny_retail, 2.30),
        'new_york_retail_gasoline': np.maximum(ny_retail, 2.30),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'new_york_crack_spread': spot_ny - (brent_crude / 42.0),
        'bayway_crack_spread': spot_ny - (brent_crude / 42.0),
        'new_york_rack_margin': ny_retail - spot_ny,
        'total_regulatory_tax_burden': 0.472 + 0.184
    })


def get_new_york_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 1B New York Harbor refining & pipeline dynamics (Bayway 258 kbpd,
    Buckeye Pipeline, Colonial Line 1 terminus), NY State statutory fuel tax ($0.472/gal baseline),
    EPA NYC/Long Island summer RFG standards vs Upstate conventional rules, and localized NYC/Hudson Valley NOAA Weather alerts.
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. New York Harbor & NY State Regional Logistics, Refining & Policy Disruption Dataset
    new_york_events = [
        {"date": "2021-05-10", "headline": "Colonial Pipeline cyberattack halts Line 1 deliveries into Linden, NJ terminus; New York Harbor barge racks draw down inventory while Buckeye Pipeline limits allocations.", "category": "Pipeline Disruption"},
        {"date": "2021-06-01", "headline": "EPA reformulated gasoline (RFG) summer blending rules take effect across NYC and Long Island; summer grade premiums expand rack basis over Upstate 9.0 psi conventional fuel.", "category": "Summer RFG Transition"},
        {"date": "2021-09-02", "headline": "Remnants of Hurricane Ida cause catastrophic flash flooding across NYC metro, subway systems, and New Jersey terminal racks, briefly halting Buckeye Pipeline deliveries to JFK and LaGuardia.", "category": "Tropical Storm / Flooding"},
        {"date": "2022-01-18", "headline": "Severe coastal freeze and harbor ice formation slow Hudson River and Long Island Sound petroleum barge lightering traffic, raising terminal rack transport surcharges.", "category": "Harbor Freeze / Barge Delay"},
        {"date": "2022-06-01", "headline": "New York State temporarily suspends state motor fuel excise tax (16¢/gal fuel tax holiday) to mitigate record retail pump prices, narrowing the retail tax wedge through December.", "category": "Tax Policy Holiday"},
        {"date": "2022-10-15", "headline": "Phillips 66 Bayway Refinery (258 kbpd) initiates scheduled multi-week turnaround on its fluid catalytic cracking unit (FCCU), tightening New York Harbor prompt product supply.", "category": "Refinery Turnaround"},
        {"date": "2023-01-01", "headline": "New York State motor fuel excise tax holiday expires, restoring full $0.472/gal statutory baseline tax burden across all retail dispensing locations.", "category": "Tax Policy Restoration"},
        {"date": "2023-06-01", "headline": "Summer driving demand begins across the Long Island Expressway and New York Thruway corridors; NYC metropolitan retail prices trade at a 30¢ premium over Delaware River terminals.", "category": "Seasonal Demand & Basis Premium"},
        {"date": "2024-01-16", "headline": "Arctic airmass and winter storm bring sub-zero wind chills across Upstate New York; heating oil demand surges, lifting distillate crack spreads and tightening shared pipeline capacity.", "category": "Winter Freeze / Distillate Surge"},
        {"date": "2024-05-20", "headline": "Buckeye Pipeline completes automated terminal monitoring upgrade across Linden-to-Rochester system, enhancing scheduling reliability ahead of summer driving season.", "category": "Midstream Infrastructure"}
    ]

    regional_df = pd.DataFrame(new_york_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    # 3. Merge Localized NOAA Weather Alerts for NYC Metro, Long Island & Hudson Valley
    noaa_ny_df = get_new_york_weather_dataset()
    noaa_formatted = noaa_ny_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    frames = [macro_events_df, regional_df, noaa_formatted]

    # Ingest Live Regional Intraday Anomalies
    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_ny_df = load_live_regional_intraday_events("New_York")
        if not intraday_ny_df.empty:
            frames.append(intraday_ny_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for New York: {e}")

    # Combine Macro + Regional + Local NOAA Weather
    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
