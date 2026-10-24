import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import nacl from "tweetnacl";
import intradayWorker, {
  normalizeHeadline,
  isAnomalyHeadline,
  hexToUint8Array,
  verifyDiscordSignature,
  handleDiscordInteraction,
  handleQueueBatch,
  isHeadlineDispatchedInCache,
  markHeadlineDispatchedInCache,
  generateEventToken,
  getWorkerSigningSecret,
  timingSafeEqual as intradayTimingSafeEqual,
  clearWorkerSubscriptionsMemoryForTesting,
  ensureFlagReplaySchema,
  isEdgarRelevant,
  isEdgar8kSeen,
  markEdgar8kSeen,
  clearEdgarCacheForTesting,
  pollEdgar8KFeeds,
  EDGAR_OPERATIONAL_KEYWORDS,
  getEdgarFeedCache,
  setEdgarFeedCache,
  Env as IntradayEnv,
  QueueMessageBatch
} from "../workers/intraday_monitor_worker";
import cacheWorker, { timingSafeEqual as cacheTimingSafeEqual, Env as CacheEnv } from "../workers/cache_worker";
import {
  scoreHeadlineAtEdge,
  querySemanticDedupe,
  indexHeadlineVector,
  retainHindsightMemory,
  queryHindsightBank,
  synthesizeAnalystBrief,
  getHeadlineEmbedding,
  fallbackRegexScore,
  extractMatchedEntityAtEdge
} from "../workers/ai_event_scorer";

function uint8ArrayToHex(arr: Uint8Array): string {
  return Array.from(arr)
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
}

function createMockD1Database(initialColumns: string[] = ["clean_key", "value", "used_at"]) {
  const store = new Map<string, any>();
  const columns = new Set<string>(initialColumns);
  return {
    store,
    columns,
    prepare(query: string) {
      if (query.includes("PRAGMA table_info(flag_replay_tokens)")) {
        return {
          async all() {
            return {
              results: Array.from(columns).map(c => ({ name: c }))
            };
          }
        };
      }
      if (query.includes("ALTER TABLE flag_replay_tokens ADD COLUMN value")) {
        return {
          async run() {
            columns.add("value");
            return { success: true };
          }
        };
      }
      if (query.includes("edgar_8k_seen")) {
        return {
          bind(...args: any[]) {
            return {
              async first() {
                const k1 = args[0];
                const k2 = args[1];
                if (store.has(k1) || (k2 && store.has(k2))) {
                  return { found: 1 };
                }
                return null;
              },
              async run() {
                const accessionId = args[0];
                const ticker = args[1];
                const filedAt = args[2];
                store.set(accessionId, { accession_id: accessionId, ticker, filed_at: filedAt });
                return { success: true };
              }
            };
          },
          async run() {
            return { success: true };
          }
        };
      }
      return {
        bind(...args: any[]) {
          return {
            async first() {
              const key = args[0];
              if (query.includes("value") && !columns.has("value")) {
                throw new Error("no such column: value");
              }
              if (store.has(key)) {
                return store.get(key);
              }
              return null;
            },
            async run() {
              if (query.includes("value") && !columns.has("value")) {
                throw new Error("table flag_replay_tokens has no column named value");
              }
              if (query.startsWith("DELETE")) {
                store.delete(args[0]);
                return { success: true };
              }
              const key = args[0];
              const value = args[1] || "{}";
              store.set(key, { clean_key: key, value, created_at: new Date().toISOString() });
              return { success: true };
            }
          };
        },
        async all() {
          if (query.includes("value") && !columns.has("value")) {
            throw new Error("no such column: value");
          }
          const results = Array.from(store.values());
          return { results };
        },
        async run() {
          return { success: true };
        }
      };
    }
  };
}

describe("Cloudflare Intraday Monitor Worker", () => {
  describe("Headline Normalization & Filtering", () => {
    it("strips trailing news publisher suffixes and generates alphanumeric keys", () => {
      expect(normalizeHeadline("Oil surges as refinery halts operations - Reuters")).toBe(
        "oilsurgesasrefineryhaltsoperations"
      );
      expect(normalizeHeadline("Gasoline prices steady | Bloomberg")).toBe(
        "gasolinepricessteady"
      );
      expect(normalizeHeadline("Crude supply disruption reported - Seeking Alpha")).toBe(
        "crudesupplydisruptionreported"
      );
    });

    it("identifies energy anomaly headlines via trigger keywords", () => {
      expect(isAnomalyHeadline("Refinery explosion reported in West Tulsa")).toBe(true);
      expect(isAnomalyHeadline("Retaliatory fuel tariff announced on crude imports")).toBe(true);
      expect(isAnomalyHeadline("Pipeline halt in Colonial Pipeline main line")).toBe(true);
      expect(isAnomalyHeadline("Tanker attack reported near Strait of Hormuz")).toBe(true);
      expect(isAnomalyHeadline("PBF Energy reports unplanned crude distillation unit outage")).toBe(true);
      expect(isAnomalyHeadline("Delaware City refinery FCC unit outage reported")).toBe(true);
    });

    it("filters out non-energy tariffs, non-energy sanctions, and localized facility spills", () => {
      expect(isAnomalyHeadline("Global IT airline outage causes major airport delays")).toBe(false);
      expect(isAnomalyHeadline("New steel tariff and aluminum tariff proposed by Congress")).toBe(false);
      expect(isAnomalyHeadline("Section 301 semiconductor tariff under congressional review")).toBe(false);
      expect(isAnomalyHeadline("Canola oil trade tariff sparks agricultural debates")).toBe(false);
      expect(isAnomalyHeadline("Supreme Court Dismisses Appeal on Classification of Hydrogenated Rice Bran Oil Due to Retention of Essential Characteristics. Classified under Tariff Item 12 as Vegetable Non-Essential Oil")).toBe(false);
      expect(isAnomalyHeadline("Government raises edible oil and palm oil tariff values")).toBe(false);
      // Issues #312, #318: Macro sanctions without petroleum co-occurrence
      expect(isAnomalyHeadline("Russia sanctions bill gives Trump sweeping new tariff powers - Reuters")).toBe(false);
      expect(isAnomalyHeadline("Trump signs Russia sanctions bill championed by Lindsey Graham - CBS News")).toBe(false);
      // Issue #317: Local data center spill
      expect(isAnomalyHeadline("Data Center’s Spill of 5,000 Gallons of Diesel Forces N.J. River Cleanup")).toBe(false);
      // Valid petroleum energy sanctions must still be recognized
      expect(isAnomalyHeadline("New US sanctions target crude oil tankers and petroleum exports")).toBe(true);
    });
  });

  describe("Discord Ed25519 Signature Verification", () => {
    const keyPair = nacl.sign.keyPair();
    const publicKeyHex = uint8ArrayToHex(keyPair.publicKey);
    const secretKey = keyPair.secretKey;

    it("converts hex strings to Uint8Array correctly", () => {
      const hex = "0123456789abcdef";
      const u8 = hexToUint8Array(hex);
      expect(u8.length).toBe(8);
      expect(uint8ArrayToHex(u8)).toBe(hex);
    });

    it("validates authentic Ed25519 detached signatures", () => {
      const timestamp = "1727123456";
      const body = JSON.stringify({ type: 1 });
      const message = new TextEncoder().encode(timestamp + body);
      const signature = nacl.sign.detached(message, secretKey);
      const signatureHex = uint8ArrayToHex(signature);

      const isValid = verifyDiscordSignature(publicKeyHex, signatureHex, timestamp, body);
      expect(isValid).toBe(true);
    });

    it("rejects forged or corrupted signatures", () => {
      const timestamp = "1727123456";
      const body = JSON.stringify({ type: 1 });
      const corruptedSigHex = "00".repeat(64);

      const isValid = verifyDiscordSignature(publicKeyHex, corruptedSigHex, timestamp, body);
      expect(isValid).toBe(false);
    });

    it("handles Discord interaction requests and returns HTTP 401 when headers are missing", async () => {
      const req = new Request("https://worker.local/discord/interactions", {
        method: "POST",
        body: JSON.stringify({ type: 1 })
      });
      const env: IntradayEnv = { DISCORD_PUBLIC_KEY: publicKeyHex };
      const res = await handleDiscordInteraction(req, env, {});
      expect(res.status).toBe(401);
    });

    it("responds to valid PING interactions with PONG (type 1)", async () => {
      const timestamp = String(Math.floor(Date.now() / 1000));
      const body = JSON.stringify({ type: 1 });
      const message = new TextEncoder().encode(timestamp + body);
      const signature = nacl.sign.detached(message, secretKey);
      const signatureHex = uint8ArrayToHex(signature);

      const req = new Request("https://worker.local/discord/interactions", {
        method: "POST",
        headers: {
          "X-Signature-Ed25519": signatureHex,
          "X-Signature-Timestamp": timestamp,
          "Content-Type": "application/json"
        },
        body
      });

      const env: IntradayEnv = { DISCORD_PUBLIC_KEY: publicKeyHex };
      const res = await handleDiscordInteraction(req, env, {});
      expect(res.status).toBe(200);
      const data = (await res.json()) as { type: number };
      expect(data).toEqual({ type: 1 });
    });
  });

  describe("Queue Batch Handling", () => {
    const originalFetch = globalThis.fetch;

    beforeEach(() => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        json: async () => ({})
      });
    });

    afterEach(() => {
      globalThis.fetch = originalFetch;
    });

    it("processes queue batch items and acknowledges dispatched messages", async () => {
      const ackSpy = vi.fn();
      const retrySpy = vi.fn();
      const mockDb = createMockD1Database();

      const batch: QueueMessageBatch = {
        queue: "intraday-events",
        messages: [
          {
            id: "msg-1",
            timestamp: new Date(),
            body: {
              headline: "Colonial pipeline outage shuts line 1",
              url: "https://example.com/colonial-outage",
              source: "Test_Suite"
            },
            attempts: 1,
            ack: ackSpy,
            retry: retrySpy
          }
        ],
        ackAll: vi.fn(),
        retryAll: vi.fn()
      };

      const env: IntradayEnv = {
        GH_PAT: "mock_gh_pat_token",
        REPO_OWNER: "KoshiirRa",
        REPO_NAME: "midgley",
        DB: mockDb
      };

      const result = await handleQueueBatch(batch, env);
      expect(result.processed).toBe(1);
      expect(result.acked).toBe(1);
      expect(ackSpy).toHaveBeenCalled();
    });

    it("skips and acks already-cached messages", async () => {
      const ackSpy = vi.fn();
      const retrySpy = vi.fn();
      const mockDb = createMockD1Database();
      const env: IntradayEnv = {
        GH_PAT: "mock_gh_pat_token",
        DB: mockDb
      };

      const headline = "Already dispatched headline event";
      await markHeadlineDispatchedInCache(headline, env);

      const batch: QueueMessageBatch = {
        queue: "intraday-events",
        messages: [
          {
            id: "msg-2",
            timestamp: new Date(),
            body: {
              headline,
              url: "https://example.com/cached",
              source: "Test_Suite"
            },
            attempts: 1,
            ack: ackSpy,
            retry: retrySpy
          }
        ],
        ackAll: vi.fn(),
        retryAll: vi.fn()
      };

      const result = await handleQueueBatch(batch, env);
      expect(result.acked).toBe(1);
      expect(ackSpy).toHaveBeenCalled();
    });
  });

  describe("Deduplication Cache with D1 Binding", () => {
    it("persists and retrieves dispatched headline state", async () => {
      const headline = "Test Unique Refinery Shutdown " + Date.now();
      const mockDb = createMockD1Database();
      const env: IntradayEnv = { DB: mockDb };

      const initiallyCached = await isHeadlineDispatchedInCache(headline, env);
      expect(initiallyCached).toBe(false);

      await markHeadlineDispatchedInCache(headline, env);
      const subsequentlyCached = await isHeadlineDispatchedInCache(headline, env);
      expect(subsequentlyCached).toBe(true);
    });
  });
});

