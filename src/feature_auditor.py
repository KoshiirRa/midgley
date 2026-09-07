"""
Feature Leakage & Factor Decay Auditor Module (Issue #146)
Inspired by quantitative research validation principles and Lacuna audit methodology.

Provides:
1. PointInTimeLeakageAuditor: Detects subtle lookahead bias and release lag distortion.
2. FactorDecayAuditor: Evaluates Spearman Rank IC across multi-day forward horizons (1D-20D)
   and estimates empirical exponential half-life (t1/2) vs. configured priors.
3. BacktestOverfittingAuditor: Computes Combinatorial Symmetric Cross-Validation (CSCV)
   Probability of Backtest Overfitting (PBO) and Deflated Sharpe Ratios (DSR).
4. FeatureAuditor: Unified engine generating reproducible audit reports and JSON/Markdown ledgers.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr, norm
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

logger = logging.getLogger(__name__)

# Optional upstream Lacuna adapter
try:
    import lacuna as lc
    HAS_LACUNA = True
except ImportError:
    HAS_LACUNA = False


class PointInTimeLeakageAuditor:
    """
    Audits individual features for temporal lookahead leakage and improper time-shift alignment.
    """

    @staticmethod
    def audit_feature_lead_lag(
        feature_series: pd.Series,
        price_returns: pd.Series,
        max_lags: int = 5,
        threshold_lead_corr: float = 0.35
    ) -> Dict[str, Any]:
        """
        Computes lead-lag cross-correlation between feature at time t and returns at time t + k.
        A feature should NOT have high correlation with *past* returns that disappear in future,
        nor should it exhibit unphysical instantaneous lead correlations prior to publication.

        lead_corrs (k > 0): Correlation between feature_t and returns_{t-k} (past returns).
        lag_corrs (k > 0): Correlation between feature_t and returns_{t+k} (predictive returns).
        contemporaneous (k = 0): Correlation between feature_t and returns_t.
        """
        valid_mask = ~(feature_series.isna() | price_returns.isna() | np.isinf(feature_series) | np.isinf(price_returns))
        f_clean = feature_series[valid_mask]
        r_clean = price_returns[valid_mask]

        if len(f_clean) < 20:
            return {
                "status": "UNKNOWN",
                "reason": "Insufficient samples for lead-lag audit (<20 points)",
                "lead_correlations": {},
                "lag_correlations": {},
                "contemporaneous_corr": 0.0,
                "leakage_detected": False
            }

        lag_corrs = {}
        lead_corrs = {}

        # Contemporaneous
        contemp_corr, _ = pearsonr(f_clean, r_clean)
        if np.isnan(contemp_corr):
            contemp_corr = 0.0

        # Predictive horizons (feature_t predicts returns_{t+k})
        for k in range(1, max_lags + 1):
            f_lag = f_clean.iloc[:-k]
            r_fwd = r_clean.iloc[k:]
            if len(f_lag) >= 15:
                corr, _ = pearsonr(f_lag, r_fwd)
                lag_corrs[f"+{k}d"] = round(float(corr) if not np.isnan(corr) else 0.0, 4)

        # Lookahead check: does feature_t correlate suspiciously with returns_{t-k} (past) in an unlagged raw series?
        for k in range(1, max_lags + 1):
            f_fwd = f_clean.iloc[k:]
            r_past = r_clean.iloc[:-k]
            if len(f_fwd) >= 15:
                corr, _ = pearsonr(f_fwd, r_past)
                lead_corrs[f"-{k}d"] = round(float(corr) if not np.isnan(corr) else 0.0, 4)

        # Detect leakage:
        # 1. Unphysical future lookahead: correlation with future returns exceeds realistic bounds (>0.50)
        # 2. Inverted lead leak: feature correlates strongly with past returns (>threshold_lead_corr)
        max_lead = max([abs(v) for v in lead_corrs.values()]) if lead_corrs else 0.0
        max_lag = max([abs(v) for v in lag_corrs.values()]) if lag_corrs else 0.0

        leakage_detected = False
        status = "PASS"
        reason = "Clean point-in-time temporal structure."

        if max_lag > 0.50:
            status = "WARN"
            reason = f"Unphysically high forward predictive correlation ({max_lag:.4f}). High probability of target or lookahead leakage."
            leakage_detected = True
        elif max_lead > threshold_lead_corr and max_lead > (max_lag * 1.5):
            status = "WARN"
            reason = f"Suspiciously high backward lead correlation ({max_lead:.4f} vs fwd {max_lag:.4f}). Potential lookahead or inverted shift."
            leakage_detected = True

        return {
            "status": status,
            "reason": reason,
            "contemporaneous_corr": round(float(contemp_corr), 4),
            "lead_correlations": lead_corrs,
            "lag_correlations": lag_corrs,
            "max_lead_corr": round(float(max_lead), 4),
            "max_lag_corr": round(float(max_lag), 4),
            "leakage_detected": leakage_detected
        }


class FactorDecayAuditor:
    """
    Audits Information Coefficient (IC) and empirical decay half-life across multiple forward horizons.
    """

    @staticmethod
    def compute_horizon_returns(price_series: pd.Series, horizon: int) -> pd.Series:
        """
        Computes forward percentage return: R_{t, t+H} = (P_{t+H} - P_t) / P_t
        """
        return price_series.pct_change(periods=horizon).shift(-horizon)

    @classmethod
    def evaluate_factor_ic_decay(
        cls,
        factor_name: str,
        factor_series: pd.Series,
        price_series: pd.Series,
        horizons: Optional[List[int]] = None,
        nominal_half_life: float = 4.5
    ) -> Dict[str, Any]:
        """
        Computes Pearson and Spearman Rank IC across forward horizons H,
        fits empirical half-life t_{1/2} = -ln(2) / lambda, and compares to nominal prior.
        """
        if horizons is None:
            horizons = [1, 3, 5, 10, 14, 20]

        horizon_ics = {}
        horizon_rank_ics = {}
        h_valid = []
        ic_abs_vals = []

        for h in horizons:
            fwd_ret = cls.compute_horizon_returns(price_series, h)
            valid_mask = ~(factor_series.isna() | fwd_ret.isna() | np.isinf(factor_series) | np.isinf(fwd_ret))
            f_clean = factor_series[valid_mask]
            r_clean = fwd_ret[valid_mask]

            if len(f_clean) < 15:
                continue

            # Pearson IC
            p_ic, _ = pearsonr(f_clean, r_clean)
            p_ic = float(p_ic) if not np.isnan(p_ic) else 0.0

            # Spearman Rank IC
            s_ic, _ = spearmanr(f_clean, r_clean)
            s_ic = float(s_ic) if not np.isnan(s_ic) else 0.0

            horizon_ics[f"{h}D"] = round(p_ic, 4)
            horizon_rank_ics[f"{h}D"] = round(s_ic, 4)
            h_valid.append(h)
            ic_abs_vals.append(max(0.001, abs(s_ic)))

        # Fit exponential decay: IC(h) = IC_0 * exp(-lambda * h) => ln(IC) = ln(IC_0) - lambda * h
        empirical_half_life = nominal_half_life
        decay_fit_r2 = 0.0
        decay_rate_lambda = 0.0

        if len(h_valid) >= 3 and len(set(ic_abs_vals)) > 1:
            try:
                x = np.array(h_valid, dtype=float)
                y = np.log(np.array(ic_abs_vals, dtype=float))
                coeffs = np.polyfit(x, y, 1)
                slope = coeffs[0]
                if slope < 0:
                    decay_rate_lambda = -slope
                    empirical_half_life = float(np.log(2.0) / decay_rate_lambda)
                    empirical_half_life = min(30.0, max(0.5, empirical_half_life))
                else:
                    empirical_half_life = 30.0
                    decay_rate_lambda = 0.0

                y_pred = coeffs[0] * x + coeffs[1]
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                ss_res = np.sum((y - y_pred) ** 2)
                decay_fit_r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
            except Exception as e:
                logger.debug(f"Exponential fit failed for {factor_name}: {e}")

        # Half-life evaluation
        half_life_delta = empirical_half_life - nominal_half_life
        status = "PASS"
        reason = f"Empirical half-life t1/2={empirical_half_life:.1f}d aligns with nominal prior ({nominal_half_life:.1f}d)."

        if abs(half_life_delta) > 5.0 and decay_fit_r2 > 0.4:
            status = "WARN"
            reason = f"Substantial decay divergence: empirical t1/2={empirical_half_life:.1f}d vs prior {nominal_half_life:.1f}d (R2={decay_fit_r2:.2f})."

        return {
            "factor_name": factor_name,
            "status": status,
            "reason": reason,
            "horizon_pearson_ic": horizon_ics,
            "horizon_rank_ic": horizon_rank_ics,
            "nominal_half_life_days": round(nominal_half_life, 2),
            "empirical_half_life_days": round(empirical_half_life, 2),
            "half_life_delta_days": round(half_life_delta, 2),
            "decay_rate_lambda": round(float(decay_rate_lambda), 4),
            "decay_fit_r2": round(float(max(0.0, decay_fit_r2)), 3)
        }


class BacktestOverfittingAuditor:
    """
    Computes Probability of Backtest Overfitting (PBO) via CSCV and Deflated Sharpe Ratios (DSR).
    """

    @staticmethod
    def compute_cscv_pbo(
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 6,
        alpha_grid: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Implements Combinatorial Symmetric Cross-Validation (CSCV) to calculate Probability
        of Backtest Overfitting (PBO) across a grid of candidate models/hyperparameters.
        """
        import itertools
        from sklearn.metrics import mean_squared_error

        if alpha_grid is None:
            alpha_grid = [0.01, 0.1, 1.0, 10.0, 50.0, 100.0]

        n_samples = len(X)
        if n_samples < 30:
            return {
                "status": "UNKNOWN",
                "pbo": 0.0,
                "reason": "Sample size too small for CSCV (<30 rows)",
                "combinations_tested": 0
            }

        # Divide into n_splits contiguous blocks
        block_size = n_samples // n_splits
        blocks = []
        for i in range(n_splits):
            start = i * block_size
            end = (i + 1) * block_size if i < n_splits - 1 else n_samples
            blocks.append(np.arange(start, end))

        # Generate C(N, N/2) train/test combinations
        n_test = n_splits // 2
        combos = list(itertools.combinations(range(n_splits), n_test))

        oos_ranks = []
        pbo_count = 0

        for test_block_indices in combos:
            train_block_indices = [i for i in range(n_splits) if i not in test_block_indices]

            train_idx = np.concatenate([blocks[i] for i in train_block_indices])
            test_idx = np.concatenate([blocks[i] for i in test_block_indices])

            X_tr, y_tr = X[train_idx], y[train_idx]
            X_te, y_te = X[test_idx], y[test_idx]

            in_sample_scores = []
            out_sample_scores = []

            for alpha in alpha_grid:
                pipe = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
                pipe.fit(X_tr, y_tr)
                is_mse = mean_squared_error(y_tr, pipe.predict(X_tr))
                oos_mse = mean_squared_error(y_te, pipe.predict(X_te))
                in_sample_scores.append(is_mse)
                out_sample_scores.append(oos_mse)

            best_is_idx = int(np.argmin(in_sample_scores))
            sorted_oos_indices = np.argsort(out_sample_scores)
            oos_rank = np.where(sorted_oos_indices == best_is_idx)[0][0] + 1
            relative_rank = oos_rank / len(alpha_grid)
            oos_ranks.append(relative_rank)

            if relative_rank > 0.50:
                pbo_count += 1

        pbo = float(pbo_count / len(combos)) if combos else 0.0
        status = "PASS"
        if pbo > 0.50:
            status = "WARN"
        elif pbo > 0.75:
            status = "FAIL"

        return {
            "status": status,
            "pbo": round(pbo, 4),
            "pbo_pct": round(pbo * 100.0, 2),
            "combinations_tested": len(combos),
            "mean_relative_oos_rank": round(float(np.mean(oos_ranks)), 4),
            "n_splits": n_splits,
            "alpha_grid_size": len(alpha_grid)
        }

    @staticmethod
    def compute_deflated_sharpe_ratio(
        estimated_sharpe: float,
        num_trials: int,
        var_trials: float,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        sample_length: int = 252
    ) -> Dict[str, Any]:
        """
        Computes Bailey & López de Prado (2014) Deflated Sharpe Ratio (DSR).
        Adjusts estimated Sharpe ratio for multiple testing selection bias.
        """
        if num_trials <= 1:
            expected_max_sr = 0.0
        else:
            gamma = 0.5772156649
            sr_std = np.sqrt(max(1e-6, var_trials))
            z_n = (1.0 - gamma) * norm.ppf(1.0 - 1.0 / num_trials) + gamma * norm.ppf(1.0 - 1.0 / (num_trials * np.e))
            expected_max_sr = sr_std * z_n

        sr_var = (1.0 + (0.5 * estimated_sharpe ** 2) - (skewness * estimated_sharpe) + ((kurtosis - 3.0) / 4.0 * estimated_sharpe ** 2)) / sample_length
        sr_se = np.sqrt(max(1e-6, sr_var))

        z_stat = (estimated_sharpe - expected_max_sr) / sr_se
        dsr_prob = float(norm.cdf(z_stat))

        return {
            "estimated_sharpe": round(float(estimated_sharpe), 4),
            "expected_max_sharpe": round(float(expected_max_sr), 4),
            "deflated_sharpe_prob": round(float(dsr_prob), 4),
            "dsr_significant_95": bool(dsr_prob >= 0.95),
            "num_trials_adjusted": num_trials
        }


