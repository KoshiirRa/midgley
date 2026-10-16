"""
Unit Tests for Enverus / Drillinginfo Daily Rig Count Ingestion & Cloudflare Browser Rendering (Issues #533, #640)
"""

import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.enverus_rig_feed import (
    EnverusRigFeedConnector,
    get_enverus_rig_feed,
    parse_enverus_markdown,
    ENVERUS_BENCHMARK_FIXTURE
)
from src.http_client import MIDGLEY_AGENT_USER_AGENT
from src.lookup_cache import global_cache

SAMPLE_CLOUDFLARE_MARKDOWN = """### U.S. drilling activity starts the year with a 15-rig drop

The U.S. rig count reached 657 during the week ended Jan. 3, down 15 rigs from the previous week's high point, according to Enverus Foundations data. The count is down 18 rigs, or 3%, in the last month and down 204 rigs, or 24%, YOY. All numbers discussed are weekly peaks to avoid the sometimes wide variability of daily numbers.

Most of the decrease in the last week came from drilling programs outside the major basins. Among the major basins, the Gulf Coast's two-rig drop was the largest, leaving it with 73 rigs running. Appalachia and the Permian dropped one rig each to 40 and 293. The Williston Basin added one rig to reach 35, while the Anadarko and DJ basins were flat at 52 and 15 rigs.

Total Orientation PlayWeekMonthYear

### Rig Count by Basin

| Play | 10/07/26 | 10/08/26 | 10/09/26 | 10/10/26 | 10/11/26 | 10/12/26 | 10/13/26 | 10/14/26 | 1 Day Δ | % | 1 Month Δ | % | 1 Year Δ | % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ANADARKO BASIN | 59 | 58 | 58 | 58 | 58 | 58 | 64 | 64 | 0 | 0 | -2 | -3 | 17 | 36.2 |
| APPALACHIA | 35 | 33 | 34 | 34 | 34 | 35 | 34 | 33 | -1 | -2.9 | -1 | -2.9 | -5 | -13.2 |
| DJ BASIN | 7 | 11 | 10 | 10 | 10 | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| GULF COAST BASIN (INCLUDING EAGLE FORD) | 69 | 69 | 68 | 68 | 67 | 68 | 71 | 72 | 1 | 1.4 | 2 | 2.9 | 10 | 16.1 |
| PERMIAN | 252 | 248 | 251 | 254 | 255 | 255 | 251 | 254 | 3 | 1.2 | 3 | 1.2 | 24 | 10.4 |
| WILLISTON BASIN | 38 | 38 | 38 | 38 | 38 | 38 | 36 | 36 | 0 | 0 | -1 | -2.7 | 4 | 12.5 |
| OTHER | 199 | 201 | 200 | 200 | 200 | 202 | 190 | 187 | -3 | -1.6 | -6 | -3.1 | 36 | 23.8 |
| Total | 659 | 658 | 659 | 662 | 662 | 666 | 656 | 656 | 0 | 0 | -5 | -0.8 | 86 | 15.1 |
"""


def test_user_agent_policy():
    """Verify MidgleyAgent policy string format and production dashboard link."""
    assert "MidgleyAgent" in MIDGLEY_AGENT_USER_AGENT
    assert "https://koshiirra.github.io/midgley/" in MIDGLEY_AGENT_USER_AGENT


def test_parse_enverus_markdown():
    """Tests parsing raw markdown output from Cloudflare Browser Rendering Playground."""
    res = parse_enverus_markdown(SAMPLE_CLOUDFLARE_MARKDOWN)
    assert res["status"] == "success"
    assert res["source"] == "CLOUDFLARE_BROWSER_RENDERING"
    assert res["total_rigs"] == 656
    assert res["as_of"] == "2026-10-14"
    assert res["analysis_title"] == "U.S. drilling activity starts the year with a 15-rig drop"
    assert "Enverus Foundations data" in res["analysis_text"]

    basins = {b["play"]: b for b in res["basins"]}
    assert "PERMIAN" in basins
    assert basins["PERMIAN"]["latest_count"] == 254
    assert basins["PERMIAN"]["day_delta"] == 3.0
    assert basins["PERMIAN"]["day_pct"] == 1.2

    assert "GULF COAST BASIN (INCLUDING EAGLE FORD)" in basins
    assert basins["GULF COAST BASIN (INCLUDING EAGLE FORD)"]["latest_count"] == 72
    assert basins["GULF COAST BASIN (INCLUDING EAGLE FORD)"]["day_delta"] == 1.0