describe("Cloudflare Cache Worker", () => {
  it("fails closed and rejects cache requests when auth token is unconfigured", async () => {
    const env: CacheEnv = {};

    const req = new Request("https://cache.local/api/v1/cache/test_key", {
      method: "GET"
    });

    const res = await cacheWorker.fetch(req, env, {});
    expect(res.status).toBe(401);
    const data = (await res.json()) as { error: string };
    expect(data.error).toContain("Unauthorized");
  });

  it("rejects unauthorized cache requests when auth token is configured", async () => {
    const env: CacheEnv = {
      CLOUDFLARE_AUTH_TOKEN: "secret-token-12345"
    };

    const req = new Request("https://cache.local/api/v1/cache/get?key=test", {
      method: "GET",
      headers: { Authorization: "Bearer wrong-token" }
    });

    const res = await cacheWorker.fetch(req, env, {});
    expect(res.status).toBe(401);
  });

  it("handles health checks cleanly without authentication", async () => {
    const env: CacheEnv = {
      CLOUDFLARE_AUTH_TOKEN: "secret-token-12345"
    };

    const req = new Request("https://cache.local/health", {
      method: "GET"
    });

    const res = await cacheWorker.fetch(req, env, {});
    expect(res.status).toBe(200);
    const data = (await res.json()) as { status: string };
    expect(data.status).toBe("healthy");
  });
});

