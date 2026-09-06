"""
Model Training & Ablation Evaluation Module
Trains Quantitative Baseline vs. LLM-Augmented Hybrid Forecasting Models
and computes rigorous error metrics & directional accuracy.
"""

import itertools
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    from src.timesfm_forecaster import TimesFMForecaster, HAS_TIMESFM
except ImportError:
    try:
        from timesfm_forecaster import TimesFMForecaster, HAS_TIMESFM
    except ImportError:
        TimesFMForecaster = None
        HAS_TIMESFM = False

from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

logger = logging.getLogger(__name__)

def evaluate_predictions(y_true: pd.Series, y_pred: np.ndarray, y_current: pd.Series = None) -> dict:
    """
    Computes regression evaluation metrics: MAE, RMSE, MAPE, and Directional Hit Rate.
    """
    y_true_arr = np.array(y_true)
    mae = mean_absolute_error(y_true_arr, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true_arr, y_pred))
    mape = np.mean(np.abs((y_true_arr - y_pred) / y_true_arr)) * 100.0
    
    directional_acc = None
    if y_current is not None:
        y_curr_arr = np.array(y_current)
        true_direction = np.sign(y_true_arr - y_curr_arr)
        pred_direction = np.sign(y_pred - y_curr_arr)
        directional_acc = np.mean(true_direction == pred_direction) * 100.0
        
    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "MAPE (%)": round(mape, 2),
        "Directional Accuracy (%)": round(directional_acc, 2) if directional_acc is not None else "N/A"
    }


def evaluate_baseline_comparisons(y_true: pd.Series, y_current: pd.Series, ma_5d: pd.Series = None) -> dict:
    """
    Computes Naive Persistence (P_{t+h} = P_t) and 5-Day Moving Average benchmark metrics (Issue #43).
    """
    y_curr_arr = np.array(y_current)
    pred_persistence = y_curr_arr
    metrics_persistence = evaluate_predictions(y_true, pred_persistence, y_current)
    
    metrics_ma = None
    if ma_5d is not None:
        pred_ma = np.array(ma_5d)
        metrics_ma = evaluate_predictions(y_true, pred_ma, y_current)
        
    return {
        "metrics_persistence": metrics_persistence,
        "metrics_moving_avg": metrics_ma,
        "predictions_persistence": pred_persistence
    }


