/**
 * Midgley Multi-Tier Storage & Database Adapter
 * (workers/db_adapter.ts)
 *
 * Implements Issue #641: Direct database TCP connections from Workers via cloudflare:sockets
 * with Cloudflare Hyperdrive connection pooling and defensive D1 / In-Memory fallback.
 */

import postgres from "postgres";

export interface CacheEntry<T = any> {
  value: T;
  created_at: number;
  expires_at: number;
}

export interface PredictionSyncRecord {
  forecast_id: string;
  issued_at_utc?: string;
  log_timestamp: string;
  forecast_target_date: string;
  forecast_horizon_days: number;
  region: string;
  model_version: string;
  run_type?: string;
  headline_trigger?: string;
  current_base_price?: number;
  predicted_5d_price?: number;
  predicted_direction?: string;
  actual_5d_price?: number;
  actual_direction?: string;
  error_dollars?: number;
  directional_hit?: number;
  llm_price_pressure?: number;
  llm_supply_disruption?: number;
  quant_baseline_5d_price?: number;
  llm_augmentation_delta?: number;
  prediction_lower_95ci?: number;
  prediction_upper_95ci?: number;
  within_95ci_hit?: number;
  data_source_provenance?: string;
  is_retroactive_backtest?: number;
}

export interface StorageAdapter {
  readonly tier: "hyperdrive" | "d1" | "memory";
  getCache(key: string): Promise<CacheEntry | null>;
  setCache(key: string, value: any, createdAt?: number, expiresAt?: number): Promise<void>;
  deleteCache(key?: string): Promise<void>;
  syncPredictions(records: PredictionSyncRecord[]): Promise<{ synced_rows: number }>;
  acquireAdvisoryLock?(lockKey: string, timeoutMs?: number): Promise<boolean>;
  releaseAdvisoryLock?(lockKey: string): Promise<void>;
  close(): Promise<void>;
}

export interface AdapterEnv {
  PROD_DB?: any;          // Hyperdrive binding: env.PROD_DB.connectionString
  DATABASE_URL?: string;  // Direct PostgreSQL connection URL secret
  DB?: any;               // Cloudflare D1 binding
  AXIOM_TOKEN?: string;
  AXIOM_DATASET?: string;
  SENTRY_DSN?: string;
}

/**
 * Axiom & Sentry logging helpers for failover and telemetry.
 */
async function reportTelemetry(env: AdapterEnv, ctx: any, eventData: Record<string, any>): Promise<void> {
  const token = env.AXIOM_TOKEN;
  const dataset = env.AXIOM_DATASET || "midgley-workers";
  if (!token) return;

  const url = `https://api.axiom.co/v1/datasets/${dataset}/ingest`;
  const payload = JSON.stringify([{
    ...eventData,
    _time: new Date().toISOString(),
    service: "midgley-db-adapter"
  }]);

  const p = fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: payload
  }).catch(e => console.warn(`[Adapter Telemetry Error] ${e.message || String(e)}`));

  if (ctx && typeof ctx.waitUntil === "function") {
    ctx.waitUntil(p);
  } else {
    await p;
  }
}

/**
 * PostgreSQL / Hyperdrive Storage Adapter (Issue #641)
 * Connects over direct TCP sockets via postgres.js.
 */
export class PostgresAdapter implements StorageAdapter {
  readonly tier = "hyperdrive" as const;
  private sql: any;
  private tablesEnsured = false;

  constructor(connectionString: string, sqlInstance?: any) {
    if (sqlInstance) {
      this.sql = sqlInstance;
    } else {
      this.sql = postgres(connectionString, {
        max: 1,               // Single connection per isolate; Hyperdrive pools across isolates
        idle_timeout: 5,      // Release idle socket after 5 seconds
        connect_timeout: 5,   // 5-second socket timeout before triggering fallback
        prepare: false,       // Prevent named prepared statement collision with connection poolers
      });
    }
  }

