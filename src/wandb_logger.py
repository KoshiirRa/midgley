"""
Weights & Biases (W&B) Telemetry & Experiment Tracking Module (src/wandb_logger.py)
Integrates wandb.ai for tracking quantitative model training runs, rolling MAE/RMSE metrics,
backtest loss curves, and weekly MLOps model drift audits (Issue #80).
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    import wandb
    HAS_WANDB = True
except ImportError:
    HAS_WANDB = False
    wandb = None

DEFAULT_PROJECT = "midgley-gas-forecasting"
DEFAULT_ENTITY = os.environ.get("WANDB_ENTITY")


def get_wandb_api_key() -> Optional[str]:
    """Retrieves W&B API key from environment or .env file."""
    api_key = os.environ.get("WANDB_API_KEY")
    if api_key:
        return api_key.strip()

    # Fallback to reading .env file if not in os.environ
    for env_path in [".env", os.path.join(os.path.dirname(__file__), "..", ".env")]:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("WANDB_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            if key:
                                return key
            except Exception as e:
                logger.debug(f"Notice reading {env_path} for W&B key: {e}")
    return None


def is_wandb_enabled() -> bool:
    """
    Checks if W&B logging is enabled and available.
    Returns False during test executions unless TEST_WANDB_FORCE=1.
    """
    if not HAS_WANDB:
        return False
    if os.environ.get("WANDB_MODE") == "disabled":
        return False
    if os.environ.get("TESTING") == "1" and os.environ.get("TEST_WANDB_FORCE") != "1":
        return False

    api_key = get_wandb_api_key()
    mode = os.environ.get("WANDB_MODE")
    return bool(api_key or mode in ("offline", "dryrun"))


def init_wandb_run(
    project: str = DEFAULT_PROJECT,
    job_type: str = "train",
    config: Optional[Dict[str, Any]] = None,
    name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
    mode: Optional[str] = None,
    reinit: bool = True
) -> Optional[Any]:
    """
    Initializes a Weights & Biases tracking run.
    Safely no-ops and returns None if W&B is not available or disabled.
    """
    if not is_wandb_enabled():
        logger.debug("W&B logging is disabled or unconfigured; skipping init_wandb_run.")
        return None

    api_key = get_wandb_api_key()
    if api_key and "WANDB_API_KEY" not in os.environ:
        os.environ["WANDB_API_KEY"] = api_key

    run_mode = mode or os.environ.get("WANDB_MODE")
    if not api_key and not run_mode:
        run_mode = "offline"

    try:
        run = wandb.init(
            project=project,
            entity=DEFAULT_ENTITY,
            job_type=job_type,
            config=config or {},
            name=name,
            tags=tags or ["midgley", "unleaded-gas", "forecasting"],
            notes=notes,
            mode=run_mode,
            reinit=reinit
        )
        logger.info(f"Initialized W&B run: {getattr(run, 'name', 'unnamed')} ({getattr(run, 'url', 'offline')})")
        return run
    except Exception as e:
        logger.warning(f"Failed to initialize W&B run: {e}")
        return None


def log_model_training_run(
    model_name: str,
    hyperparameters: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    feature_importances: Optional[Dict[str, float]] = None,
    run: Optional[Any] = None
) -> Optional[str]:
    """
    Logs quantitative model training hyperparameters, validation metrics, and feature importances.
    Returns the W&B run URL if available.
    """
    if not HAS_WANDB:
        return None

    active_run = run or getattr(wandb, "run", None)
    if not active_run:
        return None

    try:
        # 1. Log configuration / hyperparameters
        if hyperparameters:
            active_run.config.update({f"{model_name}_{k}": v for k, v in hyperparameters.items()}, allow_val_change=True)

        # 2. Log evaluation metrics
        if metrics:
            log_payload = {}
            for k, v in metrics.items():
                if isinstance(v, (int, float)) and not (isinstance(v, float) and (v != v)):  # check not NaN
                    log_payload[f"{model_name}/{k}"] = v
            if log_payload:
                active_run.log(log_payload)
                for k, v in log_payload.items():
                    active_run.summary[k] = v

        # 3. Log feature importances table
        if feature_importances:
            table_data = [[feat, float(val)] for feat, val in feature_importances.items()]
            table = wandb.Table(columns=["Feature", "Importance / Weight"], data=table_data)
            active_run.log({f"{model_name}/feature_importances": table})

        return getattr(active_run, "url", None)
    except Exception as e:
        logger.warning(f"Failed to log model training run to W&B for {model_name}: {e}")
        return None


def log_weekly_audit_run(
    audit_summary: Dict[str, Any],
    degradation_alerts: Optional[Dict[str, Any]] = None,
    window_days: int = 30,
    run: Optional[Any] = None,
    project: str = DEFAULT_PROJECT
) -> Dict[str, Any]:
    """
    Logs weekly MLOps audit metrics, rolling degradation status, and region-level error curves to W&B.
    """
    should_close_run = False
    active_run = run or getattr(wandb, "run", None)

    if not active_run and is_wandb_enabled():
        active_run = init_wandb_run(
            project=project,
            job_type="weekly_audit",
            config={
                "audit_window_days": window_days,
                "environment": os.environ.get("MIDGLEY_ENV", "production")
            },
            name=f"weekly-audit-{window_days}d",
            tags=["weekly-review", "mlops-audit", f"window-{window_days}d"]
        )
        should_close_run = True

    if not active_run:
        return {"status": "SKIPPED_OR_DISABLED", "run_url": None, "run_id": None}

    try:
        # 1. Log rolling MAE metrics
        nat_mae = audit_summary.get("national_mae") or audit_summary.get("nat_mae")
        tulsa_mae = audit_summary.get("tulsa_mae")
        
        metrics_payload = {
            "audit/window_days": window_days,
            "audit/is_degraded": bool(degradation_alerts.get("is_degraded")) if degradation_alerts else False
        }
        if nat_mae is not None:
            metrics_payload["audit/national_mae"] = float(nat_mae)
        if tulsa_mae is not None:
            metrics_payload["audit/tulsa_mae"] = float(tulsa_mae)

        # Region-specific rolling errors if present
        regions = audit_summary.get("regions", {})
        for reg_name, reg_data in regions.items():
            if isinstance(reg_data, dict):
                for m_k, m_v in reg_data.items():
                    if isinstance(m_v, (int, float)) and not (isinstance(m_v, float) and (m_v != m_v)):
                        metrics_payload[f"regions/{reg_name}_{m_k}"] = float(m_v)

        active_run.log(metrics_payload)
        for k, v in metrics_payload.items():
            active_run.summary[k] = v

        # 2. Log degradation alert table if alerts present
        if degradation_alerts and degradation_alerts.get("degraded_regions"):
            alert_rows = []
            for item in degradation_alerts["degraded_regions"]:
                alert_rows.append([
                    item.get("region", "Unknown"),
                    item.get("rolling_mae", 0.0),
                    item.get("threshold_mae", 0.0),
                    item.get("alert_level", "UNKNOWN"),
                    item.get("reason", "")
                ])
            alert_table = wandb.Table(
                columns=["Region", "Rolling MAE ($/gal)", "Threshold ($/gal)", "Alert Level", "Reason"],
                data=alert_rows
            )
            active_run.log({"audit/degraded_regions_table": alert_table})

        run_url = getattr(active_run, "url", None)
        run_id = getattr(active_run, "id", None)

        if should_close_run:
            finish_wandb_run(active_run)

        return {
            "status": "SUCCESS",
            "run_url": run_url,
            "run_id": run_id
        }
    except Exception as e:
        logger.warning(f"Error logging weekly audit to W&B: {e}")
        if should_close_run:
            finish_wandb_run(active_run)
        return {"status": "ERROR", "error": str(e), "run_url": None, "run_id": None}


def finish_wandb_run(run: Optional[Any] = None) -> Optional[str]:
    """Safely closes active W&B run and returns run URL."""
    if not HAS_WANDB:
        return None

    try:
        active_run = run or getattr(wandb, "run", None)
        url = getattr(active_run, "url", None) if active_run else None
        if active_run:
            active_run.finish()
        elif wandb:
            wandb.finish()
        return url
    except Exception as e:
        logger.debug(f"Notice closing W&B run: {e}")
        return None