def test_enverus_connector_worker_fetch():
    """Tests fetching telemetry from Midgley Cloudflare Edge Worker."""
    connector = EnverusRigFeedConnector(worker_url="https://mock-worker.midgley.local")

    with patch.dict(os.environ, {"TESTING": "0"}):
        with patch("src.enverus_rig_feed.http_get") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "status": "success",
                "source": "CLOUDFLARE_BROWSER_RENDERING",
                "as_of": "2026-10-14",
                "total_rigs": 656,
                "basins": [{"play": "PERMIAN", "latest_count": 254, "day_delta": 3, "day_pct": 1.2}]
            }
            mock_http.return_value = mock_resp

            data = connector.fetch_from_worker()
            assert data is not None
            assert data["total_rigs"] == 656
            assert data["source"] == "CLOUDFLARE_BROWSER_RENDERING"


def test_enverus_connector_browser_run_fetch():
    """Tests direct Cloudflare Browser Run REST API execution and markdown parsing."""
    connector = EnverusRigFeedConnector(account_id="test_account_123")

    with patch.dict(os.environ, {"TESTING": "0", "CLOUDFLARE_API_TOKEN": "mock_token_abc"}):
        with patch("src.enverus_rig_feed.http_post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "success": True,
                "result": SAMPLE_CLOUDFLARE_MARKDOWN
            }
            mock_post.return_value = mock_resp

            data = connector.fetch_via_cloudflare_browser_run()
            assert data is not None
            assert data["total_rigs"] == 656
            assert data["source"] == "CLOUDFLARE_BROWSER_RENDERING"
            assert any(b["play"] == "PERMIAN" and b["latest_count"] == 254 for b in data["basins"])


def test_enverus_connector_direct_api_fetch():
    """Tests direct Drillinginfo REST API fallback."""
    connector = EnverusRigFeedConnector()

    with patch.dict(os.environ, {"TESTING": "0"}):
        with patch("src.enverus_rig_feed.http_get") as mock_http:
            def side_effect(url, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                if "OverTable" in url:
                    resp.json.return_value = {
                        "data": [
                            {"play": "PERMIAN", "10/14/26": 254, "da_delta": 3, "da_pct": 1.2},
                            {"play": "Total", "10/14/26": 656, "da_delta": 0, "da_pct": 0.0}
                        ]
                    }
                elif "Count" in url:
                    resp.text = "656"
                elif "lastupdate" in url:
                    resp.text = '"2026-10-14"'
                elif "analysis" in url:
                    resp.json.return_value = {"text": "Weekly test analysis"}
                return resp

            mock_http.side_effect = side_effect
            data = connector.fetch_from_direct_api()
            assert data is not None
            assert data["status"] == "success"
            assert data["total_rigs"] == 656
            assert any(b["play"] == "PERMIAN" and b["latest_count"] == 254 for b in data["basins"])


def test_enverus_basin_metrics_dataframe():
    """Tests conversion of latest rig payload into structured pandas DataFrame."""
    connector = EnverusRigFeedConnector()
    df = connector.get_basin_metrics_dataframe()

    assert not df.empty
    assert "date" in df.columns
    assert "enverus_total_rigs" in df.columns
    assert "enverus_permian_rigs" in df.columns
    assert "enverus_gulf_coast_rigs" in df.columns
    assert df.iloc[0]["enverus_total_rigs"] == 656
    assert df.iloc[0]["enverus_permian_rigs"] == 254
    assert df.iloc[0]["enverus_gulf_coast_rigs"] == 72
