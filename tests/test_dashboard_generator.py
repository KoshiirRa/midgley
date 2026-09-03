import os
import sys
import pytest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dashboard_generator import (
    generate_public_dashboard,
    INDEX_PATH,
    NATIONAL_PATH,
    TULSA_PATH,
    NEWARK_PATH,
    CINCINNATI_PATH,
    GREENVILLE_PATH,
    CHARLOTTE_PATH,
    OAKLAND_PATH,
    BAYAREA_PATH,
    MATH_PATH,
    get_analytics_script,
)


def test_dashboard_generation_and_math_katex():
    """Verify that generate_public_dashboard generates clean HTML files
    and that docs/math.html contains valid KaTeX markup without Python
    string escape character corruption.
    """
    # Execute public dashboard generation
    generate_public_dashboard()

    # Verify existence of all expected dashboard HTML files
    for path in [INDEX_PATH, NATIONAL_PATH, TULSA_PATH, NEWARK_PATH, CINCINNATI_PATH, GREENVILLE_PATH, OAKLAND_PATH, BAYAREA_PATH, MATH_PATH]:
        assert os.path.exists(path), f"Expected file does not exist: {path}"
        assert os.path.getsize(path) > 0, f"Generated file is empty: {path}"

    # Read generated docs/math.html content
    with open(MATH_PATH, "r", encoding="utf-8") as f:
        math_content = f.read()

    # Check for unwanted ASCII control characters in docs/math.html
    ctrl_chars = [
        ("\t", "Tab"),
        ("\f", "Formfeed"),
        ("\r", "Carriage Return"),
        ("\a", "Bell"),
        ("\b", "Backspace"),
    ]
    for char, name in ctrl_chars:
        count = math_content.count(char)
        assert count == 0, f"Found {count} unescaped '{name}' control character(s) in docs/math.html"

    # Verify presence of expected LaTeX macros in Sections 7, 8, 9, and 10
    expected_macros = [
        r"\text",
        r"\frac",
        r"\right",
        r"\alpha",
        r"\beta",
        r"\boldsymbol",
        r"\times",
    ]
    for macro in expected_macros:
        assert macro in math_content, f"Expected LaTeX macro '{macro}' not found in docs/math.html"

    # Verify specific equations in Sections 07, 08, 09, and 10
    assert r"\mathbf{V}_{\text{Finlight}, t}" in math_content
    assert r"\mathbf{M}_t = \mathbf{M}_{t-1} \cdot \exp\left(-\frac{\ln 2}{t_{1/2}}\right) + \mathbf{V}_t" in math_content
    assert r"\min_{\boldsymbol{\beta}}" in math_content
    assert r"T_{\text{CARB}}" in math_content


def test_oakland_and_bayarea_consistency():
    """Verify that Oakland and Bay Area base prices and labels are consistent
    across index.html, oakland.html, and bayarea.html without legacy hardcoded mismatches.
    """
    generate_public_dashboard()

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_html = f.read()
    with open(OAKLAND_PATH, "r", encoding="utf-8") as f:
        oakland_html = f.read()
    with open(BAYAREA_PATH, "r", encoding="utf-8") as f:
        bayarea_html = f.read()

    # Ensure no legacy hardcoded $4.95, $5.05, or $5.12 mismatch strings exist in generated pages
    assert "($4.950/gal base)" not in oakland_html
    assert "Oakland, CA Retail ($4.95 base)" not in oakland_html
    assert "Oakland / East Bay ($4.95 base)" not in bayarea_html
    assert "SF Bay Area 9-County Avg ($5.05 base)" not in bayarea_html
    assert "San Francisco ($5.12 base)" not in bayarea_html

    # Check that sub-locale 5-day model targets and breakdown matrix table exist in bayarea.html
    assert "San Francisco Metro" in bayarea_html
    assert "San Jose / Silicon Valley" in bayarea_html
    assert "North Bay / Solano" in bayarea_html
    assert "5-Day Target:" in bayarea_html
    assert "NorCal Sub-Locale Quantitative Model Forecasts" in bayarea_html
    assert "Primary Logistics & Tax Overhead Driver" in bayarea_html