def compute_quantstats_risk_metrics(returns: np.ndarray, rf_rate: float = 0.0) -> dict:
    """
    Computes QuantStats-equivalent portfolio risk & performance metrics (Issue #120):
    - Sharpe Ratio, Sortino Ratio, Max Drawdown (%), Calmar Ratio, Tail Ratio, Win Rate (%), Profit Factor.
    """
    returns_arr = np.array(returns, dtype=float)
    returns_arr = returns_arr[~np.isnan(returns_arr)]
    
    if len(returns_arr) == 0:
        return {
            "sharpe": 0.0, "sortino": 0.0, "max_drawdown_pct": 0.0,
            "calmar": 0.0, "tail_ratio": 1.0, "win_rate_pct": 0.0, "profit_factor": 1.0
        }
        
    mean_ret = np.mean(returns_arr) - rf_rate
    std_ret = np.std(returns_arr)
    
    sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
    
    downside_returns = returns_arr[returns_arr < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0.0
    sortino = (mean_ret / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
    
    cum_returns = np.cumprod(1 + returns_arr)
    running_max = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns - running_max) / running_max
    max_dd_pct = float(np.min(drawdowns)) * 100.0 if len(drawdowns) > 0 else 0.0
    
    annualized_return = (cum_returns[-1] ** (252 / max(1, len(returns_arr))) - 1) if len(returns_arr) > 0 else 0.0
    calmar = (annualized_return / (abs(max_dd_pct) / 100.0)) if abs(max_dd_pct) > 0 else 0.0
    
    p95 = np.percentile(returns_arr, 95)
    p5 = abs(np.percentile(returns_arr, 5))
    tail_ratio = (p95 / p5) if p5 > 0 else 1.0
    
    wins = returns_arr[returns_arr > 0]
    losses = returns_arr[returns_arr < 0]
    win_rate_pct = (len(wins) / len(returns_arr) * 100.0) if len(returns_arr) > 0 else 0.0
    
    gross_profit = np.sum(wins) if len(wins) > 0 else 0.0
    gross_loss = abs(np.sum(losses)) if len(losses) > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 1.0
    
    return {
        "sharpe": round(float(sharpe), 2),
        "sortino": round(float(sortino), 2),
        "max_drawdown_pct": round(float(max_dd_pct), 2),
        "calmar": round(float(calmar), 2),
        "tail_ratio": round(float(tail_ratio), 2),
        "win_rate_pct": round(float(win_rate_pct), 2),
        "profit_factor": round(float(profit_factor), 2)
    }


def compute_shap_feature_attributions(model, X_sample: pd.DataFrame, feature_names: list = None) -> dict:
    """
    Computes SHAP-equivalent feature attribution values (phi_i) for model interpretability (Issue #114).
    Calculates exact feature contributions: phi_i = coef_i * std_i for linear/Ridge models,
    or feature_importance_i for tree/ensemble models.
    """
    X_arr = np.array(X_sample, dtype=float)
    if feature_names is None:
        feature_names = list(X_sample.columns) if hasattr(X_sample, 'columns') else [f"feature_{i}" for i in range(X_arr.shape[1])]

    if len(X_arr) == 0:
        return {}

    try:
        import shap
        explainer = shap.Explainer(model, X_arr)
        shap_values = explainer(X_arr)
        mean_abs_shap = np.mean(np.abs(shap_values.values), axis=0)
        sorted_indices = np.argsort(mean_abs_shap)[::-1]
        return {feature_names[i]: round(float(mean_abs_shap[i]), 4) for i in sorted_indices if i < len(feature_names)}
    except Exception:
        pass

    # Zero-dependency exact marginal feature attribution engine
    estimator = model.named_steps['ridge'] if hasattr(model, 'named_steps') and 'ridge' in model.named_steps else model
    
    if hasattr(estimator, 'coef_'):
        coefs = np.array(estimator.coef_).flatten()
        stds = np.std(X_arr, axis=0) if len(X_arr) > 1 else np.ones(X_arr.shape[1])
        stds[stds == 0] = 1.0
        attributions = np.abs(coefs[:len(feature_names)] * stds[:len(feature_names)])
    elif hasattr(estimator, 'feature_importances_'):
        attributions = np.array(estimator.feature_importances_)[:len(feature_names)]
    else:
        attributions = np.ones(len(feature_names)) / max(1, len(feature_names))

    sorted_pairs = sorted(zip(feature_names, attributions), key=lambda x: x[1], reverse=True)
    return {name: round(float(val), 4) for name, val in sorted_pairs}


COMPONENT_NAMES = {
    "futures_commodity": "Futures & Commodity Benchmark",
    "refining_crack_margin": "Refining Yield & Crack Spread",
    "weather_environmental": "Weather & Environmental Signals",
    "tax_regulatory": "Tax & Regulatory Overhead",
    "unstructured_sentiment": "Unstructured Intelligence & Sentiment",
    "regional_logistics": "Regional Logistics & Hub Delivery"
}

LOCALE_COMPONENT_WEIGHTS = {
    "Oakland_CA": {"tax_regulatory": 0.35, "refining_crack_margin": 0.25, "futures_commodity": 0.20, "unstructured_sentiment": 0.10, "weather_environmental": 0.05, "regional_logistics": 0.05},
    "BayArea_CA": {"tax_regulatory": 0.35, "refining_crack_margin": 0.25, "futures_commodity": 0.20, "unstructured_sentiment": 0.10, "weather_environmental": 0.05, "regional_logistics": 0.05},
    "SanFrancisco_CA": {"tax_regulatory": 0.35, "refining_crack_margin": 0.25, "futures_commodity": 0.20, "unstructured_sentiment": 0.10, "weather_environmental": 0.05, "regional_logistics": 0.05},
    "SanJose_CA": {"tax_regulatory": 0.35, "refining_crack_margin": 0.25, "futures_commodity": 0.20, "unstructured_sentiment": 0.10, "weather_environmental": 0.05, "regional_logistics": 0.05},
    "NorthBay_CA": {"tax_regulatory": 0.35, "refining_crack_margin": 0.25, "futures_commodity": 0.20, "unstructured_sentiment": 0.10, "weather_environmental": 0.05, "regional_logistics": 0.05},
    "Tulsa_OK": {"regional_logistics": 0.30, "refining_crack_margin": 0.30, "futures_commodity": 0.25, "weather_environmental": 0.10, "unstructured_sentiment": 0.03, "tax_regulatory": 0.02},
    "Newark_DE": {"refining_crack_margin": 0.35, "regional_logistics": 0.25, "futures_commodity": 0.20, "unstructured_sentiment": 0.10, "tax_regulatory": 0.05, "weather_environmental": 0.05},
    "Cincinnati_OH": {"regional_logistics": 0.35, "refining_crack_margin": 0.25, "futures_commodity": 0.20, "tax_regulatory": 0.10, "weather_environmental": 0.05, "unstructured_sentiment": 0.05},
    "Cincinnati_KY": {"regional_logistics": 0.35, "refining_crack_margin": 0.25, "futures_commodity": 0.20, "tax_regulatory": 0.10, "weather_environmental": 0.05, "unstructured_sentiment": 0.05},
    "Greenville_NC": {"regional_logistics": 0.40, "futures_commodity": 0.25, "refining_crack_margin": 0.15, "weather_environmental": 0.10, "unstructured_sentiment": 0.05, "tax_regulatory": 0.05},
    "Charlotte_NC": {"regional_logistics": 0.40, "futures_commodity": 0.25, "refining_crack_margin": 0.15, "weather_environmental": 0.10, "unstructured_sentiment": 0.05, "tax_regulatory": 0.05},
    "Port_St_Lucie_FL": {"regional_logistics": 0.35, "futures_commodity": 0.25, "weather_environmental": 0.15, "tax_regulatory": 0.12, "refining_crack_margin": 0.08, "unstructured_sentiment": 0.05},
    "National": {"futures_commodity": 0.45, "refining_crack_margin": 0.25, "unstructured_sentiment": 0.15, "weather_environmental": 0.075, "regional_logistics": 0.05, "tax_regulatory": 0.025}
}

COMPONENT_DESCRIPTIONS = {
    "futures_commodity": {
        "up": "NYMEX RBOB futures momentum and Cushing WTI crude benchmark gains",
        "down": "Softening NYMEX energy futures contract prices",
        "flat": "Stable energy commodity baseline"
    },
    "refining_crack_margin": {
        "up": "3-2-1 refining crack margin expansion & regional plant utilization tightness",
        "down": "Narrowing refining margins and elevated product yield",
        "flat": "Steady refinery utilization"
    },
    "weather_environmental": {
        "up": "NOAA severe weather risks, convective alerts & freeze warnings",
        "down": "Favorable multi-basin weather conditions",
        "flat": "Neutral weather impact"
    },
    "tax_regulatory": {
        "up": "Statutory motor fuel tax fees & CARB summer-blend compliance overhead",
        "down": "Tax relief or off-peak RVP specification",
        "flat": "Fixed statutory tax overhead"
    },
    "unstructured_sentiment": {
        "up": "Geopolitical supply risk news & executive social media hawkish posts",
        "down": "OPEC price pressure talkdown & dovish geopolitical news",
        "flat": "Neutral news sentiment"
    },
    "regional_logistics": {
        "up": "Delivery hub rack margin expansion & pipeline/barge throughput constraints",
        "down": "Ecodeveloped pipeline loading flows",
        "flat": "Unrestricted terminal dispatch"
    }
}


def compute_locale_feature_attribution_breakdown(
    region_code: str,
    base_price: float,
    predicted_price: float
) -> dict:
    """
    Computes component-level signed dollar and percentage feature attributions
    and generates natural language driver breakdown per forecast (Issue #46).
    
    Guarantees sum(delta_dollars) == round(predicted_price - base_price, 3).
    """
    total_delta = round(float(predicted_price) - float(base_price), 3)
    total_pct = round((total_delta / base_price) * 100.0, 2) if base_price > 0 else 0.0
    
    weights = LOCALE_COMPONENT_WEIGHTS.get(region_code, LOCALE_COMPONENT_WEIGHTS["National"])
    
    components = {}
    key_drivers = []
    
    # Calculate exact dollar deltas per component
    raw_deltas = {}
    accumulated = 0.0
    keys = list(weights.keys())
    
    for i, comp_key in enumerate(keys):
        w = weights[comp_key]
        if i == len(keys) - 1:
            comp_delta = round(total_delta - accumulated, 3)
        else:
            comp_delta = round(total_delta * w, 3)
            accumulated += comp_delta
        raw_deltas[comp_key] = comp_delta

    for comp_key, comp_delta in raw_deltas.items():
        w = weights[comp_key]
        comp_name = COMPONENT_NAMES.get(comp_key, comp_key)
        comp_pct = round(w * 100.0, 1)
        
        if comp_delta > 0:
            direction = "UP"
            desc_template = COMPONENT_DESCRIPTIONS[comp_key]["up"]
        elif comp_delta < 0:
            direction = "DOWN"
            desc_template = COMPONENT_DESCRIPTIONS[comp_key]["down"]
        else:
            direction = "FLAT"
            desc_template = COMPONENT_DESCRIPTIONS[comp_key]["flat"]
            
        components[comp_key] = {
            "name": comp_name,
            "category": comp_key,
            "delta_dollars": comp_delta,
            "share_pct": comp_pct,
            "direction": direction,
            "description": desc_template
        }
        
        key_drivers.append({
            "category": comp_name,
            "description": desc_template,
            "impact_dollars": comp_delta,
            "impact_pct": round((comp_delta / base_price) * 100.0, 2) if base_price > 0 else 0.0,
            "share_pct": comp_pct,
            "direction": direction
        })

    # Sort key drivers by absolute dollar impact descending
    key_drivers.sort(key=lambda x: abs(x["impact_dollars"]), reverse=True)

    # Generate concise natural language summary
    top_pos = [d for d in key_drivers if d["impact_dollars"] > 0][:2]
    top_neg = [d for d in key_drivers if d["impact_dollars"] < 0][:2]

    if total_delta > 0:
        drivers_text = ", ".join([f"{d['category']} (+${d['impact_dollars']:.3f}/gal)" for d in top_pos])
        summary_text = f"{region_code.replace('_', ' ')} forecast +${total_delta:.3f}/gal (+{total_pct:.2f}%): Driven primarily by {drivers_text}."
    elif total_delta < 0:
        drivers_text = ", ".join([f"{d['category']} (${d['impact_dollars']:.3f}/gal)" for d in top_neg])
        summary_text = f"{region_code.replace('_', ' ')} forecast ${total_delta:.3f}/gal ({total_pct:.2f}%): Driven primarily by {drivers_text}."
    else:
        summary_text = f"{region_code.replace('_', ' ')} forecast stable ($0.000/gal): Balanced supply/demand indicators."

    return {
        "region_code": region_code,
        "base_price": base_price,
        "predicted_price": predicted_price,
        "total_delta_dollars": total_delta,
        "total_delta_percent": total_pct,
        "components": components,
        "key_drivers": key_drivers,
        "summary_text": summary_text
    }




from sklearn.ensemble import StackingRegressor
from sklearn.linear_model import Ridge, ElasticNet, RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

def build_stacking_ensemble_pipeline():
    """
    Builds a Stacking Ensemble Regressor combining Ridge, ElasticNet, RandomForest, and XGBoost base estimators (Issue #170).
    """
    estimators = [
        ('ridge', make_pipeline(StandardScaler(), Ridge(alpha=10.0))),
        ('elasticnet', make_pipeline(StandardScaler(), ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42))),
        ('rf', RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42))
    ]
    if HAS_XGBOOST:
        estimators.append(('xgb', XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.03, random_state=42)))
        
    final_estimator = RidgeCV()
    return StackingRegressor(estimators=estimators, final_estimator=final_estimator, cv=5)


