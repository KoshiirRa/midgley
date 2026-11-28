import { describe, it, expect, vi } from "vitest";
import { buildWorkersAiGatewayOptions, runWorkersAi } from "../workers/ai_event_scorer";
import { resolveGeminiEndpointAndHeaders } from "../workers/sunday_review_planner";

describe("Cloudflare AI Gateway routing (Issue #764)", () => {
  it("returns undefined gateway options when unconfigured", () => {
    expect(buildWorkersAiGatewayOptions({})).toBeUndefined();
    expect(buildWorkersAiGatewayOptions(null)).toBeUndefined();
  });

  it("builds Workers AI gateway options with TTL and skipCache", () => {
    const opts = buildWorkersAiGatewayOptions({
      CF_AI_GATEWAY_ID: "midgley-ai-gateway",
      CF_AI_GATEWAY_CACHE_TTL: "1800",
      CF_AI_GATEWAY_SKIP_CACHE: "true",
    });
    expect(opts).toEqual({
      gateway: {
        id: "midgley-ai-gateway",
        cacheTtl: 1800,
        skipCache: true,
      },
    });
  });

  it("calls env.AI.run with 2 args when unconfigured and 3 args when gateway is configured", async () => {
    const runSpy = vi.fn().mockResolvedValue({ response: "ok" });
    await runWorkersAi({ AI: { run: runSpy } }, "@cf/meta/llama-3.2-3b-instruct", { prompt: "hi" });
    expect(runSpy).toHaveBeenCalledWith("@cf/meta/llama-3.2-3b-instruct", { prompt: "hi" });

    runSpy.mockClear();
    await runWorkersAi(
      { AI: { run: runSpy }, CF_AI_GATEWAY_ID: "midgley-gw" },
      "@cf/meta/llama-3.2-3b-instruct",
      { prompt: "hi" }
    );
    expect(runSpy).toHaveBeenCalledWith(
      "@cf/meta/llama-3.2-3b-instruct",
      { prompt: "hi" },
      { gateway: { id: "midgley-gw" } }
    );
  });

  it("resolves direct Gemini endpoint when AI Gateway is unconfigured", () => {
    const res = resolveGeminiEndpointAndHeaders({}, "gemini-2.5-flash", "api-key-123");
    expect(res.viaGateway).toBe(false);
    expect(res.endpoint).toBe(
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    );
    expect(res.headers).toEqual({
      "Content-Type": "application/json",
      "x-goog-api-key": "api-key-123",
    });
  });

  it("resolves Cloudflare AI Gateway Gemini endpoint and auth/cache headers", () => {
    const res = resolveGeminiEndpointAndHeaders(
      {
        CLOUDFLARE_ACCOUNT_ID: "acct123",
        CF_AI_GATEWAY_ID: "midgley-gw",
        CF_AI_GATEWAY_TOKEN: "gw-secret",
        CF_AI_GATEWAY_CACHE_TTL: "3600",
      },
      "gemini-2.5-flash",
      "api-key-123"
    );
    expect(res.viaGateway).toBe(true);
    expect(res.endpoint).toBe(
      "https://gateway.ai.cloudflare.com/v1/acct123/midgley-gw/google-ai-studio/v1beta/models/gemini-2.5-flash:generateContent"
    );
    expect(res.headers["cf-aig-authorization"]).toBe("Bearer gw-secret");
    expect(res.headers["cf-aig-cache-ttl"]).toBe("3600");
  });
});
