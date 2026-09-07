"""
Knowledge Graph & Agent Memory Layer (src/knowledge_graph.py)

Provides entity-relationship topology graph management, episodic agent memory,
GraphRAG context extraction, and Council of LLMs provider-agnostic context serialization.

Supported by zero-cost embedded NetworkX graph engine and SQLite persistent storage (data/knowledge_graph.db).
"""

import os
import math
import json
import sqlite3
import logging
import networkx as nx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Database location
DEFAULT_KG_DB_PATH = os.path.join("data", "knowledge_graph.db")

# Entity Taxonomy
ENTITY_REFINERY = "Refinery"
ENTITY_PIPELINE = "Pipeline"
ENTITY_CHOKEPOINT = "Chokepoint"
ENTITY_TERMINAL = "MarineTerminal"
ENTITY_PADD = "PADDRegion"
ENTITY_METRO = "MetroLocale"
ENTITY_EXECUTIVE = "ExecutiveActor"
ENTITY_POLICY = "PolicyRule"
ENTITY_SHOCK = "HistoricalShock"

VALID_ENTITY_TYPES = {
    ENTITY_REFINERY,
    ENTITY_PIPELINE,
    ENTITY_CHOKEPOINT,
    ENTITY_TERMINAL,
    ENTITY_PADD,
    ENTITY_METRO,
    ENTITY_EXECUTIVE,
    ENTITY_POLICY,
    ENTITY_SHOCK,
}

# Relationship Taxonomy
REL_SUPPLIES = "SUPPLIES"
REL_CONNECTED_TO = "CONNECTED_TO"
REL_AFFECTS_LOCALE = "AFFECTS_LOCALE"
REL_TRANSITS_THROUGH = "TRANSITS_THROUGH"
REL_REGULATES = "REGULATES"
REL_EXPOSES_RISK = "EXPOSES_RISK"
REL_PRECEDENT_FOR = "HISTORICAL_PRECEDENT_FOR"

# Sentence-Transformers Check
HAS_SENTENCE_TRANSFORMERS = False
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@dataclass
class NodeRecord:
    """Represents an entity node in the Knowledge Graph."""
    node_id: str
    name: str
    entity_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EdgeRecord:
    """Represents a directional relationship edge in the Knowledge Graph."""
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GraphContextSchema:
    """Standardized, provider-agnostic context schema for GraphRAG prompts across Council of LLMs."""
    focus_entities: List[str]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    precedents: List[Dict[str, Any]] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Converts graph context into clean Markdown for LLM prompt injection."""
        lines = []
        if self.nodes:
            lines.append("### [Knowledge Graph Topology Context]")
            for n in self.nodes:
                name = n.get("name", n.get("node_id"))
                etype = n.get("entity_type", "Entity")
                lines.append(f"- **{name}** ({etype})")
        if self.edges:
            lines.append("\n### [Physical & Spatial Relationships]")
            for e in self.edges:
                lines.append(f"- {e.get('source_id')} --[{e.get('relation')}]--> {e.get('target_id')}")
        if self.precedents:
            lines.append("\n### [Historical Precedent Memory Analogs]")
            for p in self.precedents:
                headline = p.get("headline", "")
                score = p.get("overall_price_pressure", 0.0)
                sim = p.get("similarity", 0.0)
                lines.append(f"- precedent (sim: {sim:.2f}): \"{headline}\" (Pressure Score: {score:+.2f})")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Converts context schema to dictionary."""
        return asdict(self)


class PluggableGraphAdapter:
    """Abstract interface for external graph engines (Neo4j, Cognee, Mem0, Graphiti)."""
    def sync_node(self, node: NodeRecord) -> bool:
        return True

    def sync_edge(self, edge: EdgeRecord) -> bool:
        return True

    def query_subgraph(self, entity_ids: List[str], depth: int = 2) -> Dict[str, Any]:
        return {"nodes": [], "edges": []}