def test_katex_mobile_responsive_css():
    """Verify that responsive KaTeX mobile CSS rules and overflow-x container protection
    are injected across all generated HTML dashboard pages.
    """
    generate_public_dashboard()

    page_paths = [
        INDEX_PATH,
        NATIONAL_PATH,
        TULSA_PATH,
        NEWARK_PATH,
        CINCINNATI_PATH,
        OAKLAND_PATH,
        BAYAREA_PATH,
        MATH_PATH,
    ]

    for path in page_paths:
        assert os.path.exists(path), f"Page missing: {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        assert ".katex-display" in content, f"Missing .katex-display CSS in {path}"
        assert "overflow-x: auto" in content, f"Missing overflow-x: auto in {path}"
        assert "@media (max-width: 640px)" in content, f"Missing mobile breakpoint in {path}"

    # Verify regional rack margin cards contain overflow-x protection
    with open(NEWARK_PATH, "r", encoding="utf-8") as f:
        newark_html = f.read()
        assert "overflow-x-auto" in newark_html

    with open(TULSA_PATH, "r", encoding="utf-8") as f:
        tulsa_html = f.read()
        assert "overflow-x-auto" in tulsa_html

    with open(CINCINNATI_PATH, "r", encoding="utf-8") as f:
        cin_html = f.read()
        assert "overflow-x-auto" in cin_html


def test_last_run_intelligence_audit_card_daily_batch(tmp_path):
    """Verifies that the audit card renders properly for a scheduled daily batch run state."""
    import json
    import pandas as pd
    from src.dashboard_generator import (
        parse_last_run_intelligence,
        build_last_run_audit_card_html
    )

    hist_file = tmp_path / "prediction_history.csv"
    df = pd.DataFrame([{
        "log_timestamp": "2026-08-26 02:00:00",
        "forecast_target_date": "2026-08-31",
        "region": "National",
        "model_version": "v1.4-Finlight-Ridge",
        "run_type": "DAILY_BATCH",
        "headline_trigger": "",
        "current_base_price": 3.184,
        "predicted_5d_price": 3.077,
        "predicted_direction": "DOWN",
        "actual_5d_price": None,
        "actual_direction": "",
        "error_dollars": None,
        "directional_hit": None
    }])
    df.to_csv(hist_file, index=False)

    intraday_file = tmp_path / "intraday_events.json"
    with open(intraday_file, "w", encoding="utf-8") as f:
        json.dump([], f)

    audit_data = parse_last_run_intelligence(history_path=str(hist_file), intraday_path=str(intraday_file))
    assert audit_data["run_type"] == "DAILY_BATCH"
    assert audit_data["headline_trigger"] == ""

    card_html = build_last_run_audit_card_html(audit_data)
    assert "Last Run Intelligence & Impact Audit" in card_html
    assert "Scheduled Daily Batch" in card_html
    assert "DAILY_BATCH" in card_html
    assert "Supply Disruption Score" in card_html
    assert "Prediction Revisions Delta" in card_html
    assert "Technical Analysis" in card_html
    assert "Simple Summary" in card_html
    assert "Headline Impact Feeds" in card_html
    assert "href=" in card_html


