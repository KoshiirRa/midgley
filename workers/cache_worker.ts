/**
 * Cloudflare Worker for Midgley Tier 2 Edge Cache & Quota Synchronization
 * (workers/cache_worker.ts)
 *
 * Implements REST endpoints for key-value caching (D1 / KV binding) and quota sync
 * with Bearer authentication and Option A2 telemetry instrumentation (Axiom & Sentry).
 */

export interface Env {
  DB?: any; // Cloudflare D1 Binding
  CLOUDFLARE_AUTH_TOKEN?: string;
  SENTRY_DSN?: string;
  AXIOM_TOKEN?: string;
  AXIOM_DATASET?: string;
}

/**
 * Axiom Event Ingest Helper (Option A2)
 */
export async function logToAxiom(env: Env, ctx: any, eventData: Record<string, any>): Promise<void> {
  const token = env.AXIOM_TOKEN;
  const dataset = env.AXIOM_DATASET || "midgley-workers";
  if (!token) return;

  const url = `https://api.axiom.co/v1/datasets/${dataset}/ingest`;
  const payload = JSON.stringify([{
    ...eventData,
    _time: new Date().toISOString(),
    service: "midgley-cache-worker"
  }]);

  const p = fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: payload
  }).catch(e => console.warn(`[Axiom Ingest Error] ${e.message || String(e)}`));

  if (ctx && typeof ctx.waitUntil === "function") {
    ctx.waitUntil(p);
  } else {
    await p;
  }
}

/**
 * Sentry Exception Capture Helper (Option A2)
 */
export async function captureSentryException(env: Env, ctx: any, error: any, extraInfo?: Record<string, any>): Promise<void> {
  const dsn = env.SENTRY_DSN;
  if (!dsn) return;

  try {
    const match = dsn.match(/^https:\/\/([^@]+)@([^/]+)\/(\d+)$/);
    if (!match) return;

    const [, key, host, projectId] = match;
    const storeUrl = `https://${host}/api/${projectId}/store/`;
    const payload = JSON.stringify({
      event_id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID().replace(/-/g, "") : String(Date.now()),
      timestamp: new Date().toISOString(),
      platform: "javascript",
      exception: {
        values: [
          {
            type: error?.name || "Error",
            value: error?.message || String(error)
          }
        ]
      },
      extra: extraInfo || {}
    });

    const p = fetch(storeUrl, {
      method: "POST",
      headers: {
        "X-Sentry-Auth": `Sentry sentry_version=7, sentry_key=${key}, sentry_client=midgley-cache-worker/1.0`,
        "Content-Type": "application/json"
      },
      body: payload
    }).catch(e => console.warn(`[Sentry Ingest Error] ${e.message || String(e)}`));

    if (ctx && typeof ctx.waitUntil === "function") {
      ctx.waitUntil(p);
    } else {
      await p;
    }
  } catch {
    // Ignore error
  }
}

