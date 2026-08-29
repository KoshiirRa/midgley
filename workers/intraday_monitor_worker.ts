/**
 * Cloudflare Worker Edge Trigger for 15-Minute Intraday Event Monitoring
 * (workers/intraday_monitor_worker.ts)
 *
 * Polls energy RSS feeds every 15 minutes, evaluates fast-path trigger keywords,
 * and sends GitHub Repository Dispatch events to main repository workflow.
 */

export interface Env {
  GH_PAT?: string;
  REPO_OWNER?: string;
  REPO_NAME?: string;
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

const TRIGGER_KEYWORDS = [
  "tariff", "retaliat", "trade war", "opec emergency", "pipeline halt",
  "explosion", "tornado", "blackout", "blockade", "sanction", "outage",
  "refinery outage", "refinery halt", "strait of hormuz", "red sea attack", "spill"
];

const TRIGGER_REGEX = new RegExp(
  `\\b(${TRIGGER_KEYWORDS.join("|")})\\b`,
  "i"
);

function parseRSSItems(xmlText: string): RSSItem[] {
  const items: RSSItem[] = [];
  const itemRegex = /<(?:item|entry)[\s\S]*?<\/(?:item|entry)>/gi;
  const itemMatches = xmlText.match(itemRegex) || [];

  for (const itemXml of itemMatches) {
    const titleMatch = itemXml.match(/<title>(?:<!\[CDATA\[([\s\S]*?)\]\]>|([\s\S]*?))<\/title>/i);
    let title = titleMatch ? (titleMatch[1] || titleMatch[2] || "").trim() : "";
    title = title
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'");

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
  return TRIGGER_REGEX.test(title);
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

export async function runMonitoringCycle(env: Env): Promise<CycleSummary> {
  let totalHeadlines = 0;
  const anomalies: RSSItem[] = [];
  const seenHeadlines = new Set<string>();

  for (const feedUrl of RSS_FEEDS) {
    try {
      const resp = await fetch(feedUrl, {
        headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Midgley-Worker/1.0" }
      });
      if (!resp.ok) continue;

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
    } catch (e) {
      // Log or swallow feed error to continue processing other feeds
    }
  }

  const dispatches: DispatchResult[] = [];
  if (anomalies.length > 0) {
    // Send 1 dispatch for the primary anomaly detected in this cycle to avoid launching multiple parallel GitHub Action runs that cancel each other
    const primary = anomalies[0];
    const res = await dispatchGitHubEvent(env, primary.title, primary.link);
    dispatches.push(res);
  }

  return {
    status: "success",
    timestamp: new Date().toISOString(),
    feeds_scanned: RSS_FEEDS.length,
    headlines_parsed: totalHeadlines,
    anomalies_detected: anomalies.length,
    dispatches
  };
}

export default {
  async scheduled(controller: any, env: Env, ctx: any): Promise<void> {
    ctx.waitUntil(runMonitoringCycle(env));
  },

  async fetch(request: Request, env: Env, ctx: any): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/run" || url.pathname === "/trigger") {
      const summary = await runMonitoringCycle(env);
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
  }
};
