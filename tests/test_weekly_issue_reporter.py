import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

if "google.genai" not in sys.modules:
    mock_genai_mod = MagicMock()
    sys.modules["google.genai"] = mock_genai_mod
    sys.modules["google.genai.types"] = MagicMock()
    try:
        import google
        google.genai = mock_genai_mod
    except ImportError:
        pass

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.weekly_issue_reporter import (
    fetch_open_github_issues,
    evaluate_open_issues_for_modelling,
    _evaluate_issues_heuristic,
    generate_weekly_markdown_report,
)


@pytest.fixture
def sample_issues():
    return [
        {
            "number": 101,
            "title": "Add NOAA Polar Vortex & Severe Weather Radar Feature Ingestion",
            "body": "Integrating NOAA NWS radar alerts for regional refinery freeze shock modeling.",
            "labels": ["enhancement"],
            "created_at": "2026-08-01T10:00:00Z",
            "html_url": "https://github.com/KoshiirRa/midgley/issues/101"
        },
        {
            "number": 102,
            "title": "Fix typo in README documentation",
            "body": "Correcting spelling of model parameter in documentation.",
            "labels": ["documentation"],
            "created_at": "2026-08-02T12:00:00Z",
            "html_url": "https://github.com/KoshiirRa/midgley/issues/102"
        },
        {
            "number": 103,
            "title": "Calibrate HF Sinclair Tulsa Refinery Outage Feature Decay",
            "body": "Refining dynamic rack margin decay half-life for local refinery outages.",
            "labels": ["modeling"],
            "created_at": "2026-08-03T15:00:00Z",
            "html_url": "https://github.com/KoshiirRa/midgley/issues/103"
        }
    ]


def test_fetch_open_github_issues_gh_cli(sample_issues):
    raw_gh_output = json.dumps([
        {
            "number": item["number"],
            "title": item["title"],
            "body": item["body"],
            "labels": [{"name": l} for l in item["labels"]],
            "createdAt": item["created_at"],
            "url": item["html_url"]
        }
        for item in sample_issues
    ])
    
    mock_run = MagicMock()
    mock_run.stdout = raw_gh_output
    
    with patch("subprocess.run", return_value=mock_run):
        issues = fetch_open_github_issues("KoshiirRa/midgley")
        assert len(issues) == 3
        assert issues[0]["number"] == 101
        assert issues[0]["title"] == "Add NOAA Polar Vortex & Severe Weather Radar Feature Ingestion"


def test_evaluate_open_issues_heuristic(sample_issues):
    result = _evaluate_issues_heuristic(sample_issues, nat_mae=0.1069, tulsa_mae=0.5611)
    
    assert result["top_issue"] is not None
    # Issue #101 or #103 should be ranked highest due to NOAA/Refinery domain keywords
    assert result["top_issue"]["number"] in [101, 103]
    assert result["top_issue"]["impact_score"] > 5.0
    
    # Check that typo fix issue #102 is ranked lower
    ranking = result["ranking"]
    assert len(ranking) == 3
    assert ranking[-1]["number"] == 102
    
    # Verify markdown summary contains expected headers
    summary_md = result["summary_markdown"]
    assert "Highest-Impact Modeling Issue" in summary_md
    assert "Open Issues Ranked by Modeling Priority" in summary_md


def test_evaluate_open_issues_empty():
    result = evaluate_open_issues_for_modelling([], nat_mae=0.1069, tulsa_mae=0.5611)
    assert result["top_issue"] is None
    assert result["ranking"] == []
    assert "No open GitHub issues currently found" in result["summary_markdown"]