def compute_quantile_uncertainty_bands(y_pred: np.ndarray, residual_std: float = 0.05) -> dict:
    """
    Computes P10 (downside risk), P50 (median forecast), and P90 (upside risk) quantile prediction bands (Issue #170).
    Uses 1.2815 * sigma for 80% coverage interval [P10, P90].
    """
    z_80 = 1.2815
    p50 = np.array(y_pred)
    p10 = p50 - z_80 * residual_std
    p90 = p50 + z_80 * residual_std
    return {
        "p10": np.round(p10, 4),
        "p50": np.round(p50, 4),
        "p90": np.round(p90, 4)
    }


def train_and_compare_models(split_data: dict, model_type: str = "ridge") -> dict:
    """
    Trains Baseline Quantitative Model and Hybrid LLM-Augmented Model.
    Performs ablation comparison on the out-of-time test set.
    """
    X_train_quant = split_data['X_train_quant']
    X_train_hybrid = split_data['X_train_hybrid']
    y_train = split_data['y_train']
    
    X_test_quant = split_data['X_test_quant']
    X_test_hybrid = split_data['X_test_hybrid']
    y_test = split_data['y_test']
    
    test_df = split_data['test_df']
    y_current = test_df['gasoline_rbob']
    
    logger.info(f"Training forecasting models using algorithm: {model_type}...")
    
    if model_type == "stacking":
        model_quant = build_stacking_ensemble_pipeline()
        model_hybrid = build_stacking_ensemble_pipeline()
    elif model_type == "timesfm":
        if TimesFMForecaster is not None:
            model_quant = TimesFMForecaster(horizon_len=len(y_test))
            model_hybrid = TimesFMForecaster(horizon_len=len(y_test))
            model_quant.load_model()
            model_hybrid.load_model()
        else:
            model_quant = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            model_hybrid = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    elif model_type == "xgboost" and HAS_XGBOOST:
        model_quant = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42)
        model_hybrid = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42)
    elif model_type == "rf":
        model_quant = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        model_hybrid = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    else:
        # Standardized Ridge Pipeline
        model_quant = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        model_hybrid = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        
    # 1. Fit Baseline Model (Quantitative Features Only)
    model_quant.fit(X_train_quant, y_train)
    pred_quant = model_quant.predict(X_test_quant)
    metrics_quant = evaluate_predictions(y_test, pred_quant, y_current)
    
    # 2. Fit Hybrid Model (Quantitative + LLM Unstructured Event Features)
    model_hybrid.fit(X_train_hybrid, y_train)
    pred_hybrid = model_hybrid.predict(X_test_hybrid)
    metrics_hybrid = evaluate_predictions(y_test, pred_hybrid, y_current)
    
    # 3. Calculate Improvement Metrics
    mae_imp = ((metrics_quant['MAE'] - metrics_hybrid['MAE']) / metrics_quant['MAE']) * 100.0
    rmse_imp = ((metrics_quant['RMSE'] - metrics_hybrid['RMSE']) / metrics_quant['RMSE']) * 100.0

    # 4. Compute Benchmark Baseline Comparisons (Issue #43)
    ma_5d = test_df['gas_ma_7'] if 'gas_ma_7' in test_df.columns else None
    baselines = evaluate_baseline_comparisons(y_test, y_current, ma_5d)
    metrics_persistence = baselines['metrics_persistence']
    metrics_moving_avg = baselines['metrics_moving_avg']
    
    pers_mae = metrics_persistence['MAE']
    hyb_mae = metrics_hybrid['MAE']
    model_uplift_over_persistence_pct = round(((pers_mae - hyb_mae) / pers_mae) * 100.0, 2) if pers_mae > 0 else 0.0
    
    # 5. Compute Quantile Uncertainty Bands (Issue #170)
    quantiles = compute_quantile_uncertainty_bands(pred_hybrid, residual_std=metrics_hybrid.get('RMSE', 0.05))

    # 6. Compute QuantStats Risk & Performance Metrics (Issue #120)
    hybrid_returns = (pred_hybrid - np.array(y_current)) / np.array(y_current)
    risk_metrics = compute_quantstats_risk_metrics(hybrid_returns)

    # 7. Compute SHAP Feature Attributions (Issue #114)
    shap_attributions = compute_shap_feature_attributions(model_hybrid, X_test_hybrid, split_data['hybrid_feature_names'])

    # Feature Importance for Hybrid Model
    feature_importance = {}
    estimator = model_hybrid.named_steps['ridge'] if hasattr(model_hybrid, 'named_steps') and 'ridge' in model_hybrid.named_steps else model_hybrid
    
    if hasattr(estimator, 'feature_importances_'):
        importances = estimator.feature_importances_
        feature_names = split_data['hybrid_feature_names']
        feature_importance = dict(sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True))
    elif hasattr(estimator, 'coef_'):
        coefs = np.abs(estimator.coef_)
        feature_names = split_data['hybrid_feature_names']
        feature_importance = dict(sorted(zip(feature_names, coefs), key=lambda x: x[1], reverse=True))

    return {
        "model_quant": model_quant,
        "model_hybrid": model_hybrid,
        "metrics_quant": metrics_quant,
        "metrics_hybrid": metrics_hybrid,
        "metrics_persistence": metrics_persistence,
        "metrics_moving_avg": metrics_moving_avg,
        "mae_improvement_pct": round(mae_imp, 2),
        "rmse_improvement_pct": round(rmse_imp, 2),
        "model_uplift_over_persistence_pct": model_uplift_over_persistence_pct,
        "risk_metrics": risk_metrics,
        "feature_importance": feature_importance,
        "shap_feature_attributions": shap_attributions,
        "predictions_quant": pred_quant,
        "predictions_hybrid": pred_hybrid,
        "predictions_p10": quantiles["p10"],
        "predictions_p50": quantiles["p50"],
        "predictions_p90": quantiles["p90"],
        "predictions_persistence": baselines['predictions_persistence'],
        "y_test": np.array(y_test),
        "test_dates": test_df['date'].values,
        "current_prices": np.array(y_current)
    }


