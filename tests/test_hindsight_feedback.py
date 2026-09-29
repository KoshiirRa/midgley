"""
Unit Tests for Hindsight Episodic Context & Feedback Loop Engine (tests/test_hindsight_feedback.py)
"""

import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from src.hindsight_context import (
    is_catalyst_headline,
    extract_catalyst_tokens,
    query_episodic_precedents,
    format_hindsight_precedent_prompt_block,
    inject_hindsight_context,
    classify_causal_anomaly,
    evaluate_and_reflect_settled_anomalies
)
from src.scenario_engine import enrich_scenario_with_episodic_memory


def test_catalyst_headline_detection():
    """Verify catalyst regex detects physical and qualitative energy disruptions."""
    assert is_catalyst_headline("Major explosion and FCC outage halts West Tulsa refinery")
    assert is_catalyst_headline("Colonial Pipeline Line 1 shutdown following leak detection")
    assert is_catalyst_headline("Category 4 Hurricane barreling toward Texas Gulf Coast refining complex")
    assert is_catalyst_headline("OPEC+ votes to cut crude oil production quota by 1.5 million bpd")
    assert is_catalyst_headline("Ohio River tow draft restrictions declared at Markland Lock")
    assert is_catalyst_headline("EPA issues emergency Reid Vapor Pressure (RVP) summer fuel waiver")
    
    # Non-catalyst headlines
    assert not is_catalyst_headline("Local bank opens new retail branch in suburban Dallas")
    assert not is_catalyst_headline("Quarterly earnings report scheduled for next Tuesday")


def test_catalyst_token_extraction():
    """Verify extraction of relevant search tokens."""
    tokens = extract_catalyst_tokens("Refinery FCC unit trip and flaring in Delaware City")
    assert "refin" in tokens or "fcc" in tokens or "flar" in tokens


def test_query_episodic_precedents_formatting():
    """Verify precedents are normalized into structured dictionaries."""
    mock_mgr = MagicMock()
    mock_mgr.recall.return_value = [
        {
            "memory_id": "mem_123",
            "content": "Delaware City FCC trip caused +$0.15/gal regional spike over 4 days",
            "region": "Newark_DE",
            "forecast_target_date": "2024-08-15",
            "anomaly_type": "LARGE_UNDERESTIMATE",
            "error_dollars": -0.15,
            "metadata": {
                "outage_duration_days": "4 trading days",
                "pass_through_lag_days": "2 days",
                "price_shock_dollars": "+$0.15/gal",
                "lesson": "Refinery trips during summer peak lead to fast local pass-through"
            },
            "score": 0.88
        }
    ]

    precedents = query_episodic_precedents("Delaware City refinery FCC outage", region="Newark_DE", memory_manager=mock_mgr)
    assert len(precedents) == 1
    p = precedents[0]
    assert p["region"] == "Newark_DE"
    assert p["duration"] == "4 trading days"
    assert p["price_shock"] == "+$0.15/gal"
    assert "Delaware City FCC trip" in p["catalyst"]

    prompt_block = format_hindsight_precedent_prompt_block(precedents)
    assert "[HISTORICAL EPISODIC MEMORY PRECEDENT" in prompt_block
    assert "Historical Outage Duration: 4 trading days" in prompt_block
    assert "Realized Price Reaction: +$0.15/gal" in prompt_block


def test_inject_hindsight_context():
    """Verify prompt block is gated by MIDGLEY_ENABLE_HINDSIGHT_PROMPT_INJECTION and generated when enabled (Issue #576 N-4)."""
    with patch("src.hindsight_context.query_episodic_precedents") as mock_query:
        mock_query.return_value = [
            {
                "memory_id": "mem_abc",
                "catalyst": "Colonial Pipeline Line 1 shutdown",
                "region": "Greenville_NC",
                "target_date": "2024-05-10",
                "duration": "5 days",
                "pass_through_lag": "3 days",
                "price_shock": "+$0.22/gal",
                "lesson": "PADD 1C retail prices surge after 72 hours of line outage"
            }
        ]

        # By default, prompt injection is disabled (fail-closed)
        with patch.dict(os.environ, {"MIDGLEY_ENABLE_HINDSIGHT_PROMPT_INJECTION": "0"}):
            block, precs = inject_hindsight_context("Colonial Pipeline main line shut down for emergency inspection")
            assert len(precs) == 0
            assert block == ""

        # Enabled via environment variable
        with patch.dict(os.environ, {"MIDGLEY_ENABLE_HINDSIGHT_PROMPT_INJECTION": "1"}):
            # Catalyst headline
            block, precs = inject_hindsight_context("Colonial Pipeline main line shut down for emergency inspection")
            assert len(precs) == 1
            assert "[HISTORICAL EPISODIC MEMORY PRECEDENT" in block

            # Non-catalyst headline
            block_empty, precs_empty = inject_hindsight_context("Stock index closes flat on quiet trading day")
            assert len(precs_empty) == 0
            assert block_empty == ""


