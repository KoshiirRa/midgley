"""
Asymmetric Error-Correction Model (ECM) for Retail-Wholesale Pass-Through (src/asymmetric_ecm.py)
Implements cointegration-based asymmetric distributed-lag error-correction modeling ('rockets and feathers')
between wholesale spot/futures RBOB and regional retail pump prices. (Issue #402)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)


class AsymmetricECM:
    """
    Asymmetric Error-Correction Model estimating long-run rack margin equilibrium
    and asymmetric adjustment speeds for rising vs falling wholesale gasoline costs.
    
    Long-Run Cointegration:
      Retail_t = beta * Wholesale_t + c + u_t
      z_t = Retail_t - beta * Wholesale_t - c
      
    Asymmetric Error Correction:
      z_t^+ = max(0, z_t)  (Retail above equilibrium / high margin)
      z_t^- = min(0, z_t)  (Retail below equilibrium / squeezed margin)
      
      Delta Retail_t = alpha^+ * z_{t-1}^+ + alpha^- * z_{t-1}^- 
                     + sum_{i=0}^k gamma_i * Delta Wholesale_{t-i} 
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
        
        # Short-run parameters
        self.alpha_pos: float = -0.05   # Speed of downward adjustment (feathers)
        self.alpha_neg: float = -0.15   # Speed of upward adjustment (rockets)
        self.gamma_coefs: List[float] = []
        self.delta_coefs: List[float] = []
        self.intercept_dynamic: float = 0.0
        
        self.is_fitted: bool = False
        self.last_retail_price: float = 3.50
        self.last_wholesale_price: float = 2.85
        self.last_residual: float = 0.0

    def fit(
        self,
        retail_data: Union[pd.Series, pd.DataFrame],
        wholesale_series: Optional[pd.Series] = None,
        retail_col: str = "retail_price",
        wholesale_col: str = "wholesale_price"
    ) -> "AsymmetricECM":
        """
        Fits two-step Engle-Granger Asymmetric Error-Correction Model.
        Accepts either two pd.Series (retail, wholesale) or a pd.DataFrame with column names.
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
        df["z_lag1"] = df["z"].shift(1)
        
        # Asymmetric Split: z^+ and z^-
        df["z_pos_lag1"] = np.maximum(0.0, df["z_lag1"])
        df["z_neg_lag1"] = np.minimum(0.0, df["z_lag1"])
        
        # Step 2: Differencing & Lags for Dynamic Regression
        df["d_retail"] = df["retail"].diff()
        df["d_wholesale"] = df["wholesale"].diff()
        
        # Feature columns for dynamic regression
        feature_cols = ["z_pos_lag1", "z_neg_lag1", "d_wholesale"]
        
        for i in range(1, self.n_lags_wholesale + 1):
            col_name = f"d_wholesale_lag{i}"
            df[col_name] = df["d_wholesale"].shift(i)
            feature_cols.append(col_name)
            
        for j in range(1, self.n_lags_retail + 1):
            col_name = f"d_retail_lag{j}"
            df[col_name] = df["d_retail"].shift(j)
            feature_cols.append(col_name)
            
        df_reg = df.dropna().copy()
        
        if len(df_reg) < 20:
            raise ValueError("Insufficient degrees of freedom after lagging for dynamic ECM regression.")
            
        X_dyn = df_reg[feature_cols].values
        y_dyn = df_reg["d_retail"].values
        
        dyn_model = LinearRegression(fit_intercept=True)
        dyn_model.fit(X_dyn, y_dyn)
        
        self.intercept_dynamic = float(dyn_model.intercept_)
        self.alpha_pos = float(dyn_model.coef_[0])
        self.alpha_neg = float(dyn_model.coef_[1])
        self.gamma_coefs = [float(dyn_model.coef_[2])] + [float(c) for c in dyn_model.coef_[3:3 + self.n_lags_wholesale]]
        self.delta_coefs = [float(c) for c in dyn_model.coef_[3 + self.n_lags_wholesale:]]
        
        self.last_retail_price = float(df["retail"].iloc[-1])
        self.last_wholesale_price = float(df["wholesale"].iloc[-1])
        self.last_residual = float(df["z"].iloc[-1])
        self.is_fitted = True
        
        logger.info(
            f"AsymmetricECM Fitted: Equilibrium Rack Margin=${self.equilibrium_margin_c:.3f}/gal, "
            f"Beta={self.beta:.3f}, Alpha^+={self.alpha_pos:.4f}, Alpha^-={self.alpha_neg:.4f}"
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
        Iteratively forecasts retail prices h-steps ahead under asymmetric error correction.
        """
        if not self.is_fitted:
            raise RuntimeError("AsymmetricECM must be fitted before calling predict_step_ahead().")

        total_steps = steps if steps is not None else steps_ahead

        # Handle DataFrame input for current_retail
        if isinstance(current_retail, pd.DataFrame):
            last_ret = float(current_retail["retail_price"].iloc[-1]) if "retail_price" in current_retail.columns else float(current_retail.iloc[-1, 0])
            last_whl = float(current_retail["wholesale_price"].iloc[-1]) if "wholesale_price" in current_retail.columns else float(current_retail.iloc[-1, 1])
            ret_price = last_ret
            whl_price = last_whl
            
            # If current_wholesale is a list/array of future wholesale levels
            if isinstance(current_wholesale, (list, np.ndarray, pd.Series)):
                future_whl = list(current_wholesale)
                whl_deltas = [future_whl[0] - last_whl] + [future_whl[i] - future_whl[i - 1] for i in range(1, len(future_whl))]
                expected_wholesale_deltas = whl_deltas
        else:
            ret_price = float(current_retail) if current_retail is not None else self.last_retail_price
            whl_price = float(current_wholesale) if (current_wholesale is not None and isinstance(current_wholesale, (int, float))) else self.last_wholesale_price

        if expected_wholesale_deltas is None:
            expected_wholesale_deltas = [0.0] * total_steps
        elif len(expected_wholesale_deltas) < total_steps:
            expected_wholesale_deltas.extend([0.0] * (total_steps - len(expected_wholesale_deltas)))

        forecasts = []
        d_whl_hist = [0.0] * (self.n_lags_wholesale + 1)
        d_ret_hist = [0.0] * self.n_lags_retail

        for step in range(total_steps):
            d_w = expected_wholesale_deltas[step]
            whl_price += d_w
            d_whl_hist[0] = d_w
            
            # Compute current cointegration disequilibrium
            z = ret_price - (self.beta * whl_price + self.equilibrium_margin_c)
            z_pos = max(0.0, z)
            z_neg = min(0.0, z)
            
            # Predict expected retail delta
            d_retail_pred = (
                self.intercept_dynamic +
                (self.alpha_pos * z_pos) +
                (self.alpha_neg * z_neg) +
                sum(g * dw for g, dw in zip(self.gamma_coefs, d_whl_hist)) +
                sum(d * dr for d, dr in zip(self.delta_coefs, d_ret_hist))
            )
            
            ret_price += d_retail_pred
            forecasts.append(round(float(ret_price), 4))
            
            # Shift histories for next recursive step
            d_ret_hist = [d_retail_pred] + d_ret_hist[:-1]
            d_whl_hist = [d_w] + d_whl_hist[:-1]

        if isinstance(current_retail, pd.DataFrame):
            return pd.Series(forecasts)
        return forecasts

    def get_asymmetry_diagnostics(self) -> Dict[str, Any]:
        """Returns structured econometric parameters and asymmetry verification."""
        if not self.is_fitted:
            return {"status": "NOT_FITTED"}

        # In empirical literature, rockets and feathers holds when |alpha_neg| > |alpha_pos|
        is_rockets_feathers = abs(self.alpha_neg) > abs(self.alpha_pos)
        asymmetry_ratio = round(abs(self.alpha_neg) / max(1e-5, abs(self.alpha_pos)), 3)

        return {
            "is_fitted": self.is_fitted,
            "beta": round(self.beta, 4),
            "pass_through_beta": round(self.beta, 4),
            "rack_spread": round(self.equilibrium_margin_c, 4),
            "equilibrium_rack_margin_c": round(self.equilibrium_margin_c, 4),
            "r2_cointegration": round(self.r2_cointegration, 4),
            "alpha_pos": round(self.alpha_pos, 4),
            "alpha_positive_margin_recovery": round(self.alpha_pos, 4),
            "alpha_neg": round(self.alpha_neg, 4),
            "alpha_negative_cost_pass_through": round(self.alpha_neg, 4),
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