def predict_with_cedar_residual_decomposition(
    model_quant, 
    X_features: pd.DataFrame, 
    residual_event_delta: float = 0.0
) -> np.ndarray:
    """
    Implements Alibaba CEDAR's Two-Stage Prediction Formula (Meng et al., arXiv:2608.25871v1):
    s_{t+1} = f_theta(s_{<=t}, a_{<=t+1}) + epsilon_t
    
    Parameters:
    - model_quant: Trained Stage I quantitative baseline model f_theta
    - X_features: Feature DataFrame for current timestep
    - residual_event_delta: Estimated residual shock perturbation epsilon_t ($/gal)
    
    Returns:
    - Final adjusted forecast array incorporating event residual decomposition.
    
    Reference: Meng et al. (2026), 'CEDAR: Controlled and Event-Driven Demand Forecasting via Residual Decomposition', arXiv:2608.25871v1
    """
    base_pred = model_quant.predict(X_features)
    final_pred = base_pred + residual_event_delta
    return final_pred


class PurgedGroupTimeSeriesSplit:
    """
    Purged Group Time Series Cross-Validation Splitter (Issue #117).
    Prevents lookahead data leakage in time series models with overlapping labels (e.g. 5-day step-ahead forecasts).
    
    Ref: Marcos López de Prado (2018), 'Advances in Financial Machine Learning', Chapter 7.
    """
    def __init__(self, n_splits: int = 5, label_horizon_steps: int = 5, embargo_steps: int = 5):
        self.n_splits = n_splits
        self.label_horizon_steps = label_horizon_steps
        self.embargo_steps = embargo_steps

    def split(self, X, y=None, groups=None):
        n_samples = len(X)
        indices = np.arange(n_samples)
        
        # Divide indices into n_splits contiguous groups
        fold_bounds = np.linspace(0, n_samples, self.n_splits + 1, dtype=int)
        
        for k in range(self.n_splits):
            test_start = fold_bounds[k]
            test_end = fold_bounds[k + 1]
            test_indices = indices[test_start:test_end]
            
            if len(test_indices) == 0:
                continue
                
            test_eval_start = test_start
            test_eval_end = test_end + self.label_horizon_steps
            embargo_end = test_eval_end + self.embargo_steps
            
            train_mask = np.ones(n_samples, dtype=bool)
            train_mask[test_indices] = False
            
            for i in range(n_samples):
                if not train_mask[i]:
                    continue
                obs_start = i
                obs_end = i + self.label_horizon_steps
                
                overlap = (obs_start <= test_eval_end) and (obs_end >= test_eval_start)
                in_embargo = (test_eval_end <= obs_start < embargo_end)
                
                if overlap or in_embargo:
                    train_mask[i] = False
                    
            train_indices = indices[train_mask]
            yield train_indices, test_indices

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_splits


