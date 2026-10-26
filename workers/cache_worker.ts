/**
 * Cloudflare Worker for Midgley Tier 2 Edge Cache & Quota Synchronization
 * (workers/cache_worker.ts)
 *
 * Implements REST endpoints for key-value caching (Hyperdrive / D1 / KV binding) and quota sync
 * with Bearer authentication and Option A2 telemetry instrumentation (Axiom & Sentry).
 * Supports Issue #641 direct database TCP connections via Cloudflare Hyperdrive and cloudflare:sockets.
 */

import { getStorageAdapter, StorageAdapter, CacheEntry } from "./db_adapter";

export interface Env {
  DB?: any;               // Cloudflare D1 Binding
  PROD_DB?: any;          // Cloudflare Hyperdrive Binding (Issue #641)
  DATABASE_URL?: string;  // Direct PostgreSQL Connection URL secret (Issue #641)
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

export function timingSafeEqual(a: string, b: string): boolean {
  if (typeof a !== "string" || typeof b !== "string") return false;
  const enc = new TextEncoder();
  const aBuf = enc.encode(a);
  const bBuf = enc.encode(b);
  if (aBuf.byteLength !== bBuf.byteLength) return false;
  let mismatch = 0;
  for (let i = 0; i < aBuf.byteLength; i++) {
    mismatch |= aBuf[i] ^ bBuf[i];
  }
  return mismatch === 0;
}

export default {
  async fetch(request: Request, env: Env, ctx: any): Promise<Response> {
    const url = new URL(request.url);
    const authHeader = request.headers.get("Authorization");

    try {
      const storageAdapter = getStorageAdapter(env, ctx);

      // Public health check endpoint
      if (url.pathname === "/health" || url.pathname === "/status") {
        console.log(`[Cache Health Check] Status requested`);
        return new Response(
          JSON.stringify({
            status: "healthy",
            service: "midgley-cache-worker",
            storage_tier: storageAdapter.tier,
            timestamp: new Date().toISOString()
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      }

      // Fail-Closed Bearer Authentication check (Issue #438, #559 Phase 5)
      const expectedToken = env.CLOUDFLARE_AUTH_TOKEN;
      if (!expectedToken) {
        console.warn(`[Cache Auth Error] CLOUDFLARE_AUTH_TOKEN is not configured on worker; rejecting request in fail-closed mode.`);
        await logToAxiom(env, ctx, { event: "cache_auth_unconfigured", ip: request.headers.get("CF-Connecting-IP") });
        return new Response(JSON.stringify({ error: "Unauthorized: Worker authentication is not configured" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        });
      }

      const token = authHeader?.replace("Bearer ", "").trim();
      if (!token || !timingSafeEqual(token, expectedToken)) {
        console.warn(`[Cache Auth Warning] Unauthorized request from ${request.headers.get("CF-Connecting-IP") || "unknown"}`);
        await logToAxiom(env, ctx, { event: "cache_auth_unauthorized", ip: request.headers.get("CF-Connecting-IP") });
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        });
      }

      // GET /api/v1/cache/:key
      if (request.method === "GET" && url.pathname.startsWith("/api/v1/cache/")) {
        const key = decodeURIComponent(url.pathname.replace("/api/v1/cache/", ""));
        console.log(`[Cache Worker GET] Request for key: "${key}"`);
        try {
          const entry = await storageAdapter.getCache(key);

          if (entry) {
            console.log(`[Cache Worker HIT] Found entry for key: "${key}"`);
            await logToAxiom(env, ctx, { event: "cache_get_hit", key, storage_tier: storageAdapter.tier });
            return new Response(
              JSON.stringify({ value: entry.value, created_at: entry.created_at, expires_at: entry.expires_at }),
              { headers: { "Content-Type": "application/json" } }
            );
          }

          console.log(`[Cache Worker MISS] No entry found for key: "${key}"`);
          await logToAxiom(env, ctx, { event: "cache_get_miss", key, storage_tier: storageAdapter.tier });
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

      // POST /api/v1/sync/predictions (Issue #302 & Issue #641: Direct/Batch prediction sync)
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

          const syncRes = await storageAdapter.syncPredictions(predictions);

          console.log(`[Cache Worker SYNC SUCCESS] Synced ${syncRes.synced_rows} records (tier: ${storageAdapter.tier})`);
          await logToAxiom(env, ctx, { event: "prediction_sync_success", count: syncRes.synced_rows, storage_tier: storageAdapter.tier });
          return new Response(JSON.stringify({
            status: "synced",
            synced_rows: syncRes.synced_rows,
            provider: storageAdapter.tier === "hyperdrive" ? "hyperdrive_postgres" : "cloudflare_d1"
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" }
          });
        } catch (err: any) {
          console.error(`[Cache Worker Error] Prediction sync failed: ${err.message || String(err)}`);
          await captureSentryException(env, ctx, err, { action: "SYNC_PREDICTIONS" });
          return new Response(JSON.stringify({ error: "Prediction sync failed" }), {
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
          const createdAt = body.created_at || Date.now() / 1000;
          const expiresAt = body.expires_at || Date.now() / 1000 + 86400;

          await storageAdapter.setCache(key, body.value, createdAt, expiresAt);

          console.log(`[Cache Worker STORE SUCCESS] Key stored: "${key}" (tier: ${storageAdapter.tier})`);
          await logToAxiom(env, ctx, { event: "cache_store_success", key, storage_tier: storageAdapter.tier });
          return new Response(JSON.stringify({ status: "stored", key }), {
            headers: { "Content-Type": "application/json" }
          });
        } catch (err: any) {
          console.error(`[Cache Worker Error] STORE for key "${key}" failed: ${err.message || String(err)}`);
          await captureSentryException(env, ctx, err, { action: "STORE", key });
          return new Response(JSON.stringify({ error: "Internal Server Error" }), {
            status: 500,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      // DELETE /api/v1/cache
      if (request.method === "DELETE" && (url.pathname === "/api/v1/cache" || url.pathname === "/api/v1/cache/")) {
        try {
          await storageAdapter.deleteCache();
          return new Response(JSON.stringify({ status: "cleared" }), {
            headers: { "Content-Type": "application/json" }
          });
        } catch (err: any) {
          console.error(`[Cache Worker Error] DELETE cache failed: ${err.message || String(err)}`);
          return new Response(JSON.stringify({ error: "Internal Server Error" }), {
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
