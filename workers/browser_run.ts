/**
 * Cloudflare Browser Run & Rendering Unified Client (workers/browser_run.ts)
 * 
 * Provides a standardized utility to render dynamic web pages into clean Markdown
 * via Cloudflare Browser Run (https://developers.cloudflare.com/browser-run/)
 * using either:
 * 1. Cloudflare Workers Paid Browser Rendering binding (env.MYBROWSER)
 * 2. Cloudflare Browser Run REST API (/browser-run/markdown) fallback
 * 
 * Note: Never hardcodes account IDs or secret credentials.
 */

export interface BrowserRunOptions {
  url: string;
  userAgent?: string;
  timeoutMs?: number;
}

/**
 * Renders a given URL into Markdown using Cloudflare Browser Run.
 * Tries the native Worker binding first (env.MYBROWSER), and falls back
 * to the direct Cloudflare Browser Run REST API if credentials exist.
 *
 * Never uses hardcoded account IDs or credentials.
 */
export async function fetchMarkdownViaBrowserRun(
  env: any,
  options: BrowserRunOptions | string
): Promise<string | null> {
  const opts: BrowserRunOptions = typeof options === "string" ? { url: options } : options;
  const url = opts.url;
  const userAgent = opts.userAgent || env?.MIDGLEY_AGENT_USER_AGENT || "MidgleyAgent/1.0 (+https://koshiirra.github.io/midgley/)";

  if (!url) {
    return null;
  }

  // 1. Try Cloudflare Workers Browser Run binding (.quickAction)
  if (env?.MYBROWSER) {
    try {
      if (typeof env.MYBROWSER.quickAction === "function") {
        const response = await env.MYBROWSER.quickAction("markdown", {
          url: url,
          userAgent: userAgent
        });
        if (typeof response === "string" && response.length > 0) return response;
        if (response && typeof response.result === "string" && response.result.length > 0) return response.result;
        if (response && typeof response.text === "function") {
          const txt = await response.text();
          if (txt && txt.length > 0) return txt;
        }
      }

      if (typeof env.MYBROWSER.fetch === "function") {
        const req = new Request(url, {
          headers: { "User-Agent": userAgent }
        });
        const res = await env.MYBROWSER.fetch(req);
        if (res && res.status === 200) {
          const body = await res.text();
          if (body && body.length > 0) return body;
        }
      }
    } catch (err: any) {
      console.warn(`[Cloudflare Browser Run] Worker binding exception for ${url}: ${err.message || String(err)}`);
    }
  }

  // 2. Direct Cloudflare Browser Run REST API fallback (https://developers.cloudflare.com/browser-run/)
  const accountId = env?.CLOUDFLARE_ACCOUNT_ID || env?.ACCOUNT_ID;
  const apiToken = env?.CLOUDFLARE_API_TOKEN || env?.CLOUDFLARE_AUTH_TOKEN;

  if (accountId && apiToken) {
    try {
      const endpoint = `https://api.cloudflare.com/client/v4/accounts/${accountId}/browser-run/markdown`;
      const restRes = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiToken}`,
          "Content-Type": "application/json",
          "User-Agent": userAgent
        },
        body: JSON.stringify({ url: url })
      });

      if (restRes && restRes.status === 200) {
        const data: any = await restRes.json();
        if (data?.result && typeof data.result === "string" && data.result.length > 0) {
          return data.result;
        }
      } else {
        const status = restRes ? restRes.status : 0;
        console.warn(`[Cloudflare Browser Run REST] HTTP ${status} for ${url}`);
      }
    } catch (err: any) {
      console.warn(`[Cloudflare Browser Run REST] Exception for ${url}: ${err.message || String(err)}`);
    }
  } else {
    // Neither binding nor REST credentials available
    console.debug(`[Cloudflare Browser Run] No browser binding or REST credentials configured for ${url}`);
  }

  return null;
}