describe("Intraday Monitor Worker Security (Issue #438)", () => {
  it("escapes malicious HTML query parameters on GET /flag", async () => {
    const maliciousHeadline = "<script>alert('XSS')</script>";
    const maliciousSource = "<b onmouseover=alert(1)>Source</b>";
    const testEventId = "0123456789abcdef";
    const env: IntradayEnv = { GH_PAT: "test_token", FLAG_SIGNING_KEY: "test_flag_secret" };
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const sig = await generateEventToken(testEventId, exp, "test_flag_secret", maliciousHeadline);

    const req = new Request(
      `https://worker.local/flag?id=${testEventId}&exp=${exp}&sig=${sig}&headline=${encodeURIComponent(maliciousHeadline)}&source=${encodeURIComponent(maliciousSource)}`,
      { method: "GET" }
    );

    const res = await intradayWorker.fetch(req, env, {});
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).not.toContain("<script>alert('XSS')</script>");
    expect(html).toContain("&lt;script&gt;alert(&#039;XSS&#039;)&lt;/script&gt;");
    expect(html).not.toContain("<b onmouseover=alert(1)>");
    expect(html).toContain("&lt;b onmouseover=alert(1)&gt;Source&lt;/b&gt;");
  });

  it("rejects unsigned GET /flag requests with HTTP 403", async () => {
    const env: IntradayEnv = {
      FLAG_SIGNING_KEY: "admin_secret_token"
    };

    const req = new Request("https://worker.local/flag?id=0123456789abcdef", {
      method: "GET"
    });

    const res = await intradayWorker.fetch(req, env, {});
    expect(res.status).toBe(403);
    const data = (await res.json()) as { error: string };
    expect(data.error).toContain("Forbidden: Missing, invalid, or expired signed flag link");
  });

  it("resolves signing secret falling back to ADMIN_TOKEN and CLOUDFLARE_AUTH_TOKEN", () => {
    expect(getWorkerSigningSecret({ FLAG_SIGNING_KEY: "flag_key" })).toBe("flag_key");
    expect(getWorkerSigningSecret({ ADMIN_TOKEN: "admin_key" })).toBe("admin_key");
    expect(getWorkerSigningSecret({ CLOUDFLARE_AUTH_TOKEN: "cf_key" })).toBe("cf_key");
    expect(getWorkerSigningSecret({})).toBe(null);
  });

  it("renders form for valid signed GET /flag requests and accepts signed POST /flag submission", async () => {
    const env: IntradayEnv = {
      GH_PAT: "real_gh_pat_token",
      FLAG_SIGNING_KEY: "admin_secret_token",
      REPO_OWNER: "KoshiirRa",
      REPO_NAME: "midgley"
    };

    const testEventId = "1234567890abcdef";
    const headline = "Non-Energy Tariff Trigger";
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const sig = await generateEventToken(testEventId, exp, "admin_secret_token", headline);

    // 1. GET /flag with valid exp & sig renders form
    const getReq = new Request(
      `https://worker.local/flag?id=${testEventId}&exp=${exp}&sig=${sig}&headline=Non-Energy+Tariff+Trigger&source=RSS_GoogleNews`,
      { method: "GET" }
    );
    const getRes = await intradayWorker.fetch(getReq, env, {});
    expect(getRes.status).toBe(200);
    const html = await getRes.text();
    expect(html).toContain(`name="sig" value="${sig}"`);
    expect(html).toContain(`name="exp" value="${exp}"`);

    // Mock GitHub issue creation response
    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        number: 499,
        html_url: "https://github.com/KoshiirRa/midgley/issues/499",
        node_id: "I_kwDOtest499"
      })
    });

    try {
      // 2. Submit POST /flag with the signed parameters
      const formData = new FormData();
      formData.append("id", "1234567890abcdef");
      formData.append("exp", exp.toString());
      formData.append("sig", sig);
      formData.append("headline", "Non-Energy Tariff Trigger");
      formData.append("source", "RSS_GoogleNews");
      formData.append("category", "Non-Energy Macro Tariff");
      formData.append("notes", "Valid false positive report from Discord user");

      const postReq = new Request("https://worker.local/flag", {
        method: "POST",
        body: formData
      });

      const postRes = await intradayWorker.fetch(postReq, env, {});
      expect(postRes.status).toBe(200);
      const postHtml = await postRes.text();
      expect(postHtml).toContain("False Positive Issue Logged!");
      expect(postHtml).toContain("Issue <strong>#499</strong>");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects unauthenticated POST /flag submissions with invalid token", async () => {
    const formData = new FormData();
    formData.append("id", "test_id");
    formData.append("headline", "Test Headline");
    formData.append("token", "invalid_token");

    const req = new Request("https://worker.local/flag", {
      method: "POST",
      body: formData
    });

    const env: IntradayEnv = {
      GH_PAT: "real_gh_pat_token",
      ADMIN_TOKEN: "admin_secret_token"
    };

    const res = await intradayWorker.fetch(req, env, {});
    expect(res.status).toBe(401);
    const data = (await res.json()) as { error: string };
    expect(data.error).toContain("Unauthorized: Missing or invalid authentication token for issue creation");
  });

  it("accepts direct admin token in Authorization header on POST /flag submissions", async () => {
    const env: IntradayEnv = {
      GH_PAT: "real_gh_pat_token",
      ADMIN_TOKEN: "admin_secret_token",
      REPO_OWNER: "KoshiirRa",
      REPO_NAME: "midgley"
    };

    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        number: 500,
        html_url: "https://github.com/KoshiirRa/midgley/issues/500",
        node_id: "I_kwDOtest500"
      })
    });

    try {
      const formData = new FormData();
      formData.append("id", "admin_flagged_id");
      formData.append("headline", "Admin Flagged Event");

      const req = new Request("https://worker.local/flag", {
        method: "POST",
        headers: {
          "Authorization": "Bearer admin_secret_token"
        },
        body: formData
      });

      const res = await intradayWorker.fetch(req, env, {});
      expect(res.status).toBe(200);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects replayed signed POST /flag submissions with HTTP 409 Conflict", async () => {
    const env: IntradayEnv = {
      GH_PAT: "real_gh_pat_token",
      FLAG_SIGNING_KEY: "secret_signing_key",
      REPO_OWNER: "KoshiirRa",
      REPO_NAME: "midgley"
    };

    const exp = Math.floor(Date.now() / 1000) + 3600;
    const headline = "Replay Attack Headline";
    const sig = await generateEventToken("deadbeefcafebabe", exp, "secret_signing_key", headline);

    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ number: 501, html_url: "https://github.com/KoshiirRa/midgley/issues/501", node_id: "I_kwDOtest501" })
    });

    try {
      const createReq = () => {
        const formData = new FormData();
        formData.append("id", "deadbeefcafebabe");
        formData.append("exp", exp.toString());
        formData.append("sig", sig);
        formData.append("headline", headline);
        return new Request("https://worker.local/flag", { method: "POST", body: formData });
      };

      // First submission succeeds
      const res1 = await intradayWorker.fetch(createReq(), env, {});
      expect(res1.status).toBe(200);

      // Second submission (replay) is rejected with 409
      const res2 = await intradayWorker.fetch(createReq(), env, {});
      expect(res2.status).toBe(409);
      const data = (await res2.json()) as { error: string };
      expect(data.error).toContain("already been used");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("handles operator review actions for duplicate and distinct decisions", async () => {
    const signingKey = "test_signing_key_secret";
    const env: IntradayEnv = {
      FLAG_SIGNING_KEY: signingKey,
      REPO_OWNER: "KoshiirRa",
      REPO_NAME: "midgley"
    };

    const exp = Math.floor(Date.now() / 1000) + 3600;
    const eventId = "abc12345";
    const priorId = "def67890";
    const headline = "Exxon Joliet refinery suffers secondary flaring";

    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey(
      "raw",
      enc.encode(signingKey),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const data = enc.encode(`review_dup:v1|${eventId}|${priorId}|duplicate|${exp}`);
    const sigBuf = await crypto.subtle.sign("HMAC", key, data);
    const sig = Array.from(new Uint8Array(sigBuf))
      .map(b => b.toString(16).padStart(2, "0"))
      .join("")
      .slice(0, 32);

    const reviewUrl = `https://worker.local/review?id=${eventId}&prior_id=${priorId}&decision=duplicate&exp=${exp}&sig=${sig}&headline=${encodeURIComponent(headline)}`;
    const req = new Request(reviewUrl, { method: "GET" });

    const res = await intradayWorker.fetch(req, env, {});
    expect(res.status).toBe(200);
    const text = await res.text();
    expect(text).toContain("Confirmed Duplicate");
  });

  it("rejects Discord interactions with expired timestamps (>300s)", async () => {
    const keyPair = nacl.sign.keyPair();
    const publicKeyHex = uint8ArrayToHex(keyPair.publicKey);
    const secretKey = keyPair.secretKey;

    const oldTimestamp = String(Math.floor(Date.now() / 1000) - 600); // 10 minutes ago
    const body = JSON.stringify({ type: 1 });
    const message = new TextEncoder().encode(oldTimestamp + body);
    const signature = nacl.sign.detached(message, secretKey);
    const signatureHex = uint8ArrayToHex(signature);

    const req = new Request("https://worker.local/discord/interactions", {
      method: "POST",
      headers: {
        "X-Signature-Ed25519": signatureHex,
        "X-Signature-Timestamp": oldTimestamp,
        "Content-Type": "application/json"
      },
      body
    });

    const env: IntradayEnv = { DISCORD_PUBLIC_KEY: publicKeyHex };
    const res = await handleDiscordInteraction(req, env, {});
    expect(res.status).toBe(401);
  });

  it("rejects unauthenticated requests to /run and /trigger when admin token is set or unset (Fail-Closed)", async () => {
    const req = new Request("https://worker.local/run", {
      method: "GET"
    });

    // Case 1: Unset ADMIN_TOKEN fails closed
    const envUnset: IntradayEnv = {};
    const resUnset = await intradayWorker.fetch(req, envUnset, {});
    expect(resUnset.status).toBe(401);

    // Case 2: Configured ADMIN_TOKEN but missing header fails closed
    const envSet: IntradayEnv = {
      ADMIN_TOKEN: "admin_secret_token"
    };
    const resSet = await intradayWorker.fetch(req, envSet, {});
    expect(resSet.status).toBe(401);
  });

  describe("Constant-Time String Comparison (timingSafeEqual)", () => {
    it("validates equal strings correctly for cache worker", () => {
      expect(cacheTimingSafeEqual("secret123", "secret123")).toBe(true);
      expect(cacheTimingSafeEqual("secret123", "secret124")).toBe(false);
      expect(cacheTimingSafeEqual("secret123", "secret1234")).toBe(false);
      expect(cacheTimingSafeEqual("", "")).toBe(true);
      expect(cacheTimingSafeEqual("a", "")).toBe(false);
    });

    it("validates equal strings correctly for intraday monitor worker", () => {
      expect(intradayTimingSafeEqual("token_abc_xyz", "token_abc_xyz")).toBe(true);
      expect(intradayTimingSafeEqual("token_abc_xyz", "token_abc_xyw")).toBe(false);
      expect(intradayTimingSafeEqual("token_abc_xyz", "token_abc")).toBe(false);
      expect(intradayTimingSafeEqual("", "")).toBe(true);
    });
  });

  describe("Discord Slash Commands (/midgley) & Direct Message Delivery (Issue #235)", () => {
    const keyPair = nacl.sign.keyPair();
    const publicKeyHex = uint8ArrayToHex(keyPair.publicKey);
    const secretKey = keyPair.secretKey;

    function createSignedInteractionRequest(payload: Record<string, any>): Request {
      const timestamp = String(Math.floor(Date.now() / 1000));
      const body = JSON.stringify(payload);
      const message = new TextEncoder().encode(timestamp + body);
      const signature = nacl.sign.detached(message, secretKey);
      const signatureHex = uint8ArrayToHex(signature);
      return new Request("https://worker.local/discord/interactions", {
        method: "POST",
        headers: {
          "X-Signature-Ed25519": signatureHex,
          "X-Signature-Timestamp": timestamp,
          "Content-Type": "application/json"
        },
        body
      });
    }

    it("handles locale autocomplete interactions (type 4) and returns filtered choices (type 8)", async () => {
      const req = createSignedInteractionRequest({
        type: 4,
        data: {
          name: "midgley",
          options: [
            {
              name: "subscribe",
              type: 1,
              options: [{ name: "locale", type: 3, value: "tul", focused: true }]
            }
          ]
        }
      });
      const res = await handleDiscordInteraction(req, { DISCORD_PUBLIC_KEY: publicKeyHex }, {});
      expect(res.status).toBe(200);
      const body = (await res.json()) as any;
      expect(body.type).toBe(8);
      expect(body.data.choices.some((c: any) => c.value === "Tulsa")).toBe(true);
    });

    it("handles /midgley subscribe, /midgley status, /midgley forecast, and /midgley unsubscribe with ephemeral + DM delivery", async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (String(url).includes("/users/@me/channels")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ id: "dm_channel_999" }),
            text: async () => '{"id":"dm_channel_999"}'
          };
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ id: "msg_1" }),
          text: async () => '{"id":"msg_1"}'
        };
      });

      const env: IntradayEnv = {
        DISCORD_PUBLIC_KEY: publicKeyHex,
        DISCORD_BOT_TOKEN: "mock_bot_token_235"
      };

      try {
        // 1. /midgley subscribe locale:Tulsa min_shock:0.30
        const subReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "777888999000", username: "energy_trader" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "subscribe",
                type: 1,
                options: [
                  { name: "locale", type: 3, value: "Tulsa" },
                  { name: "min_shock", type: 10, value: 0.3 },
                  { name: "direction", type: 3, value: "spikes_only" },
                  { name: "delivery", type: 3, value: "dm" }
                ]
              }
            ]
          }
        });
        const subRes = await handleDiscordInteraction(subReq, env, {});
        expect(subRes.status).toBe(200);
        const subJson = (await subRes.json()) as any;
        expect(subJson.type).toBe(4);
        expect(subJson.data.flags).toBe(64); // Ephemeral
        expect(subJson.data.content).toContain("Tulsa");
        expect(subJson.data.content).toContain("Direct Messages");

        // 2. /midgley status
        const statusReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "777888999000", username: "energy_trader" } },
          data: {
            name: "midgley",
            options: [{ name: "status", type: 1 }]
          }
        });
        const statusRes = await handleDiscordInteraction(statusReq, env, {});
        const statusJson = (await statusRes.json()) as any;
        expect(statusJson.data.flags).toBe(64);
        expect(JSON.stringify(statusJson.data.embeds)).toContain("Tulsa");

        // 3. /midgley forecast locale:Oakland horizon:3
        const fcReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "777888999000", username: "energy_trader" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "forecast",
                type: 1,
                options: [
                  { name: "locale", type: 3, value: "Oakland" },
                  { name: "horizon", type: 4, value: 3 }
                ]
              }
            ]
          }
        });
        const fcRes = await handleDiscordInteraction(fcReq, env, {});
        const fcJson = (await fcRes.json()) as any;
        expect(fcJson.data.flags).toBe(64);
        expect(fcJson.data.embeds[0].title).toContain("3D Forecast");
        expect(JSON.stringify(fcJson.data.embeds[0])).toContain("Projected Pump Price (3D)");
        expect(JSON.stringify(fcJson.data.embeds[0])).toContain("Expected Shift (ΔP)");
        expect(JSON.stringify(fcJson.data.embeds[0])).toContain("95% Confidence Interval");
        expect(JSON.stringify(fcJson.data.embeds[0])).toContain("Multi-Day Trajectory (1D – 3D Path)");

        // 4. /midgley unsubscribe locale:all
        const unsubReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "777888999000", username: "energy_trader" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "unsubscribe",
                type: 1,
                options: [{ name: "locale", type: 3, value: "all" }]
              }
            ]
          }
        });
        const unsubRes = await handleDiscordInteraction(unsubReq, env, {});
        const unsubJson = (await unsubRes.json()) as any;
        expect(unsubJson.data.flags).toBe(64);
        expect(unsubJson.data.content).toContain("Unsubscribed");
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it("gracefully falls back to ephemeral warning when Discord blocks DM with HTTP 403 (Error 50007)", async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        text: async () => '{"message": "Cannot send messages to this user", "code": 50007}'
      });

      const env: IntradayEnv = {
        DISCORD_PUBLIC_KEY: publicKeyHex,
        DISCORD_BOT_TOKEN: "mock_bot_token_235"
      };

      try {
        const testAlertReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "111222333444", username: "privacy_locked_user" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "test-alert",
                type: 1,
                options: [{ name: "locale", type: 3, value: "Cincinnati" }]
              }
            ]
          }
        });
        const res = await handleDiscordInteraction(testAlertReq, env, {});
        expect(res.status).toBe(200);
        const body = (await res.json()) as any;
        expect(body.type).toBe(4);
        expect(body.data.flags).toBe(64);
        expect(body.data.content).toContain("50007");
        expect(body.data.embeds.length).toBe(1);
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it("supports 5-digit US ZIP code subscriptions & forecasts and records out-of-metro ZIPs in telemetry", async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (String(url).includes("/users/@me/channels")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ id: "dm_channel_zip" }),
            text: async () => '{"id":"dm_channel_zip"}'
          };
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ id: "msg_zip" }),
          text: async () => '{"id":"msg_zip"}'
        };
      });

      const env: IntradayEnv = {
        DISCORD_PUBLIC_KEY: publicKeyHex,
        DISCORD_BOT_TOKEN: "mock_bot_token_235"
      };

      try {
        // Subscribe to out-of-metro ZIP 64101 (Kansas City, MO -> STATE_PADD_FALLBACK)
        const subZipReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "555666777888", username: "mo_driver" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "subscribe",
                type: 1,
                options: [
                  { name: "zip_code", type: 3, value: "64101" },
                  { name: "delivery", type: 3, value: "dm" }
                ]
              }
            ]
          }
        });
        const subZipRes = await handleDiscordInteraction(subZipReq, env, {});
        expect(subZipRes.status).toBe(200);
        const subZipJson = (await subZipRes.json()) as any;
        expect(subZipJson.data.flags).toBe(64);
        expect(subZipJson.data.content).toContain("64101");
        expect(subZipJson.data.content).toContain("STATE_PADD_FALLBACK");

        // Query /midgley forecast for ZIP 74103 (Tulsa Metro -> METRO_CLUSTER_HIT)
        const fcZipReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "555666777888", username: "mo_driver" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "forecast",
                type: 1,
                options: [
                  { name: "zip_code", type: 3, value: "74103" },
                  { name: "horizon", type: 4, value: 1 }
                ]
              }
            ]
          }
        });
        const fcZipRes = await handleDiscordInteraction(fcZipReq, env, {});
        expect(fcZipRes.status).toBe(200);
        const fcZipJson = (await fcZipRes.json()) as any;
        expect(fcZipJson.data.embeds[0].title).toContain("ZIP 74103");
        expect(JSON.stringify(fcZipJson.data.embeds[0])).toContain("METRO_CLUSTER_HIT");

        // Check /telemetry/unmapped-zips endpoint on worker
        const telReq = new Request("https://worker.local/telemetry/unmapped-zips", { method: "GET" });
        const telRes = await intradayWorker.fetch(telReq, env, {});
        expect(telRes.status).toBe(200);
        const telJson = (await telRes.json()) as any;
        expect(telJson.unique_unmapped_zips).toBeGreaterThanOrEqual(1);
        expect(telJson.top_unmapped_zips.some((item: any) => item.zip_code === "64101" && item.state === "MO")).toBe(true);
        // 74103 is a metro cluster hit so it must NOT appear in unmapped zips
        expect(telJson.top_unmapped_zips.some((item: any) => item.zip_code === "74103")).toBe(false);

        // Subscribe to ZIP 12946 (Lake Placid, NY -> Native New York Metro Cluster Hit, Issue #635)
        const subNyReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "999888777666", username: "adk_skier" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "subscribe",
                type: 1,
                options: [
                  { name: "zip_code", type: 3, value: "12946" },
                  { name: "delivery", type: 3, value: "dm" }
                ]
              }
            ]
          }
        });
        const subNyRes = await handleDiscordInteraction(subNyReq, env, {});
        expect(subNyRes.status).toBe(200);
        const subNyJson = (await subNyRes.json()) as any;
        expect(subNyJson.data.flags).toBe(64);
        expect(subNyJson.data.content).toContain("Lake Placid, NY");
        expect(subNyJson.data.content).toContain("METRO_CLUSTER_HIT");
        expect(JSON.stringify(subNyJson.data.embeds)).toContain("Lake Placid, NY");
        expect(JSON.stringify(subNyJson.data.embeds)).toContain("New_York");

        // Forecast for ZIP 12946 (Lake Placid, NY)
        const fcNyReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "999888777666", username: "adk_skier" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "forecast",
                type: 1,
                options: [
                  { name: "zip_code", type: 3, value: "12946" },
                  { name: "horizon", type: 4, value: 3 }
                ]
              }
            ]
          }
        });
        const fcNyRes = await handleDiscordInteraction(fcNyReq, env, {});
        expect(fcNyRes.status).toBe(200);
        const fcNyJson = (await fcNyRes.json()) as any;
        expect(fcNyJson.data.embeds[0].title).toContain("Lake Placid, NY");
        expect(JSON.stringify(fcNyJson.data.embeds[0])).toContain("Direct Metro Cluster Hit");

        // Subscribe to ZIP 19104 (Philadelphia, PA -> Significant Departure from Newark, DE)
        const subPaReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "444333222111", username: "philly_driver" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "subscribe",
                type: 1,
                options: [
                  { name: "zip_code", type: 3, value: "19104" },
                  { name: "delivery", type: 3, value: "dm" }
                ]
              }
            ]
          }
        });
        const subPaRes = await handleDiscordInteraction(subPaReq, env, {});
        expect(subPaRes.status).toBe(200);
        const subPaJson = (await subPaRes.json()) as any;
        expect(subPaJson.data.flags).toBe(64);
        expect(subPaJson.data.content).toContain("Philadelphia, PA");
        expect(subPaJson.data.content).toContain("STATE_PADD_FALLBACK");
        expect(JSON.stringify(subPaJson.data.embeds)).toContain("Philadelphia, PA");
        expect(JSON.stringify(subPaJson.data.embeds)).toContain("+$0.346/gal"); // Tax wedge
        expect(JSON.stringify(subPaJson.data.embeds)).toContain("Regional Basis & Tax Departure");

        // Forecast for ZIP 19104 (Philadelphia, PA)
        const fcPaReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "444333222111", username: "philly_driver" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "forecast",
                type: 1,
                options: [
                  { name: "zip_code", type: 3, value: "19104" },
                  { name: "horizon", type: 4, value: 3 }
                ]
              }
            ]
          }
        });
        const fcPaRes = await handleDiscordInteraction(fcPaReq, env, {});
        expect(fcPaRes.status).toBe(200);
        const fcPaJson = (await fcPaRes.json()) as any;
        expect(fcPaJson.data.embeds[0].title).toContain("Philadelphia, PA");
        expect(JSON.stringify(fcPaJson.data.embeds[0])).toContain("Statutory Tax Wedge");
        expect(JSON.stringify(fcPaJson.data.embeds[0])).toContain("+$0.346/gal");
        expect(JSON.stringify(fcPaJson.data.embeds[0])).toContain("Projected Pump Price (3D)");
        expect(JSON.stringify(fcPaJson.data.embeds[0])).toContain("Multi-Day Trajectory");

        // Forecast for ZIP 55555 (Minnesota Fallback corridor, Issue verification)
        const fcMnReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "555555555555", username: "minnesota_user" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "forecast",
                type: 1,
                options: [
                  { name: "zip_code", type: 3, value: "55555" },
                  { name: "horizon", type: 4, value: 5 }
                ]
              }
            ]
          }
        });
        const fcMnRes = await handleDiscordInteraction(fcMnReq, env, {});
        expect(fcMnRes.status).toBe(200);
        const fcMnJson = (await fcMnRes.json()) as any;
        const mnEmbed = fcMnJson.data.embeds[0];
        expect(mnEmbed.title).toContain("ZIP 55555 (MN)");
        expect(mnEmbed.title).toContain("5D Forecast");
        // Verify genuine forecast fields are now delivered on the card!
        const mnFieldsStr = JSON.stringify(mnEmbed.fields);
        expect(mnFieldsStr).toContain("Projected Pump Price (5D)");
        expect(mnFieldsStr).toContain("Expected Shift (ΔP)");
        expect(mnFieldsStr).toContain("95% Confidence Interval");
        expect(mnFieldsStr).toContain("Current Base Price");
        expect(mnFieldsStr).toContain("Quantitative Engine");
        expect(mnFieldsStr).toContain("Multi-Day Trajectory (1D – 5D Path)");
        expect(mnFieldsStr).toContain("State Statutory Fuel Tax");
        expect(mnFieldsStr).toContain("Statutory Tax Wedge");
        expect(mnFieldsStr).toContain("Estimated Basis & Price Synthesis");
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it("retains DM alert subscriptions across worker memory cache evictions with D1 database binding", async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (String(url).includes("/users/@me/channels")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ id: "dm_channel_concentus" }),
            text: async () => '{"id":"dm_channel_concentus"}'
          };
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ id: "msg_dm" }),
          text: async () => '{"id":"msg_dm"}'
        };
      });

      const mockDb = createMockD1Database(["clean_key", "value", "used_at"]);
      const env: IntradayEnv = {
        DISCORD_PUBLIC_KEY: publicKeyHex,
        DISCORD_BOT_TOKEN: "mock_bot_token_concentus",
        DB: mockDb
      };

      try {
        clearWorkerSubscriptionsMemoryForTesting();

        // 1. Subscribe user @concentus (id: "53711617") to Newark
        const subReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "53711617", username: "concentus" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "subscribe",
                type: 1,
                options: [
                  { name: "locale", type: 3, value: "Newark" },
                  { name: "min_shock", type: 10, value: 0.25 },
                  { name: "direction", type: 3, value: "all_shocks" },
                  { name: "delivery", type: 3, value: "dm" }
                ]
              }
            ]
          }
        });
        const subRes = await handleDiscordInteraction(subReq, env, {});
        expect(subRes.status).toBe(200);

        // 2. Simulate worker isolate recycling / cold start by evicting memory cache
        clearWorkerSubscriptionsMemoryForTesting();

        // 3. /midgley status must still find the active subscription from D1
        const statusReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "53711617", username: "concentus" } },
          data: {
            name: "midgley",
            options: [{ name: "status", type: 1 }]
          }
        });
        const statusRes = await handleDiscordInteraction(statusReq, env, {});
        expect(statusRes.status).toBe(200);
        const statusJson = (await statusRes.json()) as any;
        expect(statusJson.data.flags).toBe(64);
        expect(JSON.stringify(statusJson.data.embeds)).toContain("Newark");
        expect(JSON.stringify(statusJson.data.embeds)).toContain("sub_dm_53711617");
        expect(JSON.stringify(statusJson.data.embeds)).not.toContain("No active Direct Message subscriptions found");
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it("auto-migrates missing 'value' column in flag_replay_tokens table when subscriber registers", async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (String(url).includes("/users/@me/channels")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ id: "dm_channel_legacy" }),
            text: async () => '{"id":"dm_channel_legacy"}'
          };
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ id: "msg_legacy" }),
          text: async () => '{"id":"msg_legacy"}'
        };
      });

      // Initially lacking the 'value' column as in legacy init_d1_schema.sql
      const mockDb = createMockD1Database(["clean_key", "used_at"]);
      expect(mockDb.columns.has("value")).toBe(false);

      const env: IntradayEnv = {
        DISCORD_PUBLIC_KEY: publicKeyHex,
        DISCORD_BOT_TOKEN: "mock_bot_token_legacy",
        DB: mockDb
      };

      try {
        clearWorkerSubscriptionsMemoryForTesting();

        // Subscribe user
        const subReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "888999111", username: "migrated_user" } },
          data: {
            name: "midgley",
            options: [
              {
                name: "subscribe",
                type: 1,
                options: [
                  { name: "locale", type: 3, value: "Tulsa" },
                  { name: "delivery", type: 3, value: "dm" }
                ]
              }
            ]
          }
        });
        const subRes = await handleDiscordInteraction(subReq, env, {});
        expect(subRes.status).toBe(200);

        // Verify that 'value' column was automatically added via schema self-healing
        expect(mockDb.columns.has("value")).toBe(true);

        // Evict in-memory cache to simulate isolate recycle
        clearWorkerSubscriptionsMemoryForTesting();

        // Verify /midgley status retrieves record from D1
        const statusReq = createSignedInteractionRequest({
          type: 2,
          member: { user: { id: "888999111", username: "migrated_user" } },
          data: {
            name: "midgley",
            options: [{ name: "status", type: 1 }]
          }
        });
        const statusRes = await handleDiscordInteraction(statusReq, env, {});
        const statusJson = (await statusRes.json()) as any;
        expect(JSON.stringify(statusJson.data.embeds)).toContain("Tulsa");
      } finally {
        globalThis.fetch = originalFetch;
      }
    });
  });

  describe("Enverus / Drillinginfo Daily Rig Count Scraper (Issues #533, #640)", () => {
    const sampleMarkdown = `### U.S. drilling activity starts the year with a 15-rig drop

The U.S. rig count reached 657 during the week ended Jan. 3, down 15 rigs from the previous week's high point, according to Enverus Foundations data. The count is down 18 rigs, or 3%, in the last month and down 204 rigs, or 24%, YOY. All numbers discussed are weekly peaks to avoid the sometimes wide variability of daily numbers.

Most of the decrease in the last week came from drilling programs outside the major basins. Among the major basins, the Gulf Coast's two-rig drop was the largest, leaving it with 73 rigs running. Appalachia and the Permian dropped one rig each to 40 and 293. The Williston Basin added one rig to reach 35, while the Anadarko and DJ basins were flat at 52 and 15 rigs.

Total Orientation PlayWeekMonthYear

### Rig Count by Basin

| Play | 10/07/26 | 10/08/26 | 10/09/26 | 10/10/26 | 10/11/26 | 10/12/26 | 10/13/26 | 10/14/26 | 1 Day Δ | % | 1 Month Δ | % | 1 Year Δ | % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ANADARKO BASIN | 59 | 58 | 58 | 58 | 58 | 58 | 64 | 64 | 0 | 0 | -2 | -3 | 17 | 36.2 |
| APPALACHIA | 35 | 33 | 34 | 34 | 34 | 35 | 34 | 33 | -1 | -2.9 | -1 | -2.9 | -5 | -13.2 |
| DJ BASIN | 7 | 11 | 10 | 10 | 10 | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| GULF COAST BASIN (INCLUDING EAGLE FORD) | 69 | 69 | 68 | 68 | 67 | 68 | 71 | 72 | 1 | 1.4 | 2 | 2.9 | 10 | 16.1 |
| PERMIAN | 252 | 248 | 251 | 254 | 255 | 255 | 251 | 254 | 3 | 1.2 | 3 | 1.2 | 24 | 10.4 |
| WILLISTON BASIN | 38 | 38 | 38 | 38 | 38 | 38 | 36 | 36 | 0 | 0 | -1 | -2.7 | 4 | 12.5 |
| OTHER | 199 | 201 | 200 | 200 | 200 | 202 | 190 | 187 | -3 | -1.6 | -6 | -3.1 | 36 | 23.8 |
| Total | 659 | 658 | 659 | 662 | 662 | 666 | 656 | 656 | 0 | 0 | -5 | -0.8 | 86 | 15.1 |
`;

    it("parses Cloudflare Browser Rendering markdown table and analysis", async () => {
      const { parseEnverusMarkdown } = await import("../workers/enverus_scraper");
      const result = parseEnverusMarkdown(sampleMarkdown);

      expect(result.total_rigs).toBe(656);
      expect(result.as_of).toBe("2026-10-14");
      expect(result.analysis_title).toBe("U.S. drilling activity starts the year with a 15-rig drop");
      expect(result.analysis_text).toContain("Enverus Foundations data");
      expect(result.basins?.length).toBe(8);

      const permian = result.basins?.find(b => b.play === "PERMIAN");
      expect(permian).toBeDefined();
      expect(permian?.latest_count).toBe(254);
      expect(permian?.day_delta).toBe(3);
      expect(permian?.day_pct).toBe(1.2);
      expect(permian?.year_delta).toBe(24);

      const gulfCoast = result.basins?.find(b => b.play.includes("GULF COAST"));
      expect(gulfCoast).toBeDefined();
      expect(gulfCoast?.latest_count).toBe(72);
      expect(gulfCoast?.day_delta).toBe(1);
    });

    it("fetches via Cloudflare browser quickAction when available", async () => {
      const { getEnverusDailyRigCount, clearEnverusMemoryCacheForTesting } = await import("../workers/enverus_scraper");
      clearEnverusMemoryCacheForTesting();

      const mockBrowser = {
        quickAction: vi.fn().mockResolvedValue(sampleMarkdown)
      };

      const env: IntradayEnv = {
        MYBROWSER: mockBrowser,
        MIDGLEY_AGENT_USER_AGENT: "MidgleyAgent/1.0 (+https://koshiirra.github.io/midgley/)"
      };

      const result = await getEnverusDailyRigCount(env, { force_refresh: true });
      expect(mockBrowser.quickAction).toHaveBeenCalledWith("markdown", expect.objectContaining({
        url: "https://www.enverus.com/dailyrigcount/"
      }));
      expect(result.status).toBe("success");
      expect(result.source).toBe("CLOUDFLARE_BROWSER_RENDERING");
      expect(result.total_rigs).toBe(656);
      expect(result.basins.length).toBe(8);
    });

    it("serves Enverus rig count over worker HTTP endpoint", async () => {
      const { clearEnverusMemoryCacheForTesting } = await import("../workers/enverus_scraper");
      clearEnverusMemoryCacheForTesting();

      const mockBrowser = {
        quickAction: vi.fn().mockResolvedValue(sampleMarkdown)
      };

      const env: IntradayEnv = {
        MYBROWSER: mockBrowser,
        MIDGLEY_AGENT_USER_AGENT: "MidgleyAgent/1.0 (+https://koshiirra.github.io/midgley/)"
      };

      const req = new Request("https://worker.local/api/v1/energy/rig-count/enverus");
      const res = await intradayWorker.fetch(req, env, {});

      expect(res.status).toBe(200);
      const json = (await res.json()) as any;
      expect(json.status).toBe("success");
      expect(json.total_rigs).toBe(656);
      expect(json.basins).toBeDefined();
    });
  });

  describe("Cloudflare Browser Run Unified Client (workers/browser_run.ts)", () => {
    it("renders markdown using env.MYBROWSER quickAction", async () => {
      const { fetchMarkdownViaBrowserRun } = await import("../workers/browser_run");
      const mockBrowser = {
        quickAction: vi.fn().mockResolvedValue("# Header\n\nContent")
      };
      const env = { MYBROWSER: mockBrowser };
      const md = await fetchMarkdownViaBrowserRun(env, "https://example.com/test");
      expect(md).toBe("# Header\n\nContent");
      expect(mockBrowser.quickAction).toHaveBeenCalledWith("markdown", expect.objectContaining({
        url: "https://example.com/test"
      }));
    });

    it("falls back to Browser Run REST API when binding is absent and credentials are provided", async () => {
      const { fetchMarkdownViaBrowserRun } = await import("../workers/browser_run");
      const originalFetch = globalThis.fetch;
      try {
        globalThis.fetch = vi.fn().mockResolvedValue({
          status: 200,
          json: vi.fn().mockResolvedValue({ success: true, result: "## REST API Markdown" })
        } as any);

        const env = {
          CLOUDFLARE_ACCOUNT_ID: "test_acc_abc",
          CLOUDFLARE_API_TOKEN: "test_token_xyz"
        };
        const md = await fetchMarkdownViaBrowserRun(env, "https://example.com/api-test");
        expect(md).toBe("## REST API Markdown");
        expect(globalThis.fetch).toHaveBeenCalledWith(
          "https://api.cloudflare.com/client/v4/accounts/test_acc_abc/browser-run/markdown",
          expect.objectContaining({
            method: "POST"
          })
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it("returns null cleanly when neither binding nor REST credentials are provided", async () => {
      const { fetchMarkdownViaBrowserRun } = await import("../workers/browser_run");
      const env = {};
      const md = await fetchMarkdownViaBrowserRun(env, "https://example.com/none");
      expect(md).toBeNull();
    });
  });

  describe("Cloudflare Workers AI & Vectorize Edge Intelligence (Issue #645)", () => {
    describe("Zero-Shot Catalyst & Severity Scoring at the Edge", () => {
      it("scores refinery outages accurately with Workers AI structured output", async () => {
        const mockAi = {
          run: vi.fn().mockResolvedValue({
            response: JSON.stringify({
              is_anomaly: true,
              catalyst_domain: "refinery_pipeline",
              affected_hub: "Houston_TX",
              direction: "spike",
              magnitude: "critical",
              half_life_days: 6.5,
              confidence: 0.94,
              reasoning: "Port Arthur CDU shutdown tightens Gulf Coast supply"
            })
          })
        };

        const result = await scoreHeadlineAtEdge(
          "Valero Port Arthur CDU restart delay tightens Gulf Coast RBOB supply",
          { AI: mockAi }
        );

        expect(result.is_anomaly).toBe(true);
        expect(result.catalyst_domain).toBe("refinery_pipeline");
        expect(result.affected_hub).toBe("Houston_TX");
        expect(result.direction).toBe("spike");
        expect(result.magnitude).toBe("critical");
        expect(result.confidence).toBe(0.94);
        expect(result.model).toContain("llama-3.2");
        expect(mockAi.run).toHaveBeenCalled();
      });

      it("classifies non-energy macroeconomic trade discussions as noise", async () => {
        const mockAi = {
          run: vi.fn().mockResolvedValue({
            response: JSON.stringify({
              is_anomaly: false,
              catalyst_domain: "noise",
              affected_hub: "None",
              direction: "neutral",
              magnitude: "low",
              half_life_days: 0.0,
              confidence: 0.98,
              reasoning: "Timber and soft lumber tariff debate without fuel implications"
            })
          })
        };

        const result = await scoreHeadlineAtEdge(
          "Senate debate intensifies over softwood lumber tariffs",
          { AI: mockAi }
        );

        expect(result.is_anomaly).toBe(false);
        expect(result.catalyst_domain).toBe("noise");
        expect(result.direction).toBe("neutral");
      });

      it("falls back to deterministic regex heuristic when AI is unconfigured or times out", async () => {
        // 1. Unconfigured AI
        const fallbackRes = await scoreHeadlineAtEdge(
          "Colonial Pipeline outage shuts Line 1 gasoline transmission",
          {}
        );
        expect(fallbackRes.is_anomaly).toBe(true);
        expect(fallbackRes.catalyst_domain).toBe("refinery_pipeline");
        expect(fallbackRes.model).toBe("regex_heuristic_fallback");

        // 2. Timeout simulation
        const slowAi = {
          run: vi.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 200)))
        };
        const timeoutRes = await scoreHeadlineAtEdge(
          "Hurricane threatens Gulf of Mexico offshore platforms",
          { AI: slowAi },
          50 // 50ms timeout
        );
        expect(timeoutRes.is_anomaly).toBe(true);
        expect(timeoutRes.catalyst_domain).toBe("weather_hurricane");
        expect(timeoutRes.model).toBe("regex_heuristic_fallback");
      });

      it("correctly identifies noise commodities via regex fallback", () => {
        const noiseRes = fallbackRegexScore("Soybean and canola cooking oil prices drop across Midwest grocery stores");
        expect(noiseRes.is_anomaly).toBe(false);
        expect(noiseRes.catalyst_domain).toBe("noise");
      });
    });

    describe("Vectorize Dense Embedding & Semantic Deduplication", () => {
      it("computes 384-dimensional dense vector embeddings", async () => {
        const mockAi = {
          run: vi.fn().mockResolvedValue({
            shape: [1, 384],
            data: [new Array(384).fill(0.05)]
          })
        };

        const embedding = await getHeadlineEmbedding("Colonial Pipeline outage", { AI: mockAi });
        expect(embedding).toHaveLength(384);
        expect(embedding?.[0]).toBe(0.05);
      });

      it("suppresses redundant events when Vectorize cosine similarity >= 0.88", async () => {
        const mockIndex = {
          query: vi.fn().mockResolvedValue({
            matches: [
              {
                id: "vec-123",
                score: 0.93,
                metadata: { headline: "Colonial Pipeline shuts Line 1 after leak" }
              }
            ]
          }),
          insert: vi.fn()
        };

        const res = await querySemanticDedupe(
          "Colonial Pipeline Line 1 closed due to pipeline spill",
          { EVENT_INDEX: mockIndex },
          { embedding: new Array(384).fill(0.01) }
        );

        expect(res.status).toBe("duplicate");
        expect(res.similarity).toBe(0.93);
        expect(res.source).toBe("vectorize");
        expect(res.matched_id).toBe("vec-123");
      });

      it("flags evolving incident status when Vectorize similarity is in [0.70, 0.88)", async () => {
        const mockIndex = {
          query: vi.fn().mockResolvedValue({
            matches: [
              {
                id: "vec-flaring-456",
                score: 0.77,
                metadata: { headline: "Port Arthur refinery reports flaring" }
              }
            ]
          }),
          insert: vi.fn()
        };

        const res = await querySemanticDedupe(
          "Port Arthur refinery initiates full unit shutdown following flaring",
          { EVENT_INDEX: mockIndex },
          { embedding: new Array(384).fill(0.01) }
        );

        expect(res.status).toBe("evolving");
        expect(res.similarity).toBe(0.77);
        expect(res.source).toBe("vectorize");
        expect(res.matched_id).toBe("vec-flaring-456");
      });

      it("marks event as novel and inserts into Vectorize when similarity < 0.70", async () => {
        const mockIndex = {
          query: vi.fn().mockResolvedValue({
            matches: [
              {
                id: "vec-old",
                score: 0.42,
                metadata: { headline: "Denver airport jet fuel deliveries normal" }
              }
            ]
          }),
          insert: vi.fn().mockResolvedValue({ count: 1 })
        };

        const res = await querySemanticDedupe(
          "Major refinery fire reported at Joliet refinery",
          { EVENT_INDEX: mockIndex },
          { embedding: new Array(384).fill(0.01) }
        );

        expect(res.status).toBe("novel");
        expect(res.source).toBe("none");

        const inserted = await indexHeadlineVector(
          "Major refinery fire reported at Joliet refinery",
          new Array(384).fill(0.01),
          { domain: "refinery_pipeline" },
          { EVENT_INDEX: mockIndex }
        );
        expect(inserted).toBe(true);
        expect(mockIndex.insert).toHaveBeenCalled();
      });
    });

    describe("Cross-Environment Hindsight Memory Bank (midgley-event-dedupe)", () => {
      const originalFetch = globalThis.fetch;

      afterEach(() => {
        globalThis.fetch = originalFetch;
      });

      it("recalls prior memories from Hindsight SaaS when Vectorize is empty", async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          json: async () => ({
            results: [
              {
                document_id: "hs-doc-999",
                score: 0.91,
                text: "Joliet refinery CDU shutdown due to power failure",
                entities: ["Joliet"]
              }
            ]
          })
        } as any);

        const env = {
          HINDSIGHT_API_TOKEN: "mock_hindsight_key",
          HINDSIGHT_DEDUPE_BANK_ID: "midgley-event-dedupe"
        };

        const hsRes = await queryHindsightBank(
          "Power failure forces Joliet refinery CDU unit offline",
          env
        );

        expect(hsRes.matched).toBe(true);
        expect(hsRes.similarity).toBe(0.91);
        expect(hsRes.docId).toBe("hs-doc-999");
      });

      it("retains confirmed anomalies into Hindsight midgley-event-dedupe with entity extraction", async () => {
        let sentBody: any = null;
        globalThis.fetch = vi.fn().mockImplementation((url, opts) => {
          sentBody = JSON.parse(opts.body);
          return Promise.resolve({
            ok: true,
            status: 201,
            json: async () => ({ success: true })
          });
        });

        const env = {
          HINDSIGHT_API_TOKEN: "mock_hindsight_key",
          HINDSIGHT_DEDUPE_BANK_ID: "midgley-event-dedupe"
        };

        const retained = await retainHindsightMemory(
          {
            headline: "ExxonMobil Baytown refinery unit tripped after severe storm",
            url: "https://example.com/baytown-trip",
            source: "TestFeed",
            magnitude: "high",
            locales: ["Houston_TX"]
          },
          env
        );

        expect(retained).toBe(true);
        expect(sentBody).toBeDefined();
        expect(sentBody.items[0].entities[0].text).toBe("Baytown");
        expect(sentBody.items[0].tags).toContain("edge_worker");
      });

      it("extracts recognized physical facilities and operators reliably", () => {
        expect(extractMatchedEntityAtEdge("Fire reported at Joliet refinery unit")).toBe("Joliet");
        expect(extractMatchedEntityAtEdge("Colonial pipeline shutdown after leak")).toBe("Colonial Pipeline");
        expect(extractMatchedEntityAtEdge("Valero reports mechanical failure")).toBe("Valero");
        expect(extractMatchedEntityAtEdge("General interest article")).toBeNull();
      });
    });

    describe("Grounded Institutional Analyst Briefing Synthesis", () => {
      it("synthesizes grounded institutional briefs via Workers AI", async () => {
        const mockAi = {
          run: vi.fn().mockResolvedValue({
            response: "Chicago spot gasoline margins widened +4.2¢/gal following Joliet CDU restart delays. Retail stations are expected to absorb wholesale spikes over a 4-day pass-through horizon."
          })
        };

        const brief = await synthesizeAnalystBrief(
          {
            hub_name: "Chicago (IL)",
            current_price: 3.450,
            predicted_shift: 0.085,
            direction: "UP",
            confidence_interval: [3.410, 3.590],
            active_catalysts: ["Joliet CDU restart delayed"]
          },
          { AI: mockAi }
        );

        expect(brief).toContain("Chicago spot gasoline margins");
        expect(mockAi.run).toHaveBeenCalled();
      });

      it("falls back to deterministic template when Workers AI is unconfigured or times out", async () => {
        const brief = await synthesizeAnalystBrief(
          {
            hub_name: "Denver (CO)",
            current_price: 3.120,
            predicted_shift: -0.045,
            direction: "DOWN",
            confidence_interval: [3.050, 3.200]
          },
          {}
        );

        expect(brief).toContain("Denver (CO) fuel forecast projects a DOWN trajectory");
        expect(brief).toContain("-0.045 $/gal");
      });
    });

    describe("Queue Consumer Integration with Edge Deduplication & Scoring", () => {
      const originalFetch = globalThis.fetch;

      beforeEach(() => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          status: 204,
          json: async () => ({})
        });
      });

      afterEach(() => {
        globalThis.fetch = originalFetch;
      });

      it("suppresses queue batch dispatch when semantic deduplication finds an exact duplicate", async () => {
        const ackSpy = vi.fn();
        const retrySpy = vi.fn();
        const mockDb = createMockD1Database();

        const mockIndex = {
          query: vi.fn().mockResolvedValue({
            matches: [{ id: "vec-dup-99", score: 0.95, metadata: { headline: "Existing refinery fire" } }]
          }),
          insert: vi.fn()
        };

        const batch: QueueMessageBatch = {
          queue: "intraday-events",
          messages: [
            {
              id: "msg-dup",
              timestamp: new Date(),
              body: {
                headline: "Existing refinery fire in Port Arthur",
                url: "https://example.com/port-arthur",
                source: "Test_Queue"
              },
              attempts: 1,
              ack: ackSpy,
              retry: retrySpy
            }
          ],
          ackAll: vi.fn(),
          retryAll: vi.fn()
        };

        const env: IntradayEnv = {
          GH_PAT: "mock_gh_pat_token",
          REPO_OWNER: "KoshiirRa",
          REPO_NAME: "midgley",
          DB: mockDb,
          EVENT_INDEX: mockIndex
        };

        const result = await handleQueueBatch(batch, env);
        expect(result.processed).toBe(1);
        expect(result.acked).toBe(1);
        expect(ackSpy).toHaveBeenCalled();
        expect(globalThis.fetch).not.toHaveBeenCalledWith(
          expect.stringContaining("dispatches"),
          expect.anything()
        );
      });

      it("suppresses queue batch dispatch when edge scoring classifies headline as noise", async () => {
        const ackSpy = vi.fn();
        const retrySpy = vi.fn();
        const mockDb = createMockD1Database();

        const mockAi = {
          run: vi.fn().mockResolvedValue({
            response: JSON.stringify({
              is_anomaly: false,
              catalyst_domain: "noise",
              affected_hub: "None",
              direction: "neutral",
              magnitude: "low",
              confidence: 0.99
            })
          })
        };

        const batch: QueueMessageBatch = {
          queue: "intraday-events",
          messages: [
            {
              id: "msg-noise",
              timestamp: new Date(),
              body: {
                headline: "Palm oil imports hit record in Southeast Asia",
                url: "https://example.com/palm-oil",
                source: "Test_Queue"
              },
              attempts: 1,
              ack: ackSpy,
              retry: retrySpy
            }
          ],
          ackAll: vi.fn(),
          retryAll: vi.fn()
        };

        const env: IntradayEnv = {
          GH_PAT: "mock_gh_pat_token",
          REPO_OWNER: "KoshiirRa",
          REPO_NAME: "midgley",
          DB: mockDb,
          AI: mockAi
        };

        const result = await handleQueueBatch(batch, env);
        expect(result.processed).toBe(1);
        expect(result.acked).toBe(1);
        expect(ackSpy).toHaveBeenCalled();
        expect(globalThis.fetch).not.toHaveBeenCalledWith(
          expect.stringContaining("dispatches"),
          expect.anything()
        );
      });
    });

    describe("Discord /midgley forecast Dynamic Briefing Integration", () => {
      it("includes the Institutional Analyst Brief field in /midgley forecast embed responses", async () => {
        const secretKey = nacl.sign.keyPair().secretKey;
        const publicKeyHex = uint8ArrayToHex(secretKey.slice(32));
        const timestamp = String(Math.floor(Date.now() / 1000));

        const body = JSON.stringify({
          type: 2, // APPLICATION_COMMAND
          id: "interaction_forecast_brief",
          token: "mock_token_brief",
          user: { id: "test_trader_456", username: "quant_trader" },
          data: {
            name: "midgley",
            options: [
              {
                name: "forecast",
                type: 1,
                options: [
                  { name: "locale", value: "Chicago_IL" },
                  { name: "horizon", value: 5 }
                ]
              }
            ]
          }
        });

        const message = new TextEncoder().encode(timestamp + body);
        const signature = nacl.sign.detached(message, secretKey);
        const signatureHex = uint8ArrayToHex(signature);

        const req = new Request("https://worker.local/discord/interactions", {
          method: "POST",
          headers: {
            "X-Signature-Ed25519": signatureHex,
            "X-Signature-Timestamp": timestamp,
            "Content-Type": "application/json"
          },
          body
        });

        const mockAi = {
          run: vi.fn().mockResolvedValue({
            response: "Chicago wholesale basis widened due to pipeline maintenance. Expect localized retail price support through day 5."
          })
        };

        const env: IntradayEnv = {
          DISCORD_PUBLIC_KEY: publicKeyHex,
          AI: mockAi
        };

        const res = await handleDiscordInteraction(req, env, {});
        expect(res.status).toBe(200);
        const data = (await res.json()) as any;
        expect(data.type).toBe(4); // CHANNEL_MESSAGE_WITH_SOURCE
        const embed = data.data.embeds[0];
        expect(embed.title).toContain("Midgley 5D Forecast");

        const briefField = embed.fields.find((f: any) => f.name.includes("Institutional Analyst Brief"));
        expect(briefField).toBeDefined();
        expect(briefField.value).toContain("Chicago wholesale basis widened");
      });
    });
  });

  describe("EDGAR 8-K Feed Coverage & Edge Deduplication (Issue #644)", () => {
    beforeEach(() => {
      clearEdgarCacheForTesting();
      vi.restoreAllMocks();
    });

    afterEach(() => {
      clearEdgarCacheForTesting();
      vi.restoreAllMocks();
    });

    it("verifies operational relevance keyword gate detects outages, fires, upsets, and hurricanes", () => {
      expect(isEdgarRelevant("Unplanned FCC unit outage at refinery")).toBe(true);
      expect(isEdgarRelevant("Reports refinery flaring and process upset")).toBe(true);
      expect(isEdgarRelevant("Precautionary shutdown ahead of Gulf hurricane")).toBe(true);
      expect(isEdgarRelevant("Force majeure declared on pipeline deliveries")).toBe(true);
      expect(isEdgarRelevant("Crude distillation unit fire contained")).toBe(true);

      // Noise rejection
      expect(isEdgarRelevant("Quarterly financial results for Q3 2026")).toBe(false);
      expect(isEdgarRelevant("Board of Directors appoints new Chief Commercial Officer")).toBe(false);
      expect(isEdgarRelevant("Pricing of $500M Senior Notes due 2036")).toBe(false);
    });

    it("deduplicates accession IDs in memory and via D1 edgar_8k_seen table", async () => {
      const mockD1 = createMockD1Database();
      const env: IntradayEnv = { DB: mockD1 };

      const accessionId = "0001193125-26-098765";
      expect(await isEdgar8kSeen(accessionId, env)).toBe(false);

      await markEdgar8kSeen(accessionId, "SU", "2026-10-24T12:00:00Z", env);
      expect(await isEdgar8kSeen(accessionId, env)).toBe(true);
      expect(await isEdgar8kSeen(`edgar:${accessionId}`, env)).toBe(true);
    });

    it("handles ETag conditional GETs and skips body parsing on 304 Not Modified", async () => {
      const mockD1 = createMockD1Database();
      const env: IntradayEnv = {
        DB: mockD1,
        EDGAR_8K_TICKERS: "SU",
        SEC_USER_AGENT: "Midgley energy-forecasting contact@domain.com"
      };

      // Populate cached ETag
      await setEdgarFeedCache("SU", { etag: '"test-etag-12345"' }, env);

      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        new Response(null, {
          status: 304,
          statusText: "Not Modified"
        })
      );

      await pollEdgar8KFeeds(env, {});
      expect(fetchSpy).toHaveBeenCalled();
      const calledHeaders = fetchSpy.mock.calls[0][1]?.headers as Record<string, string>;
      expect(calledHeaders["If-None-Match"]).toBe('"test-etag-12345"');
    });

    it("pre-filters XML entries on title keywords and enqueues relevant filings", async () => {
      const mockD1 = createMockD1Database();
      const sentQueueMessages: any[] = [];
      const env: IntradayEnv = {
        DB: mockD1,
        EDGAR_8K_TICKERS: "PARR",
        SEC_USER_AGENT: "Midgley energy-forecasting contact@domain.com",
        INTRADAY_QUEUE: {
          async send(msg: any) {
            sentQueueMessages.push(msg);
          },
          async sendBatch(msgs: any[]) {
            sentQueueMessages.push(...msgs.map(m => m.body));
          }
        }
      };

      const syntheticXml = `<?xml version="1.0" encoding="utf-8"?>
      <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Par Pacific 8-K Feed</title>
        <entry>
          <id>0001193125-26-000001</id>
          <title>Quarterly Earnings Release Q3</title>
          <link href="https://www.sec.gov/Archives/edgar/data/parr/earnings.htm"/>
          <updated>2026-10-24T10:00:00Z</updated>
        </entry>
        <entry>
          <id>0001193125-26-000002</id>
          <title>Crude distillation unit outage at Kapolei refinery</title>
          <link href="https://www.sec.gov/Archives/edgar/data/parr/outage.htm"/>
          <updated>2026-10-24T11:00:00Z</updated>
        </entry>
      </feed>`;

      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        new Response(syntheticXml, {
          status: 200,
          headers: {
            "Content-Type": "application/atom+xml",
            "ETag": '"etag-parr-999"'
          }
        })
      );

      await pollEdgar8KFeeds(env, {});

      // Earnings noise entry should NOT be enqueued; relevant Kapolei outage entry MUST be enqueued
      expect(sentQueueMessages.length).toBe(1);
      expect(sentQueueMessages[0].headline).toBe("PARR 8-K: Crude distillation unit outage at Kapolei refinery");
      expect(sentQueueMessages[0].url).toBe("https://www.sec.gov/Archives/edgar/data/parr/outage.htm");
      expect(sentQueueMessages[0].source).toBe("EDGAR_8K");

      // Verify that ETag was cached
      const cached = await getEdgarFeedCache("PARR", env);
      expect(cached.etag).toBe('"etag-parr-999"');

      // Verify that accession ID was marked seen in D1
      expect(await isEdgar8kSeen("0001193125-26-000002", env)).toBe(true);
    });
  });
});



