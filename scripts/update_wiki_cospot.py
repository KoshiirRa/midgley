import os
import subprocess

wiki_dir = "/home/marty/projects/midgley.wiki"

citations_path = os.path.join(wiki_dir, "Academic-Citations-and-Research-Foundations.md")
if os.path.exists(citations_path):
    with open(citations_path, "r", encoding="utf-8") as f:
        text = f.read()

    if "CoSPOT" not in text:
        text = text.replace("indexes all 12 implemented papers", "indexes all 13 implemented papers")
        new_row = "| **13** | [CoSPOT: Compositional Spectral Prompts for OTSF](https://arxiv.org/abs/2609.02093v1) | Seungyoon Choi, Youngin Cho et al. (KAIST) | Sep 2026 | `src/cospot_spectral_engine.py`, `src/event_analyzer.py`, `src/models.py` | **Compositional Spectral Prompts & DWT Wavelet Context**: Orthogonal Fourier basis decomposition ($T_{\\text{dom}}, E_{\\text{low}}, H_{\\text{spectral}}$) and 2-level DWT wavelet filtering ($D_1, D_2, A_2$) to condition Gemini prompts on frequency regimes, resolving LLM numerical blindness with geometric loss-decayed online projection head adaptation ($\\delta=0.90$). |\n"
        text = text.strip() + "\n" + new_row
        with open(citations_path, "w", encoding="utf-8") as f:
            f.write(text)
        print("Updated wiki citations.")

agent_path = os.path.join(wiki_dir, "Agent-Architecture.md")
if os.path.exists(agent_path):
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_text = f.read()
    if "CoSPOT" not in agent_text:
        agent_text += "\n\n### CoSPOT Compositional Spectral & Wavelet Engine (Issue #215, arXiv:2609.02093)\n- **Discrete Fourier Transform (DFT)**: Decomposes price series into orthogonal frequency bases with low-pass filtering and spectral entropy.\n- **Discrete Wavelet Transform (DWT)**: Isolates micro-noise (D1) vs localized shock variations (D2) vs macro trend baselines (A2).\n- **Prompt Context Enrichment**: Injects `[MARKET FREQUENCY & SPECTRAL REGIME]` blocks into Gemini 2.5 Flash event analysis prompts.\n- **Online Projection Adapter**: Rapidly adapts projection weights with geometric loss decay ($\\delta=0.90$) to eliminate concept drift.\n"
        with open(agent_path, "w", encoding="utf-8") as f:
            f.write(agent_text)
        print("Updated wiki Agent-Architecture.md")

self_host_path = os.path.join(wiki_dir, "Self-Hosting.md")
if os.path.exists(self_host_path):
    with open(self_host_path, "r", encoding="utf-8") as f:
        sh_text = f.read()
    if "CoSPOT" not in sh_text:
        sh_text += "\n\n### CoSPOT Spectral & Wavelet Engine Zero-Dependency Execution\nAll Fourier and Wavelet transformations in `src/cospot_spectral_engine.py` run natively on standard Python libraries (`numpy`, `scipy`) without requiring extra cloud subscriptions, GPU accelerators, or third-party paid dependencies.\n"
        with open(self_host_path, "w", encoding="utf-8") as f:
            f.write(sh_text)
        print("Updated wiki Self-Hosting.md")

subprocess.run(["git", "add", "."], cwd=wiki_dir, check=True)
subprocess.run(["git", "commit", "-m", "docs(wiki): Update citations, agent architecture, and self-hosting for CoSPOT Spectral Engine (Issue #215)"], cwd=wiki_dir, check=True)
subprocess.run(["git", "push", "origin", "master"], cwd=wiki_dir, check=True)
print("Wiki pushed successfully.")
