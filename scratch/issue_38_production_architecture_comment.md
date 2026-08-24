## 🚀 Production Deployment Architecture Proposal (Zero-Local Server Dependency)

To deploy the **API and MCP Server endpoints** for production (`main` branch) without relying on local development infrastructure (`dev-vm` server or home network hardware), the following multi-tiered, serverless-first production deployment blueprint is proposed:

---

### 🏛️ 1. Primary Production REST API: Serverless Static JSON via GitHub Pages (100% Zero-Cost & 99.99% Availability)

Rather than running a continuous Python web application server for basic REST GET queries, the primary production API will leverage **GitHub Actions** and **GitHub Pages**.

#### Automated Deployment Pipeline:
1. **Cron Runner (`.github/workflows/gas_price_forecast.yml`)**:
   - Executes during daily forecast runs (or an hourly cron runner).
   - Ingests live AAA and GasBuddy fuel prices, calculates 5-day regional forecasts across all active locales (National RBOB, Tulsa OK, Newark DE, Cincinnati OH/KY, Oakland CA), and runs key scenario simulations.
   - Generates and writes pre-rendered, structured JSON files into `docs/api/v1/`:
     - `docs/api/v1/combined/oakland.json`
     - `docs/api/v1/combined/tulsa.json`
     - `docs/api/v1/combined/newark.json`
     - `docs/api/v1/combined/cincinnati.json`
     - `docs/api/v1/combined/national.json`
     - `docs/api/v1/scenarios/hormuz_blockade.json`
     - `docs/openapi.json`
     - `docs/.well-known/ai-plugin.json`
2. **Public HTTPS GET Access**:
   - Any external LLM agent, ChatGPT Action, or custom chatbot can query live data via standard HTTP GET requests:
     `https://koshiirra.github.io/midgley/api/v1/combined/oakland.json`
3. **Benefits**:
   - Zero hosting cost ($0/mo).
   - Zero server maintenance overhead.
   - 99.99% uptime guaranteed by GitHub's global CDN network.

---

### ☁️ 2. Live Dynamic MCP & Simulation Gateway: Serverless Containers (Google Cloud Run / Render)

For features requiring real-time on-demand scraping, custom zip-code lookups, interactive counterfactual shock simulations (`POST`), and live Model Context Protocol (MCP) Server-Sent Events (`SSE`) streams:

1. **Dockerized Microservice (`src/api_server.py` & `src/mcp_server.py`)**:
   - Containerized FastAPI + FastMCP application packaged via Docker.
2. **Scale-to-Zero Cloud Hosting (Google Cloud Run / Render / Fly.io)**:
   - Deployed to **Google Cloud Run** or **Render**, configured to **scale to zero instances when idle**.
   - Under low-to-medium LLM query traffic, hosting cost remains **$0/month** (within GCP free tier of 2M requests/month). When a live request or MCP SSE stream arrives, the container cold-starts in ~1 second.
3. **Cloudflare Global CDN Edge Caching**:
   - Cloudflare CDN proxies requests to `api.midgley.app`.
   - Caches GET responses for 15 minutes at edge nodes, preventing repeated AAA/GasBuddy scrapers and container wake-ups.

---

### 📦 3. Client-Side MCP Stdio Package (`midgley-mcp` on PyPI)

For local agent environments (Claude Desktop, Antigravity CLI, Cursor, Aider):

1. **PyPI Package (`pip install midgley-mcp` / `npx midgley-mcp`)**:
   - A lightweight client-side MCP stdio wrapper executable via `uvx midgley-mcp` or `npx midgley-mcp`.
2. **Seamless Local LLM Integration**:
   - When added to Claude Desktop or Antigravity configuration:
     ```json
     {
       "mcpServers": {
         "midgley": {
           "command": "uvx",
           "args": ["midgley-mcp"]
         }
       }
     }
     ```
   - The adapter executes locally on the user's machine, fetches the latest JSON snapshots from GitHub Pages (or Cloud Run), and presents native MCP tools directly to the LLM agent without needing any server background daemon running.

---

### 📊 Production Architectural Summary

| Environment Tier | Target Host / Technology | Cost | Uptime / Reliability | Primary Use Case |
| :--- | :--- | :---: | :---: | :--- |
| **Production REST API (Primary)** | GitHub Pages (`docs/api/v1/*.json`) | **$0** | **99.99%** (GitHub CDN) | Primary public endpoint for ChatGPT Actions, web chatbots, and static GET queries. |
| **Production MCP Gateway** | Google Cloud Run / Render (Docker) | **$0** (Scale to zero) | **High** (Cloud native) | Dynamic zip lookups, live MCP SSE streams, and counterfactual `POST` simulations. |
| **Local LLM Tool Provider** | PyPI (`uvx midgley-mcp`) | **$0** | **100%** (Runs client-side) | Plug-and-play local MCP tool provider for Claude Desktop, Antigravity CLI, & Cursor. |
| **Dev Environment (Internal)** | `dev-vm` (`10.42.42.54:8000`) | **$0** | Local Lab | Internal testing, local development, and experimental feature builds. |
