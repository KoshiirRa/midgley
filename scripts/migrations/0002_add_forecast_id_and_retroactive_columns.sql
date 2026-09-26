-- ======================================================================
-- Migration 0002: Add forecast_id, issued_at_utc, and is_retroactive_backtest
-- Target: SQLite, Cloudflare D1, Turso Edge
-- Issue: #471
-- ======================================================================

-- Add missing columns safely (SQLite 3.35.0+)
ALTER TABLE prediction_history ADD COLUMN forecast_id TEXT;
ALTER TABLE prediction_history ADD COLUMN issued_at_utc TEXT;
ALTER TABLE prediction_history ADD COLUMN is_retroactive_backtest INTEGER DEFAULT 0;

-- Backfill legacy records with stable deterministic IDs and issuance timestamps
UPDATE prediction_history 
SET forecast_id = log_timestamp || '_' || region || '_' || COALESCE(forecast_horizon_days, 5) 
WHERE forecast_id IS NULL OR forecast_id = '';

UPDATE prediction_history 
SET issued_at_utc = log_timestamp 
WHERE issued_at_utc IS NULL OR issued_at_utc = '';

-- Create performance indices
CREATE INDEX IF NOT EXISTS idx_pred_history_target ON prediction_history (forecast_target_date, region);
CREATE INDEX IF NOT EXISTS idx_pred_history_version ON prediction_history (model_version);
CREATE INDEX IF NOT EXISTS idx_pred_history_log_ts ON prediction_history (log_timestamp, forecast_target_date, region);
