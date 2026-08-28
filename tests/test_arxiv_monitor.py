import os
import sys
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.arxiv_monitor import (
    fetch_recent_arxiv_articles,
    format_arxiv_markdown_section,
)

SAMPLE_ATOM_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title type="text">ArXiv Query Results</title>
  <entry>
    <id>http://arxiv.org/abs/2608.12345v1</id>
    <published>{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}</published>
    <updated>{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>
    <title>Deep Learning for Energy Commodity Price Forecasting with LLM Sentiment Shocks</title>
    <summary>We present a novel hybrid forecasting model that fuses text sentiment vectors from financial news streams with high-frequency futures returns for RBOB gasoline.</summary>
    <author><name>J. Smith</name></author>
    <author><name>A. Johnson</name></author>
    <author><name>C. Lee</name></author>
    <author><name>D. Davis</name></author>
    <link href="http://arxiv.org/abs/2608.12345v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2608.12345v1" rel="related" type="application/pdf"/>
  </entry>
</feed>"""

OLD_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2001.00001v1</id>
    <published>2020-01-01T00:00:00Z</published>
    <title>Ancient Paper on Commodity Pricing</title>
    <summary>An old paper outside cutoff.</summary>
    <author><name>Old Author</name></author>
  </entry>
</feed>"""


def test_fetch_recent_arxiv_articles_success():
    mock_response = MagicMock()
    mock_response.read.return_value = SAMPLE_ATOM_XML.encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        articles = fetch_recent_arxiv_articles(days_back=7, max_results=5)
        assert len(articles) == 1
        art = articles[0]
        assert art["id"] == "2608.12345v1"
        assert "Deep Learning for Energy Commodity" in art["title"]
        assert len(art["authors"]) == 4
        assert art["url"] == "http://arxiv.org/abs/2608.12345v1"
        assert art["pdf_url"] == "http://arxiv.org/pdf/2608.12345v1"


def test_fetch_recent_arxiv_articles_cutoff_filtering():
    mock_response = MagicMock()
    mock_response.read.return_value = OLD_ATOM_XML.encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        articles = fetch_recent_arxiv_articles(days_back=7)
        assert len(articles) == 0


def test_fetch_recent_arxiv_articles_exception_handling():
    with patch("urllib.request.urlopen", side_effect=Exception("Connection reset")):
        articles = fetch_recent_arxiv_articles(days_back=7)
        assert articles == []


def test_format_arxiv_markdown_section_empty():
    with patch("src.arxiv_monitor.fetch_recent_arxiv_articles", return_value=[]):
        section = format_arxiv_markdown_section(days_back=7)
        assert "## 📚 Relevant Recent arXiv Research Papers" in section
        assert "No new arXiv preprints matching" in section


def test_format_arxiv_markdown_section_with_articles():
    sample = [{
        "id": "2608.12345v1",
        "title": "Deep Learning for Energy Commodity Price Forecasting",
        "authors": ["J. Smith", "A. Johnson", "C. Lee", "D. Davis"],
        "published": "2026-08-24",
        "summary": "We present a novel hybrid forecasting model...",
        "url": "https://arxiv.org/abs/2608.12345v1",
        "pdf_url": "https://arxiv.org/pdf/2608.12345v1.pdf"
    }]

    with patch("src.arxiv_monitor.fetch_recent_arxiv_articles", return_value=sample):
        section = format_arxiv_markdown_section(days_back=7)
        assert "## 📚 Relevant Recent arXiv Research Papers" in section
        assert "Deep Learning for Energy Commodity Price Forecasting" in section
        assert "J. Smith, A. Johnson, C. Lee et al." in section
        assert "[Download](https://arxiv.org/pdf/2608.12345v1.pdf)" in section