def test_last_run_intelligence_audit_card_intraday_anomaly(tmp_path):
    """Verifies that the audit card renders properly for an intraday anomaly shock revision state."""
    import json
    import pandas as pd
    from src.dashboard_generator import (
        parse_last_run_intelligence,
        build_last_run_audit_card_html
    )

    hist_file = tmp_path / "prediction_history.csv"
    df = pd.DataFrame([{
        "log_timestamp": "2026-08-26 12:30:00",
        "forecast_target_date": "2026-08-31",
        "region": "National",
        "model_version": "v1.4-Finlight-Intraday",
        "run_type": "INTRADAY_REVISION",
        "headline_trigger": "Canada Announces Retaliatory Tariffs as Trade War Escalates",
        "current_base_price": 3.184,
        "predicted_5d_price": 3.250,
        "predicted_direction": "UP",
        "actual_5d_price": None,
        "actual_direction": "",
        "error_dollars": None,
        "directional_hit": None
    }])
    df.to_csv(hist_file, index=False)

    intraday_file = tmp_path / "intraday_events.json"
    events = [{
        "timestamp": "2026-08-26T12:30:00",
        "headline": "Canada Announces Retaliatory Tariffs as Trade War Escalates",
        "source": "Webhook",
        "url": "https://news.google.com/articles/tariffs_123",
        "is_anomaly": True,
        "scores": {
            "geopolitical_risk": 0.85,
            "supply_disruption": 0.75,
            "demand_sentiment": 0.0,
            "opec_action": 0.0,
            "overall_price_pressure": 0.52
        }
    }]
    with open(intraday_file, "w", encoding="utf-8") as f:
        json.dump(events, f)

    audit_data = parse_last_run_intelligence(history_path=str(hist_file), intraday_path=str(intraday_file))
    assert audit_data["run_type"] == "INTRADAY_REVISION"
    assert "Retaliatory Tariffs" in audit_data["headline_trigger"]
    assert audit_data["scores"]["supply_disruption"] == 0.75

    card_html = build_last_run_audit_card_html(audit_data)
    assert "Last Run Intelligence & Impact Audit" in card_html
    assert "Intraday Anomaly Shock" in card_html
    assert "INTRADAY_REVISION" in card_html
    assert "Canada Announces Retaliatory Tariffs" in card_html
    assert "0.75" in card_html  # Supply disruption score
    assert "0.52" in card_html  # Price pressure score
    assert "Technical Analysis" in card_html
    assert "Simple Summary" in card_html
    assert "Exogenous supply disruption (0.75)" in card_html
    assert "Breaking news shows gas supply problems" in card_html
    assert "https://news.google.com/search?q=" in card_html

    # Verify all modeled regions and trend arrow indicators exist in Column 3
    modeled_names = ["National Wholesale", "Tulsa, OK Retail", "Newark, DE Retail", "Cincinnati, OH/KY", "Greenville, NC Retail", "Charlotte, NC Retail", "Oakland, CA Retail", "SF Bay Area Region"]
    for reg_name in modeled_names:
        assert reg_name in card_html, f"Region name '{reg_name}' missing from audit card HTML"

    assert "fa-arrow-" in card_html, "Trend arrow icon missing from audit card HTML"


def test_last_run_intelligence_audit_card_fallback_on_missing_files(tmp_path):
    """Verifies that parse_last_run_intelligence and build_last_run_audit_card_html execute cleanly
    with fallback defaults when history or intraday event files do not exist.
    """
    from src.dashboard_generator import (
        parse_last_run_intelligence,
        build_last_run_audit_card_html
    )

    non_existent_history = str(tmp_path / "non_existent_history.csv")
    non_existent_intraday = str(tmp_path / "non_existent_intraday.json")

    audit_data = parse_last_run_intelligence(history_path=non_existent_history, intraday_path=non_existent_intraday)
    assert audit_data["run_type"] == "DAILY_BATCH"
    assert audit_data["headline_trigger"] == ""
    assert "supply_disruption" in audit_data["scores"]

    card_html = build_last_run_audit_card_html(audit_data)
    assert "Last Run Intelligence & Impact Audit" in card_html
    assert "Scheduled Daily Batch" in card_html
    assert '<a href="technical_breakdown.html"' in card_html