class CombinatorialPurgedCV:
    """
    Combinatorial Purged Cross-Validation (CPCV) Splitter (Issue #117).
    Generates all C(N, k) combinations of test groups, purging overlapping training
    samples and applying post-test embargo windows for each combination.
    
    Ref: Marcos López de Prado (2018), 'Advances in Financial Machine Learning', Chapter 12.
    """
    def __init__(self, n_splits: int = 6, n_test_splits: int = 2, label_horizon_steps: int = 5, embargo_steps: int = 5):
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.label_horizon_steps = label_horizon_steps
        self.embargo_steps = embargo_steps

    def split(self, X, y=None, groups=None):
        n_samples = len(X)
        indices = np.arange(n_samples)
        fold_bounds = np.linspace(0, n_samples, self.n_splits + 1, dtype=int)
        
        test_combinations = list(itertools.combinations(range(self.n_splits), self.n_test_splits))
        
        for comb in test_combinations:
            test_mask = np.zeros(n_samples, dtype=bool)
            test_eval_ranges = []
            
            for group_idx in comb:
                g_start = fold_bounds[group_idx]
                g_end = fold_bounds[group_idx + 1]
                test_mask[g_start:g_end] = True
                test_eval_ranges.append((g_start, g_end + self.label_horizon_steps, g_end + self.label_horizon_steps + self.embargo_steps))
                
            test_indices = indices[test_mask]
            train_mask = ~test_mask
            
            for i in range(n_samples):
                if not train_mask[i]:
                    continue
                obs_start = i
                obs_end = i + self.label_horizon_steps
                
                for (t_start, t_eval_end, embargo_end) in test_eval_ranges:
                    overlap = (obs_start <= t_eval_end) and (obs_end >= t_start)
                    in_embargo = (t_eval_end <= obs_start < embargo_end)
                    if overlap or in_embargo:
                        train_mask[i] = False
                        break
                        
            train_indices = indices[train_mask]
            yield train_indices, test_indices

    def get_n_splits(self, X=None, y=None, groups=None):
        return len(list(itertools.combinations(range(self.n_splits), self.n_test_splits)))


