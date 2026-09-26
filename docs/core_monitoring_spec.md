# 🔬 Specification: CORE API Research Paper Monitoring in Weekly Review (GitHub Issue #53)

**Issue Link:** [KoshiirRa/midgley#53](https://github.com/KoshiirRa/midgley/issues/53)  
**Status:** Implemented / Active  
**Module Target:** `src/core_monitor.py` & `src/weekly_issue_reporter.py`  

---

## 1. Executive Summary & Context

The **Midgley Multi-Agent Forecasting Architecture** executes an automated weekly model performance review on GitHub Actions (`.github/workflows/weekly_model_review.yml` every Saturday at 08:12 AM US Central / 13:12 UTC). During this review, Agent 7 (`src/weekly_issue_reporter.py`) parses rolling 5-day out-of-time accuracy, updates performance benchmarks in `data/prediction_history.csv`, and publishes a GitHub Issue report detailing MAE, directional accuracy, and calibration recommendations.

**Goal of Issue #53:** Integrate the **CORE (COnnecting REpositories) API** (`https://api.core.ac.uk/v3/search/works`) to automatically monitor open-access research papers published across thousands of institutional repositories and academic publishers. Adding CORE alongside arXiv allows Agent 7 (Model Performance Review & Feedback Loop Agent) to discover emerging research papers on energy commodity forecasting, refined product crack spreads, macroeconomic oil shock modeling, and LLM-based financial time-series prediction that may not appear on arXiv.

---

## 2. Technical Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SATURDAY WEEKLY REVIEW PIPELINE                      │
│            (.github/workflows/weekly_model_review.yml)                 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     src/weekly_issue_reporter.py                        │
└───────────────────┬─────────────────────────────────┬───────────────────┘
                    │                                 │
                    ▼                                 ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────┐
│  src/arxiv_monitor.py                │  │   src/core_monitor.py         │
│  (Queries arXiv REST API)            │  │   (Queries CORE V3 API)       │
└───────────────────┬──────────────────┘  └───────────────┬───────────────┘
                    │                                     │
                    └───────────────────┬─────────────────┘
                                        │ Combined Markdown Body
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       GITHUB ISSUE REPORT                               │
│  • Rolling 30/60/90-Day Accuracy Metrics                                │
│  • Active 5-Day Out-of-Time Forecasts                                   │
│  • Model Diagnostics & Recommendations                                  │
│  • 📚 Relevant Recent arXiv Research Papers                             │
│  • 🔬 Relevant CORE Open-Access Research Papers                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CORE REST API V3 Specification

### Endpoint & Authentication
- **Base Endpoint:** `https://api.core.ac.uk/v3/search/works`
- **Method:** `GET`
- **Authentication:** `Authorization: Bearer <CORE_API_KEY>` header or `api_key` query parameter (`CORE_API_KEY` stored in environment variables / GitHub repository secrets).
- **Timeout & Rate Limits:** 10-second timeout limit. Graceful fallback on network timeout, HTTP 429 rate-limiting, missing key, or API errors.

### Search Topics & Domain Query Syntax
The default search query targets energy commodity pricing, refining margins, and machine learning time-series literature:

```text
("gasoline price forecasting" OR "RBOB futures" OR "oil market volatility" OR "refining rack margin" OR "time series LLM sentiment energy" OR "commodity price machine learning")
```

### Parameters & Sorting
- `q`: Search query string
- `limit`: Maximum results requested (default: `10`)
- `scroll`: `false`

### Response Data Structure (JSON)
The CORE API V3 returns a JSON object structured as:

```json
{
  "totalHits": 42,
  "results": [
    {
      "id": "12345678",
      "title": "Machine Learning and LLM Sentiment in Energy Commodity Price Forecasting",
      "authors": [{"name": "A. Smith"}, {"name": "B. Jones"}],
      "publishedDate": "2026-08-28T00:00:00Z",
      "abstract": "We investigate hybrid forecasting models fusing text sentiment with RBOB futures...",
      "doi": "10.1016/j.eneco.2026.107000",
      "downloadUrl": "https://core.ac.uk/download/pdf/12345678.pdf"
    }
  ]
}
```

---

## 4. Implementation Details

### File 1: `src/core_monitor.py`

Key functions implemented:
1. `fetch_recent_core_articles(days_back: int = 7, max_results: int = 10, api_key: str = None) -> List[Dict[str, Any]]`
   - Builds `https://api.core.ac.uk/v3/search/works` GET request.
   - Passes `Authorization: Bearer <CORE_API_KEY>` header.
   - Enforces a 10-second timeout limit.
   - Parses items from `results` array, mapping `id`, `title`, `authors`, `publishedDate`, `abstract`, `doi`, `downloadUrl`.
   - Filters out articles older than `days_back` cutoff date.
   - On error or rate-limiting, logs a warning and returns `[]`.

2. `format_core_markdown_section(days_back: int = 7, api_key: str = None) -> str`
   - Converts articles into GitHub Markdown section formatted with header `## 🔬 Relevant CORE Open-Access Research Papers`.
   - Displays title link, author list (with `et al.` for >3 authors), published date, DOI, PDF download link, and abstract preview snippet.
   - Formats a graceful fallback notice if no papers are found or on API errors.

### File 2: `src/weekly_issue_reporter.py`

Import `format_core_markdown_section` and append `core_section_md` to `generate_weekly_markdown_report()`.

### File 3: `.github/workflows/weekly_model_review.yml`

Pass `CORE_API_KEY: ${{ secrets.CORE_API_KEY }}` into the execution environment for the weekly review runner step.

---

## 5. Sample Rendered Markdown Output

When relevant papers are retrieved:

```markdown
## 🔬 Relevant CORE Open-Access Research Papers

The following open-access research papers were indexed on CORE within the last 7 days and may contain relevant methodological or empirical insights for the Midgley forecasting architecture:

### 📄 [Machine Learning and LLM Sentiment in Energy Commodity Price Forecasting](https://doi.org/10.1016/j.eneco.2026.107000)
- **Authors:** A. Smith, B. Jones
- **Published:** `2026-08-28` | **DOI:** `10.1016/j.eneco.2026.107000` | **PDF:** [Download](https://core.ac.uk/download/pdf/12345678.pdf)
- **Abstract Snippet:** We investigate hybrid forecasting models fusing text sentiment with RBOB futures...
```

When no new papers are indexed:

```markdown
## 🔬 Relevant CORE Open-Access Research Papers

_No new open-access research papers matching energy commodity, refining rack margin, or LLM time-series queries were indexed on CORE in the last 7 days._
```

---

## 6. Testing & Maintenance Guidelines

- **Unit Tests:** `tests/test_core_monitor.py` covers:
  - Successful JSON V3 response parsing.
  - 7-day publication window filtering.
  - Graceful fallback on network timeout, HTTP errors, and missing API key.
  - Formatting of empty and populated markdown sections.
- **Maintenance:** If CORE API schema updates, update `_parse_core_item()` in `src/core_monitor.py` to maintain field compatibility.
