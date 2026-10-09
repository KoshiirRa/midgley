import pytest
from unittest.mock import patch, MagicMock
from scripts.review_false_positive import (
    analyze_headline_triggers,
    format_diagnostic_comment,
    parse_headline_from_issue_body,
    post_issue_comment,
    fetch_issue_comments
)


def test_analyze_headline_triggers_energy():
    headline = "Exxon Refinery Outage Adds Pressure to Regional Fuel Prices"
    analysis = analyze_headline_triggers(headline, category="Refinery", notes="Outage in Texas")

    assert "refinery outage" in analysis["matched_triggers"] or "refinery" in analysis["matched_energy_tokens"]
    assert analysis["has_energy_context"] is True
    assert "refinery outage" in analysis["diagnosis"]


def test_analyze_headline_triggers_non_energy_policy():
    headline = "Trump Announces Sweeping New Auto and Semiconductor Tariff on Foreign Imports"
    analysis = analyze_headline_triggers(headline)

    assert analysis["has_energy_context"] is False
    assert any("tariff" in t for t in analysis["matched_triggers"])
    assert "non-energy policy false positive" in analysis["diagnosis"]


def test_analyze_headline_triggers_agricultural_oil():
    headline = "Global Soybean Oil and Canola Supply Drops Following Flood"
    analysis = analyze_headline_triggers(headline)

    assert "agricultural or edible oils" in analysis["diagnosis"]


def test_analyze_headline_triggers_sanctions_macro():
    headline = "Russia sanctions bill gives Trump sweeping new tariff powers - Reuters"
    analysis = analyze_headline_triggers(headline)

    assert analysis["has_energy_context"] is False
    assert any("sanction" in t for t in analysis["matched_triggers"])
    assert "non-energy policy false positive" in analysis["diagnosis"]


def test_analyze_headline_triggers_data_center_spill():
    headline = "Data Center’s Spill of 5,000 Gallons of Diesel Forces N.J. River Cleanup"
    analysis = analyze_headline_triggers(headline)

    assert "minor localized facility/generator spill" in analysis["diagnosis"]


def test_parse_headline_from_issue_body():
    body_trigger_block = """## False Positive Anomaly Report (#258)

### 🚨 Trigger Catalyst
> *"Refinery Outage In Louisiana Sparks Gas Concerns"*

- **Ingestion Source:** `Test_Runner`
"""
    assert parse_headline_from_issue_body(body_trigger_block) == "Refinery Outage In Louisiana Sparks Gas Concerns"

    body_fallback = "> *\"Pipeline Blast Halts Crude Flow\"*"
    assert parse_headline_from_issue_body(body_fallback) == "Pipeline Blast Halts Crude Flow"

    # Issue #617 case: Body is directly a flag link
    body_flag_url = "https://midgley-intraday-monitor.m-cubed-3.workers.dev/flag?id=d7bddaeb2be84d74&exp=1791590422&sig=&headline=Supreme+Court+Dismisses+Appeal+on+Classification+of+Hydrogenated+Rice+Bran+Oil&source=RSS_Feed"
    assert parse_headline_from_issue_body(body_flag_url) == "Supreme Court Dismisses Appeal on Classification of Hydrogenated Rice Bran Oil"


def test_analyze_headline_triggers_rice_bran_oil():
    headline = "Supreme Court Dismisses Appeal on Classification of Hydrogenated Rice Bran Oil Due to Retention of Essential Characteristics."
    analysis = analyze_headline_triggers(headline)
    assert "agricultural or edible oils" in analysis["diagnosis"]


def test_format_diagnostic_comment():
    headline = "Test Commodity Anomaly Headline"
    analysis = analyze_headline_triggers(headline)
    comment = format_diagnostic_comment(analysis)

    assert "### 🤖 Automated Agent Diagnostic Review" in comment
    assert "Root Cause Analysis" in comment
    assert "Regression Unit Test Case" in comment


@patch.dict("os.environ", {"GITHUB_TOKEN": "mock_token"})
@patch("scripts.review_false_positive.fetch_issue_comments")
@patch("urllib.request.urlopen")
def test_post_issue_comment_idempotent_skip(mock_urlopen, mock_fetch_comments):
    # Simulate existing diagnostic review comment
    mock_fetch_comments.return_value = [
        {"id": 12345, "body": "### 🤖 Automated Agent Diagnostic Review (Issue #258 Sub-Task)\n\nPrevious analysis..."}
    ]

    result = post_issue_comment(311, "### 🤖 Automated Agent Diagnostic Review\n\nNew analysis...")
    assert result is True
    # urlopen should not have been called because it skipped duplicate
    mock_urlopen.assert_not_called()


@patch.dict("os.environ", {"GITHUB_TOKEN": "mock_token"})
@patch("scripts.review_false_positive.fetch_issue_comments")
@patch("urllib.request.urlopen")
def test_post_issue_comment_posts_when_no_duplicate(mock_urlopen, mock_fetch_comments):
    # Simulate no existing comments
    mock_fetch_comments.return_value = []

    mock_resp = MagicMock()
    mock_resp.status = 201
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    result = post_issue_comment(311, "### 🤖 Automated Agent Diagnostic Review\n\nNew analysis...")
    assert result is True
    mock_urlopen.assert_called_once()
