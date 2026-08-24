"""
Data Ingestion Module
Fetches quantitative market time-series data (Gasoline futures, Crude Oil futures)
and provides unstructured event logs & NOAA National Production Basin Weather alerts for LLM scoring.
Includes Iran / Strait of Hormuz conflict alerts, Suez Canal / Red Sea shipping rerouting events,
Venezuela heavy crude / OFAC sanctions feeds, Executive Social Media (Trump Twitter/Truth Social) feeds,
and Key Market Movers (Saudi Energy Minister, Fed Chair Powell, DOE SPR, IEA Birol).
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging
from src.noaa_weather import get_national_production_weather_dataset
from src.geopolitical_feeds import get_geopolitical_maritime_events
from src.executive_social_feed import get_executive_social_energy_feed
from src.key_movers_feed import get_key_movers_event_feed

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
    market_df = market_df.ffill().bfill().reset_index()
    return market_df


def _generate_synthetic_market_data(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)
    
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
    Combines global macroeconomic & OPEC events, NOAA National Weather advisories,
    Iran / Strait of Hormuz conflict alerts, Suez Canal / Red Sea shipping reroutings,
    Venezuela heavy crude OFAC sanctions feeds, Executive Social Media feeds,
    and Key Market Movers (Saudi Energy Minister, Fed Chair Powell, DOE SPR).
    """
    base_events = [
        {"date": "2022-02-24", "headline": "Russia invades Ukraine; global crude oil prices surge above $100/bbl on severe energy supply disruption fears.", "category": "Geopolitics"},
        {"date": "2022-03-08", "headline": "US bans imports of Russian crude oil and petroleum products; gasoline prices reach historic highs.", "category": "Policy/Sanctions"},
        {"date": "2022-06-14", "headline": "Federal Reserve raises interest rates by 75 bps to combat high inflation; recession fears weigh on oil demand.", "category": "Macroeconomics"},
        {"date": "2022-09-05", "headline": "OPEC+ agrees to minor production cut of 100,000 barrels per day to support oil prices.", "category": "OPEC"},
        {"date": "2022-10-05", "headline": "OPEC+ announces major oil output cut of 2 million barrels per day starting November.", "category": "OPEC"},
        {"date": "2023-04-02", "headline": "Saudi Arabia and OPEC+ surprise market with unexpected voluntary oil production cuts of 1.16 million barrels per day.", "category": "OPEC"},
        {"date": "2023-06-04", "headline": "Saudi Arabia announces additional solo output cut of 1 million barrels per day starting July.", "category": "OPEC"},
        {"date": "2023-10-07", "headline": "Conflict erupts in Middle East following attack on Israel; energy market risk premium spikes.", "category": "Geopolitics"},
        {"date": "2023-11-30", "headline": "OPEC+ members agree to voluntary production cuts totaling 2.2 million barrels per day for Q1 2024.", "category": "OPEC"},
        {"date": "2023-12-19", "headline": "Houthi attacks on Red Sea shipping force major oil tankers to reroute around Africa, boosting shipping costs.", "category": "Geopolitics/Supply Chain"},
        {"date": "2024-01-12", "headline": "US and UK launch airstrikes against Houthi targets in Yemen; oil supply risk premium increases.", "category": "Geopolitics"},
        {"date": "2024-03-03", "headline": "OPEC+ extends voluntary production cuts of 2.2 million bpd through Q2 2024.", "category": "OPEC"},
        {"date": "2024-06-02", "headline": "OPEC+ outlines plan to phase out voluntary production cuts starting October, causing oil sell-off.", "category": "OPEC"},
        {"date": "2024-09-05", "headline": "OPEC+ delays scheduled October oil output increase by two months due to weak demand sentiment.", "category": "OPEC"},
        {"date": "2024-10-01", "headline": "Middle East hostilities escalate with missile attacks; crude futures rally 5% on potential Iranian oil facility risks.", "category": "Geopolitics"}
    ]
    
    events_df = pd.DataFrame(base_events)
    events_df['date'] = pd.to_datetime(events_df['date'])
    
    # 1. Merge NOAA Weather Advisories
    try:
        noaa_df = get_national_production_weather_dataset()
        events_df = pd.concat([events_df, noaa_df], ignore_index=True)
    except Exception as e:
        logger.warning(f"Could not load NOAA National Weather dataset: {e}")
        
    # 2. Merge Global Geopolitical Maritime Feeds
    try:
        geo_maritime_df = get_geopolitical_maritime_events()
        events_df = pd.concat([events_df, geo_maritime_df], ignore_index=True)
    except Exception as e:
        logger.warning(f"Could not load Geopolitical Maritime dataset: {e}")

    # 3. Merge Executive Social Media Feed
    try:
        social_feed = get_executive_social_energy_feed()
        social_events = social_feed[['date', 'post_text']].copy()
        social_events.rename(columns={'post_text': 'headline'}, inplace=True)
        social_events['category'] = 'Executive_Social_Media'
        events_df = pd.concat([events_df, social_events], ignore_index=True)
    except Exception as e:
        logger.warning(f"Could not load Executive Social Media feed: {e}")

    # 4. Merge Key Market Movers Feed (Saudi Energy Minister, Fed Chair, DOE SPR, IEA)
    try:
        movers_feed = get_key_movers_event_feed()
        movers_events = movers_feed[['date', 'headline']].copy()
        movers_events['category'] = 'Key_Market_Movers'
        events_df = pd.concat([events_df, movers_events], ignore_index=True)
    except Exception as e:
        logger.warning(f"Could not load Key Market Movers feed: {e}")

    # 5. Merge Finlight.me Real-Time Financial Energy News Feed
    try:
        from src.finlight_feed import get_finlight_energy_events
        finlight_df = get_finlight_energy_events()
        if not finlight_df.empty:
            fin_events = finlight_df[['date', 'headline']].copy()
            fin_events['category'] = 'Finlight_Energy_News'
            events_df = pd.concat([events_df, fin_events], ignore_index=True)
            logger.info(f"Successfully integrated {len(fin_events)} live finlight.me news events into LLM dataset.")
    except Exception as e:
        logger.warning(f"Could not load Finlight.me news feed: {e}")

    events_df = events_df.sort_values('date').reset_index(drop=True)
    return events_df
