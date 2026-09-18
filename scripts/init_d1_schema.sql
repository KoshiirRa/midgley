-- ======================================================================
-- Cloudflare D1 Database Schema Initialization (scripts/init_d1_schema.sql)
-- Target Database: midgley-cache-d1 (bd1954f1-33b6-4adb-9219-ea5ec43fe2b7)
-- ======================================================================

-- 1. Tier 2 Fast Edge Key-Value Lookup Cache
CREATE TABLE IF NOT EXISTS lookup_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

-- Index for expiration purging
CREATE INDEX IF NOT EXISTS idx_lookup_cache_expires_at ON lookup_cache (expires_at);

-- 2. Intraday RSS Deduplication Ledger
CREATE TABLE IF NOT EXISTS seen_rss_headlines (
    clean_key TEXT PRIMARY KEY,
    raw_headline TEXT,
    created_at TEXT NOT NULL
);

-- Index for aging deduplication records
CREATE INDEX IF NOT EXISTS idx_seen_rss_created_at ON seen_rss_headlines (created_at);

-- 3. Out-of-Time Prediction History & Evaluation Log
CREATE TABLE IF NOT EXISTS prediction_history (
    log_timestamp TEXT,
    forecast_target_date TEXT,
    forecast_horizon_days INTEGER DEFAULT 5,
    region TEXT,
    model_version TEXT,
    run_type TEXT,
    headline_trigger TEXT,
    current_base_price REAL,
    predicted_5d_price REAL,
    predicted_direction TEXT,
    actual_5d_price REAL,
    actual_direction TEXT,
    error_dollars REAL,
    directional_hit REAL,
    llm_price_pressure REAL DEFAULT 0.0,
    llm_supply_disruption REAL DEFAULT 0.0,
    quant_baseline_5d_price REAL,
    llm_augmentation_delta REAL DEFAULT 0.0,
    prediction_lower_95ci REAL,
    prediction_upper_95ci REAL,
    within_95ci_hit REAL,
    data_source_provenance TEXT DEFAULT 'yfinance',
    PRIMARY KEY (log_timestamp, forecast_target_date, region)
);

CREATE INDEX IF NOT EXISTS idx_pred_history_target ON prediction_history (forecast_target_date, region);
CREATE INDEX IF NOT EXISTS idx_pred_history_version ON prediction_history (model_version);
