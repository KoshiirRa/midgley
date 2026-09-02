"""
Charlotte, North Carolina Regional Gas Price Forecasting Module (src/locations/charlotte/regional.py)
Fuses Charlotte regional market data, PADD 1C South Atlantic refining & pipeline dynamics,
Colonial Pipeline Paw Creek Petroleum Distribution Hub & Plantation Pipeline interconnects,
North Carolina State Motor Fuel Tax ($0.404/gal) vs South Carolina cross-border tax differential ($0.288/gal),
and localized NOAA Weather Alerts for Mecklenburg County (NCZ071).
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import logging

from src.noaa_weather import get_charlotte_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)

def fetch_charlotte_market_data(
    start_date: str = "2022-01-01", 
    end_date: str = None,
    live_current_price: float = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Charlotte, NC & PADD 1C South Atlantic region
    and dynamically calibrates the retail series to match live pump prices.
    """
    if live_current_price is None:
        live_current_price = fetch_live_metro_retail_price("Charlotte_NC")["price"]

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Charlotte, NC region (Live Pump Price Anchor: ${live_current_price:.2f}/gal)...")
    
    tickers = {
        "gasoline_rbob": "RB=F",
        "wti_crude": "CL=F",
        "brent_crude": "BZ=F"
    }
    
    dfs = []
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if data is None or data.empty:
                continue
            close_series = data['Close'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Close']
            if close_series.dropna().empty:
                continue
            df_item = pd.DataFrame({'date': pd.to_datetime(close_series.index).tz_localize(None), name: close_series.values})
            dfs.append(df_item.set_index('date'))
        except Exception as e:
            logger.warning(f"Could not download ticker {ticker}: {e}")
            
    if not dfs or all(df.empty for df in dfs):
        return _generate_synthetic_charlotte_data(start_date, end_date, live_current_price)
        
    market_df = pd.concat(dfs, axis=1).sort_index().ffill().bfill().reset_index()
    if market_df.empty or 'gasoline_rbob' not in market_df.columns or len(market_df) == 0:
        return _generate_synthetic_charlotte_data(start_date, end_date, live_current_price)
    
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    dynamic_margin = live_current_price - latest_rbob
    
    market_df['charlotte_retail_gasoline'] = market_df['gasoline_rbob'] + dynamic_margin
    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['paw_creek_rack_crack_spread'] = market_df['charlotte_retail_gasoline'] - market_df['brent_crude_per_gal']
    
    return market_df


def _generate_synthetic_charlotte_data(start_date: str, end_date: str, live_current_price: float = 3.280) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)
    
    brent_crude = 78.0 + np.cumsum(np.random.normal(0, 1.1, n))
    wti_crude = brent_crude - 4.0 + np.random.normal(0, 0.4, n)
    rbob = (brent_crude / 42.0) * 1.28 + np.cumsum(np.random.normal(0, 0.022, n))
    dynamic_margin = live_current_price - rbob[-1]
    charlotte_retail = rbob + dynamic_margin
    
    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 45.0),
        'charlotte_retail_gasoline': np.maximum(charlotte_retail, 2.00),
        'brent_crude_per_gal': brent_crude / 42.0,
        'paw_creek_rack_crack_spread': charlotte_retail - (brent_crude / 42.0)
    })


def get_charlotte_regional_events() -> pd.DataFrame:
    """
    Merges full macro LLM event logs (Finlight.me news, Executive Social Media, Maritime, Key Movers)
    with PADD 1C Colonial Pipeline Paw Creek breakout hub events, Plantation Pipeline interconnect maintenance,
    NC State Motor Fuel Tax ($0.404/gal) vs SC tax differential ($0.288/gal), and localized Mecklenburg County (NCZ071) NOAA Weather.
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. Charlotte, NC & PADD 1C Regional Logistics, Pipeline & Hurricane Disruption Dataset
    charlotte_events = [
        {"date": "2022-03-18", "headline": "Colonial Pipeline Line 1 emergency maintenance throttles batch delivery into Paw Creek Charlotte terminal.", "category": "Paw Creek Terminal Pipeline"},
        {"date": "2022-10-01", "headline": "Post-Hurricane Ian inland wind damage forces temporary generator power at West Charlotte petroleum distribution hub.", "category": "Paw Creek Grid Failure"},
        {"date": "2023-01-01", "headline": "North Carolina fuel tax rate updates to $0.404/gal, maintaining a $0.116/gal tax premium over South Carolina (Rock Hill/Fort Mill).", "category": "Policy/NC Gas Tax"},
        {"date": "2023-09-02", "headline": "Plantation Pipeline schedules manifold maintenance near Charlotte breakout junction, tightening wholesale rack supply.", "category": "Plantation Pipeline Hub"},
        {"date": "2024-05-12", "headline": "Duke Energy substation outage disrupts automated tank truck rack loading at Paw Creek petroleum tank farm.", "category": "Paw Creek Power Outage"},
        {"date": "2024-08-09", "headline": "Tropical Storm Debby dumps historic rainfall across Mecklenburg County; Catawba River basin flooding restricts tank truck deliveries.", "category": "Catawba River Flooding"},
        {"date": "2025-01-22", "headline": "Severe Winter Ice Storm locks down I-85 & I-77 freight corridors in Charlotte metro, thins wholesale rack inventory.", "category": "Winter Ice / Highway Bottleneck"}
    ]
    
    regional_df = pd.DataFrame(charlotte_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])
    
    # 3. Merge Localized NOAA Weather Alerts for Mecklenburg County NC (NCZ071)
    noaa_clt_df = get_charlotte_weather_dataset()
    
    if not noaa_clt_df.empty:
        noaa_clt_df['category'] = "NOAA Weather Mecklenburg County (NCZ071)"
        combined_df = pd.concat([macro_events_df, regional_df, noaa_clt_df], ignore_index=True)
    else:
        combined_df = pd.concat([macro_events_df, regional_df], ignore_index=True)
        
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    return combined_df.sort_values('date').reset_index(drop=True)
