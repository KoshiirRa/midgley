"""
Unit Tests for Discord Interactive Flagging & Automated Reviewer (tests/test_discord_interactions.py)
"""

import unittest
from unittest.mock import patch, MagicMock

from src.discord_notifier import format_intraday_discord_payload
from scripts.review_false_positive import (
    analyze_headline_triggers,
    format_diagnostic_comment,
    parse_headline_from_issue_body
)


class TestDiscordInteractionsAndReviewer(unittest.TestCase):
    def setUp(self):
        self.sample_event = {
            "headline": "US announces 25% tariff on imported consumer electronics and semiconductors",
            "source": "RSS_GoogleNews",
            "url": "https://news.example.com/tech-tariffs",
            "scores": {
                "overall_price_pressure": 0.42,
                "supply_disruption": 0.10,
                "geopolitical_risk": 0.60
            }
        }

    def test_discord_payload_action_components(self):
        """Verifies that format_intraday_discord_payload includes interactive button components."""
        payload = format_intraday_discord_payload(self.sample_event, environment="prod")
        self.assertIn("components", payload)
        self.assertEqual(len(payload["components"]), 1)
        action_row = payload["components"][0]
        self.assertEqual(action_row["type"], 1)

        buttons = action_row["components"]
        self.assertEqual(len(buttons), 2)

        flag_btn = buttons[0]
        self.assertEqual(flag_btn["type"], 2)
        self.assertEqual(flag_btn["style"], 5)
        self.assertIn("Flag False Positive", flag_btn["label"])
        self.assertIn("/flag?", flag_btn["url"])

        link_btn = buttons[1]
        self.assertEqual(link_btn["type"], 2)
        self.assertEqual(link_btn["style"], 5)
        self.assertIn("258", link_btn["url"])

    def test_analyze_headline_macro_tariff(self):
        """Verifies root cause diagnosis for non-energy macro tariffs."""
        analysis = analyze_headline_triggers(
            headline="US announces 25% tariff on imported semiconductors",
            category="Non-Energy Tariff",
            notes="Tech sector tariffs without crude oil impact."
        )

        self.assertIn("tariff", analysis["matched_triggers"])
        self.assertFalse(analysis["has_energy_context"])
        self.assertIn("non-energy policy false positive", analysis["diagnosis"])

    def test_analyze_headline_cooking_oil(self):
        """Verifies root cause diagnosis for agricultural oils."""
        analysis = analyze_headline_triggers(
            headline="Global cooking oil export restrictions tighten food supply",
            category="Agricultural Oil"
        )
        self.assertIn("agricultural or edible oils", analysis["diagnosis"])

    def test_format_diagnostic_comment(self):
        """Verifies that formatted markdown comment contains diagnosis and unit test."""
        analysis = analyze_headline_triggers(
            headline="US imposes new tariffs on imported solar panels and electronics"
        )
        comment = format_diagnostic_comment(analysis)

        self.assertIn("### 🤖 Automated Agent Diagnostic Review", comment)
        self.assertIn("#### 🔍 Root Cause Analysis", comment)
        self.assertIn("#### 🛠️ Recommended Engine Refinement", comment)
        self.assertIn("#### 🧪 Regression Unit Test Case", comment)
        self.assertIn("test_false_positive_suppression_", comment)

    def test_parse_headline_from_issue_body(self):
        """Verifies extraction of headline from Markdown issue template."""
        sample_body = (
            "## False Positive Anomaly Report (#258)\n\n"
            "### 🚨 Trigger Catalyst\n"
            "> *\"US announces new semiconductor import restrictions\"*\n\n"
            "- **Ingestion Source:** `RSS_GoogleNews`\n"
        )
        extracted = parse_headline_from_issue_body(sample_body)
        self.assertEqual(extracted, "US announces new semiconductor import restrictions")


if __name__ == "__main__":
    unittest.main()
