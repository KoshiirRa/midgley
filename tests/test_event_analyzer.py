"""
Unit tests for LLM Event Analyzer Module (src/event_analyzer.py)
Tests single and batch headline extraction, SHA-256 deduplication, and lookup cache hits.
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

from src.event_analyzer import (
    extract_event_features_llm,
    extract_batch_event_features_llm,
    extract_event_features_rule_based,
    _get_headline_sha256,
    _LLM_SCORE_CACHE
)
from src.lookup_cache import global_cache


class TestEventAnalyzer(unittest.TestCase):

    def setUp(self):
        global_cache.clear()
        _LLM_SCORE_CACHE.clear()

    def tearDown(self):
        global_cache.clear()
        _LLM_SCORE_CACHE.clear()

    def test_headline_sha256_hashing(self):
        h1 = "OPEC Announces Sudden 1M Barrel Supply Cut"
        h2 = "OPEC Announces Sudden 1M Barrel Supply Cut"
        self.assertEqual(_get_headline_sha256(h1), _get_headline_sha256(h2))

    def test_single_headline_caching(self):
        headline = "Refinery Outage in Texas Gulf Coast Spikes Gasoline Prices"
        # First extraction (rule-based fallback when no API key)
        scores1 = extract_event_features_llm(headline)
        self.assertIsNotNone(scores1)
        self.assertIn("overall_price_pressure", scores1)

        # Verify key exists in lookup cache
        sha_key = f"llm_score:{_get_headline_sha256(headline)}"
        cached = global_cache.get(sha_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["overall_price_pressure"], scores1["overall_price_pressure"])

        # Second extraction should hit cache instantly
        scores2 = extract_event_features_llm(headline)
        self.assertEqual(scores2["overall_price_pressure"], scores1["overall_price_pressure"])

    def test_batch_headline_caching(self):
        headlines = [
            "Hurricane Threatens Gulf Oil Rigs",
            "Tornado Damages West Tulsa Refinery Pipeline"
        ]
        results1 = extract_batch_event_features_llm(headlines)
        self.assertEqual(len(results1), 2)

        # Second batch run hits cache
        results2 = extract_batch_event_features_llm(headlines)
        self.assertEqual(len(results2), 2)
        self.assertEqual(results1[0]["overall_price_pressure"], results2[0]["overall_price_pressure"])

    @patch("src.event_analyzer.extract_event_features_llm")
    def test_batch_size_mismatch_itemized_fallback(self, mock_extract_llm):
        """Verifies that when LLM returns a batch length mismatch, itemized extract_event_features_llm is invoked (Issue #334)."""
        mock_extract_llm.side_effect = lambda h, **kwargs: {
            "geopolitical_risk": 0.5,
            "supply_disruption": 0.6,
            "demand_sentiment": 0.0,
            "opec_action": 0.0,
            "overall_price_pressure": 0.36
        }

        headlines = [
            "Unexpected refinery fire in Delaware City",
            "Pipeline valve leak halts Colonial Line 1",
            "OPEC delegates signal rollover"
        ]

        # Simulate Gemini returning only 1 item for a 3-item batch
        with patch("google.genai.Client") as mock_genai_client:
            mock_client_instance = MagicMock()
            mock_resp = MagicMock()
            # Only 1 item returned instead of 3
            mock_resp.text = '[{"geopolitical_risk": 0.1, "supply_disruption": 0.2, "demand_sentiment": 0.0, "opec_action": 0.0, "overall_price_pressure": 0.1}]'
            mock_client_instance.models.generate_content.return_value = mock_resp
            mock_genai_client.return_value = mock_client_instance

            results = extract_batch_event_features_llm(headlines, api_key="test_api_key")
            self.assertEqual(len(results), 3)
            # Itemized LLM extractor should have been called for all 3 uncached headlines
            self.assertEqual(mock_extract_llm.call_count, 3)


    def test_extract_event_features_llm_gemini_38_flash(self):
        """Verifies single extraction targets gemini-3.8-flash with thinking_level='low' and no deprecated params."""
        headline = "Saudi Aramco unexpectedly cuts crude output by 500k bpd"
        with patch("google.genai.Client") as mock_genai_client, \
             patch("src.event_analyzer.log_llm_usage") as mock_log_usage, \
             patch("src.event_analyzer.token_tab_manager.record_usage") as mock_tab_record:

            mock_client_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = json.dumps({
                "geopolitical_risk": 0.3,
                "supply_disruption": 0.8,
                "demand_sentiment": 0.0,
                "opec_action": 0.9,
                "overall_price_pressure": 0.75
            })
            mock_client_instance.models.generate_content.return_value = mock_resp
            mock_genai_client.return_value = mock_client_instance

            scores = extract_event_features_llm(headline, api_key="fake_gemini_key")
            self.assertEqual(scores["overall_price_pressure"], 0.75)

            call_kwargs = mock_client_instance.models.generate_content.call_args[1]
            self.assertEqual(call_kwargs["model"], "gemini-3.8-flash")
            config = call_kwargs["config"]
            if isinstance(config, MagicMock):
                from google.genai import types
                if hasattr(types.GenerateContentConfig, "call_args") and types.GenerateContentConfig.call_args:
                    cfg_kwargs = types.GenerateContentConfig.call_args.kwargs
                    self.assertNotIn("temperature", cfg_kwargs)
                    self.assertNotIn("top_p", cfg_kwargs)
                    self.assertNotIn("top_k", cfg_kwargs)
                    self.assertNotIn("thinking_budget", cfg_kwargs)
                    self.assertIn("thinking_config", cfg_kwargs)
            else:
                self.assertIsNone(getattr(config, "temperature", None))
                self.assertIsNone(getattr(config, "top_p", None))
                self.assertIsNone(getattr(config, "top_k", None))
                self.assertIsNone(getattr(config, "thinking_budget", None))
                self.assertIn("low", str(config.thinking_config.thinking_level).lower())

            mock_log_usage.assert_called_once()
            self.assertEqual(mock_log_usage.call_args[0][1], "gemini-3.8-flash")
            mock_tab_record.assert_called_once()
            self.assertEqual(mock_tab_record.call_args[0][0], "gemini-3.8-flash")

    def test_extract_batch_event_features_llm_gemini_38_flash(self):
        """Verifies batch extraction targets gemini-3.8-flash with thinking_level='low' and no deprecated params."""
        headlines = [
            "Colonial Pipeline resumes normal service after inspection",
            "Midwest refinery announces scheduled unit overhaul"
        ]
        with patch("google.genai.Client") as mock_genai_client:
            mock_client_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = json.dumps([
                {"geopolitical_risk": 0.0, "supply_disruption": -0.2, "demand_sentiment": 0.0, "opec_action": 0.0, "overall_price_pressure": -0.1},
                {"geopolitical_risk": 0.0, "supply_disruption": 0.3, "demand_sentiment": 0.0, "opec_action": 0.0, "overall_price_pressure": 0.15}
            ])
            mock_client_instance.models.generate_content.return_value = mock_resp
            mock_genai_client.return_value = mock_client_instance

            results = extract_batch_event_features_llm(headlines, api_key="fake_gemini_key")
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["overall_price_pressure"], -0.1)

            call_kwargs = mock_client_instance.models.generate_content.call_args[1]
            self.assertEqual(call_kwargs["model"], "gemini-3.8-flash")
            config = call_kwargs["config"]
            if isinstance(config, MagicMock):
                from google.genai import types
                if hasattr(types.GenerateContentConfig, "call_args") and types.GenerateContentConfig.call_args:
                    cfg_kwargs = types.GenerateContentConfig.call_args.kwargs
                    self.assertNotIn("temperature", cfg_kwargs)
                    self.assertNotIn("top_p", cfg_kwargs)
                    self.assertNotIn("top_k", cfg_kwargs)
                    self.assertNotIn("thinking_budget", cfg_kwargs)
                    self.assertIn("thinking_config", cfg_kwargs)
            else:
                self.assertIsNone(getattr(config, "temperature", None))
                self.assertIsNone(getattr(config, "top_p", None))
                self.assertIsNone(getattr(config, "top_k", None))
                self.assertIsNone(getattr(config, "thinking_budget", None))
                self.assertIn("low", str(config.thinking_config.thinking_level).lower())


if __name__ == "__main__":
    unittest.main()
