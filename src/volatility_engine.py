"""
Wholesale RBOB Volatility Distribution & Predictive Density Engine (src/volatility_engine.py)
Issue #448: Wholesale RBOB volatility distribution forecasting via GARCH(1,1), GJR-GARCH, and HAR-RV.

Provides:
1. GARCH(1,1) / GJR-GARCH maximum-likelihood / regularized parameter estimation.
2. Analytical and recursive multi-step cumulative horizon volatility forecasting:
   sigma^2_{t,h} = sum_{k=1}^h E_t[sigma^2_{t+k}]
3. Heterogeneous Autoregressive Realized Volatility (HAR-RV) multi-scale estimation (daily, weekly, monthly).
4. Fat-tailed Student-t predictive return density modeling:
   R_{t -> t+h} ~ Student-t(df=nu, scale=sigma_{t,h} * sqrt((nu-2)/nu))
5. Probability Integral Transform (PIT) uniformity diagnostics and Continuous Ranked Probability Score (CRPS).
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import optimize, stats

logger = logging.getLogger("midgley.volatility_engine")


class GARCHVolatilityModel:
    """
    GARCH(1,1) and GJR-GARCH (Glosten-Jagannathan-Runkle) Asymmetric Volatility Model.
    Models conditional variance sigma^2_t = omega + alpha * eps^2_{t-1} + gamma * eps^2_{t-1} * I_{eps < 0} + beta * sigma^2_{t-1}.
    """

    def __init__(self, asymmetric: bool = True):
        self.asymmetric = asymmetric
        self.omega: float = 1e-5
        self.alpha: float = 0.08
        self.gamma: float = 0.04 if asymmetric else 0.0
        self.beta: float = 0.88
        self.is_fitted: bool = False
        self.last_variance: float = 0.0004
        self.unconditional_variance: float = 0.0004

    def fit(self, returns: Union[np.ndarray, pd.Series, List[float]]) -> "GARCHVolatilityModel":
        """
        Fits GARCH(1,1) / GJR-GARCH parameters via quasi-maximum likelihood estimation (QMLE).
        """
        r = np.asarray(returns, dtype=float)
        r = r[~np.isnan(r)]
        if len(r) < 30:
            logger.warning("Insufficient return observations for GARCH fit; using robust prior parameters.")
            sample_var = float(np.var(r)) if len(r) > 1 else 0.0004
            self.unconditional_variance = max(sample_var, 1e-6)
            self.omega = self.unconditional_variance * (1.0 - 0.08 - 0.88 - (0.02 if self.asymmetric else 0.0))
            self.last_variance = self.unconditional_variance
            self.is_fitted = True
            return self

        # Demean returns
        eps = r - np.mean(r)
        sample_var = float(np.var(eps))
        if sample_var < 1e-8:
            sample_var = 0.0004

        # Initial parameter guesses: [omega, alpha, gamma (if asymmetric), beta]
        if self.asymmetric:
            init_params = [sample_var * 0.05, 0.06, 0.04, 0.85]
            bounds = [(1e-8, sample_var * 0.5), (0.001, 0.4), (0.0, 0.4), (0.4, 0.98)]
        else:
            init_params = [sample_var * 0.05, 0.08, 0.87]
            bounds = [(1e-8, sample_var * 0.5), (0.001, 0.4), (0.4, 0.98)]

        def neg_log_likelihood(params: np.ndarray) -> float:
            if self.asymmetric:
                omega, alpha, gamma, beta = params
                persistence = alpha + beta + 0.5 * gamma
            else:
                omega, alpha, beta = params
                gamma = 0.0
                persistence = alpha + beta

            if persistence >= 0.999 or omega <= 0 or alpha < 0 or beta < 0 or gamma < 0:
                return 1e10

            n = len(eps)
            sigma2 = np.zeros(n)
            sigma2[0] = sample_var

            for t in range(1, n):
                leverage = 1.0 if (self.asymmetric and eps[t - 1] < 0) else 0.0
                sigma2[t] = omega + (alpha + gamma * leverage) * (eps[t - 1] ** 2) + beta * sigma2[t - 1]
                if sigma2[t] <= 1e-9:
                    sigma2[t] = 1e-9

            # Gaussian log-likelihood
            ll = -0.5 * np.sum(np.log(2 * np.pi) + np.log(sigma2) + (eps ** 2) / sigma2)
            return -ll if np.isfinite(ll) else 1e10

        try:
            res = optimize.minimize(
                neg_log_likelihood,
                init_params,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 300, "ftol": 1e-7}
            )
            if res.success and np.isfinite(res.fun):
                if self.asymmetric:
                    self.omega, self.alpha, self.gamma, self.beta = res.x
                else:
                    self.omega, self.alpha, self.beta = res.x
                    self.gamma = 0.0
            else:
                self.omega = sample_var * 0.05
                self.alpha = 0.07
                self.gamma = 0.03 if self.asymmetric else 0.0
                self.beta = 0.86
        except Exception as e:
            logger.debug(f"GARCH optimization exception: {e}; applying constrained defaults.")
            self.omega = sample_var * 0.05
            self.alpha = 0.07
            self.gamma = 0.03 if self.asymmetric else 0.0
            self.beta = 0.86

        persistence = self.alpha + self.beta + (0.5 * self.gamma if self.asymmetric else 0.0)
        persistence = min(persistence, 0.995)
        self.unconditional_variance = max(self.omega / (1.0 - persistence), 1e-6)

        # Compute last step conditional variance
        n = len(eps)
        sigma2 = np.zeros(n)
        sigma2[0] = sample_var
        for t in range(1, n):
            leverage = 1.0 if (self.asymmetric and eps[t - 1] < 0) else 0.0
            sigma2[t] = self.omega + (self.alpha + self.gamma * leverage) * (eps[t - 1] ** 2) + self.beta * sigma2[t - 1]

        last_leverage = 1.0 if (self.asymmetric and eps[-1] < 0) else 0.0
        self.last_variance = float(self.omega + (self.alpha + self.gamma * last_leverage) * (eps[-1] ** 2) + self.beta * sigma2[-1])
        self.is_fitted = True
        return self

    def forecast_variance_path(self, horizon: int = 5) -> List[float]:
        """
        Forecasts 1-step to h-step conditional variances sigma^2_{t+k|t}.
        """
        if not self.is_fitted:
            return [self.unconditional_variance] * horizon

        persistence = self.alpha + self.beta + (0.5 * self.gamma if self.asymmetric else 0.0)
        uncond_var = self.unconditional_variance
        step1_var = self.last_variance

        path = []
        for k in range(1, horizon + 1):
            if k == 1:
                path.append(step1_var)
            else:
                # E_t[sigma^2_{t+k}] = uncond_var + (persistence)^(k-1) * (step1_var - uncond_var)
                step_k_var = uncond_var + (persistence ** (k - 1)) * (step1_var - uncond_var)
                path.append(max(float(step_k_var), 1e-7))

        return path

    def forecast_cumulative_volatility(self, horizon: int = 5) -> float:
        """
        Calculates cumulative standard deviation over h-day holding period:
        sigma_{t,h} = sqrt( sum_{k=1}^h sigma^2_{t+k|t} )
        """
        path = self.forecast_variance_path(horizon)
        cum_var = sum(path)
        return math.sqrt(max(cum_var, 1e-8))


class HARRVModel:
    """
    Heterogeneous Autoregressive Model of Realized Volatility (Corsi, 2009).
    Models realized variance as an autoregression on Daily (1d), Weekly (5d), and Monthly (22d) components:
    RV_{t+1} = c + beta_d * RV_t + beta_w * RV^{(w)}_t + beta_m * RV^{(m)}_t + eps_{t+1}
    """

    def __init__(self):
        self.intercept: float = 1e-5
        self.beta_d: float = 0.35
        self.beta_w: float = 0.35
        self.beta_m: float = 0.20
        self.is_fitted: bool = False
        self.last_rv_components: Tuple[float, float, float] = (0.0004, 0.0004, 0.0004)

    def fit(self, daily_realized_variances: Union[np.ndarray, pd.Series, List[float]]) -> "HARRVModel":
        """
        Fits HAR-RV model using ordinary least squares over rolling multi-scale variance averages.
        """
        rv = np.asarray(daily_realized_variances, dtype=float)
        rv = rv[~np.isnan(rv)]
        if len(rv) < 30:
            logger.warning("Insufficient observations for HAR-RV fit; using default multi-scale priors.")
            sample_rv = float(np.mean(rv)) if len(rv) > 0 else 0.0004
            self.last_rv_components = (sample_rv, sample_rv, sample_rv)
            self.intercept = sample_rv * 0.10
            self.is_fitted = True
            return self

        # Construct daily, weekly (5d), monthly (22d) lags
        s_rv = pd.Series(rv)
        rv_d = s_rv.shift(1)
        rv_w = s_rv.rolling(window=5).mean().shift(1)
        rv_m = s_rv.rolling(window=22).mean().shift(1)

        df = pd.DataFrame({"y": s_rv, "d": rv_d, "w": rv_w, "m": rv_m}).dropna()
        if len(df) < 15:
            sample_rv = float(np.mean(rv))
            self.last_rv_components = (sample_rv, sample_rv, sample_rv)
            self.is_fitted = True
            return self

        X = np.column_stack([np.ones(len(df)), df["d"].values, df["w"].values, df["m"].values])
        y = df["y"].values

        try:
            # Constrained / Ridge regularized OLS (ensuring non-negative coefficients)
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            self.intercept = max(float(beta[0]), 1e-7)
            self.beta_d = max(float(beta[1]), 0.0)
            self.beta_w = max(float(beta[2]), 0.0)
            self.beta_m = max(float(beta[3]), 0.0)

            # Normalize sum of betas if explosive
            beta_sum = self.beta_d + self.beta_w + self.beta_m
            if beta_sum >= 0.99:
                scale = 0.95 / beta_sum
                self.beta_d *= scale
                self.beta_w *= scale
                self.beta_m *= scale
        except Exception as e:
            logger.debug(f"HAR-RV lstsq error: {e}; using standard priors.")

        # Save last known components
        d_last = float(s_rv.iloc[-1])
        w_last = float(s_rv.iloc[-5:].mean()) if len(s_rv) >= 5 else d_last
        m_last = float(s_rv.iloc[-22:].mean()) if len(s_rv) >= 22 else w_last
        self.last_rv_components = (d_last, w_last, m_last)
        self.is_fitted = True
        return self

    def forecast_variance_path(self, horizon: int = 5) -> List[float]:
        """
        Forecasts h-step forward variance path recursively using HAR components.
        """
        d, w, m = self.last_rv_components
        path = []
        recent_history = [m] * 22 + [w] * 5 + [d]

        for _ in range(horizon):
            d_curr = recent_history[-1]
            w_curr = np.mean(recent_history[-5:])
            m_curr = np.mean(recent_history[-22:])
            pred_rv = self.intercept + self.beta_d * d_curr + self.beta_w * w_curr + self.beta_m * m_curr
            pred_rv = max(float(pred_rv), 1e-7)
            path.append(pred_rv)
            recent_history.append(pred_rv)

        return path

    def forecast_cumulative_volatility(self, horizon: int = 5) -> float:
        path = self.forecast_variance_path(horizon)
        return math.sqrt(max(sum(path), 1e-8))


class StudentTPredictiveDistribution:
    """
    Fat-tailed Student-t Predictive Density Engine.
    Models return innovations R_{t -> t+h} ~ Student-t(loc=mu, scale=s_h, df=nu).
    Includes PIT uniformity testing and CRPS score calculation.
    """

    def __init__(self, degrees_of_freedom: float = 6.0):
        self.df = max(degrees_of_freedom, 3.0)

    def fit_degrees_of_freedom(self, standardized_residuals: Union[np.ndarray, List[float]]) -> float:
        """
        Fits optimal Student-t degrees of freedom nu on standardized residuals via MLE.
        """
        z = np.asarray(standardized_residuals, dtype=float)
        z = z[~np.isnan(z)]
        if len(z) < 20:
            return self.df

        try:
            params = stats.t.fit(z, floc=0.0)
            fitted_df = params[0]
            self.df = float(np.clip(fitted_df, 3.5, 30.0))
        except Exception:
            self.df = 6.0
        return self.df

    def compute_quantiles(
        self,
        mu: float,
        cumulative_volatility: float,
        quantiles: Optional[List[float]] = None
    ) -> Dict[str, float]:
        """
        Calculates exact quantiles for the h-day predictive return distribution.
        """
        if quantiles is None:
            quantiles = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]

        # Student-t scale: s = sigma * sqrt((nu - 2) / nu)
        scale = cumulative_volatility * math.sqrt((self.df - 2.0) / self.df)
        dist = stats.t(df=self.df, loc=mu, scale=scale)

        res = {}
        for q in quantiles:
            q_key = f"q{int(round(q * 100)):02d}"
            res[q_key] = float(dist.ppf(q))
        return res

    def compute_pit_values(
        self,
        realized_returns: np.ndarray,
        predicted_vols: np.ndarray,
        mu: float = 0.0
    ) -> Tuple[np.ndarray, float]:
        """
        Computes Probability Integral Transform (PIT) values u_t = F(R_t) and performs Kolmogorov-Smirnov test for Uniform(0,1).
        Returns (pit_array, ks_pvalue).
        """
        r = np.asarray(realized_returns, dtype=float)
        v = np.asarray(predicted_vols, dtype=float)
        valid = (~np.isnan(r)) & (~np.isnan(v)) & (v > 1e-8)
        r, v = r[valid], v[valid]

        if len(r) == 0:
            return np.array([]), 1.0

        scales = v * np.sqrt((self.df - 2.0) / self.df)
        pit_values = stats.t.cdf(r, df=self.df, loc=mu, scale=scales)

        # Kolmogorov-Smirnov test against Uniform(0, 1)
        ks_stat, p_value = stats.kstest(pit_values, "uniform")
        return pit_values, float(p_value)

    @staticmethod
    def compute_crps(
        realized_return: float,
        mu: float,
        cumulative_volatility: float,
        df: float = 6.0
    ) -> float:
        """
        Computes Continuous Ranked Probability Score (CRPS) for Student-t predictive density.
        Uses standard numerical quadrature / closed-form quantile integration.
        """
        scale = cumulative_volatility * math.sqrt((df - 2.0) / df)
        dist = stats.t(df=df, loc=mu, scale=scale)

        # Numerical integral approximation of CRPS = integral (F(x) - 1_{x >= y})^2 dx
        # over [mu - 7*scale, mu + 7*scale]
        grid = np.linspace(mu - 7 * scale, mu + 7 * scale, 200)
        cdf_vals = dist.cdf(grid)
        indicator = (grid >= realized_return).astype(float)
        integrand = (cdf_vals - indicator) ** 2
        crps = float(np.trapezoid(integrand, grid))
        return crps


class RBOBVolatilityEngine:
    """
    Master Quantitative Wholesale RBOB Volatility Engine.
    Coordinates GARCH(1,1), GJR-GARCH leverage, HAR-RV, and Student-t predictive distributions.
    """

    def __init__(self, asymmetric: bool = True, degrees_of_freedom: float = 6.0):
        self.garch = GARCHVolatilityModel(asymmetric=asymmetric)
        self.har_rv = HARRVModel()
        self.dist = StudentTPredictiveDistribution(degrees_of_freedom=degrees_of_freedom)
        self.is_calibrated: bool = False

    def calibrate(self, price_series: Union[pd.Series, np.ndarray, List[float]]) -> "RBOBVolatilityEngine":
        """
        Calibrates GARCH and HAR-RV models from historical wholesale RBOB prices.
        """
        p = np.asarray(price_series, dtype=float)
        p = p[~np.isnan(p)]
        if len(p) < 10:
            logger.warning("Price series too short for full volatility calibration; using defaults.")
            self.is_calibrated = True
            return self

        # Compute log returns
        log_returns = np.diff(np.log(p))
        self.garch.fit(log_returns)

        # Realized daily variance proxy: log_returns^2
        realized_variances = log_returns ** 2
        self.har_rv.fit(realized_variances)

        # Standardized residuals for Student-t df fit
        if len(log_returns) > 30 and self.garch.last_variance > 1e-8:
            std_residuals = (log_returns - np.mean(log_returns)) / np.sqrt(self.garch.last_variance)
            self.dist.fit_degrees_of_freedom(std_residuals)

        self.is_calibrated = True
        return self

    def forecast_volatility_term_structure(self, current_price: float, max_horizon: int = 5) -> Dict[str, Any]:
        """
        Generates full predictive volatility term structure and price quantiles for horizons h in [1..max_horizon].
        """
        if not self.is_calibrated:
            self.calibrate(np.array([current_price * 0.98, current_price, current_price * 1.01]))

        horizon_forecasts = {}
        for h in range(1, max_horizon + 1):
            garch_cum_vol = self.garch.forecast_cumulative_volatility(horizon=h)
            har_cum_vol = self.har_rv.forecast_cumulative_volatility(horizon=h)

            # Ensemble cumulative volatility (weighted combination: 60% GARCH, 40% HAR-RV)
            ensemble_vol = 0.60 * garch_cum_vol + 0.40 * har_cum_vol

            # Compute return quantiles
            return_quantiles = self.dist.compute_quantiles(mu=0.0, cumulative_volatility=ensemble_vol)

            # Convert return quantiles to wholesale price levels: P_q = current_price * exp(q_return)
            price_quantiles = {
                q_k: round(current_price * math.exp(q_val), 4)
                for q_k, q_val in return_quantiles.items()
            }

            horizon_forecasts[f"horizon_{h}d"] = {
                "horizon_days": h,
                "garch_volatility": round(garch_cum_vol, 5),
                "har_rv_volatility": round(har_cum_vol, 5),
                "ensemble_volatility": round(ensemble_vol, 5),
                "annualized_volatility_pct": round(ensemble_vol * math.sqrt(252.0 / h) * 100.0, 2),
                "student_t_df": round(self.dist.df, 2),
                "return_quantiles": {k: round(v, 5) for k, v in return_quantiles.items()},
                "price_quantiles": price_quantiles,
                "expected_price_range_90pct": [price_quantiles["q05"], price_quantiles["q95"]],
                "expected_price_range_50pct": [price_quantiles["q25"], price_quantiles["q75"]]
            }

        return {
            "current_wholesale_price": current_price,
            "garch_parameters": {
                "omega": self.garch.omega,
                "alpha": self.garch.alpha,
                "gamma": self.garch.gamma,
                "beta": self.garch.beta,
                "unconditional_variance": self.garch.unconditional_variance
            },
            "har_rv_parameters": {
                "intercept": self.har_rv.intercept,
                "beta_daily": self.har_rv.beta_d,
                "beta_weekly": self.har_rv.beta_w,
                "beta_monthly": self.har_rv.beta_m
            },
            "horizons": horizon_forecasts
        }
