/**
 * Cloudflare Worker Edge Trigger for 15-Minute Intraday Event Monitoring
 * (workers/intraday_monitor_worker.ts)
 *
 * Polls energy RSS feeds every 15 minutes, evaluates fast-path trigger keywords,
 * sends GitHub Repository Dispatch events, and exports trace/log telemetry to Axiom & Sentry.
 */

export interface Env {
  GH_PAT?: string;
  REPO_OWNER?: string;
  REPO_NAME?: string;
  SENTRY_DSN?: string;
  AXIOM_TOKEN?: string;
  AXIOM_DATASET?: string;
}

export interface RSSItem {
  title: string;
  link: string;
}

export interface DispatchResult {
  headline: string;
  url: string;
  dispatched: boolean;
  status?: number;
  error?: string;
}

export interface CycleSummary {
  status: string;
  timestamp: string;
  feeds_scanned: number;
  headlines_parsed: number;
  anomalies_detected: number;
  dispatches: DispatchResult[];
}

const RSS_FEEDS = [
  "https://news.google.com/rss/search?q=unleaded+gasoline+when:1d&hl=en-US&gl=US&ceid=US:en",
  "https://news.google.com/rss/search?q=refinery+outage+when:1d&hl=en-US&gl=US&ceid=US:en",
  "https://news.google.com/rss/search?q=oil+tariff+when:1d&hl=en-US&gl=US&ceid=US:en",
  "https://rss.nytimes.com/services/xml/rss/nyt/EnergyEnvironment.xml",
  "https://www.cnbc.com/id/19854911/device/rss/rss.html"
];

const EXCLUDE_KEYWORDS = [
  "wikipedia", "software outage", "airline outage", "it outage", "cloud outage", "gaming outage", "network outage"
];

const TRIGGER_KEYWORDS = [
  "tariff", "retaliat", "trade war", "opec emergency", "pipeline halt", "pipeline outage",
  "explosion", "tornado", "blackout", "blockade", "sanction",
  "refinery outage", "refinery halt", "power grid outage", "plant outage", "terminal outage",
  "strait of hormuz", "red sea attack", "spill"
];

const TRIGGER_REGEX = new RegExp(
  `\\b(${TRIGGER_KEYWORDS.join("|")})\\b`,
  "i"
);

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
    service: "midgley-intraday-monitor"
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
        "X-Sentry-Auth": `Sentry sentry_version=7, sentry_key=${key}, sentry_client=midgley-worker/1.0`,
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

function parseRSSItems(xmlText: string): RSSItem[] {
  const items: RSSItem[] = [];
  const itemRegex = /<(?:item|entry)[\s\S]*?<\/(?:item|entry)>/gi;
  const itemMatches = xmlText.match(itemRegex) || [];

  for (const itemXml of itemMatches) {
    const titleMatch = itemXml.match(/<title>(?:<!\[CDATA\[([\s\S]*?)\]\]>|([\s\S]*?))<\/title>/i);
    let title = titleMatch ? (titleMatch[1] || titleMatch[2] || "").trim() : "";
    title = title
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&amp;/g, "&");

    const linkMatch =
      itemXml.match(/<link(?:\s+href=["']([^"']+)["'])?[^>]*>(?:<!\[CDATA\[([\s\S]*?)\]\]>|([\s\S]*?))?<\/link>/i) ||
      itemXml.match(/<link>([^<]+)<\/link>/i);

    let link = "";
    if (linkMatch) {
      link = (linkMatch[1] || linkMatch[2] || linkMatch[3] || "").trim();
    }

    if (title) {
      items.push({ title, link });
    }
  }
  return items;
}

export function isAnomalyHeadline(title: string): boolean {
  const lower = title.toLowerCase();
  if (EXCLUDE_KEYWORDS.some(k => lower.includes(k))) {
    return false;
  }
  return TRIGGER_REGEX.test(title);
}

export async function isHeadlineDispatchedInCache(headline: string): Promise<boolean> {
  try {
    if (typeof caches === "undefined" || !caches.default) return false;
    const cleanKey = headline.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 80);
    const dummyUrl = `https://midgley-cache.internal/dispatched/${cleanKey}`;
    const req = new Request(dummyUrl);
    const cachedResp = await caches.default.match(req);
    const isHit = !!cachedResp;
    if (isHit) {
      console.log(`[Cache HIT] Headline already dispatched: "${cleanKey}"`);
    } else {
      console.log(`[Cache MISS] Headline not yet dispatched: "${cleanKey}"`);
    }
    return isHit;
  } catch (err: any) {
    console.warn(`[Cache ERROR] Failed checking edge cache for "${headline}": ${err.message || String(err)}`);
    return false;
  }
}

export async function markHeadlineDispatchedInCache(headline: string): Promise<void> {
  try {
    if (typeof caches === "undefined" || !caches.default) return;
    const cleanKey = headline.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 80);
    const dummyUrl = `https://midgley-cache.internal/dispatched/${cleanKey}`;
    const req = new Request(dummyUrl);
    const resp = new Response("dispatched", {
      headers: {
        "Cache-Control": "public, max-age=86400"
      }
    });
    await caches.default.put(req, resp);
    console.log(`[Cache STORE] Marked headline dispatched in edge cache: "${cleanKey}"`);
  } catch (err: any) {
    console.warn(`[Cache ERROR] Failed writing to edge cache for "${headline}": ${err.message || String(err)}`);
  }
}

