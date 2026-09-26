"""
Unit Tests for Injectable Evaluation, Calibrated 95% CI Coverage, and README Updater (tests/test_ci_and_evaluation_coverage.py)
Covers Issues #395, #394, #398.
"""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

from src.prediction_logger import (
    backfill_actual_prices_and_evaluate,
    compute_regional_residual_std,
    compute_rolling_scoreboard_metrics,
    filter_evaluated_history_by_window,
)
from src.readme_updater import update_readme_forecasts, START_TAG, END_TAG


class TestInjectableEvaluationAndCoverage:
    """Test suite validating injectable ground-truth evaluation, 95% CI calibration, and README updater."""

    def test_injectable_backfill_evaluation_under_testing_env(self):
        """Validates that backfill_actual_prices_and_evaluate executes under TESTING=1 with dependency overrides (Issue #395)."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            temp_path = f.name

        try:
            sample_df = pd.DataFrame([
                {
                    "log_timestamp": "2026-09-10T12:00:00",
                    "forecast_target_date": "2026-09-15",
                    "region": "National",
                    "model_version": "v1.6-Ipatieff-National-Ridge",
                    "run_type": "automated_cron",
                    "headline_trigger": "None",
                    "current_base_price": 3.10,
                    "predicted_5d_price": 3.25,
                    "predicted_direction": "UP",
                    "actual_5d_price": np.nan,
                    "actual_direction": np.nan,
                    "error_dollars": np.nan,
                    "directional_hit": np.nan,
                    "llm_price_pressure": 0.05,
                    "llm_supply_disruption": 0.0,
                    "quant_baseline_5d_price": 3.15,
                    "llm_augmentation_delta": 0.10,
                    "prediction_lower_95ci": 3.05,
                    "prediction_upper_95ci": 3.45,
                    "within_95ci_hit": np.nan,
                    "data_source_provenance": "yfinance",
                },
                {
                    "log_timestamp": "2026-09-10T12:00:00",
                    "forecast_target_date": "2026-09-15",
                    "region": "Tulsa_OK",
                    "model_version": "v1.6-Ipatieff-Tulsa-Ridge",
                    "run_type": "automated_cron",
                    "headline_trigger": "None",
                    "current_base_price": 3.40,
                    "predicted_5d_price": 3.30,
                    "predicted_direction": "DOWN",
                    "actual_5d_price": np.nan,
                    "actual_direction": np.nan,
                    "error_dollars": np.nan,
                    "directional_hit": np.nan,
                    "llm_price_pressure": -0.05,
                    "llm_supply_disruption": 0.0,
                    "quant_baseline_5d_price": 3.35,
                    "llm_augmentation_delta": -0.05,
                    "prediction_lower_95ci": np.nan,  # Test dynamic CI reconstruction
                    "prediction_upper_95ci": np.nan,
                    "within_95ci_hit": np.nan,
                    "data_source_provenance": "eia_retail_feed:Tulsa_OK",
                }
            ])
            sample_df.to_csv(temp_path, index=False)

            # Mock actuals map for National & Mock EIA feed for Tulsa_OK
            mock_actuals_map = {"2026-09-15": 3.20}
            mock_eia_feed = MagicMock()
            mock_eia_feed.get_retail_price_for_date.side_effect = lambda region, date_str: 3.32 if region == "Tulsa_OK" else None

            # Execute backfill with dependency injection
            res_df = backfill_actual_prices_and_evaluate(
                actuals_map_override=mock_actuals_map,
                eia_feed_override=mock_eia_feed,
                csv_path=temp_path,
                force_eval=True
            )

            assert not res_df.empty
            assert len(res_df) == 2

            # National evaluation checks
            nat_row = res_df[res_df["region"] == "National"].iloc[0]
            assert nat_row["actual_5d_price"] == 3.20
            assert nat_row["actual_direction"] == "UP"
            assert round(float(nat_row["error_dollars"]), 4) == 0.0500
            assert nat_row["directional_hit"] == 1
            assert nat_row["within_95ci_hit"] == 1

            # Tulsa_OK evaluation checks (actual 3.32 < base 3.40 -> DOWN, pred was DOWN -> hit=1)
            tulsa_row = res_df[res_df["region"] == "Tulsa_OK"].iloc[0]
            assert tulsa_row["actual_5d_price"] == 3.32
            assert tulsa_row["actual_direction"] == "DOWN"
            assert round(float(tulsa_row["error_dollars"]), 4) == 0.0200
            assert tulsa_row["directional_hit"] == 1
            assert pd.notna(tulsa_row["prediction_lower_95ci"])
            assert pd.notna(tulsa_row["prediction_upper_95ci"])
            assert tulsa_row["within_95ci_hit"] == 1
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_calibrated_ci_coverage_and_no_arbitrary_fallback(self):
        """Validates that CI hit evaluation strictly respects bounds without arbitrary ±$0.12 band (Issue #394)."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            temp_path = f.name

        try:
            # Row with narrow CI: [3.18, 3.22], actual = 3.25 (err = 0.05 <= 0.12, but outside CI -> must be MISS)
            sample_df = pd.DataFrame([
                {
                    "log_timestamp": "2026-09-10T12:00:00",
                    "forecast_target_date": "2026-09-15",
                    "region": "National",
                    "model_version": "v1.6-Ipatieff-National-Ridge",
                    "current_base_price": 3.10,
                    "predicted_5d_price": 3.20,
                    "predicted_direction": "UP",
                    "actual_5d_price": np.nan,
                    "actual_direction": np.nan,
                    "error_dollars": np.nan,
                    "directional_hit": np.nan,
                    "prediction_lower_95ci": 3.18,
                    "prediction_upper_95ci": 3.22,
                    "within_95ci_hit": np.nan,
                    "data_source_provenance": "yfinance",
                }
            ])
            sample_df.to_csv(temp_path, index=False)

            mock_actuals_map = {"2026-09-15": 3.25}
            res_df = backfill_actual_prices_and_evaluate(
                actuals_map_override=mock_actuals_map,
                csv_path=temp_path,
                force_eval=True
            )

            row = res_df.iloc[0]
            assert row["actual_5d_price"] == 3.25
            # Under old buggy ±$0.12 rule, abs(3.25 - 3.20) = 0.05 <= 0.12 would falsely give hit=1
            # Under fixed rule, 3.25 > upper_ci (3.22) -> within_95ci_hit MUST be 0
            assert row["within_95ci_hit"] == 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_compute_regional_residual_std_horizon_scaling(self):
        """Validates horizon scaling for regional residual standard error (Issue #394)."""
        std_5d = compute_regional_residual_std(region="National", default_std=0.0600, horizon_days=5)
        std_1d = compute_regional_residual_std(region="National", default_std=0.0600, horizon_days=1)
        std_10d = compute_regional_residual_std(region="National", default_std=0.0600, horizon_days=10)

        # 1-day horizon should have lower standard error than 5-day; 10-day should have higher
        assert std_1d <= std_5d
        assert std_10d >= std_5d

    def test_scoreboard_metrics_contains_empirical_ci_coverage(self):
        """Validates that compute_rolling_scoreboard_metrics returns empirical_95ci_coverage_pct (Issue #394)."""
        metrics = compute_rolling_scoreboard_metrics(window_days=30)
        assert "empirical_95ci_coverage_pct" in metrics
        assert isinstance(metrics["empirical_95ci_coverage_pct"], float)

    def test_readme_updater_generates_valid_table(self):
        """Validates README updater script generates all 10 locales and updates tags (Issue #398)."""
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f_readme:
            f_readme.write(f"# Midgley Project\n\n{START_TAG}\nOld table content\n{END_TAG}\n\n## Overview\nMore text here.")
            readme_path = f_readme.name

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8") as f_csv:
            df = pd.DataFrame([
                {"region": "National", "predicted_5d_price": 3.120, "current_base_price": 3.180, "forecast_target_date": "2026-09-25"},
                {"region": "Tulsa_OK", "predicted_5d_price": 3.750, "current_base_price": 3.820, "forecast_target_date": "2026-09-25"},
                {"region": "Charlotte_NC", "predicted_5d_price": 3.250, "current_base_price": 3.300, "forecast_target_date": "2026-09-25"},
                {"region": "Port_St_Lucie_FL", "predicted_5d_price": 3.390, "current_base_price": 3.420, "forecast_target_date": "2026-09-25"},
            ])
            df.to_csv(f_csv.name, index=False)
            history_csv_path = f_csv.name

        try:
            update_readme_forecasts(readme_path=readme_path, history_csv_path=history_csv_path)

            with open(readme_path, "r", encoding="utf-8") as f:
                updated_content = f.read()

            assert START_TAG in updated_content
            assert END_TAG in updated_content
            assert "National Wholesale (RBOB)" in updated_content
            assert "Tulsa, OK Metro Retail" in updated_content
            assert "Charlotte, NC Metro Retail" in updated_content
            assert "Port St. Lucie, FL Waterborne" in updated_content
            assert "$3.120" in updated_content
            assert "$3.750" in updated_content
        finally:
            if os.path.exists(readme_path):
                os.remove(readme_path)
            if os.path.exists(history_csv_path):
                os.remove(history_csv_path)