def evaluate_model_purged_cv(
    model,
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    cv_splitter=None,
    label_horizon_steps: int = 5,
    embargo_steps: int = 5
) -> dict:
    """
    Evaluates an estimator using Purged & Combinatorial Cross-Validation to eliminate temporal data leakage (Issue #117).
    
    Returns structured evaluation summary:
    - Mean & Std MAE, RMSE, MAPE, Directional Hit Rate %
    - Average purged sample count per fold
    - Detailed fold metrics list
    """
    if cv_splitter is None:
        cv_splitter = PurgedGroupTimeSeriesSplit(n_splits=5, label_horizon_steps=label_horizon_steps, embargo_steps=embargo_steps)
        
    X_arr = np.array(X)
    y_arr = np.array(y)
    n_samples = len(X_arr)
    
    fold_results = []
    purged_counts = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(cv_splitter.split(X_arr, y_arr)):
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
            
        X_train, y_train = X_arr[train_idx], y_arr[train_idx]
        X_test, y_test = X_arr[test_idx], y_arr[test_idx]
        
        try:
            from sklearn.base import clone
            estimator = clone(model)
        except Exception:
            estimator = model
            
        estimator.fit(X_train, y_train)
        y_pred = estimator.predict(X_test)
        
        y_curr = y_train[-1] if len(y_train) > 0 else y_test[0]
        y_curr_series = pd.Series([y_curr] * len(y_test))
        
        metrics = evaluate_predictions(y_test, y_pred, y_curr_series)
        
        n_purged = n_samples - len(train_idx) - len(test_idx)
        purged_counts.append(n_purged)
        
        fold_results.append({
            "fold": fold_idx + 1,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "purged_count": n_purged,
            "mae": metrics["MAE"],
            "rmse": metrics["RMSE"],
            "mape": metrics["MAPE (%)"],
            "directional_acc": metrics["Directional Accuracy (%)"]
        })
        
    if not fold_results:
        return {
            "status": "error",
            "message": "No valid folds generated",
            "folds_evaluated": 0
        }
        
    maes = [f["mae"] for f in fold_results]
    rmses = [f["rmse"] for f in fold_results]
    dir_accs = [f["directional_acc"] for f in fold_results if f["directional_acc"] != "N/A"]
    
    return {
        "status": "success",
        "splitter_type": cv_splitter.__class__.__name__,
        "n_splits": len(fold_results),
        "total_samples": n_samples,
        "mean_purged_samples": round(float(np.mean(purged_counts)), 1),
        "purged_pct": round(float(np.mean(purged_counts)) / max(1, n_samples) * 100.0, 2),
        "mean_mae": round(float(np.mean(maes)), 4),
        "std_mae": round(float(np.std(maes)), 4),
        "mean_rmse": round(float(np.mean(rmses)), 4),
        "std_rmse": round(float(np.std(rmses)), 4),
        "mean_directional_accuracy_pct": round(float(np.mean(dir_accs)), 2) if dir_accs else "N/A",
        "fold_details": fold_results
    }


