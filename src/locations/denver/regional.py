"""
Denver Metro & Rocky Mountain Regional Gas Price Forecasting Module (src/locations/denver/regional.py)
Fuses Denver & Rocky Mountain (PADD 4) market data, modeling the isolated high-altitude refining island
dominated by Suncor Commerce City Refinery (103k bpd), regional crude differentials (DJ Basin sweet crude
and Wyoming sour blends), statutory Colorado motor fuel excise tax ($0.280/gal), EPA Front Range ozone
nonattainment reformulated summer blending requirements, and localized NOAA Weather Alerts for Adams/Denver
counties (COZ040 / KDEN).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from src.noaa_weather import get_denver_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)


def fetch_denver_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Denver Metro & Rocky Mountain Regional Hub (PADD 4)
    and dynamically calibrates the retail series to match live pump prices:
      - Colorado State Motor Fuel Tax: $0.280/gal statutory excise (no local sales tax add-on)
      - Suncor Commerce City Refinery (103 kbpd) supply-island pricing dynamics
      - Denver rack wholesale spot benchmark with DJ Basin feedstock differentials.
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("Denver_CO")["price"]
        except Exception:
            live_price = 3.150

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Denver & Rocky Mountain region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_denver_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via EIA survey (Weekly Denver All Formulations EMM_EPMR_PTE_Y35DE_DPG)
    market_df['denver_co_retail_gasoline'] = get_regional_retail_history("Denver_CO", market_df['date'], live_price)
    market_df['denver_retail_gasoline'] = market_df['denver_co_retail_gasoline']

    # Denver wholesale spot / rack benchmark column
    if 'spot_denver_rack' not in market_df.columns:
        market_df['spot_denver_rack'] = market_df['gasoline_rbob'] + 0.045

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['denver_crack_spread'] = market_df['spot_denver_rack'] - market_df['wti_crude_per_gal']
    market_df['denver_rack_margin'] = market_df['denver_retail_gasoline'] - market_df['spot_denver_rack']

    return market_df


def _generate_synthetic_denver_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = 3.150
) -> pd.DataFrame:
    """Generates synthetic historical business day series for Denver & Rocky Mountain Refining Hub."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 78.0 + np.cumsum(np.random.normal(0, 1.10, n))
    wti_crude = brent_crude - 4.5 + np.random.normal(0, 0.35, n)
    rbob = (wti_crude / 42.0) * 1.32 + np.cumsum(np.random.normal(0, 0.022, n))
    spot_denver = rbob + 0.045 + np.random.normal(0, 0.012, n)

    margin_denver = live_pump_price - spot_denver[-1]
    var_denver = 0.14 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.020, n)
    var_denver -= var_denver[-1]

    denver_retail = spot_denver + margin_denver + var_denver

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'spot_denver_rack': np.maximum(spot_denver, 1.55),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 44.0),
        'denver_co_retail_gasoline': np.maximum(denver_retail, 2.10),
        'denver_retail_gasoline': np.maximum(denver_retail, 2.10),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'denver_crack_spread': spot_denver - (wti_crude / 42.0),
        'suncor_crack_spread': spot_denver - (wti_crude / 42.0),
        'denver_rack_margin': denver_retail - spot_denver,
        'total_regulatory_tax_burden': 0.280 + 0.184
    })


def get_denver_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 4 Rocky Mountain refining dynamics (Suncor Commerce City 103 kbpd),
    Front Range pipeline terminals (Magellan, Sinclair, Chase), Colorado statutory fuel tax ($0.280/gal),
    EPA Front Range ozone nonattainment summer standards, and localized Denver/Boulder NOAA Weather alerts.
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. Denver & Rocky Mountain Regional Logistics, Refining & Policy Disruption Dataset
    denver_events = [
        {"date": "2021-02-17", "headline": "Severe Arctic cold front sweeps Colorado Front Range; Suncor Commerce City refinery reports temporary throughput reductions due to instrument line freezing.", "category": "Refinery Freeze-Off"},
        {"date": "2021-06-01", "headline": "Colorado Front Range 9-county ozone nonattainment area transitions to EPA 7.8 psi summer gasoline standard, tightening regional rack wholesale supply.", "category": "RVP Summer Transition"},
        {"date": "2022-03-24", "headline": "Suncor Commerce City (103 kbpd) reports unplanned fluid catalytic cracking unit (FCCU) shutdown following equipment malfunction; Denver rack prices surge.", "category": "Unplanned FCCU Outage"},
        {"date": "2022-12-24", "headline": "Historic Arctic deep freeze (-24°F) causes catastrophic equipment freeze damage and fires at Suncor Commerce City, forcing complete refinery shutdown for over three months.", "category": "Refinery Freeze Disaster"},
        {"date": "2023-01-15", "headline": "Colorado Governor Polis issues emergency fuel regulatory waivers to allow out-of-spec fuel imports via rail and truck from Kansas and Texas during Commerce City shutdown.", "category": "Emergency Fuel Waiver"},
        {"date": "2023-04-08", "headline": "Suncor Commerce City completes phased restart of Plant 1 and Plant 2 after 105-day freeze turnaround, restoring 103,000 bpd regional refining capacity.", "category": "Refinery Restart"},
        {"date": "2023-06-01", "headline": "EPA reclassifies Denver Metro / Front Range nonattainment area to Severe, mandating reformulated gasoline (RFG) blending standards for summer driving season.", "category": "Severe Ozone RFG Mandate"},
        {"date": "2024-01-14", "headline": "Polar vortex brings sub-zero temperatures and blizzard conditions to eastern Colorado; Magellan Front Range pipeline terminals maintain continuous deliveries.", "category": "Blizzard / Polar Vortex"},
        {"date": "2024-06-01", "headline": "High-altitude summer driving season begins with Front Range reformulated gasoline retail prices decoupling from Midwest wholesale trends.", "category": "Seasonal Demand & RFG Decoupling"},
        {"date": "2024-09-18", "headline": "Suncor announces scheduled maintenance turnaround on Commerce City coker unit with refined product reserves prepositioned across Denver rack terminals.", "category": "Scheduled Turnaround"}
    ]

    regional_df = pd.DataFrame(denver_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    # 3. Merge Localized NOAA Weather Alerts for Denver Metro & Adams/Arapahoe Counties
    noaa_den_df = get_denver_weather_dataset()
    noaa_formatted = noaa_den_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    frames = [macro_events_df, regional_df, noaa_formatted]

    # Ingest Live Regional Intraday Anomalies
    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_denver_df = load_live_regional_intraday_events("Denver")
        if not intraday_denver_df.empty:
            frames.append(intraday_denver_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for Denver: {e}")

    # Combine Macro + Regional + Local NOAA Weather
    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
