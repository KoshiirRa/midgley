# Release Notes - v0.4.7

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Qualitative Intelligence Knowledge Graph & Agent Memory Layer (Issue #116)
- **Zero-Cost Embedded Graph Engine (`src/knowledge_graph.py`):** Built `KnowledgeGraphEngine` using pure Python `NetworkX` graph core with `SQLite` persistent storage (`data/knowledge_graph.db`), ensuring **$0 infrastructure cost** and zero external database server requirements.
- **Automated Petroleum Topology Seeding:** Automatically seeds all 9 refining assets, 4 marine chokepoints, 5 PADD regions, and 6 regional metro hubs on initial startup from `src/spatial_refinery.py`.
- **GraphRAG Subgraph Context Injection (`src/event_analyzer.py`):** Resolves entity nodes from breaking headlines, extracts 2-hop neighborhood subgraphs, and formats standardized `GraphContextSchema` contexts into LLM prompts (`LLM_SINGLE_PROMPT`) to ground scoring calls with physical supply topology.
- **Episodic Shock Memory & Precedent Retrieval Engine:** Ingests high-impact event shocks into `kg_memory_shocks`, supporting TF-IDF + graph distance precedent retrieval (*"Find historical gas price reactions to East Bay PSPS heatwave refinery curtailments"*).
- **Council of LLMs Forward-Compatible Architecture:** Standardizes graph context serialization for multi-provider LLM ensembles (Gemini, OpenAI, Anthropic, DeepSeek, local models) while recording multi-model attribution, individual provider opinions, and consensus disagreement metrics (`council_variance`).
- **REST API & MCP Tooling:**
  - Added REST endpoints: `GET /api/v1/graph/topology`, `GET /api/v1/graph/subgraph`, `GET /api/v1/memory/precedents`, `POST /api/v1/graph/ingest`.
  - Registered MCP tools in `src/mcp_server.py`: `query_knowledge_graph` and `retrieve_event_precedents`.
- **Pluggable Enterprise Adapters:** Included `PluggableGraphAdapter` abstract class supporting optional external backends (`Neo4jAdapter`, `Mem0Adapter`, `CogneeAdapter`).

---

## 🧪 Verification & Test Suite Results

- **Knowledge Graph Unit Test Suite (`pytest tests/test_knowledge_graph.py`):**
  ```bash
  pytest tests/test_knowledge_graph.py -v
  ```
  **Result:** `8 passed` (100% pass rate on `dev-vm` and Windows host).
- **Full System & Event Test Suite Execution:**
  ```bash
  pytest tests/test_knowledge_graph.py tests/test_event_analyzer.py tests/test_api_server.py -v
  ```
  **Result:** `31 passed, 0 warnings` (100% clean execution).

---

## 📋 Closed GitHub Issues
- **Issue #116**: `[Feature Request] Implement Knowledge Graph & Agent Memory Layer for Qualitative Intelligence (Cognee, GraphRAG, Graphiti, Mem0 & Neo4j)` (Closed as completed)
