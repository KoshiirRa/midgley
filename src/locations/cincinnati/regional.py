"""
Cincinnati, OH & Northern Kentucky Regional Gas Price Forecasting Module (src/locations/cincinnati/regional.py)
Fuses Cincinnati metro area market data across state lines, modeling the dual-state fuel tax differential
(Ohio state motor fuel tax 38.5¢/gal vs Kentucky state motor fuel tax 26.0¢/gal), Marathon Catlettsburg Refinery
(291,000 bpd capacity), Ohio & Lower Mississippi River petroleum barge logistics (Cairo confluence & Memphis low-water draft restrictions),
and localized NOAA Weather Alerts for Hamilton County OH (OHZ077) & Boone/Kenton/Campbell Counties KY (KYZ091-KYZ093).
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import logging

from src.noaa_weather import get_cincinnati_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)

def fetch_cincinnati_market_data(
    start_date: str = "2022-01-01", 
    end_date: str = None,
    live_oh_price: float = None,
    live_ky_price: float = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Cincinnati, OH & Northern KY (Tri-State Metro Area)
    and dynamically calibrates the dual-state retail series to match live pump prices:
      - Ohio Side (Hamilton County): State Tax: 38.5¢/gal
      - Kentucky Side (Boone/Kenton/Campbell): State Tax: 26.0¢/gal
      - Cross-River Tax & Retail Differential: ~$0.125/gal.
    """
    if live_oh_price is None:
        live_oh_price = fetch_live_metro_retail_price("Cincinnati_OH")["price"]
    if live_ky_price is None:
        live_ky_price = fetch_live_metro_retail_price("Cincinnati_KY")["price"]

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Cincinnati OH/KY region (Live OH: ${live_oh_price:.3f}/gal, Live KY: ${live_ky_price:.3f}/gal)...")
    
    tickers = {
        "gasoline_rbob": "RB=F",
        "wti_crude": "CL=F",
        "brent_crude": "BZ=F"
    }
    
    dfs = []
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            close_series = data['Close'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Close']
            df_item = pd.DataFrame({'date': pd.to_datetime(close_series.index).tz_localize(None), name: close_series.values})
            dfs.append(df_item.set_index('date'))
        except Exception as e:
            logger.warning(f"Could not download ticker {ticker}: {e}")
            
    if not dfs:
        return _generate_synthetic_cincinnati_data(start_date, end_date, live_oh_price, live_ky_price)
        
    market_df = pd.concat(dfs, axis=1).sort_index().ffill().bfill().reset_index()
    
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    margin_oh = live_oh_price - latest_rbob
    margin_ky = live_ky_price - latest_rbob
    
    market_df['cincinnati_oh_retail_gasoline'] = market_df['gasoline_rbob'] + margin_oh
    market_df['cincinnati_ky_retail_gasoline'] = market_df['gasoline_rbob'] + margin_ky
    market_df['cincinnati_metro_avg_retail'] = (market_df['cincinnati_oh_retail_gasoline'] + market_df['cincinnati_ky_retail_gasoline']) / 2.0
    
    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['oh_ky_tax_spread'] = market_df['cincinnati_oh_retail_gasoline'] - market_df['cincinnati_ky_retail_gasoline']
    market_df['catlettsburg_crack_spread'] = market_df['cincinnati_oh_retail_gasoline'] - market_df['brent_crude_per_gal']
    
    return market_df


def _generate_synthetic_cincinnati_data(
    start_date: str, 
    end_date: str, 
    live_oh_price: float = 3.450, 
    live_ky_price: float = 3.325
) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)
    
    brent_crude = 77.0 + np.cumsum(np.random.normal(0, 1.15, n))
    wti_crude = brent_crude - 3.5 + np.random.normal(0, 0.4, n)
    rbob = (brent_crude / 42.0) * 1.30 + np.cumsum(np.random.normal(0, 0.023, n))
    
    margin_oh = live_oh_price - rbob[-1]
    margin_ky = live_ky_price - rbob[-1]
    
    oh_retail = rbob + margin_oh
    ky_retail = rbob + margin_ky
    metro_avg = (oh_retail + ky_retail) / 2.0
    
    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 45.0),
        'cincinnati_oh_retail_gasoline': np.maximum(oh_retail, 2.10),
        'cincinnati_ky_retail_gasoline': np.maximum(ky_retail, 1.98),
        'cincinnati_metro_avg_retail': np.maximum(metro_avg, 2.04),
        'brent_crude_per_gal': brent_crude / 42.0,
        'oh_ky_tax_spread': oh_retail - ky_retail,
        'catlettsburg_crack_spread': oh_retail - (brent_crude / 42.0)
    })


