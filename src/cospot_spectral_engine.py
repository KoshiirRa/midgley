"""
CoSPOT: Compositional Spectral Prompts & Wavelet Context Engine
Reference: arXiv:2609.02093v1 (KAIST OTSF Framework)

Implements:
1. Discrete Fourier Transform (DFT) Spectral Basis Decomposition (dominant cycles, low-frequency trend power, spectral entropy).
2. Discrete Wavelet Transform (DWT) Localized Detail Decomposition (Level 1/2 micro-noise vs structural shock isolation).
3. Natural Language Spectral Prompt Context Generator for Gemini 2.5 Flash event analysis.
4. Online Linear Projection Head Adapter with Geometric Loss Decay (delta = 0.90).
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


def compute_dft_spectral_features(
    series: Union[np.ndarray, pd.Series, List[float]], 
    lookback: int = 21, 
    low_pass_gamma: float = 0.4
) -> Dict[str, float]:
    """
    Decomposes lookback price/return series into orthogonal Fourier frequency bases.
    
    Parameters:
    - series: Array or Series of historical prices or returns (most recent observation at index -1).
    - lookback: Lookback window length L in trading days (default 21 days ~ 1 trading month).
    - low_pass_gamma: Low-pass frequency cutoff fraction in [0, 1] for trend isolation.
    
    Returns:
    - Dictionary with dominant cycle period, low-frequency energy ratio, spectral entropy, and trend slope.
    """
    arr = np.array(series, dtype=float)
    arr = arr[~np.isnan(arr)]
    
    if len(arr) < 4:
        return {
            "dominant_cycle_period_days": float(lookback),
            "low_freq_energy_ratio": 1.0,
            "spectral_entropy": 0.0,
            "spectral_trend_slope": 0.0,
            "total_spectral_energy": 0.0
        }
        
    window = arr[-lookback:] if len(arr) >= lookback else arr
    L = len(window)
    
    # Detrend window for clean frequency analysis
    t = np.arange(L)
    p = np.polyfit(t, window, 1)
    detrended = window - (p[0] * t + p[1])
    
    # Real-valued Discrete Fourier Transform
    fft_vals = np.fft.rfft(detrended)
    amplitudes = np.abs(fft_vals)
    power = amplitudes ** 2
    
    total_power = np.sum(power)
    if total_power <= 1e-12:
        return {
            "dominant_cycle_period_days": float(L),
            "low_freq_energy_ratio": 1.0,
            "spectral_entropy": 0.0,
            "spectral_trend_slope": float(p[0]),
            "total_spectral_energy": 0.0
        }
        
    norm_power = power / total_power
    num_freqs = len(norm_power)
    
    # Dominant cycle period (ignoring DC component k=0)
    if num_freqs > 1:
        k_dom = int(np.argmax(power[1:])) + 1
        dominant_cycle_period = float(L / k_dom)
    else:
        dominant_cycle_period = float(L)
        
    # Low-pass energy ratio
    cutoff_idx = max(1, int(np.ceil(num_freqs * low_pass_gamma)))
    low_freq_energy = np.sum(norm_power[:cutoff_idx])
    
    # Spectral Entropy (normalized to [0, 1])
    # H = - sum(P_k * ln(P_k)) / ln(K)
    p_safe = norm_power[norm_power > 0]
    entropy_raw = -np.sum(p_safe * np.log(p_safe))
    max_entropy = np.log(num_freqs) if num_freqs > 1 else 1.0
    spectral_entropy = float(np.clip(entropy_raw / max_entropy, 0.0, 1.0))
    
    return {
        "dominant_cycle_period_days": round(dominant_cycle_period, 2),
        "low_freq_energy_ratio": round(float(low_freq_energy), 4),
        "spectral_entropy": round(spectral_entropy, 4),
        "spectral_trend_slope": round(float(p[0]), 5),
        "total_spectral_energy": round(float(total_power), 4)
    }


def compute_dwt_wavelet_features(
    series: Union[np.ndarray, pd.Series, List[float]], 
    level: int = 2
) -> Dict[str, float]:
    """
    Performs 2-level Discrete Wavelet Transform (DWT) decomposition using Haar wavelet filters.
    Isolates micro-frequency noise (D1), localized shock fluctuations (D2), and macro trend (A2).
    
    Parameters:
    - series: Array or Series of historical prices (most recent observation at index -1).
    - level: Multi-resolution decomposition level (default 2).
    
    Returns:
    - Dictionary with wavelet detail-to-approximation ratio, shock magnitude, and approximation momentum.
    """
    arr = np.array(series, dtype=float)
    arr = arr[~np.isnan(arr)]
    
    if len(arr) < 8:
        return {
            "dwt_detail_energy_ratio": 0.0,
            "dwt_detail_shock_mag": 0.0,
            "dwt_approx_momentum": 0.0,
            "dwt_d1_norm": 0.0,
            "dwt_d2_norm": 0.0
        }
        
    # Take latest power-of-2 length window (min 8, max 32)
    win_len = 16 if len(arr) >= 16 else 8
    x = arr[-win_len:]
    
    # Haar Wavelet Step 1: Low-pass (cA1) and High-pass (cD1)
    cA1 = (x[0::2] + x[1::2]) / np.sqrt(2.0)
    cD1 = (x[0::2] - x[1::2]) / np.sqrt(2.0)
    
    # Haar Wavelet Step 2: Low-pass (cA2) and High-pass (cD2)
    cA2 = (cA1[0::2] + cA1[1::2]) / np.sqrt(2.0)
    cD2 = (cA1[0::2] - cA1[1::2]) / np.sqrt(2.0)
    
    d1_energy = np.sum(cD1 ** 2)
    d2_energy = np.sum(cD2 ** 2)
    a2_energy = np.sum(cA2 ** 2)
    
    detail_energy_ratio = float((d1_energy + d2_energy) / (a2_energy + 1e-8))
    
    # Recent localized shock magnitude (latest high-frequency wavelet detail)
    latest_shock = float(abs(cD1[-1]) + abs(cD2[-1])) if len(cD1) > 0 and len(cD2) > 0 else 0.0
    
    # Approximation momentum (trend movement of coarse approximation baseline)
    approx_momentum = float(cA2[-1] - cA2[-2]) if len(cA2) >= 2 else 0.0
    
    return {
        "dwt_detail_energy_ratio": round(detail_energy_ratio, 4),
        "dwt_detail_shock_mag": round(latest_shock, 4),
        "dwt_approx_momentum": round(approx_momentum, 4),
        "dwt_d1_norm": round(float(np.sqrt(d1_energy)), 4),
        "dwt_d2_norm": round(float(np.sqrt(d2_energy)), 4)
    }


def generate_spectral_prompt_context(
    series: Union[np.ndarray, pd.Series, List[float]], 
    lookback: int = 21
) -> str:
    """
    Generates a structured Natural Language Spectral Context block for LLM prompts
    following CoSPOT (arXiv:2609.02093v1) specification.
    """
    dft_metrics = compute_dft_spectral_features(series, lookback=lookback)
    dwt_metrics = compute_dwt_wavelet_features(series)
    
    dom_cycle = dft_metrics["dominant_cycle_period_days"]
    low_freq_pct = dft_metrics["low_freq_energy_ratio"] * 100.0
    entropy = dft_metrics["spectral_entropy"]
    trend_slope = dft_metrics["spectral_trend_slope"]
    shock_mag = dwt_metrics["dwt_detail_shock_mag"]
    detail_ratio = dwt_metrics["dwt_detail_energy_ratio"]
    momentum = dwt_metrics["dwt_approx_momentum"]
    
    # Determine regime description
    if entropy < 0.45:
        regime_desc = "Coherent structural trend (High low-frequency stability)"
    elif entropy > 0.75:
        regime_desc = "Turbulent / Non-stationary regime (High frequency dispersion)"
    else:
        regime_desc = "Balanced cyclical regime"
        
    # Determine wavelet shock state
    if detail_ratio > 0.15 or shock_mag > 0.03:
        shock_desc = f"Elevated localized high-frequency shock detected (Detail-to-Approx ratio: {detail_ratio:.3f}, Shock: ${shock_mag:.3f}/gal)"
    else:
        shock_desc = f"Stable localized micro-structure (Low noise ratio: {detail_ratio:.3f})"
        
    trend_dir = "Bullish" if trend_slope > 0.001 else ("Bearish" if trend_slope < -0.001 else "Neutral")
    
    prompt_block = (
        "[MARKET FREQUENCY & SPECTRAL REGIME (CoSPOT arXiv:2609.02093)]\n"
        f"• Dominant Cycle: {dom_cycle:.1f} days (Low-frequency trend energy: {low_freq_pct:.1f}% | Direction: {trend_dir})\n"
        f"• Spectral Regime: {regime_desc} (Entropy H: {entropy:.2f})\n"
        f"• Wavelet Noise & Shock State: {shock_desc} (Approx Momentum: {momentum:+.4f})\n"
        "• Guidance: Condition qualitative news scoring on whether breaking events reinforce the structural low-frequency momentum or represent transient high-frequency noise."
    )
    return prompt_block


def compute_rolling_spectral_features(
    df: pd.DataFrame, 
    price_col: str = "gasoline_rbob", 
    lookback: int = 21
) -> pd.DataFrame:
    """
    Computes rolling DFT and DWT features across a historical price DataFrame without temporal lookahead.
    """
    df_out = df.copy()
    if price_col not in df_out.columns:
        for c in [
            'cospot_dft_dominant_period', 'cospot_dft_low_freq_energy_ratio', 
            'cospot_dft_spectral_entropy', 'cospot_dwt_detail_energy_ratio', 
            'cospot_dwt_detail_shock_mag', 'cospot_dwt_approx_momentum'
        ]:
            df_out[c] = 0.0
        return df_out
        
    n = len(df_out)
    prices = df_out[price_col].values
    
    dom_periods = np.zeros(n)
    low_freq_ratios = np.zeros(n)
    entropies = np.zeros(n)
    detail_ratios = np.zeros(n)
    shock_mags = np.zeros(n)
    momentums = np.zeros(n)
    
    for i in range(n):
        sub_series = prices[:i+1]
        dft_res = compute_dft_spectral_features(sub_series, lookback=lookback)
        dwt_res = compute_dwt_wavelet_features(sub_series)
        
        dom_periods[i] = dft_res["dominant_cycle_period_days"]
        low_freq_ratios[i] = dft_res["low_freq_energy_ratio"]
        entropies[i] = dft_res["spectral_entropy"]
        detail_ratios[i] = dwt_res["dwt_detail_energy_ratio"]
        shock_mags[i] = dwt_res["dwt_detail_shock_mag"]
        momentums[i] = dwt_res["dwt_approx_momentum"]
        
    df_out['cospot_dft_dominant_period'] = dom_periods
    df_out['cospot_dft_low_freq_energy_ratio'] = low_freq_ratios
    df_out['cospot_dft_spectral_entropy'] = entropies
    df_out['cospot_dwt_detail_energy_ratio'] = detail_ratios
    df_out['cospot_dwt_detail_shock_mag'] = shock_mags
    df_out['cospot_dwt_approx_momentum'] = momentums
    
    return df_out


class CoSPOTOnlineAdapter:
    """
    Ultra-low compute online projection adapter with geometric loss decay (delta = 0.90)
    for rapid online adaptation to non-stationary market regime shifts.
    """
    def __init__(self, delta: float = 0.90, learning_rate: float = 0.01, l2_reg: float = 0.01):
        self.delta = delta
        self.learning_rate = learning_rate
        self.l2_reg = l2_reg
        self.weights: Optional[np.ndarray] = None
        self.bias: float = 0.0
        self.history_errors: List[float] = []

    def fit_online_step(self, x_vec: np.ndarray, y_true: float, y_pred_base: float):
        """
        Updates residual projection weights on a single new observation step
        using geometrically discounted error gradient.
        """
        x = np.array(x_vec, dtype=float).flatten()
        if self.weights is None:
            self.weights = np.zeros(len(x))
            
        residual = y_true - (y_pred_base + float(np.dot(self.weights, x)) + self.bias)
        self.history_errors.append(residual)
        
        # Gradient descent step with geometric loss decay weighting
        grad_w = -residual * x + self.l2_reg * self.weights
        grad_b = -residual
        
        self.weights -= self.learning_rate * grad_w
        self.bias -= self.learning_rate * grad_b
        
        # Apply geometric decay to projection head weights
        self.weights *= self.delta
        self.bias *= self.delta

    def predict_residual(self, x_vec: np.ndarray) -> float:
        """
        Predicts online residual adjustment for a feature vector.
        """
        if self.weights is None:
            return 0.0
        x = np.array(x_vec, dtype=float).flatten()
        if len(x) != len(self.weights):
            return 0.0
        return float(np.dot(self.weights, x) + self.bias)