class FeatureAuditReport:
    """
    Structured research validation & feature health audit report.
    """

    def __init__(self, audit_dict: Dict[str, Any]):
        self.data = audit_dict

    def to_dict(self) -> Dict[str, Any]:
        return self.data

    def to_json(self, filepath: Optional[str] = None) -> str:
        json_str = json.dumps(self.data, indent=2)
        if filepath:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    def to_markdown(self) -> str:
        summary = self.data.get("summary", {})
        lines = [
            "# 🔬 Quantitative Feature & Research Validation Audit Report",
            f"**Audit Timestamp:** `{self.data.get('timestamp_utc', 'N/A')}`  ",
            f"**Total Features Audited:** `{summary.get('total_features', 0)}` | "
            f"**Pass:** `{summary.get('pass_count', 0)}` | "
            f"**Warn:** `{summary.get('warn_count', 0)}` | "
            f"**Fail:** `{summary.get('fail_count', 0)}`  ",
            f"**Probability of Backtest Overfitting (PBO):** `{self.data.get('pbo_audit', {}).get('pbo_pct', 0.0)}%`",
            "",
            "---",
            "",
            "### 1. Point-in-Time Temporal Leakage Findings",
            "| Feature Name | Status | Contemp Corr | Max Lead Corr | Max Lag Corr | Diagnostic Reason |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |"
        ]

        leakage_results = self.data.get("leakage_audit", {})
        for feat, res in leakage_results.items():
            lines.append(
                f"| `{feat}` | **`{res.get('status', 'N/A')}`** | "
                f"`{res.get('contemporaneous_corr', 0.0)}` | "
                f"`{res.get('max_lead_corr', 0.0)}` | "
                f"`{res.get('max_lag_corr', 0.0)}` | "
                f"{res.get('reason', '')} |"
            )

        lines.extend([
            "",
            "### 2. Multi-Horizon Factor IC & Decay Half-Life Analysis",
            "| Factor Name | Status | 1D Rank IC | 5D Rank IC | 14D Rank IC | Nom t1/2 | Emp t1/2 | Fit R2 |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
        ])

        decay_results = self.data.get("decay_audit", {})
        for feat, res in decay_results.items():
            r_ics = res.get("horizon_rank_ic", {})
            lines.append(
                f"| `{feat}` | **`{res.get('status', 'N/A')}`** | "
                f"`{r_ics.get('1D', 0.0)}` | `{r_ics.get('5D', 0.0)}` | `{r_ics.get('14D', 0.0)}` | "
                f"`{res.get('nominal_half_life_days', 0.0)}d` | "
                f"`{res.get('empirical_half_life_days', 0.0)}d` | "
                f"`{res.get('decay_fit_r2', 0.0)}` |"
            )

        lines.extend([
            "",
            "---",
            "*(Audit generated by Midgley Quantitative Research & Feature Leakage Engine)*"
        ])

        return "\n".join(lines)


