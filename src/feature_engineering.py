"""
Feature Engineering & Data Fusion Module
Computes technical time-series features, applies exponential decay to LLM event scores,
and merges quantitative, physical alternative data (Cboe OVX Volatility, Baker Hughes Rigs),
and qualitative features chronologically without lookahead bias.
"""

import pandas as pd
import numpy as np
import logging
from src.alternative_data_feeds import fetch_cboe_crude_volatility_ovx, get_baker_hughes_rig_count_feed

logger = logging.getLogger(__name__)

def create_feature_matrix(
    market_df: pd.DataFrame, 
    events_df: pd.DataFrame = None, 
    forecast_horizon: int = 5,
    decay_half_life_days: float = 5.0
) -> pd.DataFrame:
    """
    Creates a unified feature dataset for time-series forecasting.
    
    Parameters:
    - market_df: DataFrame with 'date', 'gasoline_rbob', 'wti_crude', 'brent_crude'
    - events_df: DataFrame with LLM scored events containing 'date', 'geopolitical_risk', etc.
    - forecast_horizon: Number of business days ahead to forecast (default 5 days = 1 week)
    - decay_half_life_days: Exponential decay half-life for news event sentiment impact
    """
    logger.info(f"Engineering features with {forecast_horizon}-day forecast horizon...")
    df = market_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # 1. Quantitative Technical Indicators
    if 'wti_crude' in df.columns:
        df['crude_per_gal'] = df['wti_crude'] / 42.0
        df['crack_spread'] = df['gasoline_rbob'] - df['crude_per_gal']
        df['crude_return_1d'] = df['wti_crude'].pct_change(1)
        df['crude_return_5d'] = df['wti_crude'].pct_change(5)
    else:
        df['crack_spread'] = 0.0
        df['crude_return_1d'] = 0.0
        df['crude_return_5d'] = 0.0
        
    df['gas_return_1d'] = df['gasoline_rbob'].pct_change(1)
    df['gas_return_5d'] = df['gasoline_rbob'].pct_change(5)
    df['gas_return_10d'] = df['gasoline_rbob'].pct_change(10)
    
    # Moving Averages & Volatility
    df['gas_ma_7'] = df['gasoline_rbob'].rolling(7).mean()
    df['gas_ma_14'] = df['gasoline_rbob'].rolling(14).mean()
    df['gas_ma_30'] = df['gasoline_rbob'].rolling(30).mean()
    df['gas_volatility_14'] = df['gas_return_1d'].rolling(14).std()
    
    # Seasonality
    df['day_of_year'] = df['date'].dt.dayofyear
    df['sin_day'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['cos_day'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
    
    # 2. Merge Alternative Physical Data (Cboe OVX Volatility & Baker Hughes Rig Count)
    try:
        ovx_df = fetch_cboe_crude_volatility_ovx(start_date=df['date'].min().strftime("%Y-%m-%d"))
        if not ovx_df.empty:
            df = pd.merge(df, ovx_df, on='date', how='left')
            df['ovx_volatility_index'] = df['ovx_volatility_index'].ffill().bfill()
            df['ovx_return_1d'] = df['ovx_volatility_index'].pct_change(1)
    except Exception as e:
        logger.warning(f"Could not merge OVX volatility feed: {e}")
        
    try:
        rigs_df = get_baker_hughes_rig_count_feed()
        if not rigs_df.empty:
            df = pd.merge(df, rigs_df, on='date', how='left')
            df['us_active_oil_rigs'] = df['us_active_oil_rigs'].ffill().bfill()
            df['permian_rigs'] = df['permian_rigs'].ffill().bfill()
    except Exception as e:
        logger.warning(f"Could not merge Baker Hughes Rig Count feed: {e}")
        
    # Fill any remaining missing alternative values
    for col in ['ovx_volatility_index', 'ovx_return_1d', 'us_active_oil_rigs', 'permian_rigs']:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)
        else:
            df[col] = 0.0

    # 3. Event Feature Fusion with Exponential Decay Memory
    llm_feature_cols = ['geopolitical_risk', 'supply_disruption', 'demand_sentiment', 'opec_action', 'overall_price_pressure']
    
    if events_df is not None and not events_df.empty:
        events = events_df.copy()
        events['date'] = pd.to_datetime(events['date'])
        
        merged = pd.merge(df, events[['date'] + llm_feature_cols], on='date', how='left')
        merged[llm_feature_cols] = merged[llm_feature_cols].fillna(0.0)
        
        decay_factor = np.exp(-np.log(2) / decay_half_life_days)
        
        for col in llm_feature_cols:
            decayed_values = np.zeros(len(merged))
            current_val = 0.0
            for i in range(len(merged)):
                new_shock = merged.loc[i, col]
                current_val = current_val * decay_factor + new_shock
                decayed_values[i] = current_val
            merged[f'event_{col}'] = decayed_values
        df = merged
    else:
        for col in llm_feature_cols:
            df[f'event_{col}'] = 0.0

    # 4. Forecast Target Construction
    df[f'target_price_{forecast_horizon}d'] = df['gasoline_rbob'].shift(-forecast_horizon)
    df[f'target_return_{forecast_horizon}d'] = (df[f'target_price_{forecast_horizon}d'] - df['gasoline_rbob']) / df['gasoline_rbob']
    
    df = df.dropna().reset_index(drop=True)
    return df


def prepare_chronological_splits(df: pd.DataFrame, train_ratio: float = 0.8, forecast_horizon: int = 5):
    """
    Splits dataset chronologically to prevent temporal data leakage.
    Returns: X_train_quant, X_train_hybrid, y_train, X_test_quant, X_test_hybrid, y_test, test_df
    """
    quant_features = [
        'gasoline_rbob', 'wti_crude', 'crack_spread',
        'gas_return_1d', 'gas_return_5d', 'gas_return_10d',
        'crude_return_1d', 'crude_return_5d',
        'gas_ma_7', 'gas_ma_14', 'gas_ma_30',
        'gas_volatility_14', 'ovx_volatility_index', 'ovx_return_1d',
        'us_active_oil_rigs', 'permian_rigs',
        'sin_day', 'cos_day'
    ]
    quant_features = [f for f in quant_features if f in df.columns]
    
    event_features = [c for c in df.columns if c.startswith('event_')]
    hybrid_features = quant_features + event_features
    
    target_col = f'target_price_{forecast_horizon}d'
    
    split_idx = int(len(df) * train_ratio)
    
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    X_train_quant = train_df[quant_features]
    X_train_hybrid = train_df[hybrid_features]
    y_train = train_df[target_col]
    
    X_test_quant = test_df[quant_features]
    X_test_hybrid = test_df[hybrid_features]
    y_test = test_df[target_col]
    
    return {
        'X_train_quant': X_train_quant,
        'X_train_hybrid': X_train_hybrid,
        'y_train': y_train,
        'X_test_quant': X_test_quant,
        'X_test_hybrid': X_test_hybrid,
        'y_test': y_test,
        'quant_feature_names': quant_features,
        'hybrid_feature_names': hybrid_features,
        'test_df': test_df
    }
