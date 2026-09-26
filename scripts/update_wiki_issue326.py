"""
Wiki Update Script for Issue #326 (Turso Hrana Protocol String Serialization & Region-Scoped Memory Retention)
"""

import os
import subprocess

wiki_dir = "/home/marty/projects/midgley.wiki"

if os.path.exists(wiki_dir):
    # 1. Update Agent-Architecture.md
    agent_path = os.path.join(wiki_dir, "Agent-Architecture.md")
    if os.path.exists(agent_path):
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_text = f.read()
        if "Region-Scoped Memory Retention" not in agent_text:
            memory_note = """
- **Region-Scoped Anomaly Retention (Issue #326)**: Ingestion of evaluated prediction anomalies ($|error| \\ge \\$0.25/\\text{gal}$) into `AgentMemoryManager` is strictly scoped to the target region being evaluated (`backfill_actual_prices_and_evaluate(target_region=...)`), eliminating redundant global tail re-evaluations across multiple hub executions.
"""
            agent_text += memory_note
            with open(agent_path, "w", encoding="utf-8") as f:
                f.write(agent_text)
            print("Updated wiki Agent-Architecture.md")

    # 2. Update Self-Hosting.md
    self_host_path = os.path.join(wiki_dir, "Self-Hosting.md")
    if os.path.exists(self_host_path):
        with open(self_host_path, "r", encoding="utf-8") as f:
            sh_text = f.read()
        if "Turso Hrana Protocol Serialization" not in sh_text:
            sh_note = """
- **Turso Hrana Protocol Serialization (Issue #326)**: Historical prediction cloud synchronization formats integer types as string values in JSON requests (`{\"type\": \"integer\", \"value\": \"5\"}`) to ensure 100% compatibility with Turso Edge SQLite HTTP endpoints.
"""
            sh_text += sh_note
            with open(self_host_path, "w", encoding="utf-8") as f:
                f.write(sh_text)
            print("Updated wiki Self-Hosting.md")

    # Commit and push
    try:
        subprocess.run(["git", "add", "."], cwd=wiki_dir, check=True)
        subprocess.run(["git", "commit", "-m", "docs(wiki): Document region-scoped memory retention and Turso Hrana serialization (#326)"], cwd=wiki_dir, check=True)
        print("Committed wiki updates on master branch.")
    except Exception as e:
        print(f"Notice during wiki git commit: {e}")
else:
    print("Notice: wiki_dir not found on this host.")
