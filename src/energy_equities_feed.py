"""
Energy Equities & Refining Crack Spread Correlation Module (src/energy_equities_feed.py)
Analyzes correlation between RBOB Gasoline futures (RB=F), WTI Crude (CL=F),
and major US energy equities:
- XLE: Energy Select Sector SPDR ETF
- VLO: Valero Energy Corp (Largest US Independent Refiner)
- MPC: Marathon Petroleum Corp
- DINO: HF Sinclair Corp (Operates 125,000 bpd West Tulsa Refinery!)
- XOM: ExxonMobil Corp
"""

import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

ENERGY_EQUITY_TICKERS = {
    "XLE": "Energy Select Sector SPDR Fund (Sector Benchmark)",
    "VLO": "Valero Energy Corp (Independent Refining Leader)",
    "MPC": "Marathon Petroleum Corp (Midwest Refining)",
    "DINO": "HF Sinclair Corp (Operator of West Tulsa 125,000 bpd Refinery)",
    "XOM": "ExxonMobil Corp (Integrated Supermajor)"
}

def fetch_energy_equities_data(start_date: str = "2022-01-01", end_date: str = None) -> pd.DataFrame:
    """
    Fetches historical daily close prices for key energy sector equities & ETFs.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
        
    logger.info(f"Fetching energy equities market data from {start_date} to {end_date}...")
    
    dfs = []
    for ticker, desc in ENERGY_EQUITY_TICKERS.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                close_series = data['Close'][ticker]
            else:
                close_series = data['Close']
            
            df_item = pd.DataFrame({'date': close_series.index, ticker: close_series.values})
            df_item['date'] = pd.to_datetime(df_item['date']).dt.tz_localize(None)
            dfs.append(df_item.set_index('date'))
        except Exception as e:
            logger.warning(f"Could not download energy equity {ticker}: {e}")
            
    if not dfs:
        return pd.DataFrame()
        
    equities_df = pd.concat(dfs, axis=1).sort_index().ffill().bfill().reset_index()
    return equities_df

def compute_commodity_equity_correlations(market_df: pd.DataFrame, equities_df: pd.DataFrame) -> dict:
    """
    Calculates Pearson correlation coefficients (r) between RBOB gasoline futures returns,
    WTI crude returns, refining crack spreads, and energy equity stock returns.
    """
    merged = pd.merge(market_df, equities_df, on='date', how='inner')
    if merged.empty:
        return {}
        
    # Calculate daily 1-day percentage returns
    returns_df = pd.DataFrame({'date': merged['date']})
    
    if 'gasoline_rbob' in merged.columns:
        returns_df['rbob_return'] = merged['gasoline_rbob'].pct_change()
    if 'wti_crude' in merged.columns:
        returns_df['crude_return'] = merged['wti_crude'].pct_change()
        # Compute crack spread ($/gal)
        merged['crack_spread'] = merged['gasoline_rbob'] - (merged['wti_crude'] / 42.0)
        returns_df['crack_spread_change'] = merged['crack_spread'].diff()

    for ticker in ENERGY_EQUITY_TICKERS.keys():
        if ticker in merged.columns:
            returns_df[f'{ticker}_return'] = merged[ticker].pct_change()

    returns_df = returns_df.dropna()
    
    correlations = {}
    if 'rbob_return' in returns_df.columns:
        for ticker in ENERGY_EQUITY_TICKERS.keys():
            col = f'{ticker}_return'
            if col in returns_df.columns:
                r_rbob = returns_df['rbob_return'].corr(returns_df[col])
                r_crude = returns_df['crude_return'].corr(returns_df[col]) if 'crude_return' in returns_df.columns else 0.0
                r_crack = returns_df['crack_spread_change'].corr(returns_df[col]) if 'crack_spread_change' in returns_df.columns else 0.0
                
                correlations[ticker] = {
                    "description": ENERGY_EQUITY_TICKERS[ticker],
                    "corr_with_RBOB_gasoline": round(float(r_rbob), 3),
                    "corr_with_WTI_crude": round(float(r_crude), 3),
                    "corr_with_Refining_Crack_Spread": round(float(r_crack), 3),
                    "relationship_type": "Strong Refining Margin Proxy" if r_crack > 0.35 else "Broad Commodity Beta"
                }
                
    return correlations

if __name__ == "__main__":
    from src.data_ingestion import fetch_market_data
    m_df = fetch_market_data("2022-01-01")
    e_df = fetch_energy_equities_data("2022-01-01")
    corr_results = compute_commodity_equity_correlations(m_df, e_df)
    print("\n" + "="*80)
    print(" COMMODITY FUTURES vs. ENERGY EQUITIES CORRELATION MATRIX")
    print("="*80)
    print(json.dumps(corr_results, indent=2))
