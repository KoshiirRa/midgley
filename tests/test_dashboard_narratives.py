"""
Unit tests for automated narrative synthesis and dashboard narrative card integration (Issue #493).
"""

import os
import pytest
from src.narrative_generator import (
    generate_metro_narrative,
    generate_macro_synthesis_narrative,
    generate_national_wholesale_narrative,
    render_narrative_card_html,
)


def test_generate_metro_narrative_bullish():
    res = generate_metro_narrative(
        metro_key="Tulsa_OK",
        current_price=3.50,
        forecast_price=3.65,
        horizon_days=5,
        logistics_hub="Cushing WTI Storage & West Tulsa HF Sinclair",
        crack_spread=28.5,
        outage_exposure=0.08,
    )
    assert res["metro_key"] == "Tulsa_OK"
    assert res["direction"] == "bullish"
    assert res["delta_dollars"] > 0
    assert "+$" in res["delta_str"]
    assert "Tulsa" in res["narrative"]
    assert "Cushing" in res["narrative"]
    assert len(res["driver_tags"]) >= 1


def test_generate_metro_narrative_bearish():
    res = generate_metro_narrative(
        metro_key="Oakland_CA",
        current_price=5.40,
        forecast_price=5.15,
        horizon_days=5,
        logistics_hub="Chevron Richmond Refinery & CARB LCFS/Cap-and-Trade Standard",
    )
    assert res["metro_key"] == "Oakland_CA"
    assert res["direction"] == "bearish"
    assert res["delta_dollars"] < 0
    assert "-$" in res["delta_str"]
    assert "Oakland" in res["narrative"]
    assert "moderating" in res["narrative"].lower() or "downward" in res["narrative"].lower() or "lower" in res["narrative"].lower() or "falling" in res["narrative"].lower() or "retreating" in res["narrative"].lower() or "relief" in res["narrative"].lower()


def test_generate_metro_narrative_neutral():
    res = generate_metro_narrative(
        metro_key="Newark_DE",
        current_price=3.200,
        forecast_price=3.204,
        horizon_days=5,
    )
    assert res["metro_key"] == "Newark_DE"
    assert res["direction"] == "neutral"
    assert "stable" in res["narrative"].lower() or "range-bound" in res["narrative"].lower() or "balanced" in res["narrative"].lower()


def test_generate_national_wholesale_narrative():
    res = generate_national_wholesale_narrative(
        current_price=2.350,
        forecast_price=2.450,
        horizon_days=5,
    )
    assert res["target_name"] == "National Wholesale RBOB"
    assert res["direction"] == "bullish"
    assert res["delta_dollars"] == pytest.approx(0.10, abs=1e-3)
    assert "National Wholesale" in res["narrative"]
    assert "RBOB" in res["narrative"]


def test_generate_macro_synthesis_narrative():
    prices_map = {
        "National": {"base": 2.35, "pred": 2.40},
        "Tulsa_OK": {"base": 3.10, "pred": 3.15},
        "Newark_DE": {"base": 3.30, "pred": 3.25},
        "Cincinnati_OH": {"base": 3.20, "pred": 3.22},
        "Oakland_CA": {"base": 5.20, "pred": 5.05},
    }
    res = generate_macro_synthesis_narrative(prices_map=prices_map, horizon_days=5)
    assert "macro_summary" in res
    assert "divergence_note" in res
    assert "Executive Multi-Market Synthesis" in res["headline"]
    assert "PADD" in res["divergence_note"] or "macro" in res["macro_summary"].lower() or "gasoline" in res["macro_summary"].lower()


def test_render_narrative_card_html_metro():
    narrative_data = generate_metro_narrative(
        metro_key="Charlotte_NC",
        current_price=3.15,
        forecast_price=3.25,
        horizon_days=5,
        logistics_hub="Colonial & Plantation Pipeline Paw Creek Terminal",
    )
    card_html = render_narrative_card_html(narrative_data, variant="metro")
    assert "Model Narrative &amp; Catalyst Breakdown" in card_html or "Model Narrative & Catalyst Breakdown" in card_html
    assert "Charlotte" in card_html
    assert "Paw Creek" in card_html
    assert "Colonial Pipeline" in card_html


def test_render_narrative_card_html_macro():
    prices_map = {
        "National": {"base": 2.35, "pred": 2.40},
        "Tulsa_OK": {"base": 3.10, "pred": 3.15},
    }
    narrative_data = generate_macro_synthesis_narrative(prices_map=prices_map, horizon_days=5)
    card_html = render_narrative_card_html(narrative_data, variant="macro")
    assert "Macro Cross-Regional Overview" in card_html
    assert "Multi-Region Divergence" in card_html


