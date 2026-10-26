-- ======================================================================
-- Migration 0004: Create edgar_8k_seen table for edge deduplication
-- Target: SQLite, Cloudflare D1, Turso Edge
-- Issue: #644
-- ======================================================================

CREATE TABLE IF NOT EXISTS edgar_8k_seen (
    accession_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    filed_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_edgar_8k_seen_accession ON edgar_8k_seen (accession_id);
CREATE INDEX IF NOT EXISTS idx_edgar_8k_seen_ticker ON edgar_8k_seen (ticker);
CREATE INDEX IF NOT EXISTS idx_edgar_8k_seen_filed_at ON edgar_8k_seen (filed_at);