class FeatureAuditor:
    """
    Unified Quantitative Research Validation & Feature Leakage Auditor.
    """

    def __init__(self, nominal_decay_half_life: float = 4.5):
        self.nominal_decay_half_life = nominal_decay_half_life
        self.leakage_auditor = PointInTimeLeakageAuditor()
        self.decay_auditor = FactorDecayAuditor()
        self.overfitting_auditor = BacktestOverfittingAuditor()

    def audit_feature_matrix(
        self,
        feature_df: pd.DataFrame,
        target_col: str = "target_rbob_5d",
        price_col: str = "gasoline_rbob",
        qualitative_features: Optional[List[str]] = None,
        horizons: Optional[List[int]] = None
    ) -> FeatureAuditReport:
        """
        Conducts full point-in-time leakage checks, factor IC decay evaluations,
        and CSCV PBO estimation across all numerical feature columns in the matrix.
        """
        import datetime
        timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if price_col not in feature_df.columns:
            price_series = feature_df[target_col] if target_col in feature_df.columns else pd.Series(np.ones(len(feature_df)))
        else:
            price_series = feature_df[price_col]

        price_returns = price_series.pct_change().fillna(0.0)

        exclude_cols = {target_col, price_col, "date", "timestamp", "target", "region"}
        feature_cols = [c for c in feature_df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(feature_df[c])]

        leakage_results = {}
        decay_results = {}
        pass_count = 0
        warn_count = 0
        fail_count = 0

        # 1. Point-in-Time Leakage Audit
        for col in feature_cols:
            res = self.leakage_auditor.audit_feature_lead_lag(
                feature_series=feature_df[col],
                price_returns=price_returns,
                max_lags=5
            )
            leakage_results[col] = res
            status = res.get("status", "PASS")
            if status == "PASS":
                pass_count += 1
            elif status == "WARN":
                warn_count += 1
            elif status == "FAIL":
                fail_count += 1

        # 2. Multi-Horizon Factor IC Decay Audit
        if qualitative_features is None:
            qualitative_features = [
                c for c in feature_cols if any(k in c.lower() for k in [
                    "risk", "shock", "decay", "event", "disruption", "sentiment",
                    "weather", "tornado", "hurricane", "seismic", "tweet", "ovx"
                ])
            ]
            if not qualitative_features and feature_cols:
                qualitative_features = feature_cols[:5]

        for col in qualitative_features:
            if col in feature_df.columns:
                decay_res = self.decay_auditor.evaluate_factor_ic_decay(
                    factor_name=col,
                    factor_series=feature_df[col],
                    price_series=price_series,
                    horizons=horizons or [1, 3, 5, 10, 14, 20],
                    nominal_half_life=self.nominal_decay_half_life
                )
                decay_results[col] = decay_res

        # 3. CSCV Probability of Backtest Overfitting (PBO)
        pbo_result = {"pbo": 0.0, "pbo_pct": 0.0, "status": "PASS"}
        if target_col in feature_df.columns and len(feature_cols) > 0:
            clean_df = feature_df[feature_cols + [target_col]].dropna()
            if len(clean_df) >= 30:
                X = clean_df[feature_cols].values
                y = clean_df[target_col].values
                pbo_result = self.overfitting_auditor.compute_cscv_pbo(X=X, y=y, n_splits=6)

        audit_dict = {
            "timestamp_utc": timestamp_utc,
            "engine": "LacunaFeatureAuditor",
            "has_lacuna_native_pkg": HAS_LACUNA,
            "summary": {
                "total_features": len(feature_cols),
                "pass_count": pass_count,
                "warn_count": warn_count,
                "fail_count": fail_count,
                "qualitative_factor_count": len(qualitative_features)
            },
            "pbo_audit": pbo_result,
            "leakage_audit": leakage_results,
            "decay_audit": decay_results
        }

        return FeatureAuditReport(audit_dict)