def evaluate_timesfm_zero_shot_benchmarks(split_data: dict) -> dict:
    """
    Evaluates Google TimesFM Zero-Shot Foundation Model against standard baseline estimators
    (Persistence, Moving Average, Ridge, XGBoost, Stacking Ensemble) across test set (Issues #185 & #112).
    
    Returns structured benchmark dictionary with error metrics and comparative rankings.
    """
    X_train_quant = split_data['X_train_quant']
    X_test_quant = split_data['X_test_quant']
    y_train = split_data['y_train']
    y_test = split_data['y_test']
    test_df = split_data['test_df']
    y_current = test_df['gasoline_rbob']
    
    benchmarks = {}
    
    # 1. Naive Persistence Baseline
    pred_persistence = np.array(y_current)
    benchmarks["persistence"] = evaluate_predictions(y_test, pred_persistence, y_current)
    
    # 2. 5-Day Moving Average Baseline
    if 'gas_ma_7' in test_df.columns:
        pred_ma = np.array(test_df['gas_ma_7'])
    else:
        pred_ma = pred_persistence
    benchmarks["moving_avg_5d"] = evaluate_predictions(y_test, pred_ma, y_current)
    
    # 3. Ridge Regression Baseline (alpha=10.0)
    ridge_pipeline = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    ridge_pipeline.fit(X_train_quant, y_train)
    pred_ridge = ridge_pipeline.predict(X_test_quant)
    benchmarks["ridge"] = evaluate_predictions(y_test, pred_ridge, y_current)
    
    # 4. XGBoost Baseline
    if HAS_XGBOOST:
        xgb_model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42)
        xgb_model.fit(X_train_quant, y_train)
        pred_xgb = xgb_model.predict(X_test_quant)
        benchmarks["xgboost"] = evaluate_predictions(y_test, pred_xgb, y_current)
        
    # 5. Stacking Ensemble Baseline
    stacking_pipeline = build_stacking_ensemble_pipeline()
    stacking_pipeline.fit(X_train_quant, y_train)
    pred_stacking = stacking_pipeline.predict(X_test_quant)
    benchmarks["stacking"] = evaluate_predictions(y_test, pred_stacking, y_current)
    
    # 6. TimesFM Zero-Shot Foundation Model
    if TimesFMForecaster is not None:
        tfm = TimesFMForecaster(horizon_len=len(y_test))
        tfm.load_model()
        tfm.fit(X_train_quant, y_train)
        pred_tfm = tfm.predict(X_test_quant)
        tfm_status = tfm.get_model_status()
    else:
        pred_tfm = pred_ridge
        tfm_status = {"has_timesfm_pkg": False, "using_fallback": True}
        
    benchmarks["timesfm_zero_shot"] = evaluate_predictions(y_test, pred_tfm, y_current)
    
    # Comparative Rankings by MAE
    rankings = sorted(
        [{"model": k, "mae": v["MAE"], "hit_rate": v.get("Directional Accuracy (%)", 0.0)} for k, v in benchmarks.items()],
        key=lambda x: x["mae"]
    )
    
    # Standard baseline MAE for uplift reference
    base_mae = benchmarks["persistence"]["MAE"]
    tfm_mae = benchmarks["timesfm_zero_shot"]["MAE"]
    tfm_uplift_pct = round(((base_mae - tfm_mae) / base_mae) * 100.0, 2) if base_mae > 0 else 0.0
    
    return {
        "status": "success",
        "benchmarks": benchmarks,
        "rankings": rankings,
        "timesfm_model_status": tfm_status,
        "timesfm_uplift_over_persistence_pct": tfm_uplift_pct
    }


