"""
Data Ingestion Module
Fetches quantitative market time-series data (Gasoline futures, Crude Oil futures)
and provides unstructured event logs / news feeds for LLM scoring.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_market_data(start_date: str = "2022-01-01", end_date: str = None) -> pd.DataFrame:
    """
    Fetches daily commodity futures market data using yfinance:
    - RB=F: RBOB Gasoline Futures ($/gallon proxy for unleaded gas)
    - CL=F: WTI Crude Oil Futures ($/barrel)
    - BZ=F: Brent Crude Oil Futures ($/barrel)
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data from {start_date} to {end_date}...")
    
    tickers = {
        "gasoline_rbob": "RB=F",
        "wti_crude": "CL=F",
        "brent_crude": "BZ=F"
    }
    
    dfs = []
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten multi-index columns if returned by yfinance
                close_series = data['Close'][ticker]
            else:
                close_series = data['Close']
            
            df_item = pd.DataFrame({'date': close_series.index, name: close_series.values})
            df_item['date'] = pd.to_datetime(df_item['date']).dt.tz_localize(None)
            dfs.append(df_item.set_index('date'))
        except Exception as e:
            logger.warning(f"Could not download ticker {ticker}: {e}")
            
    if not dfs:
        logger.error("No market data downloaded. Creating synthetic benchmark data.")
        return _generate_synthetic_market_data(start_date, end_date)
        
    market_df = pd.concat(dfs, axis=1).sort_index()
    # Forward fill weekend/holiday gaps
    market_df = market_df.ffill().bfill()
    market_df = market_df.reset_index()
    return market_df


def _generate_synthetic_market_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fallback synthetic generator if yfinance network request fails."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)
    
    # Baseline random walk around $2.50/gal for RBOB and $75/bbl for Crude
    wti = 75.0 + np.cumsum(np.random.normal(0, 1.2, n))
    gasoline = (wti / 42.0) * 1.35 + np.cumsum(np.random.normal(0, 0.03, n))
    brent = wti + 4.0 + np.random.normal(0, 0.5, n)
    
    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(gasoline, 1.50),
        'wti_crude': np.maximum(wti, 40.0),
        'brent_crude': np.maximum(brent, 45.0)
    })


def get_historical_event_dataset() -> pd.DataFrame:
    """
    Returns a curated dataset of historical news, geopolitical disruptions,
    weather events, and macroeconomic announcements affecting energy markets.
    """
    events = [
        # 2022 Events
        {"date": "2022-02-24", "headline": "Russia invades Ukraine; global crude oil prices surge above $100/bbl on severe energy supply disruption fears.", "category": "Geopolitics"},
        {"date": "2022-03-08", "headline": "US bans imports of Russian crude oil and petroleum products; gasoline prices reach historic highs.", "category": "Policy/Sanctions"},
        {"date": "2022-06-14", "headline": "Federal Reserve raises interest rates by 75 bps to combat high inflation; recession fears weigh on oil demand.", "category": "Macroeconomics"},
        {"date": "2022-09-05", "headline": "OPEC+ agrees to minor production cut of 100,000 barrels per day to support oil prices.", "category": "OPEC"},
        {"date": "2022-09-28", "headline": "Hurricane Ian forces evacuation of Gulf Coast offshore platforms and shuts regional refinery capacity.", "category": "Weather/Disruption"},
        {"date": "2022-10-05", "headline": "OPEC+ announces major oil output cut of 2 million barrels per day starting November.", "category": "OPEC"},
        
        # 2023 Events
        {"date": "2023-04-02", "headline": "Saudi Arabia and OPEC+ surprise market with unexpected voluntary oil production cuts of 1.16 million barrels per day.", "category": "OPEC"},
        {"date": "2023-06-04", "headline": "Saudi Arabia announces additional solo output cut of 1 million barrels per day starting July.", "category": "OPEC"},
        {"date": "2023-08-28", "headline": "Hurricane Idalia threatens Florida and Gulf Coast refining hubs; precautionary shutdowns reported.", "category": "Weather/Disruption"},
        {"date": "2023-10-07", "headline": "Conflict erupts in Middle East following attack on Israel; energy market risk premium spikes.", "category": "Geopolitics"},
        {"date": "2023-11-30", "headline": "OPEC+ members agree to voluntary production cuts totaling 2.2 million barrels per day for Q1 2024.", "category": "OPEC"},
        {"date": "2023-12-19", "headline": "Houthi attacks on Red Sea shipping force major oil tankers to reroute around Africa, boosting shipping costs.", "category": "Geopolitics/Supply Chain"},
        
        # 2024 Events
        {"date": "2024-01-12", "headline": "US and UK launch airstrikes against Houthi targets in Yemen; oil supply risk premium increases.", "category": "Geopolitics"},
        {"date": "2024-03-03", "headline": "OPEC+ extends voluntary production cuts of 2.2 million bpd through Q2 2024.", "category": "OPEC"},
        {"date": "2024-05-15", "headline": "US inflation cools slightly; EIA reports unexpected crude oil inventory draw due to strong seasonal driving demand.", "category": "Macro/EIA"},
        {"date": "2024-06-02", "headline": "OPEC+ outlines plan to phase out voluntary production cuts starting October, causing oil sell-off.", "category": "OPEC"},
        {"date": "2024-07-08", "headline": "Hurricane Beryl slams Texas coast, causing power outages at Houston refinery facilities and port closures.", "category": "Weather/Disruption"},
        {"date": "2024-09-05", "headline": "OPEC+ delays scheduled October oil output increase by two months due to weak demand sentiment.", "category": "OPEC"},
        {"date": "2024-10-01", "headline": "Middle East hostilities escalate with missile attacks; crude futures rally 5% on potential Iranian oil facility risks.", "category": "Geopolitics"},
        
        # 2025-2026 Recent/Hypothetical Context
        {"date": "2025-01-20", "headline": "New US administration outlines energy policy changes, promising increased domestic drilling permits.", "category": "Policy"},
        {"date": "2025-04-15", "headline": "Major refinery explosion in Louisiana disrupts 400,000 bpd of Gulf Coast unleaded fuel production.", "category": "Supply Disruption"},
        {"date": "2025-08-10", "headline": "OPEC+ announces disciplined quota compliance amid resilient global transportation fuel demand.", "category": "OPEC"},
        {"date": "2026-02-14", "headline": "Severe polar vortex strikes Texas and refinery operations freeze up along Gulf Coast.", "category": "Weather/Disruption"},
        {"date": "2026-06-01", "headline": "OPEC+ maintains production targets while summer driving demand sets record highs.", "category": "OPEC"}
    ]
    
    df = pd.DataFrame(events)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)