def test_evaluate_open_issues_llm_mock(sample_issues):
    mock_llm_json = json.dumps({
        "top_issue_number": 103,
        "top_issue_title": "Calibrate HF Sinclair Tulsa Refinery Outage Feature Decay",
        "impact_score": 9.2,
        "category": "Refining & Physical Feeds",
        "reasoning": "Directly targets regional refining outage decay half-life, reducing Tulsa pump price prediction error.",
        "recommended_implementation": "Adjust exponential decay half-life t1/2 parameter from 4.0 to 3.5 days.",
        "all_issues_ranked": [
            {"number": 103, "title": "Calibrate HF Sinclair Tulsa Refinery Outage Feature Decay", "impact_score": 9.2, "category": "Refining & Physical Feeds"},
            {"number": 101, "title": "Add NOAA Polar Vortex & Severe Weather Radar Feature Ingestion", "impact_score": 8.5, "category": "Weather Data"},
            {"number": 102, "title": "Fix typo in README documentation", "impact_score": 1.5, "category": "General Maintenance"}
        ]
    })
    
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = f"```json\n{mock_llm_json}\n```"
    mock_genai_client.models.generate_content.return_value = mock_response
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}), \
         patch("google.genai.Client", return_value=mock_genai_client):
        
        result = evaluate_open_issues_for_modelling(sample_issues, nat_mae=0.1069, tulsa_mae=0.5611, api_key="fake_test_key")
        
        assert result["top_issue"]["number"] == 103
        assert result["top_issue"]["impact_score"] == 9.2
        assert "Adjust exponential decay" in result["recommended_implementation"]
        assert "High-Impact Modeling Issue" in result["summary_markdown"] or "Highest-Impact" in result["summary_markdown"]

        call_kwargs = mock_genai_client.models.generate_content.call_args[1]
        assert call_kwargs["model"] == "gemini-3.8-flash"
        config = call_kwargs["config"]
        if isinstance(config, MagicMock):
            from google.genai import types
            if hasattr(types.GenerateContentConfig, "call_args") and types.GenerateContentConfig.call_args:
                cfg_kwargs = types.GenerateContentConfig.call_args.kwargs
                assert "temperature" not in cfg_kwargs
                assert "top_p" not in cfg_kwargs
                assert "top_k" not in cfg_kwargs
                assert "thinking_budget" not in cfg_kwargs
        else:
            assert getattr(config, "temperature", None) is None
            assert getattr(config, "top_p", None) is None
            assert getattr(config, "top_k", None) is None
            assert getattr(config, "thinking_budget", None) is None


def test_generate_weekly_markdown_report_includes_self_review(sample_issues):
    with patch("src.weekly_issue_reporter.fetch_open_github_issues", return_value=sample_issues):
        report = generate_weekly_markdown_report()
        assert "## 🎯 High-Impact Issue Analysis & Self-Review" in report
        assert "Highest-Impact Modeling Issue" in report
        assert "## ⚠️ Model Degradation & Baseline Underperformance Alerts" in report
        assert "## 📚 Relevant Recent arXiv Research Papers" in report
        assert "## 🔬 Relevant CORE Open-Access Research Papers" in report


def test_load_prediction_records_db_and_csv(tmp_path):
    from src.weekly_issue_reporter import load_prediction_records
    import pandas as pd

    # Test 1: DB query succeeds
    mock_db = MagicMock()
    mock_db.execute.return_value = [
        {
            "forecast_id": "f123",
            "region": "National",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": "2026-09-30",
            "forecast_target_date": "2026-10-05",
            "forecast_horizon_days": 5,
            "predicted_5d_price": 3.12,
            "prediction_lower_95ci": 2.95,
            "prediction_upper_95ci": 3.30,
            "llm_price_pressure": 0.05,
            "llm_supply_disruption": 0.02,
            "run_type": "LIVE_PROSPECTIVE",
            "actual_5d_price": 3.14,
            "error_dollars": 0.02,
            "directional_hit": 1,
            "within_95ci_hit": 1
        }
    ]
    with patch("src.db.client.get_db", return_value=mock_db):
        df = load_prediction_records("nonexistent.csv")
        assert len(df) == 1
        assert df.iloc[0]["forecast_id"] == "f123"
        assert df.iloc[0]["predicted_5d_price"] == 3.12

    # Test 2: DB fails -> fallback to CSV
    csv_file = tmp_path / "test_history.csv"
    sample_df = pd.DataFrame([{
        "forecast_id": "f456",
        "region": "Tulsa_OK",
        "predicted_5d_price": 2.85,
        "actual_5d_price": 2.88,
        "error_dollars": 0.03
    }])
    sample_df.to_csv(csv_file, index=False)

    with patch("src.db.client.get_db", side_effect=RuntimeError("DB down")):
        df_csv = load_prediction_records(str(csv_file))
        assert len(df_csv) == 1
        assert df_csv.iloc[0]["forecast_id"] == "f456"