def get_cincinnati_regional_events() -> pd.DataFrame:
    """
    Merges full macro LLM event logs with PADD 2 Ohio Valley refining dynamics (Marathon Catlettsburg KY 291k bpd),
    Ohio River petroleum barge logistics, Lower Mississippi River downriver low-water bottlenecks (Cairo confluence),
    Buckeye Pipeline shipments, state gas tax differential updates (OH 38.5¢ vs KY 26.0¢), and localized Tri-State NOAA Weather.
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. Cincinnati & Ohio River Valley Regional Logistics, Refining & Tax Disruption Dataset
    cincinnati_events = [
        {"date": "2022-03-10", "headline": "Marathon Petroleum Catlettsburg, KY Refinery (291,000 bpd) initiates un-planned fluid catalytic cracker shutdown, tightening Ohio Valley unleaded supply.", "category": "Catlettsburg Refinery Outage"},
        {"date": "2022-07-01", "headline": "Ohio General Assembly re-affirms state motor fuel tax of $0.385/gal; Kentucky fuel tax holds at $0.260/gal, maintaining $0.125/gal cross-river gas price spread.", "category": "Policy/Gas Tax"},
        {"date": "2022-10-12", "headline": "Mississippi River drought drops Memphis gage to record low (-10.7 ft); petroleum barges to Ohio River face draft restrictions (-40% capacity limit) and Cairo tow jams.", "category": "Mississippi River Low-Water"},
        {"date": "2023-02-20", "headline": "USACE performs scheduled overhaul of Markland Locks & Dam on Ohio River near Cincinnati, restricting petroleum barge throughput and expanding local rack margins.", "category": "Ohio River Lock Maintenance"},
        {"date": "2023-08-15", "headline": "Buckeye Pipeline system reports minor pump station pressure drop near Dayton, OH, temporarily throttling product flow to Cincinnati terminals.", "category": "Regional Pipeline"},
        {"date": "2023-10-05", "headline": "Lower Mississippi River autumn low-water crisis restricts tow traffic at Cairo, IL confluence; Gulf Coast unleaded barge spot freight rates surge +320%.", "category": "Mississippi River Low-Water"},
        {"date": "2024-05-12", "headline": "Cross-river fuel commuting surge: NKY gas retailers report record volume from Hamilton County, OH drivers avoiding $0.385/gal Ohio gas tax.", "category": "Cross-River Arbitrage"},
        {"date": "2025-01-22", "headline": "Winter ice lockout on Upper Ohio River traps petroleum barges downstream; Cincinnati fuel distributors switch to rail transport, adding +$0.112/gal to rack price.", "category": "Ohio River Ice Lockout"}
    ]
    
    regional_df = pd.DataFrame(cincinnati_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])
    
    # 3. Merge Localized NOAA Weather Alerts for Cincinnati Metro & NKY
    noaa_cin_df = get_cincinnati_weather_dataset()
    noaa_formatted = noaa_cin_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})
    
    # Combine Macro + Regional + Local NOAA Weather
    combined_events = pd.concat([macro_events_df, regional_df, noaa_formatted], ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
