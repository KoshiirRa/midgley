-- ======================================================================
-- Migration 0003: Add value column to flag_replay_tokens
-- Target: SQLite, Cloudflare D1, Turso Edge
-- Issues: #235, #581, #605
-- ======================================================================

-- Add missing value column safely to flag_replay_tokens table for edge key-value storage
ALTER TABLE flag_replay_tokens ADD COLUMN value TEXT;