def test_load_prediction_records_enriches_current_base_price_from_csv(tmp_path):
    from src.weekly_issue_reporter import load_prediction_records
    import pandas as pd

    csv_file = tmp_path / "enrich_history.csv"
    pd.DataFrame([{
        "forecast_id": "f_nat_5d",
        "region": "National",
        "forecast_target_date": "2026-11-05",
        "forecast_horizon_days": 5,
        "current_base_price": 2.912,
        "predicted_5d_price": 2.946,
        "predicted_direction": "UP",
        "is_retroactive_backtest": False
    }]).to_csv(csv_file, index=False)

    mock_db = MagicMock()
    mock_db.execute.return_value = [{
        "forecast_id": "f_nat_5d",
        "region": "National",
        "model_version": "v1.6-Ipatieff",
        "log_timestamp": "2026-10-31",
        "forecast_target_date": "2026-11-05",
        "forecast_horizon_days": 5,
        "predicted_5d_price": 2.946,
        "prediction_lower_95ci": 2.81,
        "prediction_upper_95ci": 3.08,
        "llm_price_pressure": 0.02,
        "llm_supply_disruption": 0.01,
        "point_in_time_features": None,
        "run_type": "LIVE_PROSPECTIVE",
        "actual_5d_price": None,
        "error_dollars": None,
        "directional_hit": None,
        "within_95ci_hit": None
    }]
    with patch("src.db.client.get_db", return_value=mock_db):
        df = load_prediction_records(str(csv_file))
        assert len(df) == 1
        assert abs(float(df.iloc[0]["current_base_price"]) - 2.912) < 1e-6
        assert abs(float(df.iloc[0]["predicted_5d_price"]) - 2.946) < 1e-6


def test_heuristic_filters_false_positive_and_cross_repo_and_avoids_saturation():
    issues = [
        {
            "number": 631,
            "title": "feat(features): Bifurcate physical supply shock decay half-lives into upstream shut-ins vs structural refinery damage",
            "body": "Split supply_disruption half-life into upstream_offshore_shutin (3.5d) and downstream_refinery_damage (14.0d).",
            "labels": ["modeling", "feature-engineering"],
            "created_at": "2026-10-10T00:00:00Z",
            "html_url": "https://github.com/KoshiirRa/midgley/issues/631"
        },
        {
            "number": 640,
            "title": "feat(ingestion): Integrate Cloudflare Browser Run for edge headless Chromium scraping",
            "body": "Scrape dynamic energy news articles and refinery outage notifications with weather and crack spread context.",
            "labels": ["data-ingestion", "infrastructure"],
            "created_at": "2026-10-12T00:00:00Z",
            "html_url": "https://github.com/KoshiirRa/midgley/issues/640"
        },
        {
            "number": 698,
            "title": "[False Positive] Incorrectly matched non-energy headline (#698)",
            "body": "Flagged false positive news item.",
            "labels": ["false-positive"],
            "created_at": "2026-10-30T00:00:00Z",
            "html_url": "https://github.com/KoshiirRa/midgley/issues/698"
        },
        {
            "number": 699,
            "title": "feat(options): Add options chain Greek surface solver",
            "body": "Tracked in KoshiirRa/agentic-trading-robinhood.",
            "labels": ["enhancement"],
            "created_at": "2026-10-30T00:00:00Z",
            "html_url": "https://github.com/KoshiirRa/agentic-trading-robinhood/issues/699"
        }
    ]
    res = _evaluate_issues_heuristic(issues, nat_mae=0.0569, tulsa_mae=0.5611)
    ranked_nums = [r["number"] for r in res["ranking"]]
    assert 698 not in ranked_nums
    assert 699 not in ranked_nums
    assert res["top_issue"]["number"] == 631
    assert res["ranking"][0]["impact_score"] > res["ranking"][1]["impact_score"]


