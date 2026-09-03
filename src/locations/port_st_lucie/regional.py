"""
Port St. Lucie, Florida Regional Gas Price Forecasting Module (src/locations/port_st_lucie/regional.py)
Fuses Port St. Lucie regional market data, PADD 1C South Atlantic waterborne marine supply dynamics,
Port Everglades & Port Canaveral petroleum terminal offloading, Florida State Motor Fuel Tax ($0.384/gal),
and localized NOAA Weather Alerts for St. Lucie County (FLZ147 / Zip 34952).
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import logging

from src.noaa_weather import get_port_st_lucie_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)

def fetch_port_st_lucie_market_data(
    start_date: str = "2022-01-01", 
    end_date: str = None,
    live_current_price: float = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Port St. Lucie, FL & PADD 1C South Atlantic region
    and dynamically calibrates the retail series to match live pump prices.
    """
    if live_current_price is None:
        live_current_price = fetch_live_metro_retail_price("Port_St_Lucie_FL")["price"]

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Port St. Lucie, FL region (Live Pump Price Anchor: ${live_current_price:.2f}/gal)...")
    
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
        return _generate_synthetic_port_st_lucie_data(start_date, end_date, live_current_price)
        
    market_df = pd.concat(dfs, axis=1).sort_index().ffill().bfill().reset_index()
    if market_df.empty or 'gasoline_rbob' not in market_df.columns or len(market_df) == 0:
        return _generate_synthetic_port_st_lucie_data(start_date, end_date, live_current_price)
    
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    dynamic_margin = live_current_price - latest_rbob
    
    market_df['port_st_lucie_retail_gasoline'] = market_df['gasoline_rbob'] + dynamic_margin
    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['port_st_lucie_rack_crack_spread'] = market_df['port_st_lucie_retail_gasoline'] - market_df['brent_crude_per_gal']
    
    return market_df


def _generate_synthetic_port_st_lucie_data(start_date: str, end_date: str, live_current_price: float = 3.380) -> pd.DataFrame:
    """
    Generates synthetic time series for Port St. Lucie, FL when offline or yfinance fails.
    """
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)
    
    brent_crude = 78.0 + np.cumsum(np.random.normal(0, 1.1, n))
    wti_crude = brent_crude - 4.0 + np.random.normal(0, 0.4, n)
    rbob = (brent_crude / 42.0) * 1.28 + np.cumsum(np.random.normal(0, 0.022, n))
    dynamic_margin = live_current_price - rbob[-1]
    psl_retail = rbob + dynamic_margin
    
    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 45.0),
        'port_st_lucie_retail_gasoline': np.maximum(psl_retail, 2.00),
        'brent_crude_per_gal': brent_crude / 42.0,
        'port_st_lucie_rack_crack_spread': psl_retail - (brent_crude / 42.0)
    })


def get_port_st_lucie_regional_events() -> pd.DataFrame:
    """
    Merges full macro LLM event logs (Finlight.me news, Executive Social Media, Maritime, Key Movers)
    with PADD 1C Port Everglades waterborne barge offloading, Florida State Motor Fuel Tax ($0.384/gal),
    Atlantic hurricane landfalls, and localized St. Lucie County (FLZ147) NOAA Weather.
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. Port St. Lucie, FL & PADD 1C Regional Logistics, Waterborne Tanker & Hurricane Disruption Dataset
    psl_events = [
        {"date": "2022-09-28", "headline": "Hurricane Ian forces emergency port closures at Port Everglades and Tampa marine oil terminals, disrupting Treasure Coast tank truck supply.", "category": "Port Everglades Marine Closure"},
        {"date": "2023-04-13", "headline": "Historic 25-inch flash deluge floods Fort Lauderdale & Port Everglades fuel loading racks, halting tank truck dispatches to Port St. Lucie.", "category": "Port Everglades Deluge Outage"},
        {"date": "2023-10-01", "headline": "Florida annual motor fuel tax holiday expires, reinstating state excise tax of $0.253/gal ($0.384/gal total St. Lucie tax burden).", "category": "Policy/FL Gas Tax"},
        {"date": "2024-08-05", "headline": "Hurricane Debby marine storm surge bottlenecks Straits of Florida barge transit lanes to Port Canaveral petroleum terminals.", "category": "Marine Barge Transit Bottleneck"},
        {"date": "2024-10-09", "headline": "Hurricane Milton landfall shuts Port Canaveral berths, triggering acute retail panic buying along I-95 & Florida Turnpike corridors.", "category": "Port Canaveral Hurricane Shutdown"},
        {"date": "2025-02-15", "headline": "Peak South Florida winter tourist driving season surges regional gasoline demand across St. Lucie County retail hubs.", "category": "Tourist Driving Season Spike"}
    ]
    
    regional_df = pd.DataFrame(psl_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])
    
    # 3. Merge Localized NOAA Weather Alerts for St. Lucie County FL (FLZ147 / Zip 34952)
    noaa_psl_df = get_port_st_lucie_weather_dataset()
    
    if not noaa_psl_df.empty:
        noaa_psl_df['category'] = "NOAA Weather St. Lucie County (FLZ147)"
        combined_df = pd.concat([macro_events_df, regional_df, noaa_psl_df], ignore_index=True)
    else:
        combined_df = pd.concat([macro_events_df, regional_df], ignore_index=True)
        
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    return combined_df.sort_values('date').reset_index(drop=True)