def test_dashboard_generator_includes_narratives(monkeypatch, tmp_path):
    from src.dashboard_generator import generate_public_dashboard, DOCS_DIR

    # Generate the dashboard pages
    generate_public_dashboard()

    index_path = os.path.join(DOCS_DIR, "index.html")
    national_path = os.path.join(DOCS_DIR, "national.html")
    tulsa_path = os.path.join(DOCS_DIR, "tulsa.html")
    oakland_path = os.path.join(DOCS_DIR, "oakland.html")

    assert os.path.exists(index_path)
    with open(index_path, "r", encoding="utf-8") as f:
        index_content = f.read()
        assert "Macro Cross-Regional Overview" in index_content or "Model Narrative" in index_content

    assert os.path.exists(national_path)
    with open(national_path, "r", encoding="utf-8") as f:
        nat_content = f.read()
        assert "National Wholesale RBOB Term Structure" in nat_content or "Model Narrative" in nat_content

    assert os.path.exists(tulsa_path)
    with open(tulsa_path, "r", encoding="utf-8") as f:
        tul_content = f.read()
        assert "Tulsa" in tul_content
        assert "Model Narrative" in tul_content

    assert os.path.exists(oakland_path)
    with open(oakland_path, "r", encoding="utf-8") as f:
        oak_content = f.read()
        assert "Oakland" in oak_content
        assert "Model Narrative" in oak_content


def test_narrative_attribution_drivers_sign_and_sum():
    """Verify that narrative drivers sum to the forecast delta and share its sign (Issue #604)."""
    metros = [
        ("Greenville_NC", 3.45, 3.405),   # -0.045
        ("Cincinnati_OH", 3.50, 3.462),   # -0.038
        ("Oakland_CA", 5.20, 5.147),      # -0.053
        ("Tulsa_OK", 3.20, 3.160),        # -0.040
        ("Newark_DE", 3.35, 3.315),       # -0.035
        ("Charlotte_NC", 3.30, 3.270),    # -0.030
        ("Port_St_Lucie_FL", 3.50, 3.465),# -0.035
        ("Greenville_NC", 3.40, 3.475),   # +0.075
        ("Cincinnati_OH", 3.50, 3.560),   # +0.060
        ("Oakland_CA", 5.10, 5.200),      # +0.100
    ]

    for metro_key, current_p, forecast_p in metros:
        expected_delta = round(forecast_p - current_p, 3)
        res = generate_metro_narrative(
            metro_key=metro_key,
            current_price=current_p,
            forecast_price=forecast_p,
            horizon_days=5
        )
        assert res["delta_dollars"] == pytest.approx(expected_delta, abs=1e-3)
        drivers = res["key_drivers"]
        assert len(drivers) == 3

        driver_sum = sum(d["impact_dollars"] for d in drivers)
        assert driver_sum == pytest.approx(expected_delta, abs=1e-3), (
            f"{metro_key}: Driver sum {driver_sum} != forecast delta {expected_delta}"
        )

        for d in drivers:
            if expected_delta < -0.005:
                assert d["impact_dollars"] <= 0.0, f"Positive driver under negative forecast: {d}"
                assert "+$" not in d["impact"]
            elif expected_delta > 0.005:
                assert d["impact_dollars"] >= 0.0, f"Negative driver under positive forecast: {d}"
                assert "-$" not in d["impact"]

        # Ensure no contradictory prose
        if expected_delta < -0.005:
            assert "driving upward cost pass-through" not in res["detailed_prose"].lower()


def test_national_narrative_drivers_sign_and_sum():
    """Verify national wholesale narrative drivers sum to delta and match sign (Issue #604)."""
    # Negative delta
    res_neg = generate_national_wholesale_narrative(
        current_price=2.450,
        forecast_price=2.400,
        horizon_days=5
    )
    assert res_neg["delta_dollars"] == pytest.approx(-0.050, abs=1e-3)
    sum_neg = sum(d["impact_dollars"] for d in res_neg["key_drivers"])
    assert sum_neg == pytest.approx(-0.050, abs=1e-3)
    for d in res_neg["key_drivers"]:
        assert d["impact_dollars"] <= 0.0

    # Positive delta
    res_pos = generate_national_wholesale_narrative(
        current_price=2.400,
        forecast_price=2.480,
        horizon_days=5
    )
    assert res_pos["delta_dollars"] == pytest.approx(0.080, abs=1e-3)
    sum_pos = sum(d["impact_dollars"] for d in res_pos["key_drivers"])
    assert sum_pos == pytest.approx(0.080, abs=1e-3)
    for d in res_pos["key_drivers"]:
        assert d["impact_dollars"] >= 0.0


