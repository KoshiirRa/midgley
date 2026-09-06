"""
Dynamic Data Grouping Domain Adaptation (DDG-DA) Module
Implements dynamic market regime clustering and sample/estimator re-weighting to combat concept drift
and non-stationary market distribution shifts in fuel commodity price forecasting.
Inspired by Microsoft Research Qlib DDG-DA architecture.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

logger = logging.getLogger(__name__)


class DDGDAAdapter:
    """
    Dynamic Data Grouping Domain Adaptation (DDG-DA) Engine.
    Identifies market regimes (domains) in fuel time-series features and dynamically
    re-weights training instances and ensemble estimators based on current market domain similarity.
    """

    def __init__(self, n_domains: int = 3, similarity_kernel_gamma: float = 1.0):
        self.n_domains = n_domains
        self.gamma = similarity_kernel_gamma
        self.domain_model: Optional[GaussianMixture] = None
        self.recent_domain_centroid: Optional[np.ndarray] = None

    def fit_domain_grouping(self, X: pd.DataFrame) -> np.ndarray:
        """
        Clusters historical feature matrix into n_domains market regimes (DDG phase).
        Returns array of domain cluster labels.
        """
        X_num = X.select_dtypes(include=[np.number]).fillna(0.0)
        if len(X_num) < self.n_domains * 5:
            # Insufficient samples for clustering, default single domain
            return np.zeros(len(X), dtype=int)

        try:
            self.domain_model = GaussianMixture(
                n_components=min(self.n_domains, max(1, len(X_num) // 10)),
                random_state=42,
                covariance_type="diag"
            )
            labels = self.domain_model.fit(X_num).predict(X_num)
            logger.info(f"DDG Market Domain Grouping fitted across {len(X)} samples into {self.n_domains} regimes.")
            return labels
        except Exception as e:
            logger.warning(f"GMM domain grouping failed ({e}). Falling back to K-Means.")
            km = KMeans(n_components=min(self.n_domains, max(1, len(X_num) // 10)), random_state=42, n_init=10)
            return km.fit_predict(X_num)

    def calculate_sample_domain_weights(self, X_train: pd.DataFrame, recent_window_size: int = 10) -> np.ndarray:
        """
        Calculates Domain Adaptation (DA) sample weights based on Gaussian RBF kernel similarity
        between historical training samples and the most recent market regime window.
        """
        X_num = X_train.select_dtypes(include=[np.number]).fillna(0.0).values
        if len(X_num) == 0:
            return np.ones(len(X_train))

        # Recent market window centroid
        recent_window = X_num[-min(recent_window_size, len(X_num)):]
        recent_centroid = np.mean(recent_window, axis=0)
        self.recent_domain_centroid = recent_centroid

        # Feature standardization for distance calculation
        std_devs = np.std(X_num, axis=0) + 1e-8
        norm_diffs = (X_num - recent_centroid) / std_devs

        # Squared Euclidean distance to recent market centroid
        sq_dists = np.sum(norm_diffs ** 2, axis=1)

        # Gaussian RBF Kernel similarity weight: w_i = exp(-gamma * sq_dist / d)
        d_dim = X_num.shape[1]
        weights = np.exp(-self.gamma * sq_dists / max(1.0, d_dim))

        # Normalize weights to mean=1.0 so sample weight scale matches standard objective function
        weights = weights / (np.mean(weights) + 1e-8)
        return weights

    def fit_predict_adapted(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        model_type: str = "ridge",
        recent_window_size: int = 10
    ) -> np.ndarray:
        """
        Fits domain-adapted base estimator using DA sample weights and predicts on X_test.
        """
        sample_weights = self.calculate_sample_domain_weights(X_train, recent_window_size=recent_window_size)
        X_tr_num = X_train.select_dtypes(include=[np.number]).fillna(0.0)
        X_te_num = X_test.select_dtypes(include=[np.number]).fillna(0.0)

        # Align columns
        missing_cols = set(X_tr_num.columns) - set(X_te_num.columns)
        for c in missing_cols:
            X_te_num[c] = 0.0
        X_te_num = X_te_num[X_tr_num.columns]

        if model_type.lower() == "ridge":
            estimator = Ridge(alpha=10.0)
            estimator.fit(X_tr_num, y_train, sample_weight=sample_weights)
            return estimator.predict(X_te_num)
        elif model_type.lower() == "xgboost" and HAS_XGBOOST:
            estimator = XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
            estimator.fit(X_tr_num, y_train, sample_weight=sample_weights)
            return estimator.predict(X_te_num)
        elif model_type.lower() == "random_forest":
            estimator = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
            estimator.fit(X_tr_num, y_train, sample_weight=sample_weights)
            return estimator.predict(X_te_num)
        else:
            # Fallback Ridge
            estimator = Ridge(alpha=10.0)
            estimator.fit(X_tr_num, y_train, sample_weight=sample_weights)
            return estimator.predict(X_te_num)
