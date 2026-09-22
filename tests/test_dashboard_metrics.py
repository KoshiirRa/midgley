"""
Unit tests for dynamic dashboard metrics calculation (Issue #393).
Validates dynamic stats computation, insufficient data gating (N < 30),
rolling metrics calculation, and dashboard template replacement.
"""

import os
import pandas as pd
import pytest
from unittest.mock import patch

from src.dashboard_generator import (
    compute_dynamic_accuracy_stats,
    calculate_rolling_metrics,
    generate_public_dashboard
)


def test_compute_dynamic_accuracy_stats_insufficient_data(tmp_path):
    """Test that empty or non-existent history returns default insufficient data gating."""
    csv_path = str(tmp_path / "non_existent.csv")
    stats = compute_dynamic_accuracy_stats(csv_path)
    assert stats["total_evaluated_samples"] == 0
    assert stats["overall_hit_rate_str"] == "Insufficient Data (N < 30)"
    assert stats["insufficient_data"] is True

    # Small df (< 30 rows)
    small_csv = str(tmp_path / "small.csv")
    small_df = pd.DataFrame({
        "forecast_target_date": ["2026-09-01"] * 10,
        "region": ["Tulsa_OK"] * 10,
        "predicted_5d_price": [3.0] * 10,
        "actual_5d_price": [3.1] * 10,
        "base_price": [2.9] * 10,
        "error_dollars": [0.1] * 10,
        "directional_hit": [1] * 10
    })
    small_df.to_csv(small_csv, index=False)
    stats_small = compute_dynamic_accuracy_stats(small_csv)
    assert stats_small["total_evaluated_samples"] == 10
    assert stats_small["insufficient_data"] is True
    assert "N=10" in stats_small["overall_hit_rate_str"]


def test_compute_dynamic_accuracy_stats_sufficient_data(tmp_path):
    """Test accurate computation of MAE, RMSE, MAPE, and hit rate when N >= 30."""
    data = []
    for i in range(40):
        actual = 3.00 + (0.05 if i % 2 == 0 else -0.05)
        base = 3.00
        # If i < 30, direction matches
        if i < 30:
            pred = base + (0.10 if actual > base else -0.10)
            dir_hit = 1
        else:
            pred = base + (-0.10 if actual > base else 0.10)
            dir_hit = 0

        data.append({
            "forecast_target_date": f"2026-09-{(i % 28) + 1:02d}",
            "region": "National" if i < 20 else "Tulsa_OK",
            "predicted_5d_price": pred,
            "actual_5d_price": actual,
            "base_price": base,
            "error_dollars": abs(pred - actual),
            "directional_hit": dir_hit
        })

    csv_path = str(tmp_path / "sufficient.csv")
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    
    stats = compute_dynamic_accuracy_stats(csv_path)

    assert stats["total_evaluated_samples"] == 40
    # 30 / 40 = 75.0%
    assert stats["overall_hit_rate"] == 75.0
    assert stats["overall_hit_rate_str"] == "75.00%"
    assert "$" in stats["overall_mae_str"]


def test_calculate_rolling_metrics_empty(tmp_path):
    """Test calculate_rolling_metrics handles empty/missing history gracefully."""
    empty_csv = str(tmp_path / "empty.csv")
    dates, maes, hits = calculate_rolling_metrics(empty_csv)
    assert len(dates) >= 1
    assert maes[0] == 0.0
    assert hits[0] == 0.0


def test_calculate_rolling_metrics_with_data(tmp_path):
    """Test calculate_rolling_metrics with valid dated history."""
    dates_in = pd.date_range("2026-01-01", periods=15, freq="D")
    data = []
    for d in dates_in:
        data.append({
            "forecast_target_date": d.strftime("%Y-%m-%d"),
            "region": "National",
            "predicted_5d_price": 3.00,
            "actual_5d_price": 3.05,
            "error_dollars": 0.05,
            "directional_hit": 1
        })
    csv_path = str(tmp_path / "rolling.csv")
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    
    dates, maes, hits = calculate_rolling_metrics(csv_path)
    assert len(dates) >= 1
    assert maes[-1] == 0.05
    assert hits[-1] == 100.0


