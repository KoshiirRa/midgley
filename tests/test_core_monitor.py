import os
import sys
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core_monitor import (
    fetch_recent_core_articles,
    format_core_markdown_section,
    _parse_date,
    _parse_core_item,
)

SAMPLE_CORE_JSON_V3 = {
    "totalHits": 1,
    "results": [
        {
            "id": "987654321",
            "title": "Machine Learning Approaches for RBOB Gasoline Futures and Refining Rack Margin Forecasting",
            "publishedDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "abstract": "This study demonstrates an empirical LLM multi-agent framework for predicting wholesale and retail gas prices under geopolitical and severe weather shock events.",
            "authors": [
                {"name": "Dr. A. Smith"},
                {"name": "Prof. B. Jones"},
                {"name": "C. Miller"},
                {"name": "D. Wilson"}
            ],
            "doi": "10.1016/j.eneco.2026.109999",
            "downloadUrl": "https://core.ac.uk/download/pdf/987654321.pdf"
        }
    ]
}

OLD_CORE_JSON_V3 = {
    "totalHits": 1,
    "results": [
        {
            "id": "11111111",
            "title": "Historical Oil Price Elasticity",
            "publishedDate": "2015-05-10T00:00:00Z",
            "abstract": "An old paper published years ago outside the cutoff window.",
            "authors": ["E. Oldman"],
            "doi": "10.1000/old.paper"
        }
    ]
}


def test_parse_date():
    assert _parse_date(None) is None
    assert _parse_date("") is None
    
    dt = _parse_date("2026-08-28T14:30:00Z")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 8 and dt.day == 28
    
    dt_ymd = _parse_date("2026-08-28")
    assert dt_ymd is not None
    assert dt_ymd.year == 2026
    
    dt_year = _parse_date(2026)
    assert dt_year is not None
    assert dt_year.year == 2026


def test_parse_core_item():
    raw_item = SAMPLE_CORE_JSON_V3["results"][0]
    parsed = _parse_core_item(raw_item)
    
    assert parsed["id"] == "987654321"
    assert "Machine Learning Approaches" in parsed["title"]
    assert len(parsed["authors"]) == 4
    assert parsed["authors"][0] == "Dr. A. Smith"
    assert parsed["doi"] == "10.1016/j.eneco.2026.109999"
    assert parsed["url"] == "https://doi.org/10.1016/j.eneco.2026.109999"
    assert parsed["pdf_url"] == "https://core.ac.uk/download/pdf/987654321.pdf"


def test_fetch_recent_core_articles_success():
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(SAMPLE_CORE_JSON_V3).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        articles = fetch_recent_core_articles(days_back=7, max_results=5, api_key="test_key")
        assert len(articles) == 1
        art = articles[0]
        assert art["id"] == "987654321"
        assert "RBOB Gasoline" in art["title"]
        assert len(art["authors"]) == 4
        assert art["doi"] == "10.1016/j.eneco.2026.109999"


def test_fetch_recent_core_articles_cutoff_filtering():
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(OLD_CORE_JSON_V3).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        articles = fetch_recent_core_articles(days_back=7)
        assert len(articles) == 0


def test_fetch_recent_core_articles_exception_handling():
    with patch("urllib.request.urlopen", side_effect=Exception("API Connection Refused")):
        articles = fetch_recent_core_articles(days_back=7)
        assert articles == []


def test_format_core_markdown_section_empty():
    with patch("src.core_monitor.fetch_recent_core_articles", return_value=[]):
        section = format_core_markdown_section(days_back=7)
        assert "## 🔬 Relevant CORE Open-Access Research Papers" in section
        assert "No new open-access research papers matching" in section


def test_format_core_markdown_section_with_articles():
    sample = [{
        "id": "987654321",
        "title": "Machine Learning Approaches for RBOB Gasoline Futures",
        "authors": ["Dr. A. Smith", "Prof. B. Jones", "C. Miller", "D. Wilson"],
        "published": "2026-08-28",
        "summary": "This study demonstrates an empirical LLM multi-agent framework...",
        "doi": "10.1016/j.eneco.2026.109999",
        "url": "https://doi.org/10.1016/j.eneco.2026.109999",
        "pdf_url": "https://core.ac.uk/download/pdf/987654321.pdf"
    }]

    with patch("src.core_monitor.fetch_recent_core_articles", return_value=sample):
        section = format_core_markdown_section(days_back=7)
        assert "## 🔬 Relevant CORE Open-Access Research Papers" in section
        assert "Machine Learning Approaches for RBOB Gasoline Futures" in section
        assert "Dr. A. Smith, Prof. B. Jones, C. Miller et al." in section
        assert "[Download](https://core.ac.uk/download/pdf/987654321.pdf)" in section
        assert "**DOI:** `10.1016/j.eneco.2026.109999`" in section
