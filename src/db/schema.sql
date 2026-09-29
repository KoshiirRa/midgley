-- Project Midgley Unified Relational Schema (Turso libSQL / Cloudflare D1 / SQLite)
-- Strict schemas, deterministic primary keys, and indexed point-in-time querying.

CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    model_version TEXT NOT NULL,
    origin_date TEXT NOT NULL,
    horizon INTEGER NOT NULL,
    target_date TEXT NOT NULL,
    predicted_price REAL NOT NULL,
    ci_lower_95 REAL,
    ci_upper_95 REAL,
    ci_lower_80 REAL,
    ci_upper_80 REAL,
    llm_price_pressure REAL DEFAULT 0.0,
    llm_supply_disruption REAL DEFAULT 0.0,
    point_in_time_features TEXT,
    run_type TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_forecasts_lookup ON forecasts (region, horizon, target_date);
CREATE INDEX IF NOT EXISTS idx_forecasts_run_type ON forecasts (run_type, target_date);
CREATE INDEX IF NOT EXISTS idx_forecasts_origin ON forecasts (origin_date);

CREATE TABLE IF NOT EXISTS intraday_revisions (
    revision_id TEXT PRIMARY KEY,
    parent_forecast_id TEXT NOT NULL,
    region TEXT NOT NULL,
    horizon INTEGER NOT NULL,
    delta_price REAL NOT NULL,
    revised_predicted_price REAL NOT NULL,
    event_id TEXT,
    rationale TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_forecast_id) REFERENCES forecasts(forecast_id)
);

CREATE INDEX IF NOT EXISTS idx_revisions_parent ON intraday_revisions (parent_forecast_id);

CREATE TABLE IF NOT EXISTS intraday_events (
    event_id TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    published_at TEXT NOT NULL,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
    geopolitical_risk REAL DEFAULT 0.0,
    supply_disruption REAL DEFAULT 0.0,
    demand_sentiment REAL DEFAULT 0.0,
    opec_action REAL DEFAULT 0.0,
    is_anomaly INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_intraday_events_pub ON intraday_events (published_at);

CREATE TABLE IF NOT EXISTS evaluated_headlines (
    headline_hash TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    model_tier TEXT NOT NULL,
    scores_json TEXT NOT NULL,
    evaluated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_vintages (
    vintage_id TEXT PRIMARY KEY,
    feed TEXT NOT NULL,
    entity TEXT NOT NULL,
    obs_date TEXT NOT NULL,
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    quality TEXT NOT NULL,
    values_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vintages_asof ON data_vintages (feed, entity, obs_date, published_at);
CREATE INDEX IF NOT EXISTS idx_vintages_feed_entity ON data_vintages (feed, entity);

CREATE TABLE IF NOT EXISTS ground_truth (
    series_id TEXT NOT NULL,
    obs_date TEXT NOT NULL,
    actual_price REAL NOT NULL,
    settled_at TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (series_id, obs_date)
);

CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id TEXT PRIMARY KEY,
    forecast_id TEXT NOT NULL,
    series_id TEXT NOT NULL,
    actual_price REAL NOT NULL,
    absolute_error REAL NOT NULL,
    percentage_error REAL NOT NULL,
    directional_correct INTEGER NOT NULL,
    within_95ci INTEGER NOT NULL,
    evaluated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (forecast_id) REFERENCES forecasts(forecast_id)
);

CREATE INDEX IF NOT EXISTS idx_evaluations_forecast ON evaluations (forecast_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_series ON evaluations (series_id, evaluated_at);

CREATE TABLE IF NOT EXISTS sync_watermarks (
    source_name TEXT PRIMARY KEY,
    last_sync_timestamp TEXT NOT NULL,
    records_synced INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hindsight_telemetry (
    log_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    context_key TEXT NOT NULL,
    query_or_doc TEXT NOT NULL,
    result_summary TEXT,
    latency_ms REAL,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hindsight_telemetry_op ON hindsight_telemetry (operation, created_at);

