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
  Env as IntradayEnv,
  QueueMessageBatch
} from "../workers/intraday_monitor_worker";
import cacheWorker, { Env as CacheEnv } from "../workers/cache_worker";

function uint8ArrayToHex(arr: Uint8Array): string {
  return Array.from(arr)
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
}

function createMockD1Database() {
  const store = new Map<string, any>();
  return {
    store,
    prepare(query: string) {
      return {
        bind(...args: any[]) {
          return {
            async first() {
              const key = args[0];
              if (store.has(key)) {
                return store.get(key);
              }
              return null;
            },
            async run() {
              const key = args[0];
              const value = args[1] || "{}";
              store.set(key, { clean_key: key, value, created_at: new Date().toISOString() });
              return { success: true };
            }
          };
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

    it("filters out non-energy tariffs and unrelated outages", () => {
      expect(isAnomalyHeadline("Global IT airline outage causes major airport delays")).toBe(false);
      expect(isAnomalyHeadline("New steel tariff and aluminum tariff proposed by Congress")).toBe(false);
      expect(isAnomalyHeadline("Section 301 semiconductor tariff under congressional review")).toBe(false);
      expect(isAnomalyHeadline("Canola oil trade tariff sparks agricultural debates")).toBe(false);
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
    const req = new Request(
      `https://worker.local/flag?id=123&headline=${encodeURIComponent(maliciousHeadline)}&source=${encodeURIComponent(maliciousSource)}`,
      { method: "GET" }
    );

    const env: IntradayEnv = { GH_PAT: "test_token" };
    const res = await intradayWorker.fetch(req, env, {});
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).not.toContain("<script>alert('XSS')</script>");
    expect(html).toContain("&lt;script&gt;alert(&#039;XSS&#039;)&lt;/script&gt;");
    expect(html).not.toContain("<b onmouseover=alert(1)>");
    expect(html).toContain("&lt;b onmouseover=alert(1)&gt;Source&lt;/b&gt;");
  });

  it("rejects unauthenticated POST /flag submissions", async () => {
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
  });

  it("rejects unauthenticated requests to /run and /trigger when admin token is set", async () => {
    const req = new Request("https://worker.local/run", {
      method: "GET"
    });

    const env: IntradayEnv = {
      ADMIN_TOKEN: "admin_secret_token"
    };

    const res = await intradayWorker.fetch(req, env, {});
    expect(res.status).toBe(401);
  });
});
