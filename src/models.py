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
        "mae_improvement_pct": round(mae_imp, 2),
        "rmse_improvement_pct": round(rmse_imp, 2),
        "feature_importance": feature_importance,
        "predictions_quant": pred_quant,
        "predictions_hybrid": pred_hybrid,
        "y_test": np.array(y_test),
        "test_dates": test_df['date'].values,
        "current_prices": np.array(y_current)
    }
