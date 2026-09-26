"""
Unit Test Suite for Defusedxml XML Parsing Security Hardening (tests/test_defusedxml_security.py)
Verifies that all remote XML data connectors use defusedxml to guard against XML Entity Expansion
(Billion Laughs / quadratic blowup) and DoS vulnerabilities (Issue #351).
"""

import pytest
import defusedxml.ElementTree as defused_ET
from defusedxml.common import DefusedXmlException, EntitiesForbidden, DTDForbidden

import src.arxiv_monitor as arxiv_mod
import src.bsee_shutins as bsee_mod
import src.edgar_8k_monitor as edgar_mod
import src.fireworks_tech_graph as fireworks_mod
import src.geopolitical_feeds as geo_mod
import src.nhc_hurricane as nhc_mod
import src.reachability_adapters as reach_mod


# Malicious XML payload with entity expansion (Billion Laughs attack)
ENTITY_EXPANSION_XML = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ELEMENT lolz (#PCDATA)>
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
 <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<lolz>&lol3;</lolz>
"""

# Valid sample XML payloads
SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Sample Feed</title>
  <entry>
    <id>12345</id>
    <title>Refinery FCC unit temporary maintenance</title>
    <updated>2026-09-22T12:00:00Z</updated>
    <published>2026-09-22T12:00:00Z</published>
    <summary>Sample summary for energy research</summary>
    <link href="https://example.com/item/1" />
  </entry>
</feed>
"""

SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample RSS</title>
    <item>
      <title>Gulf of Mexico offshore production report</title>
      <description>BSEE reports minor platform shut-in status</description>
      <link>https://example.com/rss/1</link>
      <pubDate>Tue, 22 Sep 2026 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="blue" />
</svg>
"""


def test_modules_import_defusedxml():
    """Verify that all 7 modules import defusedxml.ElementTree as ET."""
    assert arxiv_mod.ET == defused_ET
    assert bsee_mod.ET == defused_ET
    assert edgar_mod.ET == defused_ET
    assert fireworks_mod.ET == defused_ET
    assert geo_mod.ET == defused_ET
    assert nhc_mod.ET == defused_ET
    assert reach_mod.ET == defused_ET


def test_defusedxml_blocks_entity_expansion():
    """Verify that defusedxml blocks entity expansion / DTD vulnerabilities."""
    with pytest.raises((EntitiesForbidden, DTDForbidden, DefusedXmlException)):
        defused_ET.fromstring(ENTITY_EXPANSION_XML)


def test_arxiv_monitor_parses_valid_atom(monkeypatch):
    """Verify arXiv monitor parses valid Atom XML response."""
    class MockResponse:
        def read(self):
            return SAMPLE_ATOM_FEED.encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: MockResponse())
    articles = arxiv_mod.fetch_recent_arxiv_articles(days_back=365, max_results=5)
    assert isinstance(articles, list)
    assert len(articles) == 1
    assert "Refinery" in articles[0]["title"]


def test_arxiv_monitor_handles_adversarial_xml(monkeypatch):
    """Verify arXiv monitor gracefully handles malicious entity expansion XML without crashing."""
    class MockMaliciousResponse:
        def read(self):
            return ENTITY_EXPANSION_XML
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: MockMaliciousResponse())
    # Should catch DefusedXmlException internally and return empty list
    articles = arxiv_mod.fetch_recent_arxiv_articles(days_back=7)
    assert articles == []


def test_bsee_shutins_handles_adversarial_xml(monkeypatch):
    """Verify BSEE shutin connector safely handles malicious entity expansion XML."""
    class MockMaliciousResponse:
        status = 200
        def read(self):
            return ENTITY_EXPANSION_XML
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=5: MockMaliciousResponse())
    connector = bsee_mod.BSEEShutInConnector()
    data = connector.fetch_gulf_shutin_data()
    assert isinstance(data, dict)
    assert data.get("status") == "SUCCESS"


def test_edgar_8k_monitor_handles_adversarial_xml():
    """Verify EDGAR 8-K monitor handles entity expansion XML safely."""
    monitor = edgar_mod.EDGAR8KMonitor(tickers=["TEST"])
    # Directly pass malicious XML to _fetch_atom_entries via mock _fetch_url
    monitor._fetch_url = lambda url: ENTITY_EXPANSION_XML.decode("utf-8")
    entries = monitor._fetch_atom_entries("TEST")
    assert entries == []


def test_fireworks_tech_graph_valid_svg_and_rejection():
    """Verify Fireworks Tech Graph validates legitimate SVG and rejects entity expansion payloads."""
    assert fireworks_mod.validate_svg_content(SAMPLE_SVG) is True
    assert fireworks_mod.validate_svg_content(ENTITY_EXPANSION_XML.decode("utf-8")) is False


def test_geopolitical_feeds_handles_adversarial_xml(monkeypatch):
    """Verify Geopolitical feeds handle malicious entity expansion XML safely."""
    class MockMaliciousResponse:
        status = 200
        def read(self):
            return ENTITY_EXPANSION_XML
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=5: MockMaliciousResponse())
    connector = geo_mod.GeopoliticalFeedConnector()
    events = connector.fetch_geopolitical_headlines()
    assert isinstance(events, list)
    assert len(events) == 0


def test_nhc_hurricane_handles_adversarial_xml(monkeypatch):
    """Verify NOAA NHC connector handles malicious entity expansion XML safely."""
    class MockMaliciousResponse:
        status = 200
        def read(self):
            return ENTITY_EXPANSION_XML
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=5: MockMaliciousResponse())
    connector = nhc_mod.NHCHurricaneConnector()
    data = connector.fetch_active_hurricane_threats()
    assert isinstance(data, dict)
    assert data.get("status") == "SUCCESS"


def test_reachability_rss_handles_adversarial_xml(monkeypatch):
    """Verify RSS reachability adapter handles malicious entity expansion XML safely."""
    class MockMaliciousResponse:
        status = 200
        def read(self):
            return ENTITY_EXPANSION_XML
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=5.0: MockMaliciousResponse())
    adapter = reach_mod.RSSSyndicationAdapter()
    posts = adapter.fetch_posts(query="refinery fire")
    assert posts == []
