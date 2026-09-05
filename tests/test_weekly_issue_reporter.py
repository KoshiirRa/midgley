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


def test_generate_weekly_markdown_report_includes_self_review(sample_issues):
    with patch("src.weekly_issue_reporter.fetch_open_github_issues", return_value=sample_issues):
        report = generate_weekly_markdown_report()
        assert "## 🎯 High-Impact Issue Analysis & Self-Review" in report
        assert "Highest-Impact Modeling Issue" in report
        assert "## ⚠️ Model Degradation & Baseline Underperformance Alerts" in report
        assert "## 📚 Relevant Recent arXiv Research Papers" in report
