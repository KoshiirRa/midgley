"""
Unit Tests for OpenAlex Academic Literature Connector (tests/test_academic_openalex.py)
Issue #263: OpenAlex API Integration
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from src.academic_openalex import (
    OpenAlexConnector,
    _load_openalex_cache,
    _save_openalex_cache
)


def test_openalex_init():
    """Verifies default initialization and headers."""
    oa = OpenAlexConnector(mailto="research@midgley.org")
    assert "research@midgley.org" in oa.headers["User-Agent"]


def test_openalex_testing_mode_results():
    """Verifies structured synthetic results returned under TESTING environment."""
    oa = OpenAlexConnector()
    with patch.dict(os.environ, {"TESTING": "1"}):
        results = oa.search_energy_literature(topic="crack spread", limit=3)
        assert len(results) > 0
        assert "title" in results[0]
        assert "doi" in results[0]
        assert "concepts" in results[0]
        assert "authors" in results[0]


def test_openalex_api_success_mock():
    """Verifies response parsing with mocked successful OpenAlex response."""
    oa = OpenAlexConnector()
    mock_payload = {
        "results": [
            {
                "id": "https://openalex.org/W987654321",
                "doi": "https://doi.org/10.1016/j.energy.2025.1001",
                "title": "Refinery Disruptions and Pass-Through Dynamics",
                "publication_year": 2025,
                "cited_by_count": 15,
                "open_access": {"oa_url": "https://oa.org/paper.pdf"},
                "authorships": [{"author": {"display_name": "Jane Doe"}}],
                "concepts": [{"display_name": "Gasoline"}, {"display_name": "Crude Oil"}],
                "abstract_inverted_index": {"Refinery": [0], "shocks": [1], "decay": [2], "rapidly": [3]}
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch.dict(os.environ, {"TESTING": "0", "SUPPRESS_OUTBOUND_APIS": "0"}), \
         patch("requests.get", return_value=mock_resp):
        res = oa.search_energy_literature(topic="refinery shock decay", limit=1)
        assert len(res) == 1
        assert res[0]["title"] == "Refinery Disruptions and Pass-Through Dynamics"
        assert res[0]["authors"] == ["Jane Doe"]
        assert "Gasoline" in res[0]["concepts"]
        assert res[0]["summary_abstract"] == "Refinery shocks decay rapidly"


def test_openalex_api_error_handling():
    """Verifies graceful recovery on network exception or non-200 HTTP code."""
    oa = OpenAlexConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch.dict(os.environ, {"TESTING": "0", "SUPPRESS_OUTBOUND_APIS": "0"}), \
         patch("requests.get", return_value=mock_resp):
        res = oa.search_energy_literature(topic="error topic")
        assert res == []


def test_openalex_prior_bounds():
    """Verifies empirical econometric prior parameter bounds helper."""
    oa = OpenAlexConnector()
    shock_priors = oa.get_econometric_prior_bounds("shock_decay")
    assert shock_priors["parameter"] == "exponential_half_life_days"
    assert shock_priors["recommended_value"] == 4.5
    assert shock_priors["lower_bound"] == 4.0
    assert shock_priors["upper_bound"] == 5.0
    assert len(shock_priors["literature_citations"]) >= 2

    weekend_priors = oa.get_econometric_prior_bounds("weekend_gap_multiplier")
    assert weekend_priors["recommended_value"] == 1.42

    tax_priors = oa.get_econometric_prior_bounds("tax_pass_through")
    assert tax_priors["recommended_value"] == 1.00
