"""
Unit Tests for Component-Level Feature Attribution & Driver Breakdown (Issue #46)
Tests compute_locale_feature_attribution_breakdown for exact marginal attributions,
signed dollar sum consistency, locale component weights, and driver summary text.
"""

import pytest
from src.models import compute_locale_feature_attribution_breakdown, LOCALE_COMPONENT_WEIGHTS


def test_feature_attribution_dollar_sum_consistency():
    """Verify sum(delta_dollars) strictly equals (predicted_price - base_price)."""
    locales = ["National", "Tulsa_OK", "Newark_DE", "Cincinnati_OH", "Greenville_NC", "Charlotte_NC", "Oakland_CA", "BayArea_CA"]
    
    test_cases = [
        (3.184, 3.269),  # +$0.085/gal
        (3.890, 3.845),  # -$0.045/gal
        (3.350, 3.350),  # $0.000/gal
    ]
    
    for loc in locales:
        for base, pred in test_cases:
            res = compute_locale_feature_attribution_breakdown(loc, base, pred)
            expected_total_delta = round(pred - base, 3)
            
            assert res["total_delta_dollars"] == expected_total_delta
            
            comp_sum = round(sum(c["delta_dollars"] for c in res["components"].values()), 3)
            assert comp_sum == expected_total_delta, f"Mismatch in {loc}: sum={comp_sum} != total={expected_total_delta}"
            
            assert len(res["key_drivers"]) == 6
            assert "summary_text" in res
            assert len(res["summary_text"]) > 10


def test_feature_attribution_locale_specific_weights():
    """Verify locale-specific component weight prioritization."""
    # Oakland CA should prioritize tax_regulatory
    oak_res = compute_locale_feature_attribution_breakdown("Oakland_CA", 5.550, 5.635)
    assert oak_res["components"]["tax_regulatory"]["share_pct"] == 35.0
    
    # Tulsa OK should prioritize regional_logistics & refining_crack_margin
    tul_res = compute_locale_feature_attribution_breakdown("Tulsa_OK", 3.890, 3.935)
    assert tul_res["components"]["regional_logistics"]["share_pct"] == 30.0
    assert tul_res["components"]["refining_crack_margin"]["share_pct"] == 30.0
    
    # Greenville NC should prioritize regional_logistics (Colonial Pipeline)
    grn_res = compute_locale_feature_attribution_breakdown("Greenville_NC", 3.250, 3.295)
    assert grn_res["components"]["regional_logistics"]["share_pct"] == 40.0


def test_feature_attribution_summary_text():
    """Verify natural language summary generation for positive, negative, and flat trends."""
    pos = compute_locale_feature_attribution_breakdown("Tulsa_OK", 3.890, 3.935)
    assert "Tulsa OK forecast +$0.045/gal" in pos["summary_text"]
    assert "Driven primarily by" in pos["summary_text"]
    
    neg = compute_locale_feature_attribution_breakdown("Oakland_CA", 5.550, 5.465)
    assert "Oakland CA forecast $-0.085/gal" in neg["summary_text"]
    
    flat = compute_locale_feature_attribution_breakdown("National", 3.184, 3.184)
    assert "National forecast stable ($0.000/gal)" in flat["summary_text"]
