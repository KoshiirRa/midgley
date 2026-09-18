# Release Notes - v0.6.6 (Draft)

**Release Date:** September 18, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`) & Cloudflare Edge  
**Git Branch:** `dev`  

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.6** integrates multi-agent financial simulation and scenario decision graph concepts evaluated from [666ghj/MiroFish](https://github.com/666ghj/MiroFish) into Midgley's qualitative and quantitative forecasting pipeline (Issue #307). It introduces a 4-persona deliberative market cohort, token-efficient single-round structured consensus, a Tier 3 deterministic elasticity matrix fallback, dynamic dashboard observability, and configurable feature toggles:

1. **MiroFish 4-Persona Deliberative Market Cohort (`src/scenario_simulator.py` - Issue #307):**
   - Implemented a 4-persona deliberative market simulation cohort:
     - `Agent_Refiner` (Refinery Operations & 3-2-1 Crack Spreads): Evaluates crude slates, refining margins, FCCU/Hydrocracker status, and product yields.
     - `Agent_Logistics` (Pipeline & River Barge Arbitrageur): Evaluates Colonial Pipeline allocations, barge draft restrictions (Ohio/Mississippi River), and rack freight basis.
     - `Agent_Consumer` (Commercial Fleet & Retail Buyer): Evaluates retail price elasticity, commuter driving patterns, and demand destruction thresholds.
     - `Agent_Macro` (Macro Strategist & Geopolitical Analyst): Evaluates Cboe OVX tail volatility, OPEC+ production quotas, central bank rate actions, and trade tariffs.
   - **Single-Round Prompt Consensus Contract (`COHORT_SIMULATION_PROMPT`):** All 4 personas deliberate and provide structured JSON outputs in a single batched LLM invocation, preventing multi-turn chat token explosion.
   - **Behavioral Divergence Index ($\sigma$):** Computes the standard deviation of persona price shock estimates to quantify market disagreement and uncertainty.
   - **Cross-Commodity Math:** Simultaneously models price impacts across RBOB Wholesale Gasoline ($\Delta P_{\text{RBOB}}$), Heating Oil / ULSD Distillate ($\Delta P_{\text{HO}}$), and Regional Freight Basis ($\Delta B_{\text{cents}}$).

2. **Tier 3 Deterministic Elasticity Matrix Fallback:**
   - 100% offline, zero-cost calibrated rule-based matrix covering 6 shock archetypes: `refinery_outage`, `pipeline_disruption`, `meteorological`, `hydrological`, `geopolitical`, and `regulatory_spec`. Guarantees zero downtime and $0 API spend when LLM API keys are absent.

3. **Mermaid & JSON Decision Graph Export:**
   - `export_scenario_decision_graph_mermaid()` automatically generates clean, syntactically valid Mermaid flowchart diagrams (`flowchart TD`) and JSON causal graphs for dashboard visualization.

4. **Modular Feature Toggle & Observability:**
   - **Environment Variable:** `MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION` (`0` default / `1` active) for safe production enablement.
   - **Request-Level Override:** `enable_cohort_simulation: Optional[bool]` and `custom_headline: Optional[str]` on `POST /api/v1/forecast/simulate` and MCP tool `simulate_fuel_market_shock`.
   - **Public Dashboard Observability (`src/dashboard_generator.py`):** Added `get_multi_agent_sim_badge()` rendering dynamic status badges (`Multi-Agent Cohort: ON` in purple vs `Multi-Agent Cohort: OFF` in slate) across all generated HTML page headers.
   - **GitHub Actions Integration:** Bound `MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION: ${{ vars.MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION }}` across `.github/workflows/gas_price_forecast.yml` and `.github/workflows/weekly_model_review.yml`.

5. **Documentation & Agent Guidance Updates:**
   - Updated [`docs/AGENT_GUIDANCE.md`](docs/AGENT_GUIDANCE.md) with feature status inspection helpers (`is_multi_agent_sim_enabled()`) and testing directives.
   - Updated [`AGENTS.md`](AGENTS.md) under Agent 5 specification.
   - Updated [`API.md`](API.md) with request/response schema specifications.
   - Synchronized official GitHub Wiki (`KoshiirRa/midgley.wiki` on `master`).

---

## 🧪 Verification & Test Suite Matrix

- **Execution Target:** Dedicated Linux VM (`dev-vm` / `10.42.42.54`).
- **Test Suite Results:**
  - `tests/test_scenario_simulator.py` (6/6 tests passing)
  - `tests/test_scenario_engine.py` (6/6 tests passing)
  - `tests/test_api_server.py` (21/21 tests passing)
  - `tests/test_dashboard_generator.py` (19/19 tests passing)
  - **Total: 52 / 52 tests passing (100% pass rate).**
