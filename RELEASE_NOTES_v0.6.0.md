# Release Notes - v0.6.0

**Release Date:** September 17, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Architectural Enhancements & Algorithmic Upgrades

### 1. Headline Arena Energy Benchmark & Probabilistic Brier Calibration Connector (Issue #182)
- **Independent Third-Party Verification Engine ([`src/headline_arena_connector.py`](file:///src/headline_arena_connector.py)):**
  - Integrated Midgley with **Headline Arena** (`headlinearena.com`), enabling independent continuous probability (Brier / CRPS) scoring of daily **RBOB Wholesale Gasoline (`RB`)** and **Cushing WTI Crude (`CL`)** directional market forecasts against frozen resolution criteria and mechanical price settlement.
  - Implemented **OAuth2 `client_credentials` Authentication Flow**:
    - Exchanges `HEADLINE_ARENA_CLIENT_ID` and `HEADLINE_ARENA_CLIENT_SECRET` (or `HEADLINE_ARENA_API_KEY`) for session bearer tokens via `POST /api/v1/auth/token` with in-memory TTL caching.
    - Added one-time interactive agent registration helper (`python -m src.headline_arena_connector --register`).
  - Implemented **Closed-Form Normal CDF Quantile Conversion**:
    - Translates Midgley's stacking ensemble quantile bands ($\mu = P_{50}$, $\sigma = \frac{P_{90} - P_{10}}{2.5631}$) and open spot price $S_0$ over asset dead-zone thresholds $d$ ($0.0030$ for RB, $0.0020$ for CL) into normalized categorical Brier probabilities:
      $$P(\text{bullish}) = 1 - \Phi\left(\frac{S_0 \cdot (1+d) - \mu}{\sigma}\right)$$
      $$P(\text{bearish}) = \Phi\left(\frac{S_0 \cdot (1-d) - \mu}{\sigma}\right)$$
      $$P(\text{neutral}) = \max\left(0, 1 - P(\text{bullish}) - P(\text{bearish})\right)$$
    - Categorical submission format: `{"asset": "RB", "direction": "bullish" | "bearish" | "neutral", "confidence": 0.0 - 1.0, "reasoning": "..."}`.
  - **Settlement Rules Dynamic Ingestion**:
    - Dynamically queries `GET /api/v1/eval/settlement-rules` for per-asset dead-zone widths and precision rules with offline fallback defaults.
  - **Environment Isolation & Dev-Test Provenance**:
    - **Local / Dev (`MIDGLEY_ENV=dev`)**: Dry-run by default. Computes and logs Brier probabilities without making external network POST requests.
    - **Explicit Dev Test Submissions (`--live` / `HEADLINE_ARENA_DEV_SUBMIT=1`)**: Automatically prefixes submission reasoning with `[DEV-TEST] [DEVELOPMENT]` to distinguish model evaluations from official production track records.
    - **Production (`MIDGLEY_ENV=prod` / GitHub Actions)**: Executes live headless submissions during scheduled daily runs when repository secrets are present.
    - **Test Suite (`TESTING=1`)**: Completely mocks and suppresses outgoing network calls.
  - **Connector Telemetry Integration**:
    - Automatically records execution latencies and connection health to `data/connector_telemetry.json` via [`src/connector_telemetry.py`](file:///src/connector_telemetry.py).
- **REST API Server Gateway Endpoints ([`src/api_server.py`](file:///src/api_server.py)):**
  - Exposed `GET /api/v1/connectors/headline-arena/status`: Connection status, environment, and settlement rules.
  - Exposed `POST /api/v1/connectors/headline-arena/submit`: Dry-run or live prediction submission endpoint.
- **Master Execution Pipeline Integration ([`run_all.py`](file:///run_all.py)):**
  - Integrated optional `--submit-headline-arena` CLI flag support and automatic production benchmark submission during master execution runs.
- **Dedicated Test Suite ([`tests/test_headline_arena_connector.py`](file:///tests/test_headline_arena_connector.py)):**
  - 17/17 unit tests passing covering normal CDF probability math, dead-zone thresholds, OAuth2 caching, dry-run safety gates, explicit dev-test tagging, and REST API endpoints.

---

## 🧪 Comprehensive Test Suite & Validation

- **Execution Target:** Local dedicated Linux VM (`dev-vm` / `10.42.42.54`) & Local Windows Test Runner.
- **Newly Added Unit Test Suites:**
  - `tests/test_headline_arena_connector.py` (17/17 tests passed in 3.74s)
- **Full Repository Test Suite Execution:**
  - **Status:** **265 passed, 1 skipped, 0 failed** in 74.70s.
  - **Test Pass Rate:** 100%.

---

## 📋 Closed & Remediated GitHub Issues

- **[Issue #182](https://github.com/KoshiirRa/midgley/issues/182):** feat(integration): Implement Headline Arena Energy Forecasting Connector with Independent Brier Continuous Probability Scoring & OAuth2 Flow.

---

## 📚 Documentation & Wiki Enhancements

1. **`midgley.wiki` ([`Data-Ingestion-and-APIs.md`](https://github.com/KoshiirRa/midgley/wiki/Data-Ingestion-and-APIs)):**
   - Added **Section 43: Headline Arena Energy Benchmark Connector & Probabilistic Calibration**, documenting the OAuth2 client credentials flow, closed-form normal CDF quantile conversion over dead-zone thresholds, environment isolation rules, and REST API endpoints.
2. **`SELF_HOSTING.md` & `midgley.wiki` ([`Self-Hosting.md`](https://github.com/KoshiirRa/midgley/wiki/Self-Hosting)):**
   - Added **Section 2: Headline Arena Benchmark & Calibration Configuration**, detailing environment variables (`HEADLINE_ARENA_CLIENT_ID`, `HEADLINE_ARENA_CLIENT_SECRET`, `HEADLINE_ARENA_DEV_SUBMIT`) and the one-time registration CLI helper.
3. **`AGENTS.md`:**
   - Added **Section 24: Headline Arena Energy Benchmark & Continuous Calibration Directives**, specifying architecture, probability integration, and environment safety boundaries.
