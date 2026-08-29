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

    # 3. Event Feature Fusion with Exponential Decay Memory (Paper 2608.25128v1 Diagnostic Routing)
    llm_feature_cols = ['geopolitical_risk', 'supply_disruption', 'demand_sentiment', 'opec_action', 'overall_price_pressure']
    
    diagnostic = compute_context_routing_diagnostic(df, target_col='gasoline_rbob', horizon=forecast_horizon, threshold=0.95)
    logger.info(f"Context Routing Diagnostic (Paper 2608.25128v1): rho_{forecast_horizon}={diagnostic['rho_h']:.4f} -> Recommendation: {diagnostic['recommendation']}")

    if events_df is not None and not events_df.empty:
        events = events_df.copy()
        events['date'] = pd.to_datetime(events['date'])
        
        merged = pd.merge(df, events[['date'] + llm_feature_cols], on='date', how='left')
        merged[llm_feature_cols] = merged[llm_feature_cols].fillna(0.0)
        
        # Modulate decay half-life dynamically based on context routing diagnostic
        effective_half_life = decay_half_life_days if diagnostic['recommendation'] == 'TRY_FUSION' else decay_half_life_days * 0.20
        decay_factor = np.exp(-np.log(2) / effective_half_life)
        fusion_weight = 1.0 if diagnostic['recommendation'] == 'TRY_FUSION' else 0.10
        
        for col in llm_feature_cols:
            decayed_values = np.zeros(len(merged))
            current_val = 0.0
            for i in range(len(merged)):
                new_shock = merged.loc[i, col] * fusion_weight
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


def compute_context_routing_diagnostic(
    df: pd.DataFrame, 
    target_col: str = 'gasoline_rbob', 
    horizon: int = 5, 
    threshold: float = 0.95
) -> dict:
    """
    Implements the Pre-Training Context Routing Diagnostic from Zhou et al. (arXiv:2608.25128v1).
    Calculates target temporal autocorrelation rho_h = Corr(X_t, X_{t+h}).
    
    If rho_h > threshold (0.95), returns SKIP_FUSION because last-value shortcuts dominate.
    If rho_h <= threshold, returns TRY_FUSION because exogenous context can provide relative gain.
    
    Reference: Zhou et al. (2026), 'When Does Context Routing Help?', arXiv:2608.25128v1
    """
    if target_col not in df.columns or len(df) <= horizon + 1:
        return {'rho_h': 0.0, 'recommendation': 'TRY_FUSION', 'rbu_bound': 1.0}
        
    series = df[target_col].values
    s_t = series[:-horizon]
    s_th = series[horizon:]
    
    corr_matrix = np.corrcoef(s_t, s_th)
    rho_h = float(corr_matrix[0, 1]) if corr_matrix.shape == (2, 2) and not np.isnan(corr_matrix[0, 1]) else 0.0
    
    # RBU Room for Improvement Bound: (1 - rho_h^2)
    rbu_bound = max(0.0, 1.0 - (rho_h ** 2))
    
    recommendation = "SKIP_FUSION" if rho_h > threshold else "TRY_FUSION"
    
    return {
        'rho_h': rho_h,
        'recommendation': recommendation,
        'rbu_bound': rbu_bound,
        'threshold': threshold
    }



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