  private async ensureTables(): Promise<void> {
    if (this.tablesEnsured) return;

    await this.sql`
      CREATE TABLE IF NOT EXISTS lookup_cache (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at DOUBLE PRECISION NOT NULL,
        expires_at DOUBLE PRECISION NOT NULL
      )
    `;

    await this.sql`
      CREATE TABLE IF NOT EXISTS prediction_history (
        forecast_id TEXT PRIMARY KEY,
        issued_at_utc TEXT,
        log_timestamp TEXT,
        forecast_target_date TEXT,
        forecast_horizon_days INTEGER,
        region TEXT,
        model_version TEXT,
        run_type TEXT,
        headline_trigger TEXT,
        current_base_price DOUBLE PRECISION,
        predicted_5d_price DOUBLE PRECISION,
        predicted_direction TEXT,
        actual_5d_price DOUBLE PRECISION,
        actual_direction TEXT,
        error_dollars DOUBLE PRECISION,
        directional_hit DOUBLE PRECISION,
        llm_price_pressure DOUBLE PRECISION,
        llm_supply_disruption DOUBLE PRECISION,
        quant_baseline_5d_price DOUBLE PRECISION,
        llm_augmentation_delta DOUBLE PRECISION,
        prediction_lower_95ci DOUBLE PRECISION,
        prediction_upper_95ci DOUBLE PRECISION,
        within_95ci_hit DOUBLE PRECISION,
        data_source_provenance TEXT,
        is_retroactive_backtest INTEGER DEFAULT 0
      )
    `;

    this.tablesEnsured = true;
  }

  async getCache(key: string): Promise<CacheEntry | null> {
    await this.ensureTables();
    const rows = await this.sql`
      SELECT value, created_at, expires_at
      FROM lookup_cache
      WHERE key = ${key}
      LIMIT 1
    `;
    if (!rows || rows.length === 0) return null;

    let parsedVal: any;
    try {
      parsedVal = JSON.parse(rows[0].value);
    } catch {
      parsedVal = rows[0].value;
    }

    return {
      value: parsedVal,
      created_at: Number(rows[0].created_at),
      expires_at: Number(rows[0].expires_at)
    };
  }

  async setCache(key: string, value: any, createdAt?: number, expiresAt?: number): Promise<void> {
    await this.ensureTables();
    const valStr = typeof value === "string" ? value : JSON.stringify(value);
    const nowSec = Date.now() / 1000;
    const cAt = createdAt ?? nowSec;
    const eAt = expiresAt ?? (nowSec + 86400);

    await this.sql`
      INSERT INTO lookup_cache (key, value, created_at, expires_at)
      VALUES (${key}, ${valStr}, ${cAt}, ${eAt})
      ON CONFLICT (key) DO UPDATE SET
        value = EXCLUDED.value,
        created_at = EXCLUDED.created_at,
        expires_at = EXCLUDED.expires_at
    `;
  }

  async deleteCache(key?: string): Promise<void> {
    await this.ensureTables();
    if (key) {
      await this.sql`DELETE FROM lookup_cache WHERE key = ${key}`;
    } else {
      await this.sql`DELETE FROM lookup_cache`;
    }
  }

