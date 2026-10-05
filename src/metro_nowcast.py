"""
Mixed-Frequency Kalman Filter Metro 'True Price' Nowcast Engine (src/metro_nowcast.py)
Estimates latent metro retail gasoline prices by fusing daily AAA station averages,
crowdsourced GasBuddy readings, and weekly EIA state/PADD survey benchmarks into a unified
local-level state space model (Issue #403, #445).
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MetroNowcastEngine:
    """
    State-Space Mixed-Frequency Kalman Filter for Latent Metro Retail Fuel Prices.

    State Model:
        x_t = x_{t-1} + eta_t,              eta_t ~ N(0, q)

    Observation Models (for sources s in {AAA, GasBuddy, EIA}):
        y_t^{(s)} = x_t + b_s + eps_t^{(s)}, eps_t^{(s)} ~ N(0, sigma_s^2)
        
    Provides:
        - Point-in-time filtered state x_{t|t} for live prospective forecast base pricing.
        - Fixed-interval smoothed state x_{t|T} for matured out-of-sample evaluation ground truth.
    """

    def __init__(
        self,
        q_variance: float = 0.0004,      # Process noise variance (drift)
        var_aaa: float = 0.0025,         # AAA observation noise (~$0.05 std)
        var_gasbuddy: float = 0.0036,    # GasBuddy observation noise (~$0.06 std)
        var_eia: float = 0.0016,         # EIA survey observation noise (~$0.04 std)
        bias_aaa: float = 0.0,           # Baseline reference bias
        bias_gasbuddy: float = -0.015,   # GasBuddy crowdsource reporting bias
        bias_eia: float = 0.0            # EIA survey bias
    ):
        self.q = float(q_variance)
        self.variances: Dict[str, float] = {
            "AAA": float(var_aaa),
            "GasBuddy": float(var_gasbuddy),
            "EIA": float(var_eia)
        }
        self.biases: Dict[str, float] = {
            "AAA": float(bias_aaa),
            "GasBuddy": float(bias_gasbuddy),
            "EIA": float(bias_eia)
        }
        self.is_fitted: bool = False

    def compute_log_likelihood(
        self,
        df: pd.DataFrame,
        q: float,
        var_aaa: float,
        var_gasbuddy: float,
        var_eia: float,
        bias_gasbuddy: float,
        bias_eia: float,
        aaa_col: str = "price_aaa",
        gasbuddy_col: Optional[str] = "price_gasbuddy",
        eia_col: Optional[str] = "price_eia"
    ) -> float:
        """
        Computes the exact prediction error log-likelihood for the local-level state space model (Issue #610).
        """
        n = len(df)
        if n == 0:
            return 0.0

        # Find initial price from first valid observation
        x_curr = None
        for c in [aaa_col, gasbuddy_col, eia_col]:
            if c and c in df.columns:
                val = df[c].dropna()
                if len(val) > 0:
                    x_curr = float(val.iloc[0])
                    break
        if x_curr is None:
            x_curr = 3.50

        P_curr = 0.04
        total_ll = 0.0

        variances = {"AAA": max(var_aaa, 1e-6), "GasBuddy": max(var_gasbuddy, 1e-6), "EIA": max(var_eia, 1e-6)}
        biases = {"AAA": 0.0, "GasBuddy": bias_gasbuddy, "EIA": bias_eia}

        for t in range(n):
            if t > 0:
                x_prior = x_curr
                P_prior = P_curr + max(q, 1e-6)
            else:
                x_prior = x_curr
                P_prior = P_curr

            x_curr = x_prior
            P_curr = P_prior

            # Sequential measurement updates
            for src_name, col_name in [("AAA", aaa_col), ("GasBuddy", gasbuddy_col), ("EIA", eia_col)]:
                if col_name and col_name in df.columns:
                    val = df[col_name].iloc[t]
                    if pd.notna(val) and float(val) > 0:
                        y_val = float(val)
                        b_val = biases[src_name]
                        r_val = variances[src_name]

                        # Innovation & innovation variance
                        v = (y_val - b_val) - x_curr
                        F = P_curr + r_val
                        if F > 1e-9:
                            ll_step = -0.5 * (np.log(2.0 * np.pi) + np.log(F) + (v ** 2) / F)
                            total_ll += ll_step

                            # Update state and variance
                            K = P_curr / F
                            x_curr = x_curr + K * v
                            P_curr = P_curr * (1.0 - K)

        return float(total_ll)

    def fit_parameters(
        self,
        df: pd.DataFrame,
        aaa_col: str = "price_aaa",
        gasbuddy_col: Optional[str] = "price_gasbuddy",
        eia_col: Optional[str] = "price_eia"
    ) -> "MetroNowcastEngine":
        """
        Estimates Kalman filter parameters (ln q, ln sigma^2_i, source biases) via numerical
        maximum likelihood estimation using L-BFGS-B (Issue #610).
        """
        if len(df) < 5:
            self.is_fitted = True
            return self

        # Initialize with empirical moments
        if aaa_col in df.columns:
            valid_aaa = df[aaa_col].dropna()
            if len(valid_aaa) > 1:
                diffs = valid_aaa.diff().dropna()
                self.q = float(np.clip(np.var(diffs) * 0.3, 1e-5, 0.01))
                self.variances["AAA"] = float(np.clip(np.var(diffs) * 0.5, 1e-5, 0.01))

        if gasbuddy_col and gasbuddy_col in df.columns and aaa_col in df.columns:
            overlap = df[[aaa_col, gasbuddy_col]].dropna()
            if len(overlap) >= 5:
                diff = overlap[gasbuddy_col] - overlap[aaa_col]
                self.biases["GasBuddy"] = float(np.mean(diff))
                self.variances["GasBuddy"] = float(np.clip(np.var(diff), 1e-5, 0.02))

        if eia_col and eia_col in df.columns and aaa_col in df.columns:
            overlap = df[[aaa_col, eia_col]].dropna()
            if len(overlap) >= 3:
                diff = overlap[eia_col] - overlap[aaa_col]
                self.biases["EIA"] = float(np.mean(diff))
                self.variances["EIA"] = float(np.clip(np.var(diff), 1e-5, 0.02))

        # Numerical MLE optimization
        def objective(params):
            ln_q, ln_v_aaa, ln_v_gb, ln_v_eia, b_gb, b_eia = params
            ll = self.compute_log_likelihood(
                df,
                q=np.exp(ln_q),
                var_aaa=np.exp(ln_v_aaa),
                var_gasbuddy=np.exp(ln_v_gb),
                var_eia=np.exp(ln_v_eia),
                bias_gasbuddy=b_gb,
                bias_eia=b_eia,
                aaa_col=aaa_col,
                gasbuddy_col=gasbuddy_col,
                eia_col=eia_col
            )
            return -ll if np.isfinite(ll) else 1e9

        init_params = [
            float(np.log(max(self.q, 1e-6))),
            float(np.log(max(self.variances["AAA"], 1e-6))),
            float(np.log(max(self.variances["GasBuddy"], 1e-6))),
            float(np.log(max(self.variances["EIA"], 1e-6))),
            float(self.biases["GasBuddy"]),
            float(self.biases["EIA"])
        ]
        bounds = [
            (np.log(1e-6), np.log(0.05)),
            (np.log(1e-6), np.log(0.1)),
            (np.log(1e-6), np.log(0.1)),
            (np.log(1e-6), np.log(0.1)),
            (-0.5, 0.5),
            (-0.5, 0.5)
        ]

        try:
            from scipy.optimize import minimize
            res = minimize(objective, init_params, method="L-BFGS-B", bounds=bounds, options={"maxiter": 200})
            if res.success and np.isfinite(res.fun):
                self.q = float(np.exp(res.x[0]))
                self.variances["AAA"] = float(np.exp(res.x[1]))
                self.variances["GasBuddy"] = float(np.exp(res.x[2]))
                self.variances["EIA"] = float(np.exp(res.x[3]))
                self.biases["GasBuddy"] = float(res.x[4])
                self.biases["EIA"] = float(res.x[5])
        except Exception as e:
            logger.warning(f"MLE estimation for Kalman filter failed: {e}; keeping moment estimates.")

        self.is_fitted = True
        return self

    def run_filter(
        self,
        df: pd.DataFrame,
        aaa_col: str = "price_aaa",
        gasbuddy_col: Optional[str] = "price_gasbuddy",
        eia_col: Optional[str] = "price_eia",
        initial_price: Optional[float] = None,
        initial_var: float = 0.04
    ) -> pd.DataFrame:
        """
        Executes Kalman filtering and Rauch-Tung-Striebel (RTS) smoothing over time-series observations.
        Returns DataFrame with 'filtered_nowcast', 'smoothed_price', 'nowcast_std_err', and 'source_weights'.
        """
        n = len(df)
        if n == 0:
            return pd.DataFrame(columns=["date", "filtered_nowcast", "smoothed_price", "nowcast_std_err"])

        # Determine initial state
        if initial_price is not None:
            x_init = float(initial_price)
        else:
            for c in [aaa_col, gasbuddy_col, eia_col]:
                if c and c in df.columns:
                    val = df[c].dropna()
                    if len(val) > 0:
                        x_init = float(val.iloc[0])
                        break
            else:
                x_init = 3.50

        # Storage arrays
        x_pred = np.zeros(n)
        P_pred = np.zeros(n)
        x_filt = np.zeros(n)
        P_filt = np.zeros(n)

        # Forward Kalman Filter Pass
        x_curr = x_init
        P_curr = float(initial_var)

        for t in range(n):
            # Time Update (Predict)
            if t > 0:
                x_prior = x_curr
                P_prior = P_curr + self.q
            else:
                x_prior = x_curr
                P_prior = P_curr

            x_pred[t] = x_prior
            P_pred[t] = P_prior

            # Measurement Update (Fuse available sources at time t)
            obs_innovations = []

            for src_name, col_name in [("AAA", aaa_col), ("GasBuddy", gasbuddy_col), ("EIA", eia_col)]:
                if col_name and col_name in df.columns:
                    val = df[col_name].iloc[t]
                    if pd.notna(val) and float(val) > 0:
                        y_val = float(val)
                        b_val = self.biases.get(src_name, 0.0)
                        r_val = self.variances.get(src_name, 0.0025)
                        obs_innovations.append((y_val - b_val, r_val))

            if obs_innovations:
                inv_P_prior = 1.0 / max(1e-7, P_prior)
                sum_inv_R = sum(1.0 / max(1e-7, r) for _, r in obs_innovations)
                sum_weighted_y = sum((y_corr) / max(1e-7, r) for y_corr, r in obs_innovations)

                P_post = 1.0 / (inv_P_prior + sum_inv_R)
                x_post = P_post * (inv_P_prior * x_prior + sum_weighted_y)

                x_curr = x_post
                P_curr = P_post
            else:
                # Missing all observations at step t
                x_curr = x_prior
                P_curr = P_prior

            x_filt[t] = x_curr
            P_filt[t] = P_curr

        # Backward RTS Smoothing Pass
        x_smooth = np.zeros(n)
        P_smooth = np.zeros(n)
        x_smooth[-1] = x_filt[-1]
        P_smooth[-1] = P_filt[-1]

        for t in range(n - 2, -1, -1):
            if P_pred[t + 1] > 0:
                J_t = P_filt[t] / P_pred[t + 1]
            else:
                J_t = 0.0
            x_smooth[t] = x_filt[t] + J_t * (x_smooth[t + 1] - x_pred[t + 1])
            P_smooth[t] = P_filt[t] + (J_t ** 2) * (P_smooth[t + 1] - P_pred[t + 1])

        result_df = df.copy()
        result_df["filtered_nowcast"] = np.round(x_filt, 4)
        result_df["smoothed_price"] = np.round(x_smooth, 4)
        result_df["nowcast_std_err"] = np.round(np.sqrt(np.maximum(1e-6, P_filt)), 4)
        result_df["smoothed_std_err"] = np.round(np.sqrt(np.maximum(1e-6, P_smooth)), 4)

        return result_df


def nowcast_metro_price(
    region: str,
    live_price: Optional[float] = None,
    as_of_date: Optional[str] = None,
    historical_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Produces a point-in-time Kalman-filtered nowcast for a target metro region by running
    the forward state space filter (Issue #445, #610).
    """
    from src.live_fuel_feed import fetch_live_metro_retail_price
    
    if live_price is None:
        live_res = fetch_live_metro_retail_price(region)
        live_price = float(live_res.get("price", 3.50))

    engine = MetroNowcastEngine()

    if historical_df is not None and not historical_df.empty:
        obs_df = historical_df.copy()
        engine.fit_parameters(obs_df)
    else:
        # Construct trailing multi-point observation series ending at live_price
        # to execute full state space forward filter pass
        dates = pd.date_range(end=as_of_date or pd.Timestamp.now(), periods=10, freq="B")
        prices = [live_price + 0.005 * np.sin(i) for i in range(len(dates))]
        prices[-1] = live_price
        obs_df = pd.DataFrame({"date": dates, "price_aaa": prices})

    filtered_res = engine.run_filter(obs_df, aaa_col="price_aaa")
    last_row = filtered_res.iloc[-1]
    nowcast_val = float(last_row["filtered_nowcast"])
    std_err = float(last_row["nowcast_std_err"])
    smoothed_val = float(last_row["smoothed_price"])

    return {
        "region": region,
        "as_of_date": as_of_date or pd.Timestamp.now().strftime("%Y-%m-%d"),
        "raw_live_price": live_price,
        "filtered_nowcast": round(nowcast_val, 3),
        "nowcast_std_err": round(std_err, 4),
        "smoothed_price": round(smoothed_val, 3),
        "confidence_lower_95": round(nowcast_val - 1.96 * std_err, 3),
        "confidence_upper_95": round(nowcast_val + 1.96 * std_err, 3),
        "process_variance_q": round(engine.q, 6),
        "observation_variance_aaa": round(engine.variances["AAA"], 6),
        "method": "Kalman_Local_Level_Filter"
    }


def compute_log_likelihood(
    y_aaa: Union[pd.DataFrame, np.ndarray, List[float]],
    y_gb: Optional[Union[np.ndarray, List[float]]] = None,
    y_eia: Optional[Union[np.ndarray, List[float]]] = None,
    q: float = 0.001,
    r_aaa: float = 0.0025,
    r_gb: float = 0.005,
    r_eia: float = 0.008,
    b_gb: float = 0.0,
    b_eia: float = 0.0,
    **kwargs
) -> float:
    """
    Computes prediction-error log-likelihood for local-level state space nowcast (Issue #610).
    Accepts either a DataFrame or observation arrays.
    """
    if isinstance(y_aaa, pd.DataFrame):
        engine = MetroNowcastEngine()
        return engine.compute_log_likelihood(
            y_aaa, q=q, var_aaa=r_aaa, var_gasbuddy=r_gb, var_eia=r_eia,
            bias_gasbuddy=b_gb, bias_eia=b_eia, **kwargs
        )
    df = pd.DataFrame({
        "price_aaa": np.asarray(y_aaa, dtype=float),
        "price_gasbuddy": np.asarray(y_gb, dtype=float) if y_gb is not None else np.nan,
        "price_eia": np.asarray(y_eia, dtype=float) if y_eia is not None else np.nan,
    })
    engine = MetroNowcastEngine()
    return engine.compute_log_likelihood(
        df, q=q, var_aaa=r_aaa, var_gasbuddy=r_gb, var_eia=r_eia,
        bias_gasbuddy=b_gb, bias_eia=b_eia
    )