def test_load_prediction_records_csv_fallback_filters_test_regions(tmp_path):
    """Verify CSV fallback path purges Test_Region/Test_* artifacts consistently with DB path (Issue #737)."""
    from src.weekly_issue_reporter import load_prediction_records
    import pandas as pd

    csv_file = tmp_path / "fallback_history.csv"
    pd.DataFrame([
        {
            "forecast_id": "f_tulsa",
            "region": "Tulsa_OK",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "current_base_price": 3.186,
            "predicted_5d_price": 3.089,
            "run_type": "LIVE_PROSPECTIVE",
        },
        {
            "forecast_id": "f_test",
            "region": "Test_Region",
            "forecast_target_date": "2026-01-15",
            "forecast_horizon_days": 5,
            "current_base_price": 3.550,
            "predicted_5d_price": 3.550,
            "run_type": "LIVE_PROSPECTIVE",
        },
    ]).to_csv(csv_file, index=False)

    with patch("src.db.client.get_db", side_effect=RuntimeError("DB unavailable")):
        df = load_prediction_records(str(csv_file))

    assert list(df["region"].unique()) == ["Tulsa_OK"]


def test_load_prediction_records_horizon_aware_enrichment_and_missing_base_preservation(tmp_path):
    """Verify CSV enrichment respects horizon and preserves genuine NaN base prices without fabrication (Issue #737)."""
    from src.weekly_issue_reporter import load_prediction_records
    import pandas as pd

    csv_file = tmp_path / "horizon_enrich.csv"
    pd.DataFrame([
        {
            "forecast_id": "csv_1d",
            "region": "National",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 1,
            "current_base_price": 2.999,
            "predicted_5d_price": 3.010,
        },
        {
            "forecast_id": "csv_5d",
            "region": "National",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "current_base_price": 2.482,
            "predicted_5d_price": 2.450,
        },
    ]).to_csv(csv_file, index=False)

    mock_db = MagicMock()
    mock_db.execute.return_value = [
        {
            "forecast_id": "db_5d_different_id",
            "region": "National",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": "2026-11-22",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "predicted_5d_price": 2.450,
            "point_in_time_features": None,
            "run_type": "LIVE_PROSPECTIVE",
        },
        {
            "forecast_id": "db_missing_base",
            "region": "Boston_MA",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": "2026-11-22",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "predicted_5d_price": 3.754,
            "point_in_time_features": None,
            "run_type": "LIVE_PROSPECTIVE",
        },
    ]

    with patch("src.db.client.get_db", return_value=mock_db):
        df = load_prediction_records(str(csv_file))

    nat_row = df[df["region"] == "National"].iloc[0]
    bos_row = df[df["region"] == "Boston_MA"].iloc[0]
    assert abs(float(nat_row["current_base_price"]) - 2.482) < 1e-6
    assert pd.isna(bos_row["current_base_price"])