  async syncPredictions(records: PredictionSyncRecord[]): Promise<{ synced_rows: number }> {
    if (!records || records.length === 0) return { synced_rows: 0 };
    await this.ensureTables();

    for (const row of records) {
      const forecastId = row.forecast_id || `${row.log_timestamp}_${row.region}_${row.forecast_horizon_days ?? 5}`;
      const issuedAt = row.issued_at_utc || row.log_timestamp;

      await this.sql`
        INSERT INTO prediction_history (
          forecast_id, issued_at_utc, log_timestamp, forecast_target_date, forecast_horizon_days,
          region, model_version, run_type, headline_trigger, current_base_price,
          predicted_5d_price, predicted_direction, actual_5d_price, actual_direction,
          error_dollars, directional_hit, llm_price_pressure, llm_supply_disruption,
          quant_baseline_5d_price, llm_augmentation_delta, prediction_lower_95ci,
          prediction_upper_95ci, within_95ci_hit, data_source_provenance, is_retroactive_backtest
        ) VALUES (
          ${forecastId}, ${issuedAt}, ${row.log_timestamp}, ${row.forecast_target_date}, ${row.forecast_horizon_days ?? 5},
          ${row.region}, ${row.model_version}, ${row.run_type ?? null}, ${row.headline_trigger ?? null}, ${row.current_base_price ?? null},
          ${row.predicted_5d_price ?? null}, ${row.predicted_direction ?? null}, ${row.actual_5d_price ?? null}, ${row.actual_direction ?? null},
          ${row.error_dollars ?? null}, ${row.directional_hit ?? null}, ${row.llm_price_pressure ?? null}, ${row.llm_supply_disruption ?? null},
          ${row.quant_baseline_5d_price ?? null}, ${row.llm_augmentation_delta ?? null}, ${row.prediction_lower_95ci ?? null},
          ${row.prediction_upper_95ci ?? null}, ${row.within_95ci_hit ?? null}, ${row.data_source_provenance ?? null}, ${row.is_retroactive_backtest ?? 0}
        )
        ON CONFLICT (forecast_id) DO UPDATE SET
          issued_at_utc = EXCLUDED.issued_at_utc,
          log_timestamp = EXCLUDED.log_timestamp,
          forecast_target_date = EXCLUDED.forecast_target_date,
          forecast_horizon_days = EXCLUDED.forecast_horizon_days,
          region = EXCLUDED.region,
          model_version = EXCLUDED.model_version,
          run_type = EXCLUDED.run_type,
          headline_trigger = EXCLUDED.headline_trigger,
          current_base_price = EXCLUDED.current_base_price,
          predicted_5d_price = EXCLUDED.predicted_5d_price,
          predicted_direction = EXCLUDED.predicted_direction,
          actual_5d_price = EXCLUDED.actual_5d_price,
          actual_direction = EXCLUDED.actual_direction,
          error_dollars = EXCLUDED.error_dollars,
          directional_hit = EXCLUDED.directional_hit,
          llm_price_pressure = EXCLUDED.llm_price_pressure,
          llm_supply_disruption = EXCLUDED.llm_supply_disruption,
          quant_baseline_5d_price = EXCLUDED.quant_baseline_5d_price,
          llm_augmentation_delta = EXCLUDED.llm_augmentation_delta,
          prediction_lower_95ci = EXCLUDED.prediction_lower_95ci,
          prediction_upper_95ci = EXCLUDED.prediction_upper_95ci,
          within_95ci_hit = EXCLUDED.within_95ci_hit,
          data_source_provenance = EXCLUDED.data_source_provenance,
          is_retroactive_backtest = EXCLUDED.is_retroactive_backtest
      `;
    }

    return { synced_rows: records.length };
  }

  async acquireAdvisoryLock(lockKey: string): Promise<boolean> {
    const res = await this.sql`SELECT pg_try_advisory_lock(hashtext(${lockKey})) as acquired`;
    return Boolean(res && res[0] && res[0].acquired);
  }

  async releaseAdvisoryLock(lockKey: string): Promise<void> {
    await this.sql`SELECT pg_advisory_unlock(hashtext(${lockKey}))`;
  }

  async close(): Promise<void> {
    if (this.sql && typeof this.sql.end === "function") {
      try {
        await this.sql.end({ timeout: 2 });
      } catch {
        // Ignore closing errors on edge isolate teardown
      }
    }
  }
}

/**
 * Cloudflare D1 Storage Adapter (SQLite)
 */
export class D1Adapter implements StorageAdapter {
  readonly tier = "d1" as const;
  private db: any;
  private tablesEnsured = false;

  constructor(d1Binding: any) {
    this.db = d1Binding;
  }

