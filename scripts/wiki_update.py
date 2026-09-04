import os

wiki_dir = "/home/marty/projects/midgley/wiki_tmp"

# 1. Update Data-Ingestion-and-APIs.md
apis_file = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
with open(apis_file, "r", encoding="utf-8") as f:
    apis_content = f.read()

new_api_section = """## 20. REST API Gateways & Endpoints (src/api_server.py)
* **GET /api/v1/prices/live**: Live retail gas price lookup with 3-tier fallback chain and optional `?zip_code=...` 4-tier geocoding resolution.
* **GET /api/v1/forecast/predict**: 5-day out-of-time quantitative price prediction with optional `?zip_code=...` query parameters.
* **GET /api/v1/forecast/scoreboard**: Continuous MLOps rolling model accuracy scoreboard returning 30/60/90-day MAE, RMSE, MAPE, Directional Hit Rate %, Naive Persistence Baseline MAE, and Model MAE Uplift % vs. ground-truth market actuals.
* **GET /api/v1/combined**: Reconciled current pump price, target forecast, dynamic rack margin, and key driver breakdown.
* **GET /api/v1/locales**: Dynamic discovery of all supported locale codes (`tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `port_st_lucie`, `bayarea`, `national`), `region_id`, PADD region, statutory fuel tax burdens, refining hub logistics, and metadata profiles loaded via `src/regional_metadata.py` (Issue #48).
* **POST /api/v1/forecast/batch**: Multi-region batch forecast API accepting JSON requests (`{"locales": ["tulsa", "oakland", "cincinnati"], "days": 5}`) and returning combined forecasts in a single HTTP response (Issue #48).
* **POST /api/v1/combined/batch**: Multi-region batch combined API accepting JSON requests (`{"locales": ["tulsa", "newark", "port_st_lucie"]}`) and returning combined live pump prices, forecasts, feature attributions, and provenance metadata (Issue #48).
* **POST /api/v1/forecast/cloud-sync**: Triggers out-of-time prediction history synchronization to cloud relational databases (Turso Edge SQLite, Cloudflare D1 Edge Workers, Neon Postgres) (Issue #82).
* **GET /api/v1/forecast/cloud-status**: Returns active cloud prediction database providers, local CSV fallback state, and total record counts (Issue #82).
* **GET /api/v1/telemetry/unmapped-zips**: Returns aggregated telemetry statistics for out-of-metro ZIP code lookups (Issues #50 & #195), including query hit counts, state/PADD distributions, and candidate expansion metro hubs.
* **POST /api/v1/forecast/simulate**: Counterfactual physical, weather, and geopolitical shock scenario simulator.

---

## 21. 4-Tier ZIP Code Geocoding & PADD Resolution Engine (src/zip_geocoding.py)
* **Module:** `src/zip_geocoding.py` (Issue #50)
* **Function:** Resolves any 5-digit US ZIP code or 3-digit prefix to mapped metro area locale, PADD region, state, and statutory state fuel tax policy via a 4-tier fallback engine:
  1. **Tier 1 (Metro Cluster Hit):** Maps 3-digit prefix directly to supported metro area (`tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `port_st_lucie`, `bayarea`).
  2. **Tier 2 (State & PADD Fallback):** Resolves state postal code and PADD region, routing 5-day forecast through the nearest calibrated PADD model (e.g. CA ZIPs $\rightarrow$ `Oakland_CA` CARB model; NY/NJ/PA $\rightarrow$ `Newark_DE` PADD 1B) and applying state fuel excise tax burdens.
  3. **Tier 3 (Live Station Ingestion):** Queries GasBuddy GraphQL API by ZIP code (`fetch_gasbuddy_prices_by_zip`) for local station prices.
  4. **Tier 4 (Resolution Metadata & Telemetry):** Injects explicit `zip_code_resolution` dictionary into API responses and logs unmapped lookups to `data/unmapped_zip_telemetry.json`.
"""

if "## 20. REST API Gateways & Endpoints" in apis_content:
    apis_content = apis_content.split("## 20. REST API Gateways & Endpoints")[0] + new_api_section
    with open(apis_file, "w", encoding="utf-8") as f:
        f.write(apis_content)
    print("Updated Data-Ingestion-and-APIs.md")

# 2. Update MLOps-and-Continuous-Feedback.md
mlops_file = os.path.join(wiki_dir, "MLOps-and-Continuous-Feedback.md")
with open(mlops_file, "r", encoding="utf-8") as f:
    mlops_content = f.read()

cloud_sync_sec = """
### 1.2 Cloud Relational Database Synchronization (sync_predictions_to_cloud(), Issue #82)
* **Supported Cloud Relational Backends**:
  - **Turso Edge SQLite**: HTTPS `/v2/pipeline` REST JSON payloads via `TURSO_DATABASE_URL` & `TURSO_AUTH_TOKEN`.
  - **Cloudflare D1 Edge Workers**: HTTPS REST payloads via `CLOUDFLARE_CACHE_URL` / `workers/cache_worker.ts`.
  - **Neon Serverless Postgres**: HTTP / Postgres connection URL support (`NEON_DATABASE_URL` / `POSTGRES_URL`).
* **Automated Table Schema Management**: Automatically executes `CREATE TABLE IF NOT EXISTS prediction_history (...)` DDL statements and record upserts.
* **100% Offline Fallback**: Operates defensively in background try/except blocks so local CSV logging (`data/prediction_history.csv`) remains fully functional with zero downtime when offline or when cloud credentials are empty.
* **REST API Status & Manual Sync Endpoints**:
  - `POST /api/v1/forecast/cloud-sync`: Manually triggers out-of-time prediction history cloud synchronization.
  - `GET /api/v1/forecast/cloud-status`: Returns active cloud database sync providers, primary store, fallback store, and total local record counts.
"""

if "### 1.2 Cloud Relational Database Synchronization" not in mlops_content:
    if "---\n\n## 2." in mlops_content:
        mlops_content = mlops_content.replace("---\n\n## 2.", cloud_sync_sec + "\n---\n\n## 2.")
    elif "--- \n\n## 2." in mlops_content:
        mlops_content = mlops_content.replace("--- \n\n## 2.", cloud_sync_sec + "\n---\n\n## 2.")
    with open(mlops_file, "w", encoding="utf-8") as f:
        f.write(mlops_content)
    print("Updated MLOps-and-Continuous-Feedback.md")

# 3. Update Home.md
home_file = os.path.join(wiki_dir, "Home.md")
with open(home_file, "r", encoding="utf-8") as f:
    home_content = f.read()

home_content = home_content.replace("v0.3.5", "v0.4.0").replace("v0.3.4", "v0.4.0").replace("v0.3.3", "v0.4.0")
with open(home_file, "w", encoding="utf-8") as f:
    f.write(home_content)
print("Updated Home.md")
