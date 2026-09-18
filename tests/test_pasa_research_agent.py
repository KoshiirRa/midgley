"""
Unit and Integration Tests for PaSa Dual-Agent Research Subagent (tests/test_pasa_research_agent.py)
Issue #265: PaSa Crawler-Selector Dual-Agent Architecture
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from src.pasa_research_agent import (
    CandidateDocument,
    PaSaResearchResult,
    CrawlerAgent,
    SelectorAgent,
    PaSaResearchAgent,
    _load_pasa_cache,
    _save_pasa_cache
)
from src.event_analyzer import investigate_event_with_pasa


def test_candidate_document_model():
    """Verifies CandidateDocument serialization and defaults."""
    doc = CandidateDocument(
        doc_id="test_doc_1",
        title="Refinery Outage Shock Decay in PADD 1B",
        content="Outage shocks exhibit half-life decay of 4.5 days.",
        source_type="openalex",
        doi="10.1016/j.eneco.2025.01",
        citation_count=25,
        hop_depth=0
    )
    d = doc.to_dict()
    assert d["doc_id"] == "test_doc_1"
    assert d["title"] == "Refinery Outage Shock Decay in PADD 1B"
    assert d["source_type"] == "openalex"
    assert d["citation_count"] == 25
    assert d["relevance_score"] == 0.0


def test_crawler_query_expansion():
    """Verifies CrawlerAgent query expansion across hop 0 and hop 1."""
    crawler = CrawlerAgent()
    
    # Hop 0 expansion
    hop0_queries = crawler.expand_queries("refinery outage shock decay", hop=0)
    assert len(hop0_queries) >= 2
    assert "refinery outage shock decay" in hop0_queries
    
    # Hop 1 expansion using seed docs
    seed = [
        CandidateDocument(
            doc_id="s1",
            title="Delaware City Refinery Fluid Catalytic Cracking Unplanned Outage",
            content="",
            source_type="openalex"
        )
    ]
    hop1_queries = crawler.expand_queries("refinery outage shock decay", hop=1, seed_docs=seed)
    assert len(hop1_queries) >= 1
    assert any("delaware" in q.lower() or "refinery" in q.lower() for q in hop1_queries)


def test_crawler_academic_crawl_mock():
    """Verifies crawler academic retrieval across OpenAlex and Semantic Scholar."""
    mock_oa = MagicMock()
    mock_oa.search_energy_literature.return_value = [
        {
            "id": "oa_123",
            "doi": "10.1016/j.eneco.2025.101",
            "title": "Gasoline Crack Spread Asymmetry",
            "summary_abstract": "Empirical study on pass-through speed.",
            "authors": ["Smith, J."],
            "publication_year": 2024,
            "cited_by_count": 30,
            "open_access_url": "https://oa.org/paper.pdf"
        }
    ]
    mock_ss = MagicMock()
    mock_ss.search_papers.return_value = [
        {
            "paperId": "ss_456",
            "title": "Refinery Outage Price Impacts",
            "tldr": "Outages create temporary price spikes.",
            "citationCount": 12,
            "year": 2023,
            "openAccessPdf": "https://ss.org/paper.pdf"
        }
    ]

    crawler = CrawlerAgent(openalex=mock_oa, semantic_scholar=mock_ss)
    candidates = crawler.crawl_academic(queries=["crack spread"], hop_depth=0)
    
    assert len(candidates) >= 2
    titles = [c.title for c in candidates]
    assert "Gasoline Crack Spread Asymmetry" in titles
    assert "Refinery Outage Price Impacts" in titles


def test_selector_deterministic_evaluation():
    """Verifies zero-cost deterministic evaluation and parameter extraction."""
    selector = SelectorAgent(relevance_threshold=0.30)
    candidates = [
        CandidateDocument(
            doc_id="d1",
            title="Empirical Refinery Outage Shock Decay Half-Life Study",
            content="We observe exponential shock decay with half-life between 4.0 and 5.0 days.",
            source_type="openalex",
            citation_count=40
        ),
        CandidateDocument(
            doc_id="d2",
            title="Random Agricultural Fertilizer Market Dynamics",
            content="Corn and soybean price volatility across Midwest.",
            source_type="openalex",
            citation_count=5
        )
    ]

    selected, should_continue, next_guidance, summary, params = selector.evaluate_and_select(
        candidates=candidates,
        objective="refinery outage shock decay half-life",
        current_hop=0,
        max_hops=2,
        tier="basic"
    )

    assert len(selected) == 1
    assert selected[0].doc_id == "d1"
    assert selected[0].relevance_score > 0.40
    assert "shock_decay_half_life" in params
    assert params["shock_decay_half_life"]["value"] == 4.5


def test_selector_llm_evaluation_mock():
    """Verifies LLM evaluative pass when API response is formatted."""
    selector = SelectorAgent(relevance_threshold=0.50)
    candidates = [
        CandidateDocument(
            doc_id="doc_gemini_1",
            title="Colonial Pipeline Allocation and East Coast Basis",
            content="Line 1 pipeline allocation constraints cause PADD 1C rack price premiums.",
            source_type="openalex"
        )
    ]

    mock_llm_response = {
        "evaluations": [
            {
                "doc_id": "doc_gemini_1",
                "relevance_score": 0.92,
                "relevance_explanation": "Directly analyzes pipeline basis premiums and supply constraints.",
                "extracted_parameters": {
                    "parameter_name": "pipeline_basis_premium",
                    "value": 0.12,
                    "unit": "$/gal",
                    "bounds": [0.08, 0.18]
                },
                "key_finding": "Colonial pipeline allocations increase East Coast regional basis by 12c/gal."
            }
        ],
        "should_continue_hops": False,
        "next_hop_guidance": "",
        "synthesized_summary": "Pipeline allocations create direct regional basis premiums."
    }

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_llm_response)
    mock_client.models.generate_content.return_value = mock_resp

    with patch.dict(os.environ, {"TESTING": "0", "GEMINI_API_KEY": "fake_key"}), \
         patch("google.genai.Client", return_value=mock_client):
        selected, should_continue, guidance, summary, params = selector.evaluate_and_select(
            candidates=candidates,
            objective="Colonial pipeline basis spread",
            current_hop=0,
            max_hops=2,
            tier="privileged"
        )

        assert len(selected) == 1
        assert selected[0].relevance_score == 0.92
        assert should_continue is False
        assert "pipeline_basis_premium" in params
        assert params["pipeline_basis_premium"]["value"] == 0.12


def test_pasa_multi_hop_investigation_loop():
    """Verifies multi-hop execution flow and result assembly in testing mode."""
    agent = PaSaResearchAgent(max_hops=2, relevance_threshold=0.30)
    
    with patch.dict(os.environ, {"TESTING": "1"}):
        result = agent.investigate(
            objective="Delaware City refinery outage pass-through decay",
            mode="academic",
            max_hops=2
        )

        assert isinstance(result, PaSaResearchResult)
        assert result.total_hops_executed >= 1
        assert result.total_candidates_evaluated > 0
        assert len(result.selected_documents) > 0
        assert result.status in ["completed", "completed_cached"]
        assert len(result.bibliography) > 0


def test_event_analyzer_pasa_hook():
    """Verifies investigate_event_with_pasa helper function in event_analyzer."""
    with patch.dict(os.environ, {"TESTING": "1"}):
        res = investigate_event_with_pasa(
            objective_or_headline="Delmarva pipeline detour supply shock",
            mode="event",
            max_hops=2
        )
        assert "objective" in res
        assert "synthesized_summary" in res
        assert "bibliography" in res
        assert res["total_hops_executed"] >= 1
