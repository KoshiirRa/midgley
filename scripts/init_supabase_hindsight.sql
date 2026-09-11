-- ============================================================================
-- Supabase PostgreSQL pgvector Initialization for Hindsight Agent Memory
-- Issue #230: [Weekly Review 2.0] Qualitative Anomaly Post-Mortems (Retain-Recall-Reflect)
-- ============================================================================

-- 1. Enable pgvector extension for dense semantic similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create schema / table for episodic memory records (Retain)
CREATE TABLE IF NOT EXISTS hindsight_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_id VARCHAR(64) NOT NULL DEFAULT 'midgley-gas-forecasting',
    memory_type VARCHAR(32) NOT NULL DEFAULT 'experience', -- 'experience', 'world_fact', 'anomaly_shock'
    region VARCHAR(64) NOT NULL,
    forecast_target_date DATE,
    predicted_price NUMERIC(8, 4),
    actual_price NUMERIC(8, 4),
    error_dollars NUMERIC(8, 4),
    anomaly_type VARCHAR(64), -- 'LARGE_OVERESTIMATE', 'LARGE_UNDERESTIMATE', 'DIRECTIONAL_FLIP', 'CI_BREACH'
    content TEXT NOT NULL,
    embedding vector(768), -- Gemini / text-embedding-004 standard (or 1536 for OpenAI)
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create schema / table for synthesized reflections and mental models (Reflect)
CREATE TABLE IF NOT EXISTS hindsight_mental_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_id VARCHAR(64) NOT NULL DEFAULT 'midgley-gas-forecasting',
    title VARCHAR(255) NOT NULL,
    region VARCHAR(64),
    root_cause TEXT NOT NULL,
    historical_analogy TEXT,
    calibration_suggestion TEXT,
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create performant indexes for hybrid retrieval (Recall)
CREATE INDEX IF NOT EXISTS idx_hindsight_memories_bank ON hindsight_memories(bank_id);
CREATE INDEX IF NOT EXISTS idx_hindsight_memories_region ON hindsight_memories(region);
CREATE INDEX IF NOT EXISTS idx_hindsight_memories_anomaly ON hindsight_memories(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_hindsight_memories_created ON hindsight_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_hindsight_memories_metadata ON hindsight_memories USING GIN (metadata);

-- HNSW Vector Index for fast approximate cosine similarity search
CREATE INDEX IF NOT EXISTS idx_hindsight_memories_embedding 
ON hindsight_memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 5. Helper Function for Semantic Similarity Recall Search
CREATE OR REPLACE FUNCTION match_hindsight_memories (
    query_embedding vector(768),
    filter_bank VARCHAR(64) DEFAULT 'midgley-gas-forecasting',
    filter_region VARCHAR(64) DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    bank_id VARCHAR(64),
    memory_type VARCHAR(32),
    region VARCHAR(64),
    anomaly_type VARCHAR(64),
    content TEXT,
    error_dollars NUMERIC(8, 4),
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.bank_id,
        m.memory_type,
        m.region,
        m.anomaly_type,
        m.content,
        m.error_dollars,
        m.metadata,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM hindsight_memories m
    WHERE m.bank_id = filter_bank
      AND (filter_region IS NULL OR m.region = filter_region)
      AND 1 - (m.embedding <=> query_embedding) > match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
