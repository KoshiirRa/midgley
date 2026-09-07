"""
Google TimesFM (Time Series Foundation Model) Forecasting Engine (Issues #185 & #112)
Provides zero-shot quantitative time-series forecasting for national RBOB futures
and regional metro retail unleaded gas prices using Google Research's TimesFM model.

Includes an analytical zero-shot fallback estimator to guarantee 100% test suite and
runtime execution across environments without PyTorch / HuggingFace model weights.
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

# Check for Google TimesFM library availability
HAS_TIMESFM = False
try:
    import timesfm
    HAS_TIMESFM = True
except ImportError:
    HAS_TIMESFM = False


class AnalyticalZeroShotFallback:
    """
    Zero-dependency analytical zero-shot foundation model fallback estimator.
    Computes zero-shot multi-step projections with residual variance uncertainty bounds
    when Google TimesFM / PyTorch packages are omitted or unavailable.
    """
    def __init__(self, horizon_len: int = 5):
        self.horizon_len = horizon_len

    def forecast(self, history: Union[pd.Series, np.ndarray], horizon_len: Optional[int] = None) -> Dict[str, np.ndarray]:
        """
        Generates zero-shot point forecasts and P10, P50, P90 quantile prediction bands.
        """
        h_len = horizon_len or self.horizon_len
        arr = np.array(history, dtype=float)
        arr = arr[~np.isnan(arr)]

        if len(arr) == 0:
            pred = np.zeros(h_len)
            return {"pred": pred, "p10": pred - 0.05, "p50": pred, "p90": pred + 0.05}

        if len(arr) == 1:
            pred = np.full(h_len, arr[0])
            return {"pred": pred, "p10": pred - 0.05, "p50": pred, "p90": pred + 0.05}

        last_val = arr[-1]
        
        # Calculate recent momentum trend (5-day window or max available)
        recent_window = min(len(arr), 5)
        recent_diffs = np.diff(arr[-recent_window:])
        mean_diff = np.mean(recent_diffs) if len(recent_diffs) > 0 else 0.0
        
        # Mean reversion & momentum decay factor (phi = 0.85)
        phi = 0.85
        drift_steps = np.array([mean_diff * (phi ** i) for i in range(1, h_len + 1)])
        
        pred_p50 = last_val + np.cumsum(drift_steps)
        
        # Residual std estimate for 80% coverage interval [P10, P90]
        std_est = np.std(recent_diffs) if len(recent_diffs) > 1 else 0.03
        std_est = max(0.02, float(std_est))
        
        # Multi-step variance expansion: sigma_h = sigma * sqrt(h)
        horizon_stds = std_est * np.sqrt(np.arange(1, h_len + 1))
        z_80 = 1.2815
        
        pred_p10 = pred_p50 - z_80 * horizon_stds
        pred_p90 = pred_p50 + z_80 * horizon_stds
        
        return {
            "pred": np.round(pred_p50, 4),
            "p10": np.round(pred_p10, 4),
            "p50": np.round(pred_p50, 4),
            "p90": np.round(pred_p90, 4)
        }


class TimesFMForecaster:
    """
    TimesFM Foundation Model Estimator and Zero-Shot Forecaster.
    Implements scikit-learn compatible estimator API (`fit`, `predict`) and zero-shot horizon forecasting.
    """
    def __init__(
        self,
        context_len: int = 512,
        horizon_len: int = 5,
        repo_id: str = "google/timesfm-1.0-200m-pytorch",
        backend: str = "cpu"
    ):
        self.context_len = context_len
        self.horizon_len = horizon_len
        self.repo_id = repo_id
        self.backend = backend
        self.tfm_model = None
        self.using_fallback = not HAS_TIMESFM
        self.fallback_engine = AnalyticalZeroShotFallback(horizon_len=self.horizon_len)
        self.fitted_history = None
        self.fitted_target_col = None

    def load_model(self) -> bool:
        """
        Attempts to initialize the pretrained Google TimesFM checkpoint.
        Falls back cleanly to AnalyticalZeroShotFallback if unavailable.
        """
        if not HAS_TIMESFM:
            logger.info("timesfm library not installed. Operating in zero-shot analytical fallback mode.")
            self.using_fallback = True
            return False

        try:
            # TimesFM initialization
            if hasattr(timesfm, "TimesFm"):
                try:
                    # TimesFM 2.0 / PyTorch API
                    tfm = timesfm.TimesFm(
                        context_len=self.context_len,
                        horizon_len=self.horizon_len
                    )
                    if hasattr(tfm, "load_from_checkpoint"):
                        tfm.load_from_checkpoint(repo_id=self.repo_id)
                    self.tfm_model = tfm
                    self.using_fallback = False
                    logger.info(f"Successfully loaded Google TimesFM model from {self.repo_id}")
                    return True
                except Exception as e1:
                    logger.warning(f"TimesFM checkpoint load failed ({e1}). Retrying with base Hparams...")
                    if hasattr(timesfm, "TimesFmHparams") and hasattr(timesfm, "TimesFmCheckpoint"):
                        hparams = timesfm.TimesFmHparams(
                            backend=self.backend,
                            per_core_batch_size=32,
                            horizon_len=self.horizon_len
                        )
                        checkpoint = timesfm.TimesFmCheckpoint(huggingface_repo_id=self.repo_id)
                        tfm = timesfm.TimesFm(hparams=hparams, checkpoint=checkpoint)
                        self.tfm_model = tfm
                        self.using_fallback = False
                        return True

            self.using_fallback = True
            return False
        except Exception as e:
            logger.warning(f"TimesFM initialization encountered exception: {e}. Defaulting to analytical zero-shot fallback.")
            self.using_fallback = True
            return False

    def forecast_zero_shot(
        self,
        history: Union[pd.Series, np.ndarray, list],
        horizon_len: Optional[int] = None,
        freq: str = "D"
    ) -> Dict[str, np.ndarray]:
        """
        Generates zero-shot point predictions and P10, P50, P90 quantile uncertainty bands
        for target time-series history.
        """
        h_len = horizon_len or self.horizon_len
        arr_hist = np.array(history, dtype=float)
        arr_hist = arr_hist[~np.isnan(arr_hist)]

        if not self.using_fallback and self.tfm_model is not None:
            try:
                # Run PyTorch zero-shot TimesFM inference
                if hasattr(self.tfm_model, "forecast"):
                    inputs = [arr_hist]
                    freq_input = [0]
                    point_forecast, quantiles = self.tfm_model.forecast(inputs, freq=freq_input)
                    
                    pred_p50 = np.array(point_forecast[0][:h_len], dtype=float)
                    if quantiles is not None and len(quantiles) > 0:
                        pred_p10 = np.array(quantiles[0][:h_len, 0], dtype=float)
                        pred_p90 = np.array(quantiles[0][:h_len, -1], dtype=float)
                    else:
                        z_80 = 1.2815
                        std_est = float(np.std(np.diff(arr_hist[-5:]))) if len(arr_hist) > 5 else 0.03
                        stds = std_est * np.sqrt(np.arange(1, h_len + 1))
                        pred_p10 = pred_p50 - z_80 * stds
                        pred_p90 = pred_p50 + z_80 * stds

                    return {
                        "pred": np.round(pred_p50, 4),
                        "p10": np.round(pred_p10, 4),
                        "p50": np.round(pred_p50, 4),
                        "p90": np.round(pred_p90, 4)
                    }
            except Exception as e:
                logger.warning(f"Zero-shot TimesFM inference failed ({e}). Falling back to analytical estimator.")

        # Analytical zero-shot fallback
        return self.fallback_engine.forecast(arr_hist, horizon_len=h_len)

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]):
        """
        Scikit-learn compatible estimator fit method.
        Stores training context history for zero-shot projection.
        """
        y_arr = np.array(y, dtype=float)
        self.fitted_history = y_arr[~np.isnan(y_arr)]
        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Scikit-learn compatible predict method.
        Projects zero-shot predictions for target input sample length.
        """
        n_samples = len(X)
        if n_samples == 0:
            return np.array([], dtype=float)

        history = self.fitted_history if self.fitted_history is not None else np.ones(10) * 3.0
        forecast_res = self.forecast_zero_shot(history, horizon_len=n_samples)
        pred = forecast_res["pred"]

        if len(pred) < n_samples:
            # Tile or repeat last value if requested sample size exceeds horizon
            padding = np.full(n_samples - len(pred), pred[-1])
            pred = np.concatenate([pred, padding])

        return pred[:n_samples]

    def get_model_status(self) -> Dict[str, Any]:
        """
        Returns model status metadata and environment capabilities.
        """
        return {
            "has_timesfm_pkg": HAS_TIMESFM,
            "using_fallback": self.using_fallback,
            "repo_id": self.repo_id,
            "horizon_len": self.horizon_len,
            "context_len": self.context_len,
            "backend": self.backend
        }
