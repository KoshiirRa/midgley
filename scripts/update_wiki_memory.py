"""
Wiki Update Script for Hindsight Agent Memory & Weekly Review 2.0 (Issue #230)
Updates GitHub Wiki pages in /home/marty/projects/midgley.wiki:
- Agent-Architecture.md
- Self-Hosting.md
- Data-Ingestion-and-APIs.md
- Project-History-and-Roadmap.md
"""

import os
import subprocess

wiki_dir = "/home/marty/projects/midgley.wiki"

if not os.path.exists(wiki_dir):
    print(f"Notice: {wiki_dir} does not exist locally on this host. Skipping direct git commit for wiki.")
else:
    # 1. Update Agent-Architecture.md
    agent_path = os.path.join(wiki_dir, "Agent-Architecture.md")
    if os.path.exists(agent_path):
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_text = f.read()
        if "Weekly Review 2.0" not in agent_text and "Hindsight" not in agent_text:
            memory_section = """

### Agent 7: Weekly Review 2.0 & Episodic Agent Memory (Issues #230 & #421)
- **Retain-Recall-Reflect Triad**: Implements episodic memory (`src/agent_memory.py`) capturing resolved prediction experiences and residual outliers ($|error| \\ge \\$0.25/\\text{gal}$ or directional flips).
- **Vectorize Hindsight-Hosted SaaS Gateway**: Connects to `https://api.hindsight.vectorize.io` (bank `Midgley`) with Bearer auth, zero cold-start latency, and token-efficient cost structure (~$3.50/mo).
- **Standardized Bank Mission & Reasoning Profiles (`Midgley`)**:
  - **Retain Extraction**: Concise extraction of quantitative prediction deviations, physical supply catalysts (refinery outages, pipeline shut-ins, maritime navigation restrictions, EPA/CARB RVP deadlines), and calendar spreads.
  - **Observations Consolidation**: Consolidates durable market dynamics, localized basis spreads (Tulsa, Newark, Cincinnati, Carolinas, Oakland, Port St. Lucie), regulatory blend transitions, and weekly model recalibration lessons into persistent economic beliefs.
  - **Reflect Post-Mortems & Analogies**: Synthesizes qualitative root causes and parameter adjustments (shock decay half-lives $t_{1/2}$, seasonal transition buffers), parameterized with Skepticism 4/5, Literalism 4/5, and Empathy 1/5 (Detached).
- **Zero-Cost SQLite FTS5 Fallback**: 100% offline local memory store (`data/agent_memory.sqlite`) with BM25 keyword matching for $0 cost execution.
- **Qualitative Anomaly Post-Mortems**: Synthesizes root-cause diagnoses, historical shock analogies, and parameter calibration recommendations in Saturday review reports.
"""
            agent_text += memory_section
            with open(agent_path, "w", encoding="utf-8") as f:
                f.write(agent_text)
            print("Updated wiki Agent-Architecture.md")

    # 2. Update Self-Hosting.md
    self_host_path = os.path.join(wiki_dir, "Self-Hosting.md")
    if os.path.exists(self_host_path):
        with open(self_host_path, "r", encoding="utf-8") as f:
            sh_text = f.read()
        if "Hindsight" not in sh_text:
            sh_section = """

### Vectorize Hindsight Episodic Agent Memory Setup (Issues #230 & #421)
- **Option A: Vectorize Hindsight-Hosted SaaS (Recommended)**: Set `HINDSIGHT_API_URL="https://api.hindsight.vectorize.io"`, `HINDSIGHT_API_KEY="hsk_..."`, and `HINDSIGHT_BANK_ID="Midgley"` in `.env` and configure Retain, Observations, and Reflect bank missions in control plane.
- **Option B: Local Dev-VM Docker**: Run `ghcr.io/vectorize-io/hindsight:latest` on port 8888 with Supabase PostgreSQL pgvector.
- **Option C: Zero-Cost SQLite FTS5 Fallback**: Automatically falls back to zero-cost local SQLite (`data/agent_memory.sqlite`) if cloud credentials are absent.
"""
            sh_text += sh_section
            with open(self_host_path, "w", encoding="utf-8") as f:
                f.write(sh_text)
            print("Updated wiki Self-Hosting.md")

    # 3. Update Data-Ingestion-and-APIs.md
    apis_path = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
    if os.path.exists(apis_path):
        with open(apis_path, "r", encoding="utf-8") as f:
            apis_text = f.read()
        if "Hindsight Memory" not in apis_text:
            apis_section = """

### Vectorize Hindsight Agent Memory API Gateway (`src/hindsight_client.py`, Issue #230)
| Endpoint | Method | Purpose | Payload |
| :--- | :---: | :--- | :--- |
| `/v1/default/banks/{bank_id}/memories` | `POST` | Ingests resolved prediction experience & shock tags | `RetainRequest` (`items: [{content, tags, document_id}]`) |
| `/v1/default/banks/{bank_id}/memories/recall` | `POST` | Dense vector & BM25 analogy search | `RecallRequest` (`query, tags, budget`) |
| `/v1/default/banks/{bank_id}/reflect` | `POST` | Agentic synthesis of anomaly post-mortems | `ReflectRequest` (`query, budget`) |
"""
            apis_text += apis_section
            with open(apis_path, "w", encoding="utf-8") as f:
                f.write(apis_text)
            print("Updated wiki Data-Ingestion-and-APIs.md")

    # 4. Commit and Push
    try:
        subprocess.run(["git", "add", "."], cwd=wiki_dir, check=True)
        subprocess.run(["git", "commit", "-m", "docs(wiki): Update agent architecture, self-hosting, and APIs for Weekly Review 2.0 Hindsight memory (#230)"], cwd=wiki_dir, check=True)
        subprocess.run(["git", "push", "origin", "master"], cwd=wiki_dir, check=True)
        print("Wiki pushed successfully.")
    except Exception as e:
        print(f"Notice committing wiki updates: {e}")