export default {
  async fetch(request: Request, env: Env, ctx: any): Promise<Response> {
    const url = new URL(request.url);
    const authHeader = request.headers.get("Authorization");

    try {
      // Optional Bearer Authentication check
      if (env.CLOUDFLARE_AUTH_TOKEN) {
        const token = authHeader?.replace("Bearer ", "");
        if (token !== env.CLOUDFLARE_AUTH_TOKEN) {
          console.warn(`[Cache Auth Warning] Unauthorized request from ${request.headers.get("CF-Connecting-IP") || "unknown"}`);
          await logToAxiom(env, ctx, { event: "cache_auth_unauthorized", ip: request.headers.get("CF-Connecting-IP") });
          return new Response(JSON.stringify({ error: "Unauthorized" }), {
            status: 401,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      // Health check endpoint
      if (url.pathname === "/health" || url.pathname === "/status") {
        console.log(`[Cache Health Check] Status requested`);
        return new Response(
          JSON.stringify({ status: "ok", service: "midgley-cache-worker", timestamp: new Date().toISOString() }),
          { headers: { "Content-Type": "application/json" } }
        );
      }

      // GET /api/v1/cache/:key
      if (request.method === "GET" && url.pathname.startsWith("/api/v1/cache/")) {
        const key = decodeURIComponent(url.pathname.replace("/api/v1/cache/", ""));
        console.log(`[Cache Worker GET] Request for key: "${key}"`);
        try {
          if (env.DB) {
            const result = await env.DB.prepare(
              "SELECT value, created_at, expires_at FROM lookup_cache WHERE key = ?"
            ).bind(key).first();

            if (result) {
              console.log(`[Cache Worker HIT] Found entry for key: "${key}"`);
              let parsedVal: any;
              try { parsedVal = JSON.parse(result.value); } catch { parsedVal = result.value; }

              await logToAxiom(env, ctx, { event: "cache_get_hit", key });
              return new Response(
                JSON.stringify({ value: parsedVal, created_at: result.created_at, expires_at: result.expires_at }),
                { headers: { "Content-Type": "application/json" } }
              );
            }
          }
          console.log(`[Cache Worker MISS] No entry found for key: "${key}"`);
          await logToAxiom(env, ctx, { event: "cache_get_miss", key });
          return new Response(JSON.stringify({ error: "Key not found" }), {
            status: 404,
            headers: { "Content-Type": "application/json" }
          });
        } catch (err: any) {
          console.error(`[Cache Worker Error] GET for key "${key}" failed: ${err.message || String(err)}`);
          await captureSentryException(env, ctx, err, { action: "GET", key });
          return new Response(JSON.stringify({ error: "Internal Server Error" }), {
            status: 500,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      // POST /api/v1/sync/predictions (Issue #302: Batch prediction sync to D1)
      if (request.method === "POST" && (url.pathname === "/api/v1/sync/predictions" || url.pathname === "/api/v1/sync/predictions/")) {
        console.log(`[Cache Worker SYNC] Batch prediction sync requested`);
        try {
          const body: any = await request.json();
          const predictions = Array.isArray(body.predictions) ? body.predictions : [];
          if (predictions.length === 0) {
            return new Response(JSON.stringify({ status: "synced", synced_rows: 0, message: "No predictions in payload" }), {
              headers: { "Content-Type": "application/json" }
            });
          }

          if (env.DB) {
            // Ensure table exists
            await env.DB.prepare(`
              CREATE TABLE IF NOT EXISTS prediction_history (
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
                PRIMARY KEY (log_timestamp, forecast_target_date, region)
              )
            `).run();

            // Prepare batch statements
            const statements = predictions.map((row: any) => {
              return env.DB.prepare(`
                INSERT OR REPLACE INTO prediction_history (
                  log_timestamp, forecast_target_date, forecast_horizon_days, region, model_version, run_type,
                  headline_trigger, current_base_price, predicted_5d_price, predicted_direction,
                  actual_5d_price, actual_direction, error_dollars, directional_hit,
                  llm_price_pressure, llm_supply_disruption, quant_baseline_5d_price,
                  llm_augmentation_delta, prediction_lower_95ci, prediction_upper_95ci,
                  within_95ci_hit, data_source_provenance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
              `).bind(
                String(row.log_timestamp || ""),
                String(row.forecast_target_date || ""),
                Number(row.forecast_horizon_days || 5),
                String(row.region || ""),
                String(row.model_version || ""),
                String(row.run_type || ""),
                String(row.headline_trigger || ""),
                Number(row.current_base_price || 0.0),
                Number(row.predicted_5d_price || 0.0),
                String(row.predicted_direction || ""),
                row.actual_5d_price !== undefined && row.actual_5d_price !== null && !isNaN(row.actual_5d_price) ? Number(row.actual_5d_price) : null,
                String(row.actual_direction || ""),
                row.error_dollars !== undefined && row.error_dollars !== null && !isNaN(row.error_dollars) ? Number(row.error_dollars) : null,
                row.directional_hit !== undefined && row.directional_hit !== null && !isNaN(row.directional_hit) ? Number(row.directional_hit) : null,
                Number(row.llm_price_pressure || 0.0),
                Number(row.llm_supply_disruption || 0.0),
                Number(row.quant_baseline_5d_price || 0.0),
                Number(row.llm_augmentation_delta || 0.0),
                Number(row.prediction_lower_95ci || 0.0),
                Number(row.prediction_upper_95ci || 0.0),
                row.within_95ci_hit !== undefined && row.within_95ci_hit !== null && !isNaN(row.within_95ci_hit) ? Number(row.within_95ci_hit) : null,
                String(row.data_source_provenance || "yfinance")
              );
            });

            // Execute batch statements in chunks of 50 to respect Cloudflare D1's 100-statement limit (Issue #333)
            const CHUNK_SIZE = 50;
            for (let i = 0; i < statements.length; i += CHUNK_SIZE) {
              const chunk = statements.slice(i, i + CHUNK_SIZE);
              await env.DB.batch(chunk);
            }
          }

          console.log(`[Cache Worker SYNC SUCCESS] Synced ${predictions.length} records`);
          await logToAxiom(env, ctx, { event: "prediction_sync_success", count: predictions.length });
          return new Response(JSON.stringify({ status: "synced", synced_rows: predictions.length, provider: "cloudflare_d1" }), {
            status: 200,
            headers: { "Content-Type": "application/json" }
          });
        } catch (err: any) {
          console.error(`[Cache Worker Error] Prediction sync failed: ${err.message || String(err)}`);
          await captureSentryException(env, ctx, err, { action: "SYNC_PREDICTIONS" });
          return new Response(JSON.stringify({ error: "Prediction sync failed", details: err.message || String(err) }), {
            status: 500,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      // POST /api/v1/cache and POST /api/v1/cache/:key
      if (request.method === "POST" && (url.pathname === "/api/v1/cache" || url.pathname.startsWith("/api/v1/cache/"))) {
        let key = "";
        if (url.pathname.startsWith("/api/v1/cache/")) {
          key = decodeURIComponent(url.pathname.replace("/api/v1/cache/", ""));
        }
        try {
          const body: any = await request.json();
          if (!key && body.key) {
            key = String(body.key);
          }
          if (!key) {
            return new Response(JSON.stringify({ error: "Missing key in path or body" }), {
              status: 400,
              headers: { "Content-Type": "application/json" }
            });
          }
          console.log(`[Cache Worker STORE] Writing entry for key: "${key}"`);
          if (env.DB) {
            const valStr = typeof body.value === "string" ? body.value : JSON.stringify(body.value);
            const createdAt = body.created_at || Date.now() / 1000;
            const expiresAt = body.expires_at || Date.now() / 1000 + 86400;

            await env.DB.prepare(
              "INSERT OR REPLACE INTO lookup_cache (key, value, created_at, expires_at) VALUES (?, ?, ?, ?)"
            ).bind(key, valStr, createdAt, expiresAt).run();
          }
          console.log(`[Cache Worker STORE SUCCESS] Key stored: "${key}"`);
          await logToAxiom(env, ctx, { event: "cache_store_success", key });
          return new Response(JSON.stringify({ status: "stored", key }), {
            headers: { "Content-Type": "application/json" }
          });
        } catch (err: any) {
          console.error(`[Cache Worker Error] STORE for key "${key}" failed: ${err.message || String(err)}`);
          await captureSentryException(env, ctx, err, { action: "STORE", key });
          return new Response(JSON.stringify({ error: "Internal Server Error", details: err.message || String(err) }), {
            status: 500,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      // DELETE /api/v1/cache
      if (request.method === "DELETE" && (url.pathname === "/api/v1/cache" || url.pathname === "/api/v1/cache/")) {
        try {
          if (env.DB) {
            await env.DB.prepare("DELETE FROM lookup_cache").run();
          }
          return new Response(JSON.stringify({ status: "cleared" }), {
            headers: { "Content-Type": "application/json" }
          });
        } catch (err: any) {
          console.error(`[Cache Worker Error] DELETE cache failed: ${err.message || String(err)}`);
          return new Response(JSON.stringify({ error: "Internal Server Error", details: err.message || String(err) }), {
            status: 500,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      return new Response(JSON.stringify({ error: "Endpoint not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" }
      });
    } catch (err: any) {
      console.error(`[Cache Worker Exception] ${err.message || String(err)}`);
      await captureSentryException(env, ctx, err, { pathname: url.pathname });
      return new Response(JSON.stringify({ error: "Internal Server Error" }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  }
};