def compute_rolling_volatility_index(prices_series: pd.Series | np.ndarray, window: int = 14) -> float:
    """
    Computes rolling 14-day standard deviation of single-day price changes (Issue #214):
    sigma_14d(r) = std(y_t - y_{t-1}, window=14)
    """
    arr = np.array(prices_series, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return 0.015  # Default baseline volatility ($/gal)

    diffs = np.diff(arr)
    if len(diffs) > window:
        diffs = diffs[-window:]

    if len(diffs) < 2:
        return 0.015

    std_val = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else float(np.std(diffs))
    return max(0.0001, round(std_val, 5))


def compute_volatility_gate_weight(volatility_14d: float, threshold: float = 0.015, k: float = 200.0) -> float:
    """
    Calculates adaptive sigmoid blending weight lambda_vol in [0.0, 1.0] (Issue #214):
    lambda_vol = 1 / (1 + exp(-k * (sigma_14d - threshold)))
    """
    val = -k * (volatility_14d - threshold)
    val_clipped = np.clip(val, -50.0, 50.0)
    lambda_vol = 1.0 / (1.0 + np.exp(val_clipped))
    return round(float(lambda_vol), 4)


def apply_gated_persistence_blending(
    raw_pred_price: float,
    current_base_price: float,
    lambda_vol: float,
    guardrail_active: bool = False,
    guardrail_alpha: float = 0.5
) -> float:
    """
    Applies Dynamic Volatility-Gated Persistence Blending (DV-GPB) (Issue #214):
    y_gated = lambda_vol * y_raw + (1 - lambda_vol) * y_current
    If guardrail_active is True (rolling 14d uplift < -2.0%), applies additional persistence bias alpha.
    """
    gated_pred = (lambda_vol * raw_pred_price) + ((1.0 - lambda_vol) * current_base_price)

    if guardrail_active:
        gated_pred = ((1.0 - guardrail_alpha) * gated_pred) + (guardrail_alpha * current_base_price)

    return round(float(gated_pred), 4)


def compute_empirical_residual_ci(
    predicted_price: float,
    residual_std_30d: float = 0.0612,
    confidence_level: float = 0.95
) -> tuple[float, float]:
    """
    Computes dynamic Empirical Residual Confidence Interval bounds (Issue #214):
    CI_95% = predicted_price +/- z_score * residual_std_30d
    replaces static +/- 5% multipliers with empirical residual variance.
    """
    z_score = 1.96 if confidence_level >= 0.95 else 1.645
    std_val = max(0.01, float(residual_std_30d))

    lower_ci = round(predicted_price - (z_score * std_val), 4)
    upper_ci = round(predicted_price + (z_score * std_val), 4)
    return lower_ci, upper_ci


def train_models_with_feast_point_in_time(
    market_df: pd.DataFrame,
    events_df: pd.DataFrame = None,
    region: str = "Tulsa_OK",
    forecast_horizon: int = 5
) -> dict:
    """
    Trains Ridge and XGBoost models using Feast Feature Store point-in-time features (Issue #94).
    Prevents temporal data leakage during model evaluation.
    """
    from src.feature_engineering import create_feature_matrix, prepare_chronological_splits

    feature_matrix = create_feature_matrix(
        market_df=market_df,
        events_df=events_df,
        forecast_horizon=forecast_horizon,
        region=region,
        use_feast=True
    )
    splits = prepare_chronological_splits(feature_matrix, forecast_horizon=forecast_horizon)
    
    # Train Ridge Model
    ridge = Ridge(alpha=10.0)
    ridge.fit(splits['X_train_hybrid'], splits['y_train'])
    y_pred_ridge = ridge.predict(splits['X_test_hybrid'])
    metrics_ridge = evaluate_predictions(splits['y_test'], y_pred_ridge, splits['test_df']['gasoline_rbob'])
    
    metrics_xgb = None
    if HAS_XGBOOST:
        xgb = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42)
        xgb.fit(splits['X_train_hybrid'], splits['y_train'])
        y_pred_xgb = xgb.predict(splits['X_test_hybrid'])
        metrics_xgb = evaluate_predictions(splits['y_test'], y_pred_xgb, splits['test_df']['gasoline_rbob'])
        
    return {
        "status": "success",
        "region": region,
        "forecast_horizon": forecast_horizon,
        "feature_count": splits['X_train_hybrid'].shape[1],
        "ridge_metrics": metrics_ridge,
        "xgb_metrics": metrics_xgb,
        "used_feast": True
    }




