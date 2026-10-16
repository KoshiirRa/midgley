"""
Edgeworth Price Cycle Diagnostics & Restoration-Hazard Model (src/edgeworth_cycle.py)
Issue #447: Microstructure modeling for Midwestern retail cycling markets (Cincinnati OH/KY).

Provides:
1. Cycle detection and asymmetry diagnostics (negative change fraction, skewness, run lengths).
2. Markov-switching / threshold-based cycle classification (cycling vs non-cycling).
3. Restoration hazard model estimating probability of coordinated price spike P_{t,h}.
4. State-dependent expected horizon price change:
   E[r_{t+h} - r_t] = P_{t,h} * J + (1 - P_{t,h}) * delta * h
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats, optimize

logger = logging.getLogger("midgley.edgeworth_cycle")


class EdgeworthCycleAnalyzer:
    """
    Diagnostic toolkit for detecting asymmetric retail gasoline Edgeworth price cycles.
    Characterized by fast, sharp coordinated price jumps ('restorations') followed by
    prolonged daily price undercutting.
    """

    def __init__(self, jump_threshold_cpg: float = 0.08):
        self.jump_threshold = jump_threshold_cpg  # $0.08/gal minimum for restoration jump

    def compute_cycle_diagnostics(self, price_series: Union[pd.Series, np.ndarray, List[float]]) -> Dict[str, Any]:
        """
        Computes microstructure asymmetry metrics on daily retail price changes.
        """
        p = pd.Series(price_series).dropna().astype(float)
        if len(p) < 10:
            return {
                "is_cycling": False,
                "fraction_negative_changes": 0.5,
                "change_skewness": 0.0,
                "median_daily_decrease": 0.0,
                "mean_undercut_run_length": 1.0,
                "total_restorations_detected": 0,
                "confidence_score": 0.0
            }

        dp = p.diff().dropna()
        n_changes = len(dp)
        if n_changes == 0:
            return {"is_cycling": False, "confidence_score": 0.0}

        # Fraction of negative daily price movements
        n_negative = int((dp < -0.001).sum())
        frac_neg = n_negative / n_changes

        # Skewness of price changes (cycling markets exhibit strong positive skewness)
        skewness = float(stats.skew(dp)) if len(dp) > 2 else 0.0

        # Median daily decrease during undercutting phase
        decreases = dp[dp < -0.001]
        median_decrease = float(decreases.median()) if len(decreases) > 0 else -0.015

        # Detect restoration jumps (dp >= jump_threshold)
        jumps = dp[dp >= self.jump_threshold]
        n_jumps = len(jumps)
        mean_jump_size = float(jumps.mean()) if n_jumps > 0 else 0.25

        # Compute consecutive run lengths of daily undercutting
        undercut_runs = []
        current_run = 0
        for val in dp:
            if val < 0.005:  # flat or declining
                current_run += 1
            else:
                if current_run > 0:
                    undercut_runs.append(current_run)
                current_run = 0
        if current_run > 0:
            undercut_runs.append(current_run)

        mean_run_length = float(np.mean(undercut_runs)) if undercut_runs else 1.0

        # Classification heuristics for Edgeworth cycling market (Issue #447, #612):
        # 1. fraction_negative >= 0.60 (undercutting phase dominates daily time)
        # 2. skewness >= 0.80 (asymmetric sharp positive spikes)
        # 3. mean_run_length >= 2.0 (prolonged undercutting runs)
        # 4. total_restorations_detected >= 2 with discrete jumps (minimum requirement)
        cycling_score = 0.0
        if frac_neg >= 0.60:
            cycling_score += 0.30
        if frac_neg >= 0.70:
            cycling_score += 0.10
        if skewness >= 0.8:
            cycling_score += 0.20
        if skewness >= 1.5:
            cycling_score += 0.15
        if mean_run_length >= 2.5:
            cycling_score += 0.15
        if n_jumps >= 2:
            cycling_score += 0.10

        # Strict requirement: Must exhibit authentic asymmetry, undercutting persistence, AND discrete jumps
        is_cycling = bool(
            cycling_score >= 0.60
            and frac_neg >= 0.60
            and skewness >= 0.80
            and n_jumps >= 2
            and mean_run_length >= 2.0
        )

        return {
            "is_cycling": is_cycling,
            "cycling_confidence": round(cycling_score, 3),
            "fraction_negative_changes": round(frac_neg, 3),
            "change_skewness": round(skewness, 3),
            "median_daily_decrease": round(median_decrease, 4),
            "mean_undercut_run_length": round(mean_run_length, 2),
            "total_restorations_detected": int(n_jumps),
            "mean_restoration_jump_size": round(mean_jump_size, 3)
        }


class RestorationHazardModel:
    """
    Restoration Hazard Model for retail cycling markets.
    Estimates P_{t,h} = Pr(restoration in (t, t+h] | m_t, d_t) = logit^{-1}(a + b*m_t + c*d_t)
    where:
      m_t = retail - wholesale margin ($/gal)
      d_t = days elapsed since previous price restoration
    and computes expected horizon price innovation:
      E[r_{t+h} - r_t] = P_{t,h} * J + (1 - P_{t,h}) * delta * h
    """

    def __init__(
        self,
        a: float = -1.8,
        b: float = -4.5,
        c: float = 0.28,
        mean_jump_size: float = 0.32,
        daily_undercut_rate: float = -0.025
    ):
        self.a = a  # Baseline log-odds intercept
        self.b = b  # Margin sensitivity (negative: compressed margin increases restoration hazard)
        self.c = c  # Duration sensitivity (positive: longer time since spike increases hazard)
        self.mean_jump_size = mean_jump_size
        self.daily_undercut_rate = daily_undercut_rate
        self.is_calibrated: bool = False

    def fit(
        self,
        retail_prices: Union[pd.Series, np.ndarray, List[float]],
        wholesale_prices: Union[pd.Series, np.ndarray, List[float]],
        jump_threshold: float = 0.08
    ) -> "RestorationHazardModel":
        """
        Calibrates logistic hazard coefficients (a, b, c) and jump parameters (J, delta)
        from historical paired retail-wholesale time series.
        """
        r = pd.Series(retail_prices).dropna().astype(float)
        w = pd.Series(wholesale_prices).dropna().astype(float)

        min_len = min(len(r), len(w))
        if min_len < 20:
            logger.warning("Insufficient observations for restoration hazard fit; using domain priors.")
            self.is_calibrated = True
            return self

        r = r.iloc[-min_len:].reset_index(drop=True)
        w = w.iloc[-min_len:].reset_index(drop=True)

        margins = r - w
        dr = r.diff()

        # Identify jump events (restorations)
        is_jump = (dr >= jump_threshold).astype(int)

        # Calculate elapsed days since last jump
        elapsed_days = []
        d_count = 5  # default initial elapsed days
        for j_flag in is_jump:
            if j_flag == 1:
                d_count = 0
            else:
                d_count += 1
            elapsed_days.append(d_count)

        df_fit = pd.DataFrame({
            "y": is_jump.shift(-1),  # Next day jump
            "margin": margins,
            "elapsed": elapsed_days
        }).dropna()

        # Jump size and undercutting rate
        jump_mask = dr >= jump_threshold
        undercut_mask = dr < -0.002

        if jump_mask.sum() > 0:
            self.mean_jump_size = float(dr[jump_mask].mean())
        if undercut_mask.sum() > 0:
            self.daily_undercut_rate = float(dr[undercut_mask].mean())

        # Fit logistic regression parameters via regularized MLE (Issue #612)
        if df_fit["y"].sum() >= 2:
            try:
                m_mean = float(df_fit["margin"].mean())
                m_std = float(max(df_fit["margin"].std(), 0.05))
                e_mean = float(df_fit["elapsed"].mean())
                e_std = float(max(df_fit["elapsed"].std(), 1.0))

                m_scaled = (df_fit["margin"].values - m_mean) / m_std
                e_scaled = (df_fit["elapsed"].values - e_mean) / e_std
                X_scaled = np.column_stack([np.ones(len(df_fit)), m_scaled, e_scaled])
                y = df_fit["y"].values

                def neg_log_lik(params):
                    z = np.dot(X_scaled, params)
                    z = np.clip(z, -20.0, 20.0)
                    prob = 1.0 / (1.0 + np.exp(-z))
                    prob = np.clip(prob, 1e-6, 1.0 - 1e-6)
                    ll = np.sum(y * np.log(prob) + (1.0 - y) * np.log(1.0 - prob))
                    l2_pen = 0.5 * 0.1 * (params[1] ** 2 + params[2] ** 2)
                    return -ll + l2_pen

                # Box bounds: b_scaled <= 0 (margin compression raises hazard), c_scaled >= 0 (longer time raises hazard)
                bounds = [(-10.0, 5.0), (-10.0, 0.0), (0.0, 10.0)]
                res = optimize.minimize(
                    neg_log_lik,
                    [-1.8, -0.5, 0.5],
                    method="L-BFGS-B",
                    bounds=bounds,
                    options={"maxiter": 200}
                )
                if res.success and np.isfinite(res.fun):
                    a_s, b_s, c_s = res.x
                    self.b = float(b_s / m_std)
                    self.c = float(c_s / e_std)
                    self.a = float(a_s - self.b * m_mean - self.c * e_mean)
            except Exception as e:
                logger.debug(f"Hazard model optimization error: {e}; applying priors.")

        self.is_calibrated = True
        return self

    def compute_restoration_probability(self, current_margin: float, elapsed_days: int, horizon_days: int = 5) -> float:
        """
        Calculates P_{t,h}, the cumulative probability of at least one price restoration spike
        occurring within the next h business days.
        """
        # Daily hazard rate at t+1: lambda_1 = logit^{-1}(a + b*m + c*d)
        # For multi-step horizon, accumulate hazard as margin continues to decay if no spike occurs
        prob_no_spike = 1.0
        m_sim = current_margin
        d_sim = elapsed_days

        for _ in range(horizon_days):
            z = self.a + self.b * m_sim + self.c * d_sim
            z = max(min(z, 20.0), -20.0)
            daily_hazard = 1.0 / (1.0 + math.exp(-z))
            prob_no_spike *= (1.0 - daily_hazard)

            # Advance state under no-spike trajectory
            m_sim += self.daily_undercut_rate
            d_sim += 1

        cumulative_prob = 1.0 - prob_no_spike
        return max(min(cumulative_prob, 0.999), 0.001)

    def forecast_expected_horizon_change(
        self,
        current_retail: float,
        current_wholesale: float,
        elapsed_days: int = 4,
        horizon_days: int = 5
    ) -> Dict[str, Any]:
        """
        Forecasts expected retail price change and multi-day price path under Edgeworth cycle dynamics.
        """
        current_margin = current_retail - current_wholesale
        p_spike = self.compute_restoration_probability(current_margin, elapsed_days, horizon_days)

        # Expected retail price delta: E[Delta r] = P_{t,h} * J + (1 - P_{t,h}) * delta * h
        expected_jump_contrib = p_spike * self.mean_jump_size
        expected_undercut_contrib = (1.0 - p_spike) * self.daily_undercut_rate * horizon_days
        expected_delta = expected_jump_contrib + expected_undercut_contrib
        predicted_retail = max(round(current_retail + expected_delta, 3), 1.50)

        # Generate day-by-day expected trajectory
        trajectory = []
        for h in range(1, horizon_days + 1):
            p_h = self.compute_restoration_probability(current_margin, elapsed_days, h)
            h_delta = p_h * self.mean_jump_size + (1.0 - p_h) * self.daily_undercut_rate * h
            h_price = max(round(current_retail + h_delta, 3), 1.50)
            trajectory.append({
                "horizon_days": h,
                "spike_probability": round(p_h, 3),
                "predicted_retail": h_price,
                "expected_delta": round(h_delta, 3)
            })

        return {
            "current_retail": current_retail,
            "current_wholesale": current_wholesale,
            "current_margin": round(current_margin, 3),
            "elapsed_days_since_restoration": elapsed_days,
            "restoration_spike_probability_5d": round(p_spike, 3),
            "mean_restoration_jump_size": round(self.mean_jump_size, 3),
            "daily_undercutting_rate": round(self.daily_undercut_rate, 4),
            "expected_5d_delta": round(expected_delta, 3),
            "predicted_5d_retail": predicted_retail,
            "trajectory": trajectory
        }
