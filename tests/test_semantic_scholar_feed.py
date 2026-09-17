"""
Unit Tests for Semantic Scholar Academic Graph Connector (tests/test_semantic_scholar_feed.py)
Issue #264: Semantic Scholar API Integration
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from src.semantic_scholar_feed import (
    SemanticScholarConnector,
    _load_semantic_scholar_cache,
    _save_semantic_scholar_cache
)


def test_semantic_scholar_init():
    """Verifies initialization with optional API key header."""
    ss = SemanticScholarConnector(api_key="test_api_key")
    assert ss.headers.get("x-api-key") == "test_api_key"


def test_semantic_scholar_testing_mode_search():
    """Verifies structured paper search results in TESTING environment."""
    ss = SemanticScholarConnector()
    with patch.dict(os.environ, {"TESTING": "1"}):
        papers = ss.search_papers(query="gasoline pass through", limit=2)
        assert len(papers) > 0
        assert "paperId" in papers[0]
        assert "tldr" in papers[0]
        assert "citationCount" in papers[0]


def test_semantic_scholar_search_mock():
    """Verifies response parsing with mocked API search response."""
    ss = SemanticScholarConnector()
    mock_payload = {
        "data": [
            {
                "paperId": "abc123456789",
                "title": "Empirical Dynamics of RBOB Gasoline Futures",
                "year": 2023,
                "citationCount": 50,
                "influentialCitationCount": 10,
                "tldr": {"text": "RBOB futures lead retail price movements by 5 to 7 days."},
                "abstract": "A comprehensive time-series analysis.",
                "openAccessPdf": {"url": "https://arxiv.org/pdf/2301.00000.pdf"}
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch.dict(os.environ, {"TESTING": "0", "SUPPRESS_OUTBOUND_APIS": "0"}), \
         patch("requests.get", return_value=mock_resp):
        results = ss.search_papers(query="RBOB futures dynamics", limit=1)
        assert len(results) == 1
        assert results[0]["title"] == "Empirical Dynamics of RBOB Gasoline Futures"
        assert results[0]["tldr"] == "RBOB futures lead retail price movements by 5 to 7 days."
        assert results[0]["openAccessPdf"] == "https://arxiv.org/pdf/2301.00000.pdf"


def test_semantic_scholar_get_tldr_mock():
    """Verifies single-paper TL;DR extraction."""
    ss = SemanticScholarConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "title": "Refinery Economics",
        "tldr": {"text": "Outages in PADD 2 cause transitory price spikes decaying in 4 days."}
    }

    with patch.dict(os.environ, {"TESTING": "0", "SUPPRESS_OUTBOUND_APIS": "0"}), \
         patch("requests.get", return_value=mock_resp):
        tldr = ss.get_paper_tldr("10.1016/j.eneco.2023.01")
        assert "decaying in 4 days" in tldr


def test_semantic_scholar_error_recovery():
    """Verifies graceful return on API HTTP failure."""
    ss = SemanticScholarConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch.dict(os.environ, {"TESTING": "0", "SUPPRESS_OUTBOUND_APIS": "0"}), \
         patch("requests.get", return_value=mock_resp):
        assert ss.search_papers("test") == []
        assert ss.get_paper_tldr("bad_id") is None
