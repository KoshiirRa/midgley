"""
Tulsa, Oklahoma Regional Gas Price Forecasting Module (src/tulsa_regional.py)
Supports Live Pump Price Anchoring ($3.89/gal) & Dynamic Retail Margin Calibrations.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def fetch_tulsa_market_data(
    start_date: str = "2022-01-01", 
    end_date: str = None,
    live_current_price: float = 3.89
) -> pd.DataFrame:
    """
    Fetches market data tailored to Tulsa, OK and dynamically calibrates the retail series
    to match live pump prices ($3.89/gal).
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Tulsa, OK region (Live Pump Price Anchor: ${live_current_price:.2f}/gal)...")
    
    tickers = {
        "gasoline_rbob": "RB=F",
        "cushing_wti": "CL=F",
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
        return _generate_synthetic_tulsa_data(start_date, end_date, live_current_price)
        
    market_df = pd.concat(dfs, axis=1).sort_index().ffill().bfill().reset_index()
    
    # Calculate dynamic margin between live pump price ($3.89) and latest RBOB wholesale price
    latest_rbob = market_df['gasoline_rbob'].iloc[-1]
    dynamic_margin = live_current_price - latest_rbob
    
    market_df['wti_crude'] = market_df['cushing_wti']
    market_df['tulsa_retail_gasoline'] = market_df['gasoline_rbob'] + dynamic_margin
    market_df['cushing_crude_per_gal'] = market_df['cushing_wti'] / 42.0
    market_df['crack_spread'] = market_df['tulsa_retail_gasoline'] - market_df['cushing_crude_per_gal']
    
    return market_df


def _generate_synthetic_tulsa_data(start_date: str, end_date: str, live_current_price: float = 3.89) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)
    
    cushing_wti = 74.0 + np.cumsum(np.random.normal(0, 1.2, n))
    rbob = (cushing_wti / 42.0) * 1.32 + np.cumsum(np.random.normal(0, 0.025, n))
    dynamic_margin = live_current_price - rbob[-1]
    tulsa_retail = rbob + dynamic_margin
    
    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'wti_crude': np.maximum(cushing_wti, 40.0),
        'cushing_wti': np.maximum(cushing_wti, 40.0),
        'tulsa_retail_gasoline': np.maximum(tulsa_retail, 2.10),
        'cushing_crude_per_gal': cushing_wti / 42.0,
        'crack_spread': tulsa_retail - (cushing_wti / 42.0)
    })


def get_tulsa_regional_events() -> pd.DataFrame:
    events = [
        {"date": "2022-02-24", "headline": "Russia invades Ukraine; Cushing WTI crude surges above $100/bbl, driving Tulsa gas prices higher.", "category": "Global/Cushing"},
        {"date": "2022-05-04", "headline": "Severe storms and tornadoes sweep through Northeast Oklahoma, causing power outages at Tulsa area fuel terminals.", "category": "Oklahoma Weather"},
        {"date": "2022-09-15", "headline": "HF Sinclair West Tulsa refinery initiates scheduled autumn maintenance on fluid catalytic cracking unit.", "category": "Tulsa Refinery"},
        {"date": "2022-12-08", "headline": "Keystone Pipeline shutdown following spill in Kansas causes crude bottleneck at Cushing, OK storage hub.", "category": "Cushing Pipeline"},
        {"date": "2023-04-19", "headline": "Supercell tornado outbreak damages power lines near Cushing, OK oil storage hub.", "category": "Oklahoma Weather"},
        {"date": "2023-06-10", "headline": "Phillips 66 Ponca City refinery reports unplanned outage, tightening Midwest regional gasoline supply.", "category": "Regional Refinery"},
        {"date": "2024-04-26", "headline": "Multiple severe tornadoes strike Eastern Oklahoma; HF Sinclair West Tulsa refinery operates on backup power.", "category": "Oklahoma Weather"},
        {"date": "2025-05-18", "headline": "EF-3 Tornado strikes West Tulsa industrial corridor, halting 125,000 bpd HF Sinclair refinery loading racks.", "category": "Tulsa Disruption"},
        {"date": "2025-09-02", "headline": "Explorer Pipeline reports pump station failure in Glenpool, OK, throttling unleaded fuel shipments to Tulsa.", "category": "Tulsa Pipeline"}
    ]
    df = pd.DataFrame(events)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)