def test_active_latest_forecasts_filters_stale_retired_test_and_fixes_directions():
    """Verify Active 5-Day table excludes stale/retired/test/backtest rows and computes UP/DOWN/FLAT/N/A accurately (Issue #737)."""
    import pandas as pd
    import numpy as np
    from src.weekly_issue_reporter import _select_active_latest_forecasts, _format_projected_direction

    df = pd.DataFrame([
        # Retired region (even if future target date were somehow present)
        {
            "region": "Greenville_NC",
            "log_timestamp": "2026-10-16 00:31:06",
            "forecast_target_date": "2026-10-21",
            "forecast_horizon_days": 5,
            "current_base_price": 3.691,
            "predicted_5d_price": 3.691,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False,
        },
        # Test artifact
        {
            "region": "Test_Region",
            "log_timestamp": "2026-01-10 00:00:00",
            "forecast_target_date": "2026-01-15",
            "forecast_horizon_days": 5,
            "current_base_price": 3.550,
            "predicted_5d_price": 3.550,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False,
        },
        # Stale past target date for active region
        {
            "region": "Denver_CO",
            "log_timestamp": "2026-10-01 00:00:00",
            "forecast_target_date": "2026-10-08",
            "forecast_horizon_days": 5,
            "current_base_price": 3.300,
            "predicted_5d_price": 3.250,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False,
        },
        # Active UP forecast (placed BEFORE an older row to test chronological sorting)
        {
            "region": "National",
            "log_timestamp": "2026-11-22 05:00:00",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "current_base_price": 2.482,
            "predicted_5d_price": 2.520,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False,
        },
        {
            "region": "National",
            "log_timestamp": "2026-11-19 05:00:00",
            "forecast_target_date": "2026-11-25",
            "forecast_horizon_days": 5,
            "current_base_price": 2.500,
            "predicted_5d_price": 2.400,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False,
        },
        # Active DOWN forecast
        {
            "region": "Boston_MA",
            "log_timestamp": "2026-11-22 05:00:00",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "current_base_price": 3.882,
            "predicted_5d_price": 3.754,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False,
        },
        # Active FLAT forecast (zero delta)
        {
            "region": "Phoenix_AZ",
            "log_timestamp": "2026-11-22 05:00:00",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "current_base_price": 3.899,
            "predicted_5d_price": 3.899,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False,
        },
        # Retroactive backtest with future-looking date should be ignored
        {
            "region": "Tulsa_OK",
            "log_timestamp": "2026-11-22 05:00:00",
            "forecast_target_date": "2026-11-30",
            "forecast_horizon_days": 5,
            "current_base_price": 3.100,
            "predicted_5d_price": 3.500,
            "run_type": "RETROSPECTIVE_BACKTEST",
            "is_retroactive_backtest": True,
        },
    ])

    active = _select_active_latest_forecasts(df, today_str="2026-11-23")
    regions = set(active["region"].tolist())
    assert regions == {"National", "Boston_MA", "Phoenix_AZ"}
    assert "Greenville_NC" not in regions
    assert "Test_Region" not in regions
    assert "Denver_CO" not in regions
    assert "Tulsa_OK" not in regions

    nat = active[active["region"] == "National"].iloc[0]
    bos = active[active["region"] == "Boston_MA"].iloc[0]
    phx = active[active["region"] == "Phoenix_AZ"].iloc[0]
    assert nat["forecast_target_date"] == "2026-11-30"
    assert _format_projected_direction(nat["current_base_price"], nat["predicted_5d_price"]) == "UP 📈"
    assert _format_projected_direction(bos["current_base_price"], bos["predicted_5d_price"]) == "DOWN 📉"
    assert _format_projected_direction(phx["current_base_price"], phx["predicted_5d_price"]) == "FLAT ➡️"
    assert _format_projected_direction(np.nan, 3.50) == "N/A"