async function dispatchGitHubEvent(env: Env, headline: string, url: string): Promise<DispatchResult> {
  const owner = env.REPO_OWNER || "KoshiirRa";
  const repo = env.REPO_NAME || "midgley";
  const token = env.GH_PAT;

  if (!token) {
    return {
      headline,
      url,
      dispatched: false,
      error: "GH_PAT secret not configured in Worker environment"
    };
  }

  const dispatchUrl = `https://api.github.com/repos/${owner}/${repo}/dispatches`;
  try {
    const resp = await fetch(dispatchUrl, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Midgley-Intraday-Cloudflare-Worker",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        event_type: "intraday_anomaly",
        client_payload: {
          headline,
          url,
          source: "Cloudflare_Worker"
        }
      })
    });

    return {
      headline,
      url,
      dispatched: resp.status === 204,
      status: resp.status,
      error: resp.status === 204 ? undefined : `GitHub API returned HTTP ${resp.status}`
    };
  } catch (err: any) {
    return {
      headline,
      url,
      dispatched: false,
      error: err.message || String(err)
    };
  }
}

export async function runMonitoringCycle(env: Env, ctx?: any): Promise<CycleSummary> {
  let totalHeadlines = 0;
  const anomalies: RSSItem[] = [];
  const seenHeadlines = new Set<string>();

  for (const feedUrl of RSS_FEEDS) {
    try {
      const resp = await fetch(feedUrl, {
        headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Midgley-Worker/1.0" }
      });
      if (!resp.ok) {
        console.warn(`[RSS Warning] HTTP ${resp.status} fetching feed: ${feedUrl}`);
        continue;
      }

      const xml = await resp.text();
      const items = parseRSSItems(xml);
      totalHeadlines += items.length;

      for (const item of items) {
        const key = item.title.toLowerCase();
        if (seenHeadlines.has(key)) continue;
        seenHeadlines.add(key);

        if (isAnomalyHeadline(item.title)) {
          anomalies.push(item);
        }
      }
    } catch (e: any) {
      console.error(`[RSS Feed Error] Failed fetching ${feedUrl}: ${e.message || String(e)}`);
      await captureSentryException(env, ctx, e, { feedUrl });
    }
  }

  const dispatches: DispatchResult[] = [];
  for (const anomaly of anomalies) {
    const alreadyDispatched = await isHeadlineDispatchedInCache(anomaly.title);
    if (alreadyDispatched) {
      continue;
    }

    const res = await dispatchGitHubEvent(env, anomaly.title, anomaly.link);
    if (res.dispatched) {
      console.log(`[GitHub Dispatch Success] Event dispatched for: "${anomaly.title}"`);
      await markHeadlineDispatchedInCache(anomaly.title);
    } else {
      console.error(`[GitHub Dispatch Failed] Error: ${res.error}`);
      await captureSentryException(env, ctx, new Error(res.error || "GitHub Dispatch Failed"), { anomalyTitle: anomaly.title });
    }
    dispatches.push(res);
    break; // Enforce single dispatch per 15-minute cycle
  }

  const summary: CycleSummary = {
    status: "success",
    timestamp: new Date().toISOString(),
    feeds_scanned: RSS_FEEDS.length,
    headlines_parsed: totalHeadlines,
    anomalies_detected: anomalies.length,
    dispatches
  };

  console.log(`[Cycle Summary] ${JSON.stringify(summary)}`);

  // Telemetry Ingestion to Axiom (Option A2)
  await logToAxiom(env, ctx, {
    event: "intraday_monitoring_cycle",
    ...summary
  });

  return summary;
}

export default {
  async scheduled(controller: any, env: Env, ctx: any): Promise<void> {
    try {
      ctx.waitUntil(runMonitoringCycle(env, ctx));
    } catch (err: any) {
      console.error(`[Scheduled Exception] ${err.message || String(err)}`);
      await captureSentryException(env, ctx, err, { trigger: "scheduled" });
    }
  },

  async fetch(request: Request, env: Env, ctx: any): Promise<Response> {
    const url = new URL(request.url);

    try {
      if (url.pathname === "/run" || url.pathname === "/trigger") {
        const summary = await runMonitoringCycle(env, ctx);
        return new Response(JSON.stringify(summary, null, 2), {
          headers: { "Content-Type": "application/json" }
        });
      }

      return new Response(
        JSON.stringify({
          status: "active",
          service: "midgley-intraday-monitor",
          timestamp: new Date().toISOString(),
          endpoints: ["/run", "/trigger", "/status"]
        }, null, 2),
        { headers: { "Content-Type": "application/json" } }
      );
    } catch (err: any) {
      console.error(`[Fetch Exception] ${err.message || String(err)}`);
      await captureSentryException(env, ctx, err, { pathname: url.pathname });
      return new Response(JSON.stringify({ error: err.message || String(err) }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  }
};
