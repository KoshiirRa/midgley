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

      // POST /api/v1/cache/:key
      if (request.method === "POST" && url.pathname.startsWith("/api/v1/cache/")) {
        const key = decodeURIComponent(url.pathname.replace("/api/v1/cache/", ""));
        try {
          const body: any = await request.json();
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