def test_generate_technical_breakdown_file(tmp_path):
    """Verifies that generate_technical_breakdown_file creates HTML and MD breakdown reports
    with exact substituted numerical values for all variables.
    """
    import json
    from src.dashboard_generator import (
        parse_last_run_intelligence,
        build_last_run_audit_card_html,
        generate_technical_breakdown_file
    )

    audit_data = {
        "run_type": "INTRADAY_REVISION",
        "headline_trigger": "OPEC Emergency Production Cut Announced",
        "log_timestamp": "2026-08-28 14:00:00",
        "scores": {
            "supply_disruption": 0.80,
            "overall_price_pressure": 0.52,
            "geopolitical_risk": 0.80,
            "demand_sentiment": 0.00,
            "opec_action": 0.50
        },
        "decay_half_life": 5.0,
        "headline_items": [{"headline": "OPEC Emergency Production Cut Announced", "url": "https://news.google.com", "source": "Reuters"}],
        "region_deltas": [
            {"key": "National", "name": "National Wholesale", "base_price": 3.184, "predicted_price": 3.250, "delta": 0.066, "pct_change": 2.07},
            {"key": "Tulsa_OK", "name": "Tulsa, OK Retail", "base_price": 3.890, "predicted_price": 3.780, "delta": -0.110, "pct_change": -2.83}
        ]
    }

    docs_dir = str(tmp_path / "docs")
    generate_technical_breakdown_file(audit_data, docs_dir=docs_dir)

    html_file = tmp_path / "docs" / "technical_breakdown.html"
    md_file = tmp_path / "docs" / "technical_breakdown.md"

    assert html_file.exists()
    assert md_file.exists()

    html_text = html_file.read_text(encoding="utf-8")
    md_text = md_file.read_text(encoding="utf-8")

    assert "Full Technical Analysis & Specific-Run Math Audit" in html_text
    assert "0.80" in html_text
    assert "0.52" in html_text
    assert "0.4000" in html_text
    assert "$3.250/gal" in html_text
    assert "OPEC Emergency Production Cut Announced" in html_text

    assert "Midgley LLM Energy Price Forecasting Engine" in md_text
    assert "- **Supply Disruption Score ($S$):** `0.80`" in md_text
    assert "$M_5 = 0.8000 \\times 0.50000 = 0.4000$" in md_text

    # Verify JSON payload exports in docs/runs/
    latest_json = tmp_path / "docs" / "runs" / "latest.json"
    index_json = tmp_path / "docs" / "runs" / "index.json"

    assert latest_json.exists()
    assert index_json.exists()

    payload_data = json.loads(latest_json.read_text(encoding="utf-8"))
    assert payload_data["factor_scores"]["supply_disruption"] == 0.80
    assert payload_data["decay_math"]["m5"] == 0.4000
    assert payload_data["primary_trigger"] == "OPEC Emergency Production Cut Announced"

    card_html = build_last_run_audit_card_html(audit_data)
    assert '<a href="technical_breakdown.html"' in card_html
    assert "Technical Analysis" in card_html


def test_cloudflare_analytics_injection():
    """Verify Option A environment isolation for Cloudflare Web Analytics:
    - Returns empty string when CLOUDFLARE_ANALYTICS_TOKEN is not in os.environ.
    - Emits beacon script tag when CLOUDFLARE_ANALYTICS_TOKEN is provided.
    - Verified that generated HTML files omit analytics when token is unset.
    """
    # 1. When token is missing from environment
    old_env = os.environ.pop("CLOUDFLARE_ANALYTICS_TOKEN", None)
    try:
        script_out = get_analytics_script()
        assert script_out == "", "Expected empty string when CLOUDFLARE_ANALYTICS_TOKEN is unset"

        # Generate dashboard without token and verify HTML files have no analytics script
        generate_public_dashboard()
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index_content = f.read()
        assert "beacon.min.js" not in index_content

        # 2. When token is present in environment
        test_token = "test_cf_token_xyz987"
        os.environ["CLOUDFLARE_ANALYTICS_TOKEN"] = test_token
        script_out = get_analytics_script()
        assert "beacon.min.js" in script_out
        assert f'"token": "{test_token}"' in script_out

        # Generate dashboard with token and verify HTML index contains analytics script
        generate_public_dashboard()
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index_with_analytics = f.read()
        assert "beacon.min.js" in index_with_analytics
        assert f'"token": "{test_token}"' in index_with_analytics

    finally:
        # Restore environment
        if old_env is not None:
            os.environ["CLOUDFLARE_ANALYTICS_TOKEN"] = old_env
        else:
            os.environ.pop("CLOUDFLARE_ANALYTICS_TOKEN", None)


