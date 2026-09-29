"""
MinT Hierarchical Reconciliation Engine & Empirical Bayes Parameter Shrinkage (src/hierarchical_engine.py)
Implements:
1. Geographic Hierarchy Aggregation Matrix S across National -> PADD -> Metro tiers.
2. Minimum Trace (MinT) Optimal Reconciliation (Wickramasuriya et al. 2019).
3. Empirical Bayes / Mixed-Effects Parameter Shrinkage for thin-data metros.
4. Unified Vectorized Multi-Metro Batch Forecasting.
(Issue #450)
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Standard Bottom-Level Metro Calibration Hubs (m = 9)
BOTTOM_LEVEL_METROS = [
    "Tulsa_OK",
    "Newark_DE",
    "Cincinnati_OH",
    "Cincinnati_KY",
    "Greenville_NC",
    "Charlotte_NC",
    "Port_St_Lucie_FL",
    "Oakland_CA",
    "BayArea_CA"
]

# Intermediate PADD / Regional Clusters (k = 4)
PADD_CLUSTERS = {
    "PADD_1B": ["Newark_DE"],
    "PADD_1C": ["Greenville_NC", "Charlotte_NC", "Port_St_Lucie_FL"],
    "PADD_2": ["Tulsa_OK", "Cincinnati_OH", "Cincinnati_KY"],
    "PADD_5": ["Oakland_CA", "BayArea_CA"]
}

TOTAL_HIERARCHICAL_NODES = ["National"] + list(PADD_CLUSTERS.keys()) + BOTTOM_LEVEL_METROS


def build_aggregation_matrix(
    bottom_nodes: List[str] = BOTTOM_LEVEL_METROS,
    padd_clusters: Dict[str, List[str]] = PADD_CLUSTERS,
    weights: Optional[Dict[str, float]] = None
) -> Tuple[np.ndarray, List[str]]:
    """
    Constructs the summing matrix S (n x m) mapping m bottom-level nodes to n total hierarchical nodes (Issue #450).
    n = 1 (National) + k (PADDs) + m (Metros).
    
    Structure:
    - Row 0: Top node (National = sum of all bottom nodes)
    - Rows 1..k: Middle nodes (PADD clusters = sum of component metros)
    - Rows k+1..n: Bottom nodes (Identity matrix I_m)
    """
    m = len(bottom_nodes)
    node_to_idx = {name: i for i, name in enumerate(bottom_nodes)}
    
    padd_names = list(padd_clusters.keys())
    k = len(padd_names)
    n = 1 + k + m

    all_node_names = ["National"] + padd_names + list(bottom_nodes)
    S = np.zeros((n, m), dtype=float)

    # 1. Top row: National sum
    for j in range(m):
        w = weights.get(bottom_nodes[j], 1.0 / m) if weights else (1.0 / m)
        S[0, j] = w

    # 2. Middle rows: PADD clusters
    for i, padd in enumerate(padd_names, start=1):
        comp_metros = padd_clusters[padd]
        for m_name in comp_metros:
            if m_name in node_to_idx:
                col_idx = node_to_idx[m_name]
                w = weights.get(m_name, 1.0 / len(comp_metros)) if weights else (1.0 / len(comp_metros))
                S[i, col_idx] = w

    # 3. Bottom rows: Identity matrix
    for j in range(m):
        S[1 + k + j, j] = 1.0

    return S, all_node_names


def reconcile_mint(
    base_forecasts: np.ndarray,
    S: np.ndarray,
    error_covariance: Optional[np.ndarray] = None,
    shrinkage_lambda: float = 0.05
) -> np.ndarray:
    """
    Solves Minimum Trace (MinT) Optimal Reconciliation (Wickramasuriya et al. 2019) (Issue #450).
    Formula:
        \\tilde{y} = S * (S^T * W^{-1} * S)^{-1} * S^T * W^{-1} * \\hat{y}
    
    Uses Ledoit-Wolf style shrinkage on covariance W to guarantee non-singular, stable inversion:
        W_{shrink} = (1 - lambda) * W + lambda * diag(W)
    """
    y_hat = np.asarray(base_forecasts, dtype=float).reshape(-1, 1)
    n, m = S.shape

    if error_covariance is None:
        # Standard OLS / Identity weighting fallback
        W = np.eye(n, dtype=float)
    else:
        W = np.asarray(error_covariance, dtype=float)
        if W.shape != (n, n):
            W = np.eye(n, dtype=float)
        # Apply diagonal shrinkage to guarantee positive-definiteness
        diag_W = np.diag(np.diag(W))
        W = (1.0 - shrinkage_lambda) * W + shrinkage_lambda * diag_W

    try:
        W_inv = np.linalg.pinv(W)
        St_Winv = S.T @ W_inv
        middle_inv = np.linalg.pinv(St_Winv @ S)
        # Reconciliation operator P = (S^T W^{-1} S)^{-1} S^T W^{-1}
        P = middle_inv @ St_Winv
        # Reconciled bottom-level forecasts b_tilde
        b_tilde = P @ y_hat
        # Reconciled all-level forecasts y_tilde = S @ b_tilde
        y_tilde = S @ b_tilde
        return y_tilde.flatten()
    except Exception as e:
        logger.warning(f"MinT matrix solver fallback notice ({e}); returning base forecasts.")
        return y_hat.flatten()


def empirical_bayes_shrinkage_regression(
    X: np.ndarray,
    y: np.ndarray,
    prior_weights: Optional[np.ndarray] = None,
    shrinkage_strength: float = 0.15
) -> np.ndarray:
    """
    Fits Empirical Bayes / Mixed-Effects Shrinkage Regressor (Issue #450).
    Shrinks metro-level coefficients theta_r toward prior/national coefficients theta_0:
        theta_r = (X_r^T X_r + lambda * I)^{-1} (X_r^T y_r + lambda * theta_0)
    """
    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n_samples, p_features = X_arr.shape

    if prior_weights is None:
        prior_weights = np.zeros(p_features, dtype=float)
    else:
        prior_weights = np.asarray(prior_weights, dtype=float)
        if len(prior_weights) != p_features:
            prior_weights = np.zeros(p_features, dtype=float)

    XtX = X_arr.T @ X_arr
    lambda_I = (shrinkage_strength * n_samples) * np.eye(p_features)

    # Solve penalized ridge-shrinkage system
    A = XtX + lambda_I
    b = X_arr.T @ y_arr + lambda_I @ prior_weights
    try:
        theta_eb = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        theta_eb = np.linalg.pinv(A) @ b

    return theta_eb


class MinTHierarchicalEngine:
    """
    Unified MinT Hierarchical Forecasting Engine across National, PADD and Metro levels (Issue #450).
    """

    def __init__(
        self,
        bottom_nodes: List[str] = BOTTOM_LEVEL_METROS,
        padd_clusters: Dict[str, List[str]] = PADD_CLUSTERS,
        weights: Optional[Dict[str, float]] = None
    ):
        self.bottom_nodes = list(bottom_nodes)
        self.padd_clusters = dict(padd_clusters)
        self.S, self.node_names = build_aggregation_matrix(self.bottom_nodes, self.padd_clusters, weights)
        self.node_to_idx = {name: i for i, name in enumerate(self.node_names)}

    def reconcile_forecast_dict(
        self,
        forecast_dict: Dict[str, float],
        error_covariance: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Takes unconstrained base forecasts for any subset of nodes, fills missing upper nodes
        via structural aggregation, and returns exactly sum-consistent reconciled forecasts.
        """
        n = len(self.node_names)
        base_vec = np.zeros(n, dtype=float)

        # Fill bottom nodes
        for m_name in self.bottom_nodes:
            idx = self.node_to_idx[m_name]
            base_vec[idx] = float(forecast_dict.get(m_name, 3.50))

        # Fill PADD clusters (if missing, aggregate from bottom nodes)
        for padd, metros in self.padd_clusters.items():
            idx = self.node_to_idx[padd]
            if padd in forecast_dict:
                base_vec[idx] = float(forecast_dict[padd])
            else:
                m_vals = [base_vec[self.node_to_idx[m]] for m in metros if m in self.node_to_idx]
                base_vec[idx] = float(np.mean(m_vals)) if m_vals else 3.50

        # Fill National top node
        nat_idx = self.node_to_idx["National"]
        if "National" in forecast_dict:
            base_vec[nat_idx] = float(forecast_dict["National"])
        else:
            base_vec[nat_idx] = float(np.mean(base_vec[1 + len(self.padd_clusters):]))

        # Reconcile via MinT
        reconciled_vec = reconcile_mint(base_vec, self.S, error_covariance=error_covariance)

        return {
            name: round(float(reconciled_vec[i]), 4)
            for i, name in enumerate(self.node_names)
        }
