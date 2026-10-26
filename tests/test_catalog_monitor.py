"""
Unit tests for Developer Catalog Monitor & Cross-Repository Deduplication Engine (src/catalog_monitor.py).
Verifies that duplicate candidate issues are detected and suppressed across both midgley
and companion repositories (e.g., KoshiirRa/agentic-trading-robinhood).
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.catalog_monitor import (
    check_existing_issue,
    get_existing_issues_cache,
    clear_existing_issues_cache,
    infer_issue_domain_labels,
    open_github_issue_for_item,
    evaluate_item_heuristic,
)


@pytest.fixture(autouse=True)
def reset_issues_cache():
    clear_existing_issues_cache()
    yield
    clear_existing_issues_cache()


def test_infer_issue_domain_labels():
    eval_res = {
        "category": "NOAA & Weather Intelligence",
        "target_component": "src/noaa_weather.py"
    }
    item = {
        "title": "AlphaFinch",
        "description": "Weather and hurricane radar feed",
        "url": "https://alphafinch.org"
    }
    labels = infer_issue_domain_labels(eval_res, item)
    assert "enhancement" in labels
    assert "data-ingestion" in labels


def test_check_existing_issue_exact_title():
    mock_issues = [
        {
            "number": 101,
            "title": "[Feature Request] Ingest FooTool (LLM & RAG Event Extraction)",
            "body": "Discovered candidate tool FooTool at https://footool.dev",
            "state": "OPEN",
            "repo": "KoshiirRa/midgley"
        }
    ]
    with patch("src.catalog_monitor.get_existing_issues_cache", return_value=mock_issues):
        # Exact title match
        assert check_existing_issue("[Feature Request] Ingest FooTool (LLM & RAG Event Extraction)", "https://other.dev") is True
        # Different title, non-matching
        assert check_existing_issue("[Feature Request] Ingest BarTool (General Infrastructure)", "https://bartool.dev") is False


def test_check_existing_issue_companion_repo_and_tool_name():
    mock_issues = [
        {
            "number": 54,
            "title": "[Feature Request] Ingest iPulse AI (LLM & RAG Event Extraction)",
            "body": "Discovered candidate tool iPulse AI at https://ipulseai.com",
            "state": "OPEN",
            "repo": "KoshiirRa/agentic-trading-robinhood"
        }
    ]
    with patch("src.catalog_monitor.get_existing_issues_cache", return_value=mock_issues):
        # Tool name match even if category differs
        assert check_existing_issue("[Feature Request] Ingest iPulse AI (Infrastructure)", "https://different-url.com", "iPulse AI") is True
        # Ingest tool name match extracted from title
        assert check_existing_issue("[Feature Request] Ingest iPulse AI (Quantitative Modeling)", "https://different-url.com") is True


def test_check_existing_issue_url_in_body():
    mock_issues = [
        {
            "number": 680,
            "title": "[Feature Request] Ingest gamma-seed (Security)",
            "body": "Candidate tool: **[gamma-seed](https://github.com/Timonkru/gamma-seed)**",
            "state": "CLOSED",
            "repo": "KoshiirRa/midgley"
        }
    ]
    with patch("src.catalog_monitor.get_existing_issues_cache", return_value=mock_issues):
        # URL in body match
        assert check_existing_issue("[Feature Request] Ingest DifferentName (Security)", "https://github.com/Timonkru/gamma-seed/") is True


def test_open_github_issue_skips_when_duplicate_exists():
    mock_issues = [
        {
            "number": 67,
            "title": "[Feature Request] Ingest MarginPad (Quantitative Time-Series Modeling)",
            "body": "Discovered MarginPad at https://marginpad.io/free-crypto-api/",
            "state": "OPEN",
            "repo": "KoshiirRa/agentic-trading-robinhood"
        }
    ]
    item = {
        "title": "MarginPad",
        "url": "https://marginpad.io/free-crypto-api/",
        "description": "Crypto futures and order books",
        "catalog_key": "public-apis"
    }
    eval_res = {
        "impact_score": 7.4,
        "category": "Quantitative Time-Series Modeling",
        "target_component": "src/models.py",
        "is_worthwhile": True,
        "reasoning": "High impact time series tool"
    }
    with patch("src.catalog_monitor.get_existing_issues_cache", return_value=mock_issues):
        url = open_github_issue_for_item(item, eval_res, dry_run=False)
        assert url == ""


def test_evaluate_item_heuristic_barred():
    apify_item = {
        "title": "Some Scraper",
        "url": "https://apify.com/actors/some-scraper",
        "description": "Scrapes stuff",
        "catalog_key": "awesome"
    }
    res = evaluate_item_heuristic(apify_item)
    assert res["is_worthwhile"] is False
    assert res["impact_score"] == 0.0
