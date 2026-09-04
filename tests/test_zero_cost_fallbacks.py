"""
Unit Test Suite for Zero-Cost Fallback Providers & Basic Tier Token Savings (Issue #196)

Verifies:
1. Basic tier API key requests route away from paid LLM APIs to zero-cost providers.
2. ZeroCostProviderHook interface & Kaggle open-source LLM hook readiness.
3. Domain NLP lexicon extraction accuracy across geopolitical, supply, OPEC, social, and weather taxonomies.
4. FallbackTelemetryLogger persistent accounting, token savings, and USD estimation.
5. GET /api/v1/telemetry/fallback-status REST API schema.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from src.fallback_telemetry import FallbackTelemetryLogger, fallback_logger
from src.event_analyzer import (
    extract_event_features_llm,
    extract_event_features_rule_based,
    ZeroCostProviderHook,
    TIER_3_OFFLINE_LEXICON
)
from src.api_server import app

client = TestClient(app)


def test_fallback_telemetry_logger_recording(tmp_path):
    test_file = str(tmp_path / "test_fallback_telemetry.json")
    logger = FallbackTelemetryLogger(filepath=test_file)

    summary_initial = logger.get_summary()
    assert summary_initial["total_zero_cost_invocations"] == 0
    assert summary_initial["basic_tier_routed_count"] == 0

    # Record 2 basic tier invocations
    logger.record_fallback_invocation(provider="lexicon", is_basic_tier=True, latency_ms=1.5, tokens_saved=350)
    logger.record_fallback_invocation(provider="kaggle_llm_hook", is_basic_tier=True, latency_ms=2.0, tokens_saved=350)

    summary_after = logger.get_summary()
    assert summary_after["total_zero_cost_invocations"] == 2
    assert summary_after["basic_tier_routed_count"] == 2
    assert summary_after["tokens_saved"] == 700
    assert summary_after["estimated_usd_saved"] > 0.0
    assert summary_after["provider_breakdown"]["lexicon"] == 1
    assert summary_after["provider_breakdown"]["kaggle_llm_hook"] == 1


def test_zero_cost_provider_hook():
    headline = "Refinery fire halts production in Delaware City amid hurricane warning"
    scores = ZeroCostProviderHook.extract_zero_cost_scores(headline, is_basic_tier=True)

    assert isinstance(scores, dict)
    assert "geopolitical_risk" in scores
    assert "supply_disruption" in scores
    assert scores["supply_disruption"] > 0.5


def test_basic_tier_event_extraction_routing():
    headline = "OPEC+ announces surprise voluntary production cut of 1M bpd"
    
    # Force basic tier routing
    scores = extract_event_features_llm(headline, api_key="dummy_key", tier="basic")

    assert isinstance(scores, dict)
    assert scores["opec_action"] > 0.5
    assert scores["overall_price_pressure"] > 0.0


def test_expanded_domain_lexicons():
    # Geopolitical war/sanction
    geo = extract_event_features_rule_based("Houthi missile attack halts tanker traffic in Strait of Hormuz")
    assert geo["geopolitical_risk"] >= 0.8

    # Supply disruption & NOAA weather
    supply = extract_event_features_rule_based("NOAA SPC high risk tornado outbreak damages Catlettsburg refinery unit")
    assert supply["supply_disruption"] >= 0.8

    # Executive social media dovish post
    social = extract_event_features_rule_based("Trump tweet urges OPEC to lower gas prices immediately")
    assert social["demand_sentiment"] >= 0.4

    # OPEC hike
    opec_hike = extract_event_features_rule_based("Saudi Arabia announces OPEC+ production hike to phase out cuts")
    assert opec_hike["opec_action"] < 0.0


def test_fallback_telemetry_rest_endpoint():
    response = client.get("/api/v1/telemetry/fallback-status")
    assert response.status_code == 200
    data = response.json()
    assert "total_zero_cost_invocations" in data
    assert "basic_tier_routed_count" in data
    assert "tokens_saved" in data
    assert "estimated_usd_saved" in data
    assert "provider_breakdown" in data