def test_load_prediction_records_unions_db_batch_and_csv_history(tmp_path):
    """
    Verifies that when database only returns recent prospective forecasts (e.g. 5 horizons in Turso),
    load_prediction_records retains historical evaluated records from CSV so that rolling accuracy
    is populated rather than showing '0 / 5 (Pending) | *Pending Horizon*' (Issue #716).
    """
    from src.weekly_issue_reporter import load_prediction_records
    import pandas as pd

    # CSV has 5 historical evaluated days for Phoenix_AZ
    csv_rows = []
    for i in range(5):
        csv_rows.append({
            "forecast_id": f"phx_hist_{i}",
            "region": "Phoenix_AZ",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": f"2026-11-0{i+1}",
            "forecast_target_date": f"2026-11-0{i+6}",
            "forecast_horizon_days": 5,
            "current_base_price": 4.10,
            "predicted_5d_price": 4.15,
            "actual_5d_price": 4.12,
            "error_dollars": 0.03,
            "directional_hit": 1.0,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False
        })
    csv_file = tmp_path / "prediction_history.csv"
    pd.DataFrame(csv_rows).to_csv(csv_file, index=False)

    # DB only has 5 fresh prospective rows (today's batch, pending horizon)
    mock_db = MagicMock()
    mock_db.execute.return_value = [
        {
            "forecast_id": f"phx_live_h{h}",
            "region": "Phoenix_AZ",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": "2026-11-20",
            "forecast_target_date": f"2026-11-2{h}",
            "forecast_horizon_days": h,
            "predicted_5d_price": 4.18,
            "prediction_lower_95ci": 3.90,
            "prediction_upper_95ci": 4.40,
            "llm_price_pressure": 0.0,
            "llm_supply_disruption": 0.0,
            "point_in_time_features": json.dumps({"current_base_price": 4.10}),
            "run_type": "LIVE_PROSPECTIVE",
            "actual_5d_price": None,
            "error_dollars": None,
            "directional_hit": None,
            "within_95ci_hit": None
        }
        for h in range(1, 6)
    ]

    with patch("src.db.client.get_db", return_value=mock_db):
        df = load_prediction_records(str(csv_file))

    # Should contain all 10 records: 5 evaluated from CSV + 5 fresh from DB
    assert len(df) == 10
    eval_df = df.dropna(subset=['actual_5d_price', 'error_dollars'])
    assert len(eval_df) == 5
    assert float(eval_df['error_dollars'].mean()) == pytest.approx(0.03, abs=1e-4)


def test_active_forecasts_filters_stale_target_dates_and_decommissioned_regions(tmp_path):
    """
    Verifies that 'Active 5-Day Out-of-Time Forecasts' strictly excludes decommissioned regions
    (Greenville_NC 2026-10-21), test artifacts (Test_Region 2026-01-15), and past backtests (Issue #716).
    """
    from datetime import datetime, timedelta, timezone
    from src.weekly_issue_reporter import generate_weekly_markdown_report
    import pandas as pd

    future_target = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")

    records = [
        # Greenville_NC stale prospective forecast from October
        {
            "forecast_id": "gnc_oct",
            "region": "Greenville_NC",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": "2026-10-16 00:31:00",
            "forecast_target_date": "2026-10-21",
            "forecast_horizon_days": 5,
            "current_base_price": 3.691,
            "predicted_5d_price": 3.642,
            "actual_5d_price": 3.860,
            "error_dollars": 0.218,
            "directional_hit": 1.0,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False
        },
        # Test_Region fixture from January
        {
            "forecast_id": "test_jan",
            "region": "Test_Region",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": "2026-10-01 14:48:44",
            "forecast_target_date": "2026-01-15",
            "forecast_horizon_days": 5,
            "current_base_price": 2.500,
            "predicted_5d_price": 2.550,
            "actual_5d_price": 2.510,
            "error_dollars": 0.040,
            "directional_hit": 1.0,
            "run_type": "RETROSPECTIVE_BACKTEST",
            "is_retroactive_backtest": True
        },
        # Active hub with contemporary forecast
        {
            "forecast_id": "phx_active",
            "region": "Phoenix_AZ",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d 03:00:00"),
            "forecast_target_date": future_target,
            "forecast_horizon_days": 5,
            "current_base_price": 4.097,
            "predicted_5d_price": 4.150,
            "actual_5d_price": None,
            "error_dollars": None,
            "directional_hit": None,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False
        }
    ]
    csv_file = tmp_path / "prediction_history.csv"
    pd.DataFrame(records).to_csv(csv_file, index=False)

    with patch("src.weekly_issue_reporter.HISTORY_CSV", str(csv_file)), \
         patch("src.db.client.get_db", side_effect=Exception("Offline DB")), \
         patch("src.weekly_issue_reporter.fetch_open_github_issues", return_value=[]):
        report = generate_weekly_markdown_report()

    # Active forecasts section bounded by section headers / horizontal rules
    active_section = report.split("## 🔮 Active 5-Day Out-of-Time Forecasts")[1].split("\n---\n")[0]
    assert "Phoenix_AZ" in active_section
    assert future_target in active_section
    assert "Greenville_NC" not in active_section
    assert "2026-10-21" not in active_section
    assert "Test_Region" not in report
    assert "2026-01-15" not in active_section


