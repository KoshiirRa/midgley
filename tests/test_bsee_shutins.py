"""Unit tests for direct BSEE hurricane shut-in bulletin parser (Issue #633)."""

import json
import os
from datetime import datetime

from src.bsee_shutins import (
    BSEE_HURRICANE_URL,
    BSEEShutInConnector,
    get_bsee_vintages_as_of,
    parse_bsee_bulletin_html,
    save_bsee_vintage_record,
)


SAMPLE_BSEE_TABLE_HTML = """
<html>
<body>
  <h1>Gulf of Mexico Hurricane Activity Statistics</h1>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Oil Production Shut-In</td><td>28.4%</td></tr>
    <tr><td>Natural Gas Production Shut-In</td><td>19.6%</td></tr>
    <tr><td>Production Platforms Evacuated</td><td>47</td></tr>
  </table>
</body>
</html>
"""

SAMPLE_BSEE_NARRATIVE_HTML = """
<html>
<body>
  <p>BSEE estimates that approximately 42.15% of the current oil production in the Gulf of Mexico
  has been shut-in. Approximately 31.5% of the current natural gas production has been shut-in.
  Personnel have been evacuated from a total of 63 production platforms.</p>
</body>
</html>
"""


def test_parse_bsee_bulletin_html_table():
    parsed = parse_bsee_bulletin_html(SAMPLE_BSEE_TABLE_HTML)
    assert parsed is not None
    assert parsed["bsee_gulf_oil_shutin_pct"] == 28.4
    assert parsed["bsee_gulf_gas_shutin_pct"] == 19.6
    assert parsed["bsee_evacuated_platforms_count"] == 47
    assert parsed["is_storm_evacuation_active"] is True
    assert parsed["source_url"] == BSEE_HURRICANE_URL
    assert parsed["provenance"] == "BSEE_OFFICIAL_BULLETIN"


def test_parse_bsee_bulletin_html_narrative():
    parsed = parse_bsee_bulletin_html(SAMPLE_BSEE_NARRATIVE_HTML)
    assert parsed is not None
    assert parsed["bsee_gulf_oil_shutin_pct"] == 42.15
    assert parsed["bsee_gulf_gas_shutin_pct"] == 31.5
    assert parsed["bsee_evacuated_platforms_count"] == 63
    assert parsed["is_storm_evacuation_active"] is True
    assert parsed["provenance"] == "BSEE_OFFICIAL_BULLETIN"


def test_parse_bsee_bulletin_html_empty_or_unrelated():
    assert parse_bsee_bulletin_html("") is None
    assert parse_bsee_bulletin_html("<html><body>No active storms in the Gulf.</body></html>") is None


def test_parse_bsee_bulletin_html_ignores_script_and_style_blocks():
    html = """
    <html>
    <head>
      <style>body { content: "99.9% of oil shut-in"; }</style>
      <script>var fake = "88.8% of natural gas shut-in and 999 platforms evacuated";</script >
    </head>
    <body>
      <p>Oil Production Shut-In: 12.5%</p>
    </body>
    </html>
    """
    parsed = parse_bsee_bulletin_html(html)
    assert parsed is not None
    assert parsed["bsee_gulf_oil_shutin_pct"] == 12.5
    assert parsed["bsee_gulf_gas_shutin_pct"] == 0.0
    assert parsed["bsee_evacuated_platforms_count"] == 0


def test_connector_uses_html_override_and_persists_government_provenance(tmp_path):
    vintage_path = str(tmp_path / "bsee_vintages.json")
    conn = BSEEShutInConnector(vintage_file=vintage_path)

    res = conn.fetch_gulf_shutin_data(html_override=SAMPLE_BSEE_TABLE_HTML)
    assert res["bsee_gulf_oil_shutin_pct"] == 28.4
    assert res["bsee_gulf_gas_shutin_pct"] == 19.6
    assert res["bsee_evacuated_platforms_count"] == 47
    assert res["provenance"] == "BSEE_OFFICIAL_BULLETIN"
    assert res["source_url"] == BSEE_HURRICANE_URL

    # Verify vintage file written with government provenance
    assert os.path.exists(vintage_path)
    today = datetime.now().strftime("%Y-%m-%d")
    loaded = get_bsee_vintages_as_of(today, filepath=vintage_path)
    assert loaded is not None
    assert loaded["provenance"] == "BSEE_OFFICIAL_BULLETIN"
    assert loaded["bsee_gulf_oil_shutin_pct"] == 28.4


def test_connector_testing_mode_falls_back_to_vintage_without_network(tmp_path, monkeypatch):
    vintage_path = str(tmp_path / "bsee_vintages.json")
    save_bsee_vintage_record(
        {
            "bsee_gulf_oil_shutin_pct": 15.0,
            "bsee_gulf_gas_shutin_pct": 10.0,
            "bsee_evacuated_platforms_count": 12,
            "is_storm_evacuation_active": True,
            "source_url": BSEE_HURRICANE_URL,
            "provenance": "BSEE_OFFICIAL_BULLETIN",
        },
        filepath=vintage_path,
    )

    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setattr("src.bsee_shutins.global_cache.get", lambda _k: None)
    monkeypatch.setattr("src.bsee_shutins.global_cache.set", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("Network call not allowed under TESTING=1")),
    )

    conn = BSEEShutInConnector(vintage_file=vintage_path)
    res = conn.fetch_gulf_shutin_data()
    assert res["bsee_gulf_oil_shutin_pct"] == 15.0
    assert res["bsee_evacuated_platforms_count"] == 12
    assert res["provenance"] == "CACHED_VINTAGE"
