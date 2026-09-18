"""
Unit Tests for AIHawk Self-Healing DOM Automation & State Open Data Ledger (Issue #309)
Tests fuzzy DOM selector matching, tax rate extraction resilience, and ledger persistence.
"""

import os
import json
import pytest
from src.state_open_data import (
    SelfHealingDOMParser,
    StateOpenDataLedger,
    UniversalStateOpenDataConnector,
    STATE_METADATA
)


def test_self_healing_dom_parser_table_extraction():
    parser = SelfHealingDOMParser()

    # Mock dynamic HTML from state department of taxation
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Ohio Department of Taxation - Motor Fuel Rates</title></head>
    <body>
        <div class="main-content-area">
            <h1>Motor Fuel Tax Information & Schedules</h1>
            <table class="tax-rate-table-2026 responsive-table">
                <thead>
                    <tr><th>Fuel Category</th><th>Effective Date</th><th>Rate per Gallon</th></tr>
                </thead>
                <tbody>
                    <tr><td>Gasoline / Unleaded</td><td>01/01/2026</td><td>$0.3850 / gal</td></tr>
                    <tr><td>Diesel / Special Fuel</td><td>01/01/2026</td><td>$0.4700 / gal</td></tr>
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    rate = parser.parse_tax_rate_from_html(sample_html, state_code="OH")
    assert rate is not None
    assert rate == 0.385


def test_self_healing_dom_parser_cents_format():
    parser = SelfHealingDOMParser()

    sample_html_cents = """
    <section class="portal-card">
        <h3>North Carolina Motor Fuels Tax Rates</h3>
        <p>The state excise tax rate on gasoline is currently <strong>40.4 cents per gallon</strong> for the semi-annual period.</p>
    </section>
    """

    rate = parser.parse_tax_rate_from_html(sample_html_cents, state_code="NC")
    assert rate is not None
    assert rate == 0.404


def test_self_healing_dom_parser_resilience_to_broken_dom():
    parser = SelfHealingDOMParser()

    # Highly messy unstructured snippet with script tags and noise
    messy_html = """
    <script>var x = 123; function test() { return "fuel"; }</script>
    <div id="wrapper">
        <div class="random-ad">Ad banner 99.99</div>
        <div class="dept-text">
            <span>Official State Excise Tax Schedule:</span>
            <span>Motor fuel unleaded rate is $0.230 per gallon for all distributors.</span>
        </div>
    </div>
    """

    rate = parser.parse_tax_rate_from_html(messy_html, state_code="DE")
    assert rate is not None
    assert rate == 0.230


def test_state_open_data_ledger_persistence(tmp_path):
    ledger_path = str(tmp_path / "test_state_open_data.json")
    ledger = StateOpenDataLedger(filepath=ledger_path)

    # Initial load should be empty states
    data = ledger.load_ledger()
    assert data["total_states"] == len(STATE_METADATA)

    # Update state rate
    entry = ledger.update_state_rate("OH", 0.385, source_type="aihawk_dom_parser")
    assert entry["state_code"] == "OH"
    assert entry["excise_tax_per_gal"] == 0.385
    assert entry["source_type"] == "aihawk_dom_parser"

    # Verify retrieval
    stored = ledger.get_state_rate("OH")
    assert stored is not None
    assert stored["excise_tax_per_gal"] == 0.385

    # Sync all states
    synced = ledger.sync_all_states()
    assert len(synced["states"]) >= len(STATE_METADATA)
    assert synced["states"]["CA"]["excise_tax_per_gal"] == 0.634
