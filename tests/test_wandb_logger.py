"""
Tests for Weights & Biases (W&B) Telemetry & Experiment Tracking Module (tests/test_wandb_logger.py)
Validates W&B run initialization, metric logging, graceful offline fallbacks, and weekly audit runs (Issue #80).
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd

from src.wandb_logger import (
    get_wandb_api_key,
    is_wandb_enabled,
    init_wandb_run,
    log_model_training_run,
    log_weekly_audit_run,
    finish_wandb_run,
    HAS_WANDB
)
from src.models import train_and_compare_models


class TestWandbLogger(unittest.TestCase):

    def setUp(self):
        self.orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_get_wandb_api_key_from_env(self):
        os.environ["WANDB_API_KEY"] = "wandb_test_key_12345"
        key = get_wandb_api_key()
        self.assertEqual(key, "wandb_test_key_12345")

    def test_is_wandb_enabled_disabled_by_default_in_tests(self):
        os.environ["TESTING"] = "1"
        os.environ.pop("TEST_WANDB_FORCE", None)
        self.assertFalse(is_wandb_enabled())

    def test_is_wandb_enabled_with_force_and_key(self):
        if not HAS_WANDB:
            self.skipTest("wandb is not installed")
        os.environ["TESTING"] = "1"
        os.environ["TEST_WANDB_FORCE"] = "1"
        os.environ["WANDB_API_KEY"] = "wandb_test_key_12345"
        os.environ["WANDB_MODE"] = "offline"
        self.assertTrue(is_wandb_enabled())

    @patch("src.wandb_logger.wandb")
    def test_init_wandb_run_mocked(self, mock_wandb):
        mock_run = MagicMock()
        mock_run.name = "test-run"
        mock_run.url = "https://wandb.ai/mock/run-123"
        mock_wandb.init.return_value = mock_run

        with patch("src.wandb_logger.is_wandb_enabled", return_value=True):
            run = init_wandb_run(project="test-project", job_type="train", name="test-run")
            self.assertIsNotNone(run)
            mock_wandb.init.assert_called_once()

    @patch("src.wandb_logger.wandb")
    def test_log_model_training_run_mocked(self, mock_wandb):
        mock_run = MagicMock()
        mock_run.config = {}
        mock_run.summary = {}
        mock_run.url = "https://wandb.ai/mock/run-123"

        metrics = {
            "MAE": 0.045,
            "RMSE": 0.055,
            "Directional Accuracy (%)": 85.0
        }
        feature_importances = {
            "wti_crude": 0.35,
            "crack_spread_321": 0.25,
            "cboe_ovx": 0.15
        }

        with patch("src.wandb_logger.HAS_WANDB", True):
            url = log_model_training_run(
                model_name="hybrid_ridge",
                hyperparameters={"alpha": 10.0},
                metrics=metrics,
                feature_importances=feature_importances,
                run=mock_run
            )
            self.assertEqual(url, "https://wandb.ai/mock/run-123")
            mock_run.log.assert_called()

    @patch("src.wandb_logger.wandb")
    def test_log_weekly_audit_run_mocked(self, mock_wandb):
        mock_run = MagicMock()
        mock_run.summary = {}
        mock_run.url = "https://wandb.ai/mock/audit-456"
        mock_run.id = "audit-456"

        audit_summary = {
            "national_mae": 0.085,
            "tulsa_mae": 0.350,
            "regions": {
                "Tulsa_OK": {"mae": 0.35, "hit_rate": 80.0},
                "Newark_NJ": {"mae": 0.42, "hit_rate": 75.0}
            }
        }
        degradation_alerts = {
            "is_degraded": False,
            "degraded_regions": []
        }

        res = log_weekly_audit_run(
            audit_summary=audit_summary,
            degradation_alerts=degradation_alerts,
            window_days=30,
            run=mock_run
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["run_url"], "https://wandb.ai/mock/audit-456")

    @patch("src.wandb_logger.wandb")
    def test_finish_wandb_run(self, mock_wandb):
        mock_run = MagicMock()
        mock_run.url = "https://wandb.ai/mock/run-done"

        with patch("src.wandb_logger.HAS_WANDB", True):
            url = finish_wandb_run(mock_run)
            self.assertEqual(url, "https://wandb.ai/mock/run-done")
            mock_run.finish.assert_called_once()

    def test_train_and_compare_models_with_mocked_wandb(self):
        # Generate dummy data for fast regression verification
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        X_train_quant = pd.DataFrame({"feat1": np.random.randn(20), "feat2": np.random.randn(20)})
        X_train_hybrid = pd.DataFrame({"feat1": np.random.randn(20), "feat2": np.random.randn(20), "event1": np.random.rand(20)})
        y_train = pd.Series(2.5 + 0.1 * np.random.randn(20))

        X_test_quant = pd.DataFrame({"feat1": np.random.randn(10), "feat2": np.random.randn(10)})
        X_test_hybrid = pd.DataFrame({"feat1": np.random.randn(10), "feat2": np.random.randn(10), "event1": np.random.rand(10)})
        y_test = pd.Series(2.5 + 0.1 * np.random.randn(10))

        test_df = pd.DataFrame({
            "date": dates[-10:],
            "gasoline_rbob": y_test.values,
            "gas_ma_7": y_test.values
        })

        split_data = {
            "X_train_quant": X_train_quant,
            "X_train_hybrid": X_train_hybrid,
            "y_train": y_train,
            "X_test_quant": X_test_quant,
            "X_test_hybrid": X_test_hybrid,
            "y_test": y_test,
            "test_df": test_df,
            "hybrid_feature_names": ["feat1", "feat2", "event1"]
        }

        mock_run = MagicMock()
        mock_run.config = {}
        mock_run.summary = {}
        mock_run.url = "https://wandb.ai/mock/train-run"

        res = train_and_compare_models(split_data, model_type="ridge", log_wandb=True, wandb_run=mock_run)
        self.assertIn("MAE", res["metrics_hybrid"])
        self.assertEqual(res["wandb_run_url"], "https://wandb.ai/mock/train-run")


if __name__ == "__main__":
    unittest.main()