def test_all_regional_dashboard_pages_have_dedicated_driver_cards():
    """Verify Issue #35: Ensure that ALL localized regional public web dashboard pages
    (Tulsa, Newark, Cincinnati, Greenville, Charlotte, Oakland, and Bay Area)
    display dedicated visual cards detailing their unique regional econometric drivers,
    refining logistics, tax structures, and physical delivery hub dynamics.
    """
    generate_public_dashboard()

    regional_paths = [
        TULSA_PATH,
        NEWARK_PATH,
        CINCINNATI_PATH,
        GREENVILLE_PATH,
        CHARLOTTE_PATH,
        OAKLAND_PATH,
        BAYAREA_PATH,
    ]

    for path in regional_paths:
        assert os.path.exists(path), f"Regional page missing: {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for dedicated visual card header section
        assert "Regional Econometric Drivers & Physical Infrastructure Factors" in content, (
            f"Missing dedicated driver & infrastructure card header in {path}"
        )


def test_issue_154_dom_xss_sanitization(tmp_path):
    """Verify Issue #154: Ensure that generated technical breakdown reports sanitize DOM inputs,
    avoid unsafe .innerHTML assignments, use encodeURIComponent in switchRun(), and HTML-escape
    headline triggers and bulletins.
    """
    from src.dashboard_generator import generate_technical_breakdown_file

    audit_data = {
        "run_type": "INTRADAY_REVISION",
        "headline_trigger": "<script>alert('xss_trigger')</script>",
        "log_timestamp": "2026-08-30 20:00:00",
        "scores": {
            "supply_disruption": 0.50,
            "overall_price_pressure": 0.20,
            "geopolitical_risk": 0.10,
            "demand_sentiment": 0.00,
            "opec_action": 0.00
        },
        "decay_half_life": 5.0,
        "headline_items": [
            {
                "headline": "<b>Refinery Outage</b> <img src=x onerror=alert(1)>",
                "url": "https://example.com/test?q=<script>",
                "source": "<b>Test_Source</b>"
            }
        ],
        "region_deltas": [
            {"key": "Tulsa_OK", "name": "Tulsa & Metro <OK>", "base_price": 3.89, "predicted_price": 3.75, "delta": -0.14, "pct_change": -3.6}
        ]
    }

    docs_dir = str(tmp_path / "docs")
    generate_technical_breakdown_file(audit_data, docs_dir=docs_dir)

    html_file = tmp_path / "docs" / "technical_breakdown.html"
    assert html_file.exists()

    content = html_file.read_text(encoding="utf-8")

    # 1. Verify no unsafe innerHTML = '' DOM sink exists
    assert "sel.innerHTML = '';" not in content
    assert "sel.replaceChildren()" in content

    # 2. Verify encodeURIComponent is used in switchRun
    assert "encodeURIComponent(runId)" in content

    # 3. Verify HTML-escaping of un-sanitized triggers and news bulletins
    assert "<script>alert('xss_trigger')</script>" not in content
    assert "&lt;script&gt;alert(&#x27;xss_trigger&#x27;)&lt;/script&gt;" in content

    assert "<b>Refinery Outage</b>" not in content
    assert "&lt;b&gt;Refinery Outage&lt;/b&gt;" in content

    assert "&lt;b&gt;Test_Source&lt;/b&gt;" in content


def test_feature_attribution_card_in_regional_pages():
    """Verify that all regional model pages contain the Component-Level Feature Attribution card."""
    generate_public_dashboard()

    pages = [INDEX_PATH, NATIONAL_PATH, TULSA_PATH, NEWARK_PATH, CINCINNATI_PATH, GREENVILLE_PATH, CHARLOTTE_PATH, OAKLAND_PATH, BAYAREA_PATH]

    for p in pages:
        with open(p, "r", encoding="utf-8") as f:
            html = f.read()
        assert "Component-Level Feature Attribution & Driver Breakdown" in html, f"Missing feature attribution card in {p}"
        assert "Executive Model Attribution Summary:" in html, f"Missing attribution summary in {p}"
        assert "Model Share Weight" in html, f"Missing model share weight in {p}"


def test_scoreboard_section_in_index_html():
    """Verify that index.html contains the Realized-vs-Predicted Rolling Scoreboard section."""
    generate_public_dashboard()

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    assert "Realized-vs-Predicted Rolling Model Scoreboard" in html
    assert "MLOps Continuous Performance Scoreboard" in html
    assert "Regional Accuracy Matrix" in html
    assert "Recent Completed Forecast Evaluations" in html