  private async ensureTables(): Promise<void> {
    if (this.tablesEnsured || !this.db) return;

    await this.db.prepare(`
      CREATE TABLE IF NOT EXISTS lookup_cache (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL
      )
    `).run().catch(() => {});

    await this.db.prepare(`
      CREATE TABLE IF NOT EXISTS prediction_history (
        forecast_id TEXT PRIMARY KEY,
        issued_at_utc TEXT,
        log_timestamp TEXT,
        forecast_target_date TEXT,
        forecast_horizon_days INTEGER,
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
        llm_price_pressure REAL,
        llm_supply_disruption REAL,
        quant_baseline_5d_price REAL,
        llm_augmentation_delta REAL,
        prediction_lower_95ci REAL,
        prediction_upper_95ci REAL,
        within_95ci_hit REAL,
        data_source_provenance TEXT,
        is_retroactive_backtest INTEGER
      )
    `).run().catch(() => {});

    // Migration check for forecast_id
    try {
      const tableInfo = await this.db.prepare("PRAGMA table_info(prediction_history)").all();
      const existingCols = new Set(((tableInfo && tableInfo.results) || []).map((c: any) => c.name));
      if (existingCols.size > 0 && !existingCols.has("forecast_id")) {
        await this.db.prepare("ALTER TABLE prediction_history ADD COLUMN forecast_id TEXT").run().catch(() => {});
        await this.db.prepare("ALTER TABLE prediction_history ADD COLUMN issued_at_utc TEXT").run().catch(() => {});
        await this.db.prepare("ALTER TABLE prediction_history ADD COLUMN is_retroactive_backtest INTEGER DEFAULT 0").run().catch(() => {});
        await this.db.prepare("UPDATE prediction_history SET forecast_id = log_timestamp || '_' || region || '_' || COALESCE(forecast_horizon_days, 5) WHERE forecast_id IS NULL OR forecast_id = ''").run().catch(() => {});
        await this.db.prepare("UPDATE prediction_history SET issued_at_utc = log_timestamp WHERE issued_at_utc IS NULL OR issued_at_utc = ''").run().catch(() => {});
      }
    } catch {
      // Ignore migration errors
    }

    this.tablesEnsured = true;
  }

  async getCache(key: string): Promise<CacheEntry | null> {
    if (!this.db) return null;
    await this.ensureTables();

    const result = await this.db.prepare(
      "SELECT value, created_at, expires_at FROM lookup_cache WHERE key = ?"
    ).bind(key).first();

    if (!result) return null;

    let parsedVal: any;
    try {
      parsedVal = JSON.parse(result.value);
    } catch {
      parsedVal = result.value;
    }

    return {
      value: parsedVal,
      created_at: Number(result.created_at),
      expires_at: Number(result.expires_at)
    };
  }

  async setCache(key: string, value: any, createdAt?: number, expiresAt?: number): Promise<void> {
    if (!this.db) return;
    await this.ensureTables();

    const valStr = typeof value === "string" ? value : JSON.stringify(value);
    const nowSec = Date.now() / 1000;
    const cAt = createdAt ?? nowSec;
    const eAt = expiresAt ?? (nowSec + 86400);

    await this.db.prepare(
      "INSERT OR REPLACE INTO lookup_cache (key, value, created_at, expires_at) VALUES (?, ?, ?, ?)"
    ).bind(key, valStr, cAt, eAt).run();
  }

  async deleteCache(key?: string): Promise<void> {
    if (!this.db) return;
    await this.ensureTables();

    if (key) {
      await this.db.prepare("DELETE FROM lookup_cache WHERE key = ?").bind(key).run();
    } else {
      await this.db.prepare("DELETE FROM lookup_cache").run();
    }
  }

