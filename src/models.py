"""
Model Training & Ablation Evaluation Module
Trains Quantitative Baseline vs. LLM-Augmented Hybrid Forecasting Models
and computes rigorous error metrics & directional accuracy.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

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


from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

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
    
    if model_type == "xgboost" and HAS_XGBOOST:
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
        "feature_importance": feature_importance,
        "predictions_quant": pred_quant,
        "predictions_hybrid": pred_hybrid,
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

