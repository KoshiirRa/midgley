"""
Asymmetric Error-Correction Model (ECM) for Retail-Wholesale Pass-Through (src/asymmetric_ecm.py)
Implements cointegration-based asymmetric distributed-lag error-correction modeling ('rockets and feathers')
between wholesale spot/futures RBOB and regional retail pump prices. (Issues #402, #607)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)


class AsymmetricECM:
    """
    Asymmetric Error-Correction Model estimating long-run rack margin equilibrium,
    Engle-Granger cointegration, and asymmetric adjustment speeds for rising vs falling
    wholesale gasoline costs with HAC standard errors.
    
    Long-Run Cointegration:
      Retail_t = beta * Wholesale_t + c + u_t
      z_t = Retail_t - beta * Wholesale_t - c
      
    Asymmetric Error Correction:
      z_t^+ = max(0, z_t)  (Retail above equilibrium / high margin)
      z_t^- = min(0, z_t)  (Retail below equilibrium / squeezed margin)
      
      Delta Retail_t = alpha^+ * z_{t-1}^+ + alpha^- * z_{t-1}^- 
                     + sum_{i=0}^k (gamma_i^+ * Delta Wholesale_{t-i}^+ + gamma_i^- * Delta Wholesale_{t-i}^-)
                     + sum_{j=1}^p delta_j * Delta Retail_{t-j} + epsilon_t
    """

    def __init__(
        self,
        n_lags_wholesale: Optional[int] = None,
        n_lags_retail: Optional[int] = None,
        wholesale_lags: Optional[int] = None,
        retail_lags: Optional[int] = None,
    ):
        self.n_lags_wholesale = wholesale_lags if wholesale_lags is not None else (n_lags_wholesale or 3)
        self.n_lags_retail = retail_lags if retail_lags is not None else (n_lags_retail or 2)
        self.wholesale_lags = self.n_lags_wholesale
        self.retail_lags = self.n_lags_retail
        
        # Long-run parameters
        self.beta: float = 1.0
        self.equilibrium_margin_c: float = 0.65
        self.rack_spread: float = 0.65
        self.r2_cointegration: float = 0.0
        self.adf_stat: float = -3.50
        self.is_cointegrated: bool = True
        
        # Short-run parameters
        self.alpha_pos: float = -0.05   # Speed of downward adjustment (feathers)
        self.alpha_neg: float = -0.15   # Speed of upward adjustment (rockets)
        self.gamma_pos_coefs: List[float] = []
        self.gamma_neg_coefs: List[float] = []
        self.gamma_coefs: List[float] = []
        self.delta_coefs: List[float] = []
        self.intercept_dynamic: float = 0.0
        self.hac_se: List[float] = []
        self.hac_t_stats: List[float] = []
        
        self.is_fitted: bool = False
        self.last_retail_price: float = 3.50
        self.last_wholesale_price: float = 2.85
        self.last_residual: float = 0.0
        self.last_d_wholesale_lags: List[float] = [0.0] * self.n_lags_wholesale
        self.last_d_retail_lags: List[float] = [0.0] * self.n_lags_retail

    def fit(
        self,
        retail_data: Union[pd.Series, pd.DataFrame],
        wholesale_series: Optional[pd.Series] = None,
        retail_col: str = "retail_price",
        wholesale_col: str = "wholesale_price"
    ) -> "AsymmetricECM":
        """
        Fits two-step Engle-Granger Asymmetric Error-Correction Model.
        Rejects synthetic constant-margin series where var(retail - wholesale) < 1e-6 (Issue #607).
        """
        if isinstance(retail_data, pd.DataFrame):
            df = retail_data[[retail_col, wholesale_col]].rename(
                columns={retail_col: "retail", wholesale_col: "wholesale"}
            ).dropna()
        else:
            if wholesale_series is None:
                raise ValueError("wholesale_series must be provided when retail_data is a pd.Series.")
            df = pd.DataFrame({
                "retail": retail_data,
                "wholesale": wholesale_series
            }).dropna()

        if len(df) < 30:
            raise ValueError(f"Insufficient observations for AsymmetricECM fitting ({len(df)} < 30).")

        # Refuse to fit on synthetic constant-margin series (Issue #607, T-1)
        spread = df["retail"].values - df["wholesale"].values
        spread_var = float(np.var(spread))
        if spread_var < 1e-6:
            raise ValueError(
                f"Cannot fit AsymmetricECM on synthetic constant-margin series (variance={spread_var:.2e} < 1e-6). "
                "Model must be fitted on genuine retail price history."
            )

        # Step 1: Long-Run Cointegration Equation (OLS)
        X_long = df[["wholesale"]].values
        y_long = df["retail"].values
        
        lr_model = LinearRegression(fit_intercept=True)
        lr_model.fit(X_long, y_long)
        
        self.beta = float(lr_model.coef_[0])
        self.equilibrium_margin_c = float(lr_model.intercept_)
        self.rack_spread = self.equilibrium_margin_c
        self.r2_cointegration = float(lr_model.score(X_long, y_long))
        
        # Calculate Cointegrating Residuals: z_t
        df["z"] = df["retail"] - (self.beta * df["wholesale"] + self.equilibrium_margin_c)

        # Engle-Granger Cointegration Residual Test (ADF without drift on residuals)
        z_vals = df["z"].values
        dz_vals = np.diff(z_vals)
        z_lag = z_vals[:-1]
        p_lags = min(2, max(1, len(dz_vals) // 50))
        if len(dz_vals) > p_lags + 5:
            X_adf_list = [z_lag[p_lags:]]
            for lag_i in range(1, p_lags + 1):
                X_adf_list.append(dz_vals[p_lags - lag_i : -lag_i])
            X_adf = np.column_stack(X_adf_list)
            y_adf = dz_vals[p_lags:]
            beta_adf, _, _, _ = np.linalg.lstsq(X_adf, y_adf, rcond=None)
            rho_hat = beta_adf[0]
            e_adf = y_adf - X_adf @ beta_adf
            df_adf = len(y_adf) - X_adf.shape[1]
            s2_adf = np.sum(e_adf ** 2) / max(1, df_adf)
            inv_xx = np.linalg.pinv(X_adf.T @ X_adf)
            se_rho = np.sqrt(max(1e-12, s2_adf * inv_xx[0, 0]))
            self.adf_stat = float(rho_hat / se_rho)
            # MacKinnon critical value at 10% for cointegration with 1 regressor & constant is -3.04
            self.is_cointegrated = bool(self.adf_stat < -3.04)
        else:
            self.adf_stat = -3.50
            self.is_cointegrated = True

        df["z_lag1"] = df["z"].shift(1)
        
        # Asymmetric Split: z^+ and z^-
        df["z_pos_lag1"] = np.maximum(0.0, df["z_lag1"])
        df["z_neg_lag1"] = np.minimum(0.0, df["z_lag1"])
        
        # Step 2: Differencing & Asymmetric Short-Run Lags (Issue #607, T-7)
        df["d_retail"] = df["retail"].diff()
        df["d_wholesale"] = df["wholesale"].diff()
        df["d_wholesale_pos"] = np.maximum(0.0, df["d_wholesale"])
        df["d_wholesale_neg"] = np.minimum(0.0, df["d_wholesale"])
        
        # Feature columns for dynamic regression
        feature_cols = ["z_pos_lag1", "z_neg_lag1", "d_wholesale_pos", "d_wholesale_neg"]
        
        for i in range(1, self.n_lags_wholesale + 1):
            df[f"d_wholesale_pos_lag{i}"] = np.maximum(0.0, df["d_wholesale"].shift(i))
            df[f"d_wholesale_neg_lag{i}"] = np.minimum(0.0, df["d_wholesale"].shift(i))
            feature_cols.extend([f"d_wholesale_pos_lag{i}", f"d_wholesale_neg_lag{i}"])
            
        for j in range(1, self.n_lags_retail + 1):
            col_name = f"d_retail_lag{j}"
            df[col_name] = df["d_retail"].shift(j)
            feature_cols.append(col_name)
            
        df_reg = df.dropna().copy()
        
        if len(df_reg) < 20:
            raise ValueError("Insufficient degrees of freedom after lagging for dynamic ECM regression.")
            
        T = len(df_reg)
        X_raw = df_reg[feature_cols].values
        X_dyn_const = np.column_stack([np.ones(T), X_raw])
        y_dyn = df_reg["d_retail"].values
        
        # OLS estimation
        beta_dyn, _, _, _ = np.linalg.lstsq(X_dyn_const, y_dyn, rcond=None)
        residuals_dyn = y_dyn - X_dyn_const @ beta_dyn

        # HAC (Newey-West) standard errors computation
        L = min(int(4.0 * ((T / 100.0) ** (2.0 / 9.0))) + 1, max(1, T // 4))
        scores = X_dyn_const * residuals_dyn[:, None]
        gamma_0 = (scores.T @ scores) / T
        omega = gamma_0.copy()
        for l in range(1, L + 1):
            w_l = 1.0 - (l / (L + 1.0))
            gamma_l = (scores[l:].T @ scores[:-l]) / T
            omega += w_l * (gamma_l + gamma_l.T)

        inv_XtX = np.linalg.pinv(X_dyn_const.T @ X_dyn_const)
        V_hac = inv_XtX @ (T * omega) @ inv_XtX
        se_hac = np.sqrt(np.maximum(1e-12, np.diag(V_hac)))
        t_stats_hac = beta_dyn / se_hac
        
        self.intercept_dynamic = float(beta_dyn[0])
        self.alpha_pos = float(beta_dyn[1])
        self.alpha_neg = float(beta_dyn[2])

        # Extract asymmetric short-run wholesale coefficients
        self.gamma_pos_coefs = [float(beta_dyn[3])] + [float(beta_dyn[5 + 2 * k]) for k in range(self.n_lags_wholesale)]
        self.gamma_neg_coefs = [float(beta_dyn[4])] + [float(beta_dyn[6 + 2 * k]) for k in range(self.n_lags_wholesale)]
        self.gamma_coefs = [(gp + gn) / 2.0 for gp, gn in zip(self.gamma_pos_coefs, self.gamma_neg_coefs)]

        ret_start_idx = 5 + 2 * self.n_lags_wholesale
        self.delta_coefs = [float(c) for c in beta_dyn[ret_start_idx:]]
        self.hac_se = [float(s) for s in se_hac]
        self.hac_t_stats = [float(t) for t in t_stats_hac]
        
        self.last_retail_price = float(df["retail"].iloc[-1])
        self.last_wholesale_price = float(df["wholesale"].iloc[-1])
        self.last_residual = float(df["z"].iloc[-1])

        # Store historical differences for recursive warm start
        d_whl_series = df["d_wholesale"].dropna()
        if len(d_whl_series) >= self.n_lags_wholesale:
            self.last_d_wholesale_lags = [float(d_whl_series.iloc[-k]) for k in range(1, self.n_lags_wholesale + 1)]
        else:
            self.last_d_wholesale_lags = [0.0] * self.n_lags_wholesale

        d_ret_series = df["d_retail"].dropna()
        if len(d_ret_series) >= self.n_lags_retail:
            self.last_d_retail_lags = [float(d_ret_series.iloc[-k]) for k in range(1, self.n_lags_retail + 1)]
        else:
            self.last_d_retail_lags = [0.0] * self.n_lags_retail

        self.is_fitted = True
        
        logger.info(
            f"AsymmetricECM Fitted: Rack Margin=${self.equilibrium_margin_c:.3f}/gal, "
            f"Beta={self.beta:.3f}, Alpha^+={self.alpha_pos:.4f}, Alpha^-={self.alpha_neg:.4f}, "
            f"ADF={self.adf_stat:.2f} (Cointegrated: {self.is_cointegrated})"
        )
        return self

    def predict_step_ahead(
        self,
        current_retail: Optional[Union[float, pd.DataFrame, pd.Series]] = None,
        current_wholesale: Optional[Union[float, List[float], np.ndarray]] = None,
        steps_ahead: int = 5,
        expected_wholesale_deltas: Optional[List[float]] = None,
        steps: Optional[int] = None
    ) -> Union[List[float], pd.Series]:
        """
        Iteratively forecasts retail prices h-steps ahead under asymmetric error correction
        and asymmetric short-run wholesale price lags.
        """
        if not self.is_fitted:
            raise RuntimeError("AsymmetricECM must be fitted before calling predict_step_ahead().")

        total_steps = steps if steps is not None else steps_ahead

        # Warm start historical difference buffers
        d_ret_hist = list(self.last_d_retail_lags) if len(self.last_d_retail_lags) == self.n_lags_retail else [0.0] * self.n_lags_retail
        d_whl_pos_hist = [0.0] + [max(0.0, x) for x in self.last_d_wholesale_lags]
        d_whl_neg_hist = [0.0] + [min(0.0, x) for x in self.last_d_wholesale_lags]

        # Handle DataFrame input for current_retail
        if isinstance(current_retail, pd.DataFrame):
            last_ret = float(current_retail["retail_price"].iloc[-1]) if "retail_price" in current_retail.columns else float(current_retail.iloc[-1, 0])
            last_whl = float(current_retail["wholesale_price"].iloc[-1]) if "wholesale_price" in current_retail.columns else float(current_retail.iloc[-1, 1])
            ret_price = last_ret
            whl_price = last_whl

            if len(current_retail) > 1:
                ret_col_name = "retail_price" if "retail_price" in current_retail.columns else current_retail.columns[0]
                whl_col_name = "wholesale_price" if "wholesale_price" in current_retail.columns else current_retail.columns[1]
                d_r_avail = current_retail[ret_col_name].diff().dropna()
                if len(d_r_avail) >= self.n_lags_retail:
                    d_ret_hist = [float(d_r_avail.iloc[-k]) for k in range(1, self.n_lags_retail + 1)]
                d_w_avail = current_retail[whl_col_name].diff().dropna()
                if len(d_w_avail) >= self.n_lags_wholesale:
                    d_whl_pos_hist = [0.0] + [max(0.0, float(d_w_avail.iloc[-k])) for k in range(1, self.n_lags_wholesale + 1)]
                    d_whl_neg_hist = [0.0] + [min(0.0, float(d_w_avail.iloc[-k])) for k in range(1, self.n_lags_wholesale + 1)]
            
            if isinstance(current_wholesale, (list, np.ndarray, pd.Series)):
                future_whl = list(current_wholesale)
                whl_deltas = [future_whl[0] - last_whl] + [future_whl[i] - future_whl[i - 1] for i in range(1, len(future_whl))]
                expected_wholesale_deltas = whl_deltas
        else:
            ret_price = float(current_retail) if current_retail is not None else self.last_retail_price
            whl_price = float(current_wholesale) if (current_wholesale is not None and isinstance(current_wholesale, (int, float))) else self.last_wholesale_price

        # Distribute wholesale deltas smoothly if single total delta was provided
        if expected_wholesale_deltas is None:
            expected_wholesale_deltas = [0.0] * total_steps
        elif len(expected_wholesale_deltas) == 1 and total_steps > 1:
            total_d = expected_wholesale_deltas[0]
            expected_wholesale_deltas = [total_d / total_steps] * total_steps
        elif len(expected_wholesale_deltas) < total_steps:
            expected_wholesale_deltas.extend([0.0] * (total_steps - len(expected_wholesale_deltas)))

        forecasts = []

        for step in range(total_steps):
            d_w = expected_wholesale_deltas[step]
            d_w_pos = max(0.0, d_w)
            d_w_neg = min(0.0, d_w)
            
            d_whl_pos_hist[0] = d_w_pos
            d_whl_neg_hist[0] = d_w_neg
            
            # Prior-period cointegration disequilibrium z_{t-1}
            z = ret_price - (self.beta * whl_price + self.equilibrium_margin_c)
            z_pos = max(0.0, z)
            z_neg = min(0.0, z)
            
            # Predict expected retail delta Delta retail_t with asymmetric lags
            sr_pos = sum(g * dw for g, dw in zip(self.gamma_pos_coefs, d_whl_pos_hist))
            sr_neg = sum(g * dw for g, dw in zip(self.gamma_neg_coefs, d_whl_neg_hist))
            ar_ret = sum(d * dr for d, dr in zip(self.delta_coefs, d_ret_hist))

            d_retail_pred = (
                self.intercept_dynamic +
                (self.alpha_pos * z_pos) +
                (self.alpha_neg * z_neg) +
                sr_pos +
                sr_neg +
                ar_ret
            )
            
            # Update state variables
            whl_price += d_w
            ret_price += d_retail_pred
            forecasts.append(round(float(ret_price), 4))
            
            # Shift histories for next recursive step
            d_ret_hist = [d_retail_pred] + d_ret_hist[:-1]
            d_whl_pos_hist = [d_w_pos] + d_whl_pos_hist[:-1]
            d_whl_neg_hist = [d_w_neg] + d_whl_neg_hist[:-1]

        if isinstance(current_retail, pd.DataFrame):
            return pd.Series(forecasts)
        return forecasts

    def forecast_horizon(
        self,
        current_retail: float,
        current_wholesale: float,
        future_wholesale_deltas: Union[float, List[float]],
        horizon_days: int = 5,
        forward_tax_delta: float = 0.0,
        is_california: bool = False,
        sales_tax_rate: float = 0.0325,
        method: str = "distributed"
    ) -> float:
        """
        Generates direct h-step ahead retail forecast with distributed wholesale trajectories,
        statutory tax adjustments, and corrected California sales tax scaling on wholesale pass-through
        (Issues #402, #443, #451, #607).
        """
        if isinstance(future_wholesale_deltas, (int, float)):
            whl_deltas_list = [float(future_wholesale_deltas)]
        else:
            whl_deltas_list = list(future_wholesale_deltas)

        # Distribute trajectory evenly over horizon_days if single total delta
        if len(whl_deltas_list) == 1 and horizon_days > 1:
            total_whl = whl_deltas_list[0]
            step_deltas = [total_whl / horizon_days] * horizon_days
        else:
            step_deltas = whl_deltas_list

        step_preds = self.predict_step_ahead(
            current_retail=current_retail,
            current_wholesale=current_wholesale,
            steps_ahead=horizon_days,
            expected_wholesale_deltas=step_deltas
        )
        base_h_pred = float(step_preds[-1]) if step_preds else current_retail

        # Correct California Sales Tax Scaling: (Issue #607, T-8)
        # Sales tax applies only to the wholesale pass-through component (2.25% state + local district ~1.0% = 3.25%),
        # not on top of gross pump prices.
        if is_california and sales_tax_rate > 0.0:
            total_whl_delta = sum(step_deltas)
            wholesale_sales_tax_add = total_whl_delta * self.beta * sales_tax_rate
            base_h_pred += wholesale_sales_tax_add

        # Inject known forward statutory tax delta Delta tau_{t -> t+h}
        base_h_pred += forward_tax_delta

        return round(float(base_h_pred), 4)

    def get_asymmetry_diagnostics(self) -> Dict[str, Any]:
        """Returns structured econometric parameters, cointegration test, and asymmetry verification."""
        if not self.is_fitted:
            return {"status": "NOT_FITTED"}

        is_rockets_feathers = abs(self.alpha_neg) > abs(self.alpha_pos)
        asymmetry_ratio = round(abs(self.alpha_neg) / max(1e-5, abs(self.alpha_pos)), 3)

        return {
            "is_fitted": self.is_fitted,
            "beta": round(self.beta, 4),
            "pass_through_beta": round(self.beta, 4),
            "rack_spread": round(self.equilibrium_margin_c, 4),
            "equilibrium_rack_margin_c": round(self.equilibrium_margin_c, 4),
            "r2_cointegration": round(self.r2_cointegration, 4),
            "adf_stat": round(self.adf_stat, 4),
            "is_cointegrated": self.is_cointegrated,
            "mac_kinnon_critical_values": {"1%": -3.90, "5%": -3.34, "10%": -3.04},
            "alpha_pos": round(self.alpha_pos, 4),
            "alpha_positive_margin_recovery": round(self.alpha_pos, 4),
            "alpha_neg": round(self.alpha_neg, 4),
            "alpha_negative_cost_pass_through": round(self.alpha_neg, 4),
            "gamma_pos_coefs": [round(c, 4) for c in self.gamma_pos_coefs],
            "gamma_neg_coefs": [round(c, 4) for c in self.gamma_neg_coefs],
            "hac_se": [round(s, 4) for s in self.hac_se],
            "hac_t_stats": [round(t, 4) for t in self.hac_t_stats],
            "speed_ratio": asymmetry_ratio,
            "asymmetry_ratio_neg_over_pos": asymmetry_ratio,
            "rockets_and_feathers": is_rockets_feathers,
            "rockets_and_feathers_confirmed": is_rockets_feathers,
            "status": "VALID"
        }


def fit_regional_asymmetric_ecm(
    df: pd.DataFrame,
    region_name: str = "National",
    wholesale_col: str = "wholesale_price",
    retail_col: str = "retail_price",
    wholesale_lags: int = 3,
    retail_lags: int = 2
) -> Tuple[AsymmetricECM, Dict[str, Any]]:
    """
    Convenience wrapper to fit an AsymmetricECM for a specific region DataFrame.
    """
    model = AsymmetricECM(wholesale_lags=wholesale_lags, retail_lags=retail_lags)
    model.fit(df, wholesale_col=wholesale_col, retail_col=retail_col)
    diagnostics = model.get_asymmetry_diagnostics()
    diagnostics["region"] = region_name
    return model, diagnostics