def test_classify_causal_anomaly():
    """Verify anomaly classification thresholds, categories, and robust directional hit handling (Issue #580 N-10)."""
    assert classify_causal_anomaly(predicted_price=3.50, actual_price=3.10, error_dollars=0.40, active_events_count=1) == "OVERESTIMATED_SHOCK"
    assert classify_causal_anomaly(predicted_price=3.00, actual_price=3.40, error_dollars=-0.40, active_events_count=1) == "UNDERESTIMATED_SHOCK"
    assert classify_causal_anomaly(predicted_price=3.50, actual_price=3.10, error_dollars=0.40, active_events_count=0) == "LARGE_OVERESTIMATE"
    assert classify_causal_anomaly(predicted_price=3.20, actual_price=3.10, error_dollars=0.10, directional_hit=0.0) == "DIRECTIONAL_FLIP"
    assert classify_causal_anomaly(predicted_price=3.20, actual_price=3.10, error_dollars=0.10, directional_hit=False) == "DIRECTIONAL_FLIP"
    assert classify_causal_anomaly(predicted_price=3.15, actual_price=3.13, error_dollars=0.02, directional_hit=1.0) == "NORMAL"
    assert classify_causal_anomaly(predicted_price=3.15, actual_price=3.13, error_dollars=0.02, directional_hit=True) == "NORMAL"


def test_evaluate_and_reflect_settled_anomalies():
    """Verify evaluation dataframe scans and triggers reflections for outlier rows."""
    eval_df = pd.DataFrame([
        {
            "region": "Tulsa_OK",
            "forecast_target_date": "2026-09-20",
            "predicted_5d_price": 3.45,
            "actual_5d_price": 3.10,
            "error_dollars": 0.35,
            "directional_hit": 0.0
        },
        {
            "region": "National",
            "forecast_target_date": "2026-09-21",
            "predicted_5d_price": 2.40,
            "actual_5d_price": 2.39,
            "error_dollars": 0.01,
            "directional_hit": 1.0
        }
    ])

    mock_mgr = MagicMock()
    mock_mgr.reflect_on_anomalies.return_value = [
        {
            "region": "Tulsa_OK",
            "title": "Forecast Anomaly: Tulsa_OK on 2026-09-20 (LARGE_OVERESTIMATE)",
            "root_cause": "Model over-projected local refinery run cut impact on pump margins"
        }
    ]

    reflections = evaluate_and_reflect_settled_anomalies(eval_df, memory_manager=mock_mgr)
    assert len(reflections) == 1
    mock_mgr.reflect_on_anomalies.assert_called_once()


def test_enrich_scenario_with_episodic_memory():
    """Verify scenario engine enrichment returns structured precedents."""
    with patch("src.hindsight_context.inject_hindsight_context") as mock_inject:
        mock_inject.return_value = (
            "\n[HISTORICAL EPISODIC MEMORY PRECEDENT & REALIZED ANALOGS]\n• Precedent 1: Hurricane Ida Gulf Outage\n",
            [{"catalyst": "Hurricane Ida Gulf Outage", "price_shock": "+$0.20/gal"}]
        )
        res = enrich_scenario_with_episodic_memory("greenville_hurricane")
        assert res["precedent_count"] == 1
        assert "Hurricane Ida" in res["prompt_context"]


def test_query_episodic_precedents_as_of_and_clean_metadata():
    """Verify query_episodic_precedents enforces as_of point-in-time filtering and removes synthetic defaults (Issue #576 N-5, #580 N-9)."""
    from src.hindsight_context import query_episodic_precedents, format_hindsight_precedent_prompt_block

    mock_mgr = MagicMock()
    mock_mgr.recall.return_value = [
        {
            "memory_id": "mem_past",
            "content": "Delaware City refinery FCC unit trip",
            "metadata": {
                "target_date": "2024-06-01",
                "duration": "4 days",
                "price_shock_dollars": "+$0.12/gal"
            }
        },
        {
            "memory_id": "mem_future",
            "content": "Future planned turnaround",
            "metadata": {
                "target_date": "2026-08-01",
                "duration": "10 days"
            }
        },
        {
            "memory_id": "mem_sparse",
            "content": "Unspecified flaring event",
            "metadata": {}
        }
    ]

    # as_of set to 2025-01-01 should filter out mem_future (2026-08-01)
    precs = query_episodic_precedents("refinery trip", as_of="2025-01-01", memory_manager=mock_mgr)
    assert len(precs) == 2
    assert precs[0]["memory_id"] == "mem_past"
    assert precs[1]["memory_id"] == "mem_sparse"
    # mem_sparse should not have synthetic hallucinated defaults
    assert precs[1]["duration"] == ""
    assert precs[1]["price_shock"] == ""

    block = format_hindsight_precedent_prompt_block(precs)
    assert "Delaware City refinery FCC unit trip" in block
    assert "Unspecified flaring event" in block
    assert "3-7 trading days" not in block
    assert "+$0.08 to +$0.18/gal" not in block