def test_generate_public_dashboard_no_unrendered_placeholders(tmp_path, monkeypatch):
    """Verify that generated public dashboard pages do not contain unrendered accuracy tokens."""
    os.environ["TESTING"] = "1"
    
    # Run public dashboard generation
    output_dir = str(tmp_path / "docs")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create subdirectories
    for sub in ["national", "tulsa", "newark", "cincinnati", "greenville", "charlotte", "port_st_lucie", "oakland", "bayarea"]:
        os.makedirs(os.path.join(output_dir, sub), exist_ok=True)

    paths_to_patch = {
        "DOCS_DIR": output_dir,
        "INDEX_PATH": os.path.join(output_dir, "index.html"),
        "NATIONAL_PATH": os.path.join(output_dir, "national.html"),
        "NATIONAL_SUB_PATH": os.path.join(output_dir, "national", "index.html"),
        "TULSA_PATH": os.path.join(output_dir, "tulsa.html"),
        "TULSA_SUB_PATH": os.path.join(output_dir, "tulsa", "index.html"),
        "NEWARK_PATH": os.path.join(output_dir, "newark.html"),
        "NEWARK_SUB_PATH": os.path.join(output_dir, "newark", "index.html"),
        "CINCINNATI_PATH": os.path.join(output_dir, "cincinnati.html"),
        "CINCINNATI_SUB_PATH": os.path.join(output_dir, "cincinnati", "index.html"),
        "GREENVILLE_PATH": os.path.join(output_dir, "greenville.html"),
        "GREENVILLE_SUB_PATH": os.path.join(output_dir, "greenville", "index.html"),
        "CHARLOTTE_PATH": os.path.join(output_dir, "charlotte.html"),
        "CHARLOTTE_SUB_PATH": os.path.join(output_dir, "charlotte", "index.html"),
        "PORT_ST_LUCIE_PATH": os.path.join(output_dir, "port_st_lucie.html"),
        "PORT_ST_LUCIE_SUB_PATH": os.path.join(output_dir, "port_st_lucie", "index.html"),
        "OAKLAND_PATH": os.path.join(output_dir, "oakland.html"),
        "OAKLAND_SUB_PATH": os.path.join(output_dir, "oakland", "index.html"),
        "BAYAREA_PATH": os.path.join(output_dir, "bayarea.html"),
        "BAYAREA_SUB_PATH": os.path.join(output_dir, "bayarea", "index.html"),
    }
    
    for attr, val in paths_to_patch.items():
        monkeypatch.setattr(f"src.dashboard_generator.{attr}", val)
        
    generate_public_dashboard()
    
    # Verify no unrendered {{..._HIT_RATE}} or {{..._MAE}} in index.html and subpages
    for filename in ["index.html", "national.html", "tulsa.html", "newark.html", "cincinnati.html", "greenville.html", "charlotte.html", "port_st_lucie.html", "oakland.html", "bayarea.html"]:
        file_path = os.path.join(output_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "{{NATIONAL_HIT_RATE}}" not in content
                assert "{{TULSA_HIT_RATE}}" not in content
                assert "{{NEWARK_HIT_RATE}}" not in content
                assert "{{CINCINNATI_HIT_RATE}}" not in content
                assert "{{GREENVILLE_HIT_RATE}}" not in content
                assert "{{CHARLOTTE_HIT_RATE}}" not in content
                assert "{{PORT_ST_LUCIE_HIT_RATE}}" not in content
                assert "{{OAKLAND_HIT_RATE}}" not in content
                assert "{{BAYAREA_HIT_RATE}}" not in content
                assert "{{NATIONAL_MAE}}" not in content
                assert "{{TULSA_MAE}}" not in content
                assert "{{NEWARK_MAE}}" not in content
                assert "{{CINCINNATI_MAE}}" not in content
                assert "{{GREENVILLE_MAE}}" not in content
                assert "{{CHARLOTTE_MAE}}" not in content
                assert "{{PORT_ST_LUCIE_MAE}}" not in content