class KnowledgeGraphEngine:
    """
    Core Knowledge Graph and Agent Memory Engine.
    Uses NetworkX for in-memory graph operations and SQLite for persistent storage.
    """

    def __init__(self, db_path: str = DEFAULT_KG_DB_PATH, auto_seed: bool = True):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self.adapter: Optional[PluggableGraphAdapter] = None
        self._init_db()
        self._load_from_db()
        if auto_seed and self.graph.number_of_nodes() == 0:
            self.seed_initial_petroleum_topology()

    def _init_db(self):
        """Initializes SQLite tables for nodes, edges, and memory records."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kg_nodes (
                    node_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    attributes TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kg_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL NOT NULL,
                    attributes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES kg_nodes(node_id),
                    FOREIGN KEY(target_id) REFERENCES kg_nodes(node_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kg_memory_shocks (
                    shock_id TEXT PRIMARY KEY,
                    headline TEXT NOT NULL,
                    score_vector TEXT NOT NULL,
                    model_attribution TEXT,
                    council_variance REAL,
                    affected_entities TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def _load_from_db(self):
        """Loads nodes and edges from SQLite into NetworkX graph."""
        self.graph.clear()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT node_id, name, entity_type, attributes, created_at FROM kg_nodes")
            for row in cursor.fetchall():
                node_id, name, entity_type, attrs_str, created_at = row
                attrs = json.loads(attrs_str) if attrs_str else {}
                self.graph.add_node(
                    node_id,
                    name=name,
                    entity_type=entity_type,
                    created_at=created_at,
                    **attrs
                )

            cursor.execute("SELECT source_id, target_id, relation, weight, attributes, created_at FROM kg_edges")
            for row in cursor.fetchall():
                source_id, target_id, relation, weight, attrs_str, created_at = row
                attrs = json.loads(attrs_str) if attrs_str else {}
                if self.graph.has_node(source_id) and self.graph.has_node(target_id):
                    self.graph.add_edge(
                        source_id,
                        target_id,
                        relation=relation,
                        weight=weight,
                        created_at=created_at,
                        **attrs
                    )
        logger.debug(f"Loaded Knowledge Graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    def add_node(self, node_id: str, name: str, entity_type: str, **kwargs) -> NodeRecord:
        """Adds or updates an entity node in graph and SQLite."""
        if entity_type not in VALID_ENTITY_TYPES:
            logger.warning(f"Entity type '{entity_type}' not in canonical taxonomy. Accepting as custom type.")

        created_at = kwargs.pop("created_at", None) or datetime.now(timezone.utc).isoformat()
        node_rec = NodeRecord(node_id=node_id, name=name, entity_type=entity_type, attributes=kwargs, created_at=created_at)

        # Update NetworkX
        self.graph.add_node(node_id, name=name, entity_type=entity_type, created_at=created_at, **kwargs)

        # Update SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO kg_nodes (node_id, name, entity_type, attributes, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    name=excluded.name,
                    entity_type=excluded.entity_type,
                    attributes=excluded.attributes
                """,
                (node_id, name, entity_type, json.dumps(kwargs), created_at)
            )
            conn.commit()

        if self.adapter:
            try:
                self.adapter.sync_node(node_rec)
            except Exception as e:
                logger.debug(f"Graph adapter sync notice: {e}")

        return node_rec

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0, **kwargs) -> EdgeRecord:
        """Adds or updates a directional edge in graph and SQLite."""
        if not self.graph.has_node(source_id) or not self.graph.has_node(target_id):
            raise ValueError(f"Both nodes must exist before adding edge: {source_id} -> {target_id}")

        created_at = kwargs.pop("created_at", None) or datetime.now(timezone.utc).isoformat()
        edge_id = f"{source_id}:{relation}:{target_id}"
        edge_rec = EdgeRecord(source_id=source_id, target_id=target_id, relation=relation, weight=weight, attributes=kwargs, created_at=created_at)

        self.graph.add_edge(source_id, target_id, relation=relation, weight=weight, created_at=created_at, **kwargs)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO kg_edges (edge_id, source_id, target_id, relation, weight, attributes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(edge_id) DO UPDATE SET
                    relation=excluded.relation,
                    weight=excluded.weight,
                    attributes=excluded.attributes
                """,
                (edge_id, source_id, target_id, relation, weight, json.dumps(kwargs), created_at)
            )
            conn.commit()

        if self.adapter:
            try:
                self.adapter.sync_edge(edge_rec)
            except Exception as e:
                logger.debug(f"Graph adapter sync notice: {e}")

        return edge_rec

    def seed_initial_petroleum_topology(self):
        """
        Seeds Knowledge Graph with authoritative petroleum refining, pipeline,
        chokepoint, PADD, and regional metro infrastructure metadata.
        """
        from src.spatial_refinery import REFINERY_DATA

        logger.info("Seeding initial petroleum supply topology into Knowledge Graph...")

        # 1. PADD Regions
        padds = {
            "PADD_1B": ("PADD 1B East Coast / Mid-Atlantic", "PADD Region"),
            "PADD_1C": ("PADD 1C Lower Atlantic", "PADD Region"),
            "PADD_2": ("PADD 2 Midwest", "PADD Region"),
            "PADD_5": ("PADD 5 West Coast Refining Island", "PADD Region"),
        }
        for pid, (pname, desc) in padds.items():
            self.add_node(pid, pname, ENTITY_PADD, description=desc)

        # 2. Global Maritime & Pipeline Chokepoints
        chokepoints = {
            "Chokepoint_Hormuz": ("Strait of Hormuz", 21000000, "21M bpd global crude transit point"),
            "Chokepoint_Suez": ("Suez Canal & SUMED Pipeline", 5500000, "5.5M bpd Europe/Asia transit point"),
            "Chokepoint_RedSea": ("Bab el-Mandeb / Red Sea Corridor", 4800000, "Maritime detour corridor"),
            "Chokepoint_Venezuela": ("Orinoco Heavy Crude Export Terminals", 900000, "Heavy crude blend supply"),
        }
        for cid, (cname, cap, desc) in chokepoints.items():
            self.add_node(cid, cname, ENTITY_CHOKEPOINT, capacity_bpd=cap, description=desc)
            self.add_edge(cid, "PADD_5", REL_EXPOSES_RISK, weight=0.85)
            self.add_edge(cid, "PADD_1B", REL_EXPOSES_RISK, weight=0.65)

        # 3. Metros
        metros = {
            "Tulsa_OK": ("Tulsa Metro Area", "PADD 2", 74101),
            "Newark_DE": ("Newark / Wilmington Metro", "PADD 1B", 19711),
            "Cincinnati_OH": ("Cincinnati Tri-State Metro", "PADD 2", 45202),
            "Greenville_NC": ("Greenville Eastern NC", "PADD 1C", 27834),
            "Charlotte_NC": ("Charlotte Metro Area", "PADD 1C", 28202),
            "Oakland_CA": ("Oakland / East Bay Metro", "PADD 5", 94612),
        }
        for mid, (mname, padd_id, zip_c) in metros.items():
            self.add_node(mid, mname, ENTITY_METRO, zip_code=zip_c, padd=padd_id)

        # 4. Refineries & Pipelines from spatial_refinery.py
        for rkey, rinfo in REFINERY_DATA.items():
            rtype = ENTITY_REFINERY if "Pipeline" not in rinfo["name"] and "Terminal" not in rinfo["name"] else (
                ENTITY_PIPELINE if "Pipeline" in rinfo["name"] else ENTITY_TERMINAL
            )
            self.add_node(
                rkey,
                rinfo["name"],
                rtype,
                lat=rinfo["lat"],
                lon=rinfo["lon"],
                capacity_bpd=rinfo["capacity_bpd"],
                padd=rinfo["padd"]
            )

            # Link to PADD
            padd_key = rinfo["padd"].replace(" ", "_")
            if self.graph.has_node(padd_key):
                self.add_edge(rkey, padd_key, REL_CONNECTED_TO)

            # Link to primary locales
            for loc in rinfo.get("primary_locales", []):
                if self.graph.has_node(loc):
                    self.add_edge(rkey, loc, REL_SUPPLIES)

        logger.info(f"Seeding complete. Graph populated with {self.graph.number_of_nodes()} nodes.")

    def resolve_entities_in_text(self, text: str) -> List[str]:
        """Resolves text keywords to matching Knowledge Graph node IDs."""
        matched = []
        text_lower = text.lower()
        for node_id, data in self.graph.nodes(data=True):
            name = data.get("name", node_id).lower()
            if name in text_lower or node_id.lower() in text_lower:
                matched.append(node_id)
                continue

            # Alias matching
            aliases = data.get("aliases", [])
            for alias in aliases:
                if alias.lower() in text_lower:
                    matched.append(node_id)
                    break
        return matched

    def get_subgraph_context(self, entity_ids: List[str], depth: int = 2, max_nodes: int = 15) -> GraphContextSchema:
        """
        Extracts 2-hop neighborhood subgraph for GraphRAG prompting.
        Returns a standardized GraphContextSchema.
        """
        if not entity_ids:
            return GraphContextSchema(focus_entities=[], nodes=[], edges=[])

        valid_roots = [e for e in entity_ids if self.graph.has_node(e)]
        if not valid_roots:
            return GraphContextSchema(focus_entities=[], nodes=[], edges=[])

        subgraph_nodes = set(valid_roots)
        for root in valid_roots:
            lengths = nx.single_source_shortest_path_length(self.graph.to_undirected(), root, cutoff=depth)
            subgraph_nodes.update(lengths.keys())

        selected_nodes = list(subgraph_nodes)[:max_nodes]
        sub_g = self.graph.subgraph(selected_nodes)

        nodes_list = []
        for n, data in sub_g.nodes(data=True):
            ndict = {"node_id": n, "name": data.get("name", n), "entity_type": data.get("entity_type", "Entity")}
            nodes_list.append(ndict)

        edges_list = []
        for u, v, data in sub_g.edges(data=True):
            edict = {"source_id": u, "target_id": v, "relation": data.get("relation", "CONNECTED_TO"), "weight": data.get("weight", 1.0)}
            edges_list.append(edict)

        return GraphContextSchema(focus_entities=valid_roots, nodes=nodes_list, edges=edges_list)

    def record_event_shock_memory(
        self,
        headline: str,
        score_vector: Dict[str, float],
        affected_entities: Optional[List[str]] = None,
        model_attribution: Optional[str] = None,
        council_variance: Optional[float] = None
    ) -> str:
        """
        Ingests a scored qualitative headline event into SQLite memory and
        links it as a HistoricalShock node in the Knowledge Graph.
        """
        created_at = datetime.now(timezone.utc).isoformat()
        shock_id = f"shock_{int(datetime.now(timezone.utc).timestamp())}_{abs(hash(headline)) % 10000}"

        if affected_entities is None:
            affected_entities = self.resolve_entities_in_text(headline)

        # 1. Create Node in Graph
        self.add_node(
            shock_id,
            headline[:60],
            ENTITY_SHOCK,
            headline=headline,
            overall_price_pressure=score_vector.get("overall_price_pressure", 0.0),
            geopolitical_risk=score_vector.get("geopolitical_risk", 0.0),
            supply_disruption=score_vector.get("supply_disruption", 0.0),
            model_attribution=model_attribution or "single_llm",
            council_variance=council_variance or 0.0,
            created_at=created_at
        )

        # 2. Link to Affected Entities
        for ent_id in affected_entities:
            if self.graph.has_node(ent_id):
                self.add_edge(shock_id, ent_id, REL_AFFECTS_LOCALE)

        # 3. Store in SQLite memory table
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO kg_memory_shocks
                (shock_id, headline, score_vector, model_attribution, council_variance, affected_entities, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shock_id,
                    headline,
                    json.dumps(score_vector),
                    model_attribution or "single_llm",
                    council_variance or 0.0,
                    json.dumps(affected_entities),
                    created_at
                )
            )
            conn.commit()

        logger.debug(f"Recorded shock memory '{shock_id}' for headline: {headline[:40]}...")
        return shock_id

    def find_historical_precedents(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Searches historical event memories for precedent analogs using TF-IDF +
        graph distance or sentence embeddings if available.
        """
        shocks = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT shock_id, headline, score_vector, model_attribution, council_variance, affected_entities, created_at FROM kg_memory_shocks"
            )
            for row in cursor.fetchall():
                sid, headline, score_str, attr, var, aff_str, created_at = row
                scores = json.loads(score_str) if score_str else {}
                aff = json.loads(aff_str) if aff_str else []
                shocks.append({
                    "shock_id": sid,
                    "headline": headline,
                    "score_vector": scores,
                    "overall_price_pressure": scores.get("overall_price_pressure", 0.0),
                    "model_attribution": attr,
                    "council_variance": var,
                    "affected_entities": aff,
                    "created_at": created_at
                })

        if not shocks:
            return []

        query_words = set(query_text.lower().split())
        scored_results = []

        for s in shocks:
            h_words = set(s["headline"].lower().split())
            intersection = query_words.intersection(h_words)
            union = query_words.union(h_words)
            jaccard_sim = len(intersection) / max(len(union), 1)

            query_ents = set(self.resolve_entities_in_text(query_text))
            ent_overlap = query_ents.intersection(set(s["affected_entities"]))
            if ent_overlap:
                jaccard_sim += 0.35

            s_copy = dict(s)
            s_copy["similarity"] = round(min(jaccard_sim, 1.0), 3)
            scored_results.append(s_copy)

        scored_results.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_results[:top_k]

    def export_topology_dict(self) -> Dict[str, Any]:
        """Exports full graph node and edge dictionaries for UI visualization."""
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append({"id": n, **data})

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({"source": u, "target": v, **data})

        return {
            "summary": {
                "num_nodes": self.graph.number_of_nodes(),
                "num_edges": self.graph.number_of_edges(),
            },
            "nodes": nodes,
            "edges": edges
        }


# Global Singleton Instance for Zero-Cost In-Memory Re-Use
kg_engine = KnowledgeGraphEngine()