def test_report_generation_time_latency_badge(tmp_path):
    """
    Verifies that generate_weekly_markdown_report() includes the generation time latency badge (< 10.0s target)
    without touching production CSV or database state.
    """
    from src.weekly_issue_reporter import generate_weekly_markdown_report
    import pandas as pd

    csv_file = tmp_path / "prediction_history.csv"
    pd.DataFrame([{
        "forecast_id": "nat_latency_test",
        "region": "National",
        "model_version": "v1.6-Ipatieff",
        "log_timestamp": "2026-11-20 03:00:00",
        "forecast_target_date": "2026-11-27",
        "forecast_horizon_days": 5,
        "current_base_price": 2.50,
        "predicted_5d_price": 2.52,
        "actual_5d_price": None,
        "error_dollars": None,
        "directional_hit": None,
        "run_type": "LIVE_PROSPECTIVE",
        "is_retroactive_backtest": False
    }]).to_csv(csv_file, index=False)

    with patch("src.weekly_issue_reporter.HISTORY_CSV", str(csv_file)), \
         patch("src.db.client.get_db", side_effect=Exception("Offline DB")), \
         patch("src.weekly_issue_reporter.fetch_open_github_issues", return_value=[]), \
         patch("src.catalog_monitor.run_catalog_monitors", return_value={"catalogs_scanned": 6, "new_items_discovered": 0, "issues_created": []}), \
         patch("src.benchmark_updater.refresh_all_historical_benchmarks", return_value={"benchmarks_refreshed": 10}):
        report = generate_weekly_markdown_report()

    assert "Report Generation Time:" in report
    assert "Target `< 10.0s`" in report
    assert ("🟢 OPTIMAL" in report or "⚠️ SLOW" in report)


def test_generate_weekly_markdown_report_includes_degradation_and_feature_audit_on_dev(tmp_path):
    """Verify dev weekly report includes Model Degradation Alerts and Feature Leakage Audit sections (Issue #736)."""
    from src.weekly_issue_reporter import generate_weekly_markdown_report
    import pandas as pd

    csv_file = tmp_path / "dev_report_history.csv"
    pd.DataFrame([
        {
            "forecast_id": "dev_nat_1",
            "region": "National",
            "model_version": "v1.6-Ipatieff",
            "log_timestamp": "2026-11-21",
            "forecast_target_date": "2026-11-26",
            "forecast_horizon_days": 5,
            "current_base_price": 3.10,
            "predicted_5d_price": 3.15,
            "actual_5d_price": 3.14,
            "error_dollars": 0.01,
            "directional_hit": 1,
            "within_95ci_hit": 1,
            "run_type": "LIVE_PROSPECTIVE",
        }
    ]).to_csv(csv_file, index=False)

    with patch("src.weekly_issue_reporter.HISTORY_CSV", str(csv_file)), \
         patch("src.weekly_issue_reporter.get_current_git_branch", return_value="dev"), \
         patch("src.db.client.get_db", side_effect=Exception("Offline DB")), \
         patch("src.weekly_issue_reporter.fetch_open_github_issues", return_value=[]), \
         patch("src.catalog_monitor.run_catalog_monitors", return_value={"catalogs_scanned": 6, "new_items_discovered": 0, "issues_created": []}), \
         patch("src.benchmark_updater.refresh_all_historical_benchmarks", return_value={"benchmarks_refreshed": 10}):
        report = generate_weekly_markdown_report()

    assert "## ⚠️ Model Degradation & Baseline Underperformance Alerts" in report
    assert "## 🔬 Quantitative Research Validation & Feature Leakage Audit" in report
