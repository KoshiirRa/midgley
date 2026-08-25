## Feature Request: Consolidate Finlight API Queries, Add 30-Minute Disk Cache & Quota Fallback Handling for Hourly Workflows

### 📌 Problem Statement

To support hourly forecast workflows (24 executions/day) for Midgley's REST API and MCP endpoints, the current news ingestion module (`src/finlight_feed.py` and `src/geopolitical_feeds.py`) executes **4 separate HTTP POST requests** to `api.finlight.me/v2/articles` per forecast run:
- 3 separate queries in `src/finlight_feed.py` (oil/gasoline, refining, maritime chokepoints).
- 1 separate query in `src/geopolitical_feeds.py` (Iran/Hormuz/Suez/Venezuela).

At 4 requests/run $\times$ 24 runs/day = **96 requests/day** ($\approx 2,880$ requests/month), this consumes **~57.6%** of Finlight's **5,000 requests/month free tier limit**. Adding automated PR workflows, test suites, or additional developer runs risks breaching the 5,000 monthly quota and triggering rate limit HTTP 429 / 403 errors.

---

### 💡 Proposed Optimizations & Technical Design

#### 1. Single Unified Query Consolidation (75% Request Reduction)
Consolidate the 4 separate queries into a single unified energy query string:
```python
UNIFIED_ENERGY_QUERY = (
    "(oil OR gasoline OR crude OR RBOB OR OPEC OR petroleum OR "
    "refinery OR Cushing OR outage OR Hormuz OR Red Sea OR Houthi OR Suez OR tanker OR sanctions)"
)
```
- Reduces API consumption from **4 calls/run to 1 call/run**.
- Hourly math: 1 call/hour $\times$ 24 hours/day = **24 calls/day** ($\approx 720$ calls/month, consuming only **14.4%** of the 5,000 free quota!).

#### 2. Disk-Backed Response Caching (`data/finlight_cache.json` with 30-Min TTL)
Implement a disk-backed JSON cache at `data/finlight_cache.json`:
- Cache duration: **30 minutes (1800 seconds)** TTL.
- When `get_finlight_energy_events()` or `fetch_finlight_articles()` is called, check if `data/finlight_cache.json` exists and is younger than 30 minutes.
- If valid, return cached articles immediately without making outbound HTTP calls to `api.finlight.me`.

#### 3. HTTP 429 / 403 Rate Limit & Quota Fallback Handling
Add robust exception handling to `fetch_finlight_articles()`:
- Handle HTTP status codes `429` (Too Many Requests), `403` (Quota Exceeded), and network connection timeouts gracefully.
- If an API error occurs or the quota is reached, log a warning and fall back to cached historical events and the deterministic domain NLP lexicon in `src/event_analyzer.py` without interrupting model pipeline execution.

---

### ⚙️ Tasks & Implementation Checklist

- [ ] Update `src/finlight_feed.py` with `UNIFIED_ENERGY_QUERY`, `data/finlight_cache.json` disk caching (30-min TTL), and HTTP 429/403 error handling.
- [ ] Refactor `src/geopolitical_feeds.py` to reuse cached articles from `src.finlight_feed`.
- [ ] Add unit tests in `tests/test_finlight_feed.py` verifying cache hits, TTL expiration, and rate-limit fallbacks.
- [ ] Verify test suite and forecast pipeline execution on dev branch.
