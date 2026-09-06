"""
Unit Tests for Knowledge Graph & Agent Memory Layer (tests/test_knowledge_graph.py)
"""

import os
import json
import pytest
import tempfile
import sqlite3
from src.knowledge_graph import (
    KnowledgeGraphEngine,
    NodeRecord,
    EdgeRecord,
    GraphContextSchema,
    ENTITY_REFINERY,
    ENTITY_METRO,
    ENTITY_PADD,
    ENTITY_CHOKEPOINT,
    ENTITY_SHOCK,
    REL_SUPPLIES,
    REL_CONNECTED_TO,
    REL_EXPOSES_RISK,
)


@pytest.fixture
def temp_kg_engine():
    """Fixture providing a temporary KnowledgeGraphEngine instance backed by a temp DB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = KnowledgeGraphEngine(db_path=db_path, auto_seed=True)
    yield engine

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_kg_engine_initialization_and_seeding(temp_kg_engine):
    """Verifies that KnowledgeGraphEngine initializes tables and seeds petroleum topology."""
    graph = temp_kg_engine.graph
    assert graph.number_of_nodes() > 0
    assert graph.number_of_edges() > 0

    # Verify key nodes exist
    assert graph.has_node("HF_Sinclair_West_Tulsa")
    assert graph.has_node("Chevron_Richmond")
    assert graph.has_node("Chokepoint_Hormuz")
    assert graph.has_node("Tulsa_OK")
    assert graph.has_node("Oakland_CA")
    assert graph.has_node("PADD_5")

    # Verify node attributes
    tulsa_data = graph.nodes["HF_Sinclair_West_Tulsa"]
    assert tulsa_data["name"] == "West Tulsa HF Sinclair Refinery"
    assert tulsa_data["entity_type"] == ENTITY_REFINERY
    assert tulsa_data["capacity_bpd"] == 125000


def test_add_custom_node_and_edge(temp_kg_engine):
    """Verifies custom node and edge addition and SQLite persistence."""
    node_rec = temp_kg_engine.add_node("Refinery_Custom", "Custom Test Refinery", ENTITY_REFINERY, capacity_bpd=50000)
    assert node_rec.node_id == "Refinery_Custom"
    assert temp_kg_engine.graph.has_node("Refinery_Custom")

    edge_rec = temp_kg_engine.add_edge("Refinery_Custom", "Tulsa_OK", REL_SUPPLIES, weight=0.9)
    assert edge_rec.source_id == "Refinery_Custom"
    assert edge_rec.target_id == "Tulsa_OK"
    assert temp_kg_engine.graph.has_edge("Refinery_Custom", "Tulsa_OK")

    # Verify persistence by reloading from DB
    reloaded_engine = KnowledgeGraphEngine(db_path=temp_kg_engine.db_path, auto_seed=False)
    assert reloaded_engine.graph.has_node("Refinery_Custom")
    assert reloaded_engine.graph.has_edge("Refinery_Custom", "Tulsa_OK")


def test_entity_resolution_in_text(temp_kg_engine):
    """Verifies entity resolution from text headlines."""
    text = "Breakdown at Chevron Richmond refinery impacts Oakland fuel supply."
    matched = temp_kg_engine.resolve_entities_in_text(text)
    assert "Chevron_Richmond" in matched or "Oakland_CA" in matched


def test_get_subgraph_context(temp_kg_engine):
    """Verifies 2-hop neighborhood sub-graph extraction for GraphRAG prompting."""
    schema = temp_kg_engine.get_subgraph_context(["Chevron_Richmond"], depth=2)
    assert isinstance(schema, GraphContextSchema)
    assert "Chevron_Richmond" in schema.focus_entities
    assert len(schema.nodes) > 0
    assert len(schema.edges) > 0

    markdown_text = schema.to_markdown()
    assert "Knowledge Graph Topology Context" in markdown_text
    assert "Chevron_Richmond" in markdown_text or "Chevron Richmond" in markdown_text


def test_record_shock_memory_and_precedent_search(temp_kg_engine):
    """Verifies event shock memory recording and precedent analog retrieval."""
    headline = "Emergency explosion at Chevron Richmond refinery halts East Bay gasoline production"
    score_vector = {
        "geopolitical_risk": 0.0,
        "supply_disruption": 0.85,
        "demand_sentiment": 0.0,
        "opec_action": 0.0,
        "overall_price_pressure": 0.65
    }

    shock_id = temp_kg_engine.record_event_shock_memory(
        headline=headline,
        score_vector=score_vector,
        model_attribution="test_gemini",
        council_variance=0.02
    )

    assert shock_id.startswith("shock_")
    assert temp_kg_engine.graph.has_node(shock_id)

    # Search for precedent analog
    query = "Richmond refinery explosion outage"
    precedents = temp_kg_engine.find_historical_precedents(query, top_k=3)
    assert len(precedents) > 0
    top_prec = precedents[0]
    assert "headline" in top_prec
    assert top_prec["overall_price_pressure"] == 0.65
    assert top_prec["similarity"] > 0.0


def test_export_topology_dict(temp_kg_engine):
    """Verifies topology dictionary export for REST API and UI visualization."""
    topo = temp_kg_engine.export_topology_dict()
    assert "summary" in topo
    assert topo["summary"]["num_nodes"] > 0
    assert topo["summary"]["num_edges"] > 0
    assert len(topo["nodes"]) == topo["summary"]["num_nodes"]
    assert len(topo["edges"]) == topo["summary"]["num_edges"]


def test_api_server_graph_endpoints():
    """Verifies REST API endpoints for Knowledge Graph and Agent Memory."""
    from fastapi.testclient import TestClient
    from src.api_server import app

    client = TestClient(app)

    # Test GET /api/v1/graph/topology
    r_topo = client.get("/api/v1/graph/topology")
    assert r_topo.status_code == 200
    data_topo = r_topo.json()
    assert "nodes" in data_topo
    assert "edges" in data_topo

    # Test GET /api/v1/graph/subgraph
    r_sub = client.get("/api/v1/graph/subgraph?entity=Oakland_CA")
    assert r_sub.status_code == 200
    data_sub = r_sub.json()
    assert "nodes" in data_sub

    # Test GET /api/v1/memory/precedents
    r_prec = client.get("/api/v1/memory/precedents?query=refinery+explosion")
    assert r_prec.status_code == 200
    data_prec = r_prec.json()
    assert "precedents" in data_prec


def test_mcp_knowledge_graph_tools():
    """Verifies MCP tools query_knowledge_graph and retrieve_event_precedents."""
    import asyncio
    from src.mcp_server import call_tool

    async def _test_tools():
        res_kg = await call_tool("query_knowledge_graph", {"entity": "Oakland_CA"})
        assert len(res_kg) > 0
        parsed_kg = json.loads(res_kg[0].text)
        assert "nodes" in parsed_kg

        res_prec = await call_tool("retrieve_event_precedents", {"query": "refinery outage"})
        assert len(res_prec) > 0

    asyncio.run(_test_tools())
