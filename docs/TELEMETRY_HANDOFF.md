# Agent & DevOps Handoff: System Telemetry & Grafana Dashboard Ingestion (Issue #107 & Issue #108)

This document serves as the authoritative handoff guide for AI agents, DevOps engineers, and Grafana administrators integrating Midgley's operational telemetry, API quota safety valves, and LLM token metric streams into monitoring dashboards.

---

## 1. Architecture Overview & Data Streams

Midgley exposes 3 complementary telemetry channels for observability:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MIDGLEY TELEMETRY & OBSERVABILITY                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   PROMETHEUS    │         │   SYSTEM QUOTA  │         │ LOCAL TELEMETRY │
│  GET /metrics   │         │ GET /api/v1/... │         │   JSON LEDGER   │
│ (PromText Stream)│         │ (Live JSON API) │         │ data/telemetry..│
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         ▼                           ▼                           ▼
  Grafana Exporter            Agent Dashboard              Audit Analytics
```

1. **Prometheus Text Exporter (`GET /metrics`)**:
   Standard Prometheus exposition format stream served at `http://localhost:8000/metrics`. Used for Grafana scraping, alerting, and trend visualization.
2. **System Quota REST Endpoint (`GET /api/v1/system/quota`)**:
   Live JSON status exposing quota usage, limits, remaining ratios, and safety valve statuses for Finlight, OilpriceAPI, AlphaVantage, and Gemini LLM.
3. **Structured Local Telemetry Ledgers (`data/telemetry_ledger.json` & `data/connector_telemetry.json`)**:
   Persistent structured JSON logs tracking per-call execution latencies, status codes, data ages, and fallback activations.

---

## 2. Environment Isolation (`dev` vs `prod`)

To allow tracking local development work separately from live production executions in Grafana:
* **Metric Tagging**: Every emitted metric includes an `environment` label (`environment="dev"` or `environment="prod"`).
* **Dynamic Resolution**: `MIDGLEY_ENV` environment variable dictates environment resolution (defaults to `"dev"` for local, `dev-vm`, and test runs; `"prod"` for GitHub Actions cloud runners).
* **Grafana Template Variable**: Dashboards feature an `$environment` variable filter enabling single-click switching between `prod`, `dev`, or `all`.

---

## 3. Metric Dictionary & Key Counters

### A. LLM & Token Metrics
- `llm_tokens_consumed_total{environment, vendor, model, type}`: Counter for prompt, completion, and total LLM tokens.
- `llm_estimated_cost_usd_total{environment, vendor, model}`: Cumulative estimated dollar cost (USD) based on token counts.
- `llm_tier_fallback_activations_total{environment, from_tier, to_tier}`: Counter tracking fallback activations from Tier 1 Gemini API to Tier 3 Offline Rule-Based Lexicon.

### B. API Quotas & Rate Limits
- `api_quota_remaining_ratio{environment, service}`: Gauge (0.0 to 1.0) indicating remaining API quota ratio before throttling.
- `api_quota_calls_used_total{environment, service}`: Counter tracking API calls made against hard safety caps (e.g. Finlight 150 call/month limit).

---

## 4. Sample PromQL Queries for Grafana

### Total LLM Cost (USD) by Environment
```promql
sum(llm_estimated_cost_usd_total{environment=~"$environment"}) by (model)
```

### Remaining Quota Percentage Across API Services
```promql
api_quota_remaining_ratio{environment=~"$environment"} * 100
```

### Tier Fallback Activations (Offline Lexicon Rate)
```promql
sum(rate(llm_tier_fallback_activations_total{environment=~"$environment"}[5m]))
```

---

## 5. Prometheus Scraper Configuration (`prometheus.yml`)

Add the following scrape target to your `prometheus.yml` configuration:

```yaml
scrape_configs:
  - job_name: 'midgley_telemetry'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000', '10.42.42.54:8000']
    metrics_path: '/metrics'
```

---

## 6. Grafana Dashboard Import Instructions

1. Open **Grafana** $\rightarrow$ **Dashboards** $\rightarrow$ **Import**.
2. Upload the JSON dashboard file located at [`grafana/dashboard_observability.json`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/grafana/dashboard_observability.json).
3. Select your Prometheus data source and click **Import**.
4. Use the top **Environment** dropdown filter to switch between `prod` and `dev` telemetry feeds.