  async syncPredictions(records: PredictionSyncRecord[]): Promise<{ synced_rows: number }> {
    if (!this.db || !records || records.length === 0) return { synced_rows: 0 };
    await this.ensureTables();

    const statements = records.map((row: any) => {
      const forecastId = row.forecast_id || `${row.log_timestamp}_${row.region}_${row.forecast_horizon_days ?? 5}`;
      const issuedAt = row.issued_at_utc || row.log_timestamp;

      return this.db.prepare(`
        INSERT OR REPLACE INTO prediction_history (
          forecast_id, issued_at_utc, log_timestamp, forecast_target_date, forecast_horizon_days, region, model_version, run_type,
          headline_trigger, current_base_price, predicted_5d_price, predicted_direction,
          actual_5d_price, actual_direction, error_dollars, directional_hit,
          llm_price_pressure, llm_supply_disruption, quant_baseline_5d_price,
          llm_augmentation_delta, prediction_lower_95ci, prediction_upper_95ci,
          within_95ci_hit, data_source_provenance, is_retroactive_backtest
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        forecastId,
        issuedAt,
        row.log_timestamp,
        row.forecast_target_date,
        row.forecast_horizon_days ?? 5,
        row.region,
        row.model_version,
        row.run_type ?? null,
        row.headline_trigger ?? null,
        row.current_base_price ?? null,
        row.predicted_5d_price ?? null,
        row.predicted_direction ?? null,
        row.actual_5d_price ?? null,
        row.actual_direction ?? null,
        row.error_dollars ?? null,
        row.directional_hit ?? null,
        row.llm_price_pressure ?? null,
        row.llm_supply_disruption ?? null,
        row.quant_baseline_5d_price ?? null,
        row.llm_augmentation_delta ?? null,
        row.prediction_lower_95ci ?? null,
        row.prediction_upper_95ci ?? null,
        row.within_95ci_hit ?? null,
        row.data_source_provenance ?? null,
        row.is_retroactive_backtest ? 1 : 0
      );
    });

    const CHUNK_SIZE = 50;
    for (let i = 0; i < statements.length; i += CHUNK_SIZE) {
      const chunk = statements.slice(i, i + CHUNK_SIZE);
      if (typeof this.db.batch === "function") {
        await this.db.batch(chunk);
      } else {
        for (const stmt of chunk) {
          if (stmt && typeof stmt.run === "function") await stmt.run();
        }
      }
    }

    return { synced_rows: records.length };
  }

  async close(): Promise<void> {
    // No-op for D1
  }
}

/**
 * In-Memory Fallback Adapter (Offline / Unit Testing)
 */
export class MemoryAdapter implements StorageAdapter {
  readonly tier = "memory" as const;
  private cache = new Map<string, CacheEntry>();
  private predictions = new Map<string, PredictionSyncRecord>();

  async getCache(key: string): Promise<CacheEntry | null> {
    const entry = this.cache.get(key);
    if (!entry) return null;
    return { ...entry };
  }

  async setCache(key: string, value: any, createdAt?: number, expiresAt?: number): Promise<void> {
    const nowSec = Date.now() / 1000;
    this.cache.set(key, {
      value,
      created_at: createdAt ?? nowSec,
      expires_at: expiresAt ?? (nowSec + 86400)
    });
  }

  async deleteCache(key?: string): Promise<void> {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }

  async syncPredictions(records: PredictionSyncRecord[]): Promise<{ synced_rows: number }> {
    for (const r of records) {
      const id = r.forecast_id || `${r.log_timestamp}_${r.region}_${r.forecast_horizon_days ?? 5}`;
      this.predictions.set(id, { ...r, forecast_id: id });
    }
    return { synced_rows: records.length };
  }

  async close(): Promise<void> {}
}

/**
 * Resilient Multi-Tier Storage Adapter
 * Automatically tries Hyperdrive TCP first, falling back to D1 or Memory on failure.
 */
export class ResilientStorageAdapter implements StorageAdapter {
  private primary: StorageAdapter;
  private fallback: StorageAdapter;
  private env: AdapterEnv;
  private ctx: any;
  private activeTier: "hyperdrive" | "d1" | "memory";

  constructor(primary: StorageAdapter, fallback: StorageAdapter, env: AdapterEnv, ctx: any) {
    this.primary = primary;
    this.fallback = fallback;
    this.env = env;
    this.ctx = ctx;
    this.activeTier = primary.tier;
  }

  get tier(): "hyperdrive" | "d1" | "memory" {
    return this.activeTier;
  }

  private async executeWithFallback<T>(
    operationName: string,
    fn: (adapter: StorageAdapter) => Promise<T>
  ): Promise<T> {
    if (this.activeTier === this.fallback.tier) {
      return fn(this.fallback);
    }

    try {
      return await fn(this.primary);
    } catch (err: any) {
      console.warn(`[DbAdapter Fallover Warning] Primary ${this.primary.tier} failed for ${operationName}: ${err?.message || String(err)}. Falling back to ${this.fallback.tier}.`);
      this.activeTier = this.fallback.tier;

      await reportTelemetry(this.env, this.ctx, {
        event: "db_adapter_failover",
        from_tier: this.primary.tier,
        to_tier: this.fallback.tier,
        operation: operationName,
        error: err?.message || String(err)
      });

      return fn(this.fallback);
    }
  }

  async getCache(key: string): Promise<CacheEntry | null> {
    return this.executeWithFallback("getCache", a => a.getCache(key));
  }

  async setCache(key: string, value: any, createdAt?: number, expiresAt?: number): Promise<void> {
    return this.executeWithFallback("setCache", a => a.setCache(key, value, createdAt, expiresAt));
  }

  async deleteCache(key?: string): Promise<void> {
    return this.executeWithFallback("deleteCache", a => a.deleteCache(key));
  }

  async syncPredictions(records: PredictionSyncRecord[]): Promise<{ synced_rows: number }> {
    return this.executeWithFallback("syncPredictions", a => a.syncPredictions(records));
  }

  async acquireAdvisoryLock(lockKey: string, timeoutMs?: number): Promise<boolean> {
    if (typeof this.primary.acquireAdvisoryLock === "function" && this.activeTier === this.primary.tier) {
      try {
        return await this.primary.acquireAdvisoryLock(lockKey, timeoutMs);
      } catch (err: any) {
        console.warn(`[DbAdapter Lock Fallover] Advisory lock failed on primary: ${err?.message || String(err)}`);
        this.activeTier = this.fallback.tier;
      }
    }
    // Fallback: simple advisory lock via fallback adapter or return true
    return true;
  }

  async releaseAdvisoryLock(lockKey: string): Promise<void> {
    if (typeof this.primary.releaseAdvisoryLock === "function" && this.activeTier === this.primary.tier) {
      try {
        await this.primary.releaseAdvisoryLock(lockKey);
      } catch {
        // Ignore
      }
    }
  }

  async close(): Promise<void> {
    await this.primary.close();
    await this.fallback.close();
  }
}

/**
 * Storage Adapter Factory
 * Instantiates the appropriate storage adapter hierarchy based on environment bindings.
 */
export function getStorageAdapter(env: AdapterEnv, ctx?: any): StorageAdapter {
  const fallbackAdapter = env.DB ? new D1Adapter(env.DB) : new MemoryAdapter();

  // Check for Hyperdrive binding or DATABASE_URL
  const connectionString = (env.PROD_DB && env.PROD_DB.connectionString) || env.DATABASE_URL;

  if (connectionString) {
    try {
      const postgresAdapter = new PostgresAdapter(connectionString);
      return new ResilientStorageAdapter(postgresAdapter, fallbackAdapter, env, ctx);
    } catch (err: any) {
      console.warn(`[DbAdapter Init Warning] Failed to initialize PostgresAdapter: ${err?.message || String(err)}. Using fallback.`);
      return fallbackAdapter;
    }
  }

  return fallbackAdapter;
}
