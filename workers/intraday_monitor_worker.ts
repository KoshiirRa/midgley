/**
 * Cloudflare Worker Edge Trigger for 15-Minute Intraday Event Monitoring
 * (workers/intraday_monitor_worker.ts)
 *
 * Polls energy RSS feeds every 15 minutes, evaluates fast-path trigger keywords,
 * sends GitHub Repository Dispatch events, and exports trace/log telemetry to Axiom & Sentry.
 */

import nacl from "tweetnacl";

export interface Env {
  GH_PAT?: string;
  REPO_OWNER?: string;
  REPO_NAME?: string;
  SENTRY_DSN?: string;
  AXIOM_TOKEN?: string;
  AXIOM_DATASET?: string;
  SEC_USER_AGENT?: string;
  EDGAR_8K_TICKERS?: string;
  DISCORD_PUBLIC_KEY?: string;
  DISCORD_APP_ID?: string;
  PROJECT_V2_ID?: string;
  DB?: any;
  INTRADAY_QUEUE?: {
    send(message: any, options?: any): Promise<void>;
    sendBatch(messages: { body: any }[], options?: any): Promise<void>;
  };
}

export interface QueueMessage<T = any> {
  id: string;
  timestamp: Date;
  body: T;
  attempts: number;
  ack(): void;
  retry(): void;
}

export interface QueueMessageBatch<T = any> {
  queue: string;
  messages: QueueMessage<T>[];
  ackAll(): void;
  retryAll(): void;
}

export interface QueueEventPayload {
  headline: string;
  url: string;
  source?: string;
  timestamp?: string;
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
  headlines?: string[];
  dispatches: DispatchResult[];
}

const RSS_FEEDS = [
  "https://news.google.com/rss/search?q=unleaded+gasoline+when:1d&hl=en-US&gl=US&ceid=US:en",
  "https://news.google.com/rss/search?q=refinery+outage+when:1d&hl=en-US&gl=US&ceid=US:en",
  "https://news.google.com/rss/search?q=oil+tariff+when:1d&hl=en-US&gl=US&ceid=US:en",
  "https://rss.nytimes.com/services/xml/rss/nyt/EnergyEnvironment.xml"
];

const EXCLUDE_KEYWORDS = [
  "wikipedia", "software outage", "airline outage", "it outage", "cloud outage", "gaming outage", "network outage",
  "canola", "cooking oil", "palm oil", "olive oil", "soybean oil"
];

const NON_ENERGY_TARIFF_EXCLUDES = [
  "house should not transfer", "tariff authority", "steel tariff", "aluminum tariff",
  "copper tariff", "lumber tariff", "auto tariff", "solar tariff", "washing machine",
  "semiconductor tariff", "chip tariff", "reciprocal trade act", "section 301", "section 232",
  "canola", "canola oil"
];

const TRIGGER_KEYWORDS = [
  "energy tariff", "oil tariff", "fuel tariff", "crude tariff", "gasoline tariff", "retaliatory tariff", "counter-tariff",
  "retaliat", "trade war", "opec emergency", "pipeline halt", "pipeline outage",
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

/**
 * Sentry Cron Check-In Helper (Option A2)
 */
export async function sendSentryCronCheckIn(
  env: Env,
  ctx: any,
  status: "ok" | "in_progress" | "error" = "ok",
  checkInId?: string,
  monitorSlug?: string
): Promise<string> {
  const dsn = env.SENTRY_DSN;
  const slug = monitorSlug || (env as any).SENTRY_CRON_SLUG || "midgley-intraday-monitor";
  if (!dsn) return "";

  try {
    const match = dsn.match(/^https:\/\/([^@]+)@([^/]+)\/(\d+)$/);
    if (!match) return "";

    const [, key, host, projectId] = match;
    const event_id = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID().replace(/-/g, "") : String(Date.now());
    const id = checkInId || (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID().replace(/-/g, "") : String(Date.now()));

    const header = JSON.stringify({ event_id, dsn });
    const item_header = JSON.stringify({ type: "check_in" });
    const item_payload = JSON.stringify({
      check_in_id: id,
      monitor_slug: slug,
      status
    });

    const envelope = `${header}\n${item_header}\n${item_payload}\n`;
    const storeUrl = `https://${host}/api/${projectId}/envelope/`;

    const p = fetch(storeUrl, {
      method: "POST",
      headers: {
        "X-Sentry-Auth": `Sentry sentry_version=7, sentry_key=${key}`,
        "Content-Type": "application/x-sentry-envelope"
      },
      body: envelope
    }).catch(e => console.warn(`[Sentry Cron Error] ${e.message || String(e)}`));

    if (ctx && typeof ctx.waitUntil === "function") {
      ctx.waitUntil(p);
    } else {
      await p;
    }
    return id;
  } catch {
    return "";
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

export function normalizeHeadline(title: string): string {
  if (!title) return "";
  // Strip trailing publisher attribution tag: " - Publisher", " | Publisher", " — Publisher"
  let cleaned = title.replace(/\s+[-–—|]\s+[^-–—|]+$/, "").trim();
  // Lowercase and strip non-alphanumeric for clean hashing key
  return cleaned.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 80);
}

export function isAnomalyHeadline(title: string): boolean {
  const lower = title.toLowerCase();
  if (EXCLUDE_KEYWORDS.some(k => lower.includes(k))) {
    return false;
  }
  if (NON_ENERGY_TARIFF_EXCLUDES.some(k => lower.includes(k))) {
    return false;
  }
  if (TRIGGER_REGEX.test(title)) {
    return true;
  }
  // Check if headline mentions tariff/tariffs alongside energy context
  if (/\btariffs?\b/i.test(title)) {
    const hasEnergyContext = /(?:oil|crude|gasoline|fuel|petroleum|refin|diesel|energy|opec)/i.test(title);
    return hasEnergyContext;
  }
  return false;
}

export async function isHeadlineDispatchedInCache(headline: string, env?: Env): Promise<boolean> {
  const cleanKey = normalizeHeadline(headline);
  if (!cleanKey) return false;

  // 1. Check D1 Persistent Database if available
  if (env && env.DB) {
    try {
      const stmt = env.DB.prepare(
        "SELECT 1 FROM seen_rss_headlines WHERE clean_key = ? AND datetime(created_at, '+24 hours') > datetime('now') LIMIT 1"
      );
      const row = await stmt.bind(cleanKey).first();
      if (row) {
        console.log(`[D1 HIT] Headline already dispatched: "${cleanKey}"`);
        return true;
      }
    } catch (d1Err: any) {
      try {
        await env.DB.prepare(
          "CREATE TABLE IF NOT EXISTS seen_rss_headlines (clean_key TEXT PRIMARY KEY, raw_headline TEXT, created_at TEXT NOT NULL)"
        ).run();
      } catch {
        // Ignore fallback
      }
      console.warn(`[D1 Query Warning] ${d1Err?.message || String(d1Err)}`);
    }
  }

  // 2. Check local Edge Cache (caches.default) fallback
  try {
    if (typeof caches === "undefined" || !caches.default) return false;
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

export async function markHeadlineDispatchedInCache(headline: string, env?: Env): Promise<void> {
  const cleanKey = normalizeHeadline(headline);
  if (!cleanKey) return;

  // 1. Store in D1 Persistent Database if available
  if (env && env.DB) {
    try {
      await env.DB.prepare(
        "INSERT OR REPLACE INTO seen_rss_headlines (clean_key, raw_headline, created_at) VALUES (?, ?, datetime('now'))"
      ).bind(cleanKey, headline).run();
      console.log(`[D1 STORE] Marked headline dispatched in D1: "${cleanKey}"`);
    } catch (d1Err: any) {
      try {
        await env.DB.prepare(
          "CREATE TABLE IF NOT EXISTS seen_rss_headlines (clean_key TEXT PRIMARY KEY, raw_headline TEXT, created_at TEXT NOT NULL)"
        ).run();
        await env.DB.prepare(
          "INSERT OR REPLACE INTO seen_rss_headlines (clean_key, raw_headline, created_at) VALUES (?, ?, datetime('now'))"
        ).bind(cleanKey, headline).run();
      } catch {
        // ignore
      }
    }
  }

  // 2. Also write to Edge Cache
  try {
    if (typeof caches === "undefined" || !caches.default) return;
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
      error: "Internal Server Error"
    };
  }
}

export async function enqueueIntradayEvent(
  env: Env,
  ctx: any,
  payload: QueueEventPayload
): Promise<boolean> {
  if (!env.INTRADAY_QUEUE) return false;
  try {
    await env.INTRADAY_QUEUE.send({
      ...payload,
      timestamp: payload.timestamp || new Date().toISOString()
    });
    console.log(`[Queue Enqueue Success] Enqueued event for: "${payload.headline}"`);
    await logToAxiom(env, ctx, {
      event: "intraday_queue_enqueue",
      headline: payload.headline,
      url: payload.url
    });
    return true;
  } catch (err: any) {
    console.error(`[Queue Enqueue Error] ${err.message || String(err)}`);
    await captureSentryException(env, ctx, err, { headline: payload.headline });
    return false;
  }
}

export async function handleQueueBatch(
  batch: QueueMessageBatch<QueueEventPayload>,
  env: Env,
  ctx?: any
): Promise<{ processed: number; acked: number; retried: number }> {
  console.log(`[Queue Consumer Batch] Processing ${batch.messages.length} messages from queue "${batch.queue}"`);

  let processed = 0;
  let acked = 0;
  let retried = 0;

  for (const message of batch.messages) {
    processed++;
    const { headline, url } = message.body || {};
    if (!headline) {
      message.ack();
      acked++;
      continue;
    }

    try {
      const alreadyDispatched = await isHeadlineDispatchedInCache(headline, env);
      if (alreadyDispatched) {
        console.log(`[Queue Consumer Cache HIT] Skipping already dispatched event: "${headline}"`);
        message.ack();
        acked++;
        continue;
      }

      const res = await dispatchGitHubEvent(env, headline, url);
      if (res.dispatched) {
        console.log(`[Queue Consumer Dispatch Success] Event dispatched for: "${headline}"`);
        await markHeadlineDispatchedInCache(headline, env);
        message.ack();
        acked++;
      } else {
        console.error(`[Queue Consumer Dispatch Failed] Error: ${res.error}`);
        await captureSentryException(env, ctx, new Error(res.error || "Queue Consumer Dispatch Failed"), { headline });
        message.retry();
        retried++;
      }
    } catch (err: any) {
      console.error(`[Queue Consumer Exception] ${err.message || String(err)}`);
      await captureSentryException(env, ctx, err, { headline });
      message.retry();
      retried++;
    }
  }

  await logToAxiom(env, ctx, {
    event: "intraday_queue_batch_processed",
    total: batch.messages.length,
    processed,
    acked,
    retried
  });

  return { processed, acked, retried };
}

/**
 * EDGAR 8-K Refinery Operator Monitor (Issue #129)
 * Polls EDGAR ATOM RSS feeds for new 8-K filings from target refinery operators,
 * deduplicates via D1 edgar_8k_seen table, keyword-filters for operational relevance,
 * and enqueues relevant filings to INTRADAY_QUEUE for origin scoring.
 *
 * D1 Schema (apply once to midgley-cache-d1):
 *   CREATE TABLE IF NOT EXISTS edgar_8k_seen (
 *     accession_id TEXT PRIMARY KEY,
 *     ticker       TEXT NOT NULL,
 *     filed_at     TEXT NOT NULL
 *   );
 */

const EDGAR_OPERATIONAL_KEYWORDS: string[] = [
  "outage", "force majeure", "fire", "explosion", "unplanned",
  "shutdown", "capacity reduction", "turnaround", "fcc",
  "crude distillation", "hydrocracker", "coker", "refinery",
  "pipeline", "leak", "spill", "environmental", "flaring",
  "evacuation", "accident", "incident", "disruption",
];

function isEdgarRelevant(text: string): boolean {
  const lower = text.toLowerCase();
  return EDGAR_OPERATIONAL_KEYWORDS.some(kw => lower.includes(kw));
}

async function pollEdgar8KFeeds(env: Env, ctx: any): Promise<void> {
  const tickers = (env.EDGAR_8K_TICKERS ?? "PBF,DINO,MPC,VLO,PSX")
    .split(",")
    .map(t => t.trim().toUpperCase())
    .filter(Boolean);

  const userAgent = env.SEC_USER_AGENT ?? "Midgley contact@example.com";

  for (const ticker of tickers) {
    try {
      const atomUrl =
        `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany` +
        `&CIK=${ticker}&type=8-K&dateb=&owner=include&count=5&search_text=&output=atom`;

      const resp = await fetch(atomUrl, { headers: { "User-Agent": userAgent } });
      if (!resp.ok) {
        console.warn(`[EDGAR8K] HTTP ${resp.status} fetching feed for ${ticker}`);
        continue;
      }

      const xmlText = await resp.text();

      // Parse ATOM entries via simple regex (no DOM parser in Workers)
      const entryRegex = /<entry[\s\S]*?<\/entry>/gi;
      const idRegex = /<id>([^<]+)<\/id>/i;
      const titleRegex = /<title[^>]*>([^<]+)<\/title>/i;
      const linkRegex = /<link[^>]+href="([^"]+)"/i;
      const updatedRegex = /<updated>([^<]+)<\/updated>/i;

      const entries = xmlText.match(entryRegex) || [];

      for (const entryXml of entries) {
        const accessionId = (entryXml.match(idRegex)?.[1] ?? "").trim();
        const title = (entryXml.match(titleRegex)?.[1] ?? "").trim();
        const link = (entryXml.match(linkRegex)?.[1] ?? "").trim();
        const filedAt = (entryXml.match(updatedRegex)?.[1] ?? new Date().toISOString()).trim();

        if (!accessionId || !title) continue;

        // D1 deduplication — skip if already seen
        // Note: D1 binding available via env when [[d1_databases]] edgar_8k_seen table exists
        // Fallback: use in-memory seen set per invocation if D1 unavailable
        const alreadyDispatched = await isHeadlineDispatchedInCache(`edgar:${accessionId}`, env);
        if (alreadyDispatched) continue;

        // Keyword gate on title first (saves HTML fetch round-trip for obvious noise)
        if (!isEdgarRelevant(title)) {
          // Mark noise filing as seen so we don't re-check it next cycle
          await markHeadlineDispatchedInCache(`edgar:${accessionId}`, env);
          continue;
        }

        // Enqueue to INTRADAY_QUEUE using existing WebhookRequest-compatible schema
        const headline = `${ticker} 8-K: ${title}`;
        const enqueued = await enqueueIntradayEvent(env, ctx, {
          headline,
          url: link,
          source: "EDGAR_8K",
        });

        if (enqueued) {
          await markHeadlineDispatchedInCache(`edgar:${accessionId}`, env);
          console.log(`[EDGAR8K] Enqueued relevant 8-K: ${headline}`);
          await logToAxiom(env, ctx, {
            event: "edgar_8k_enqueued",
            ticker,
            headline,
            accession_id: accessionId,
            filed_at: filedAt,
          });
        }
      }
    } catch (err: any) {
      console.error(`[EDGAR8K] Error polling ${ticker}: ${err.message || String(err)}`);
      await captureSentryException(env, ctx, err, { ticker, context: "pollEdgar8KFeeds" });
    }
  }
}

export async function runMonitoringCycle(env: Env, ctx?: any): Promise<CycleSummary> {
  const checkInId1 = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID().replace(/-/g, "") : String(Date.now());
  const checkInId2 = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID().replace(/-/g, "") : String(Date.now());

  // 1. Send Sentry Cron Check-In (in_progress at start)
  await sendSentryCronCheckIn(env, ctx, "in_progress", checkInId1);
  await sendSentryCronCheckIn(env, ctx, "in_progress", checkInId2, "new-monitor");

  let totalHeadlines = 0;
  const anomalies: RSSItem[] = [];
  const parsedHeadlines: string[] = [];
  const seenHeadlines = new Set<string>();

  try {
    for (const feedUrl of RSS_FEEDS) {
      try {
        const fetchHeaders = {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
          "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
          "Accept-Language": "en-US,en;q=0.9",
          "Cache-Control": "max-age=0"
        };

        let resp = await fetch(feedUrl, { headers: fetchHeaders });

        // Retry once on transient 503 or 429 rate-limiting with randomized backoff jitter
        if (resp.status === 503 || resp.status === 429) {
          const jitterMs = 500 + Math.floor(Math.random() * 500);
          console.warn(`[RSS Retry] HTTP ${resp.status} on ${feedUrl}, retrying once after ${jitterMs}ms backoff...`);
          await new Promise(r => setTimeout(r, jitterMs));
          resp = await fetch(feedUrl, { headers: fetchHeaders });
        }

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
          parsedHeadlines.push(item.title);

          if (isAnomalyHeadline(item.title)) {
            anomalies.push(item);
          }
        }
      } catch (e: any) {
        console.warn(`[RSS Feed Warning] Failed fetching ${feedUrl}: ${e.message || String(e)}`);
      }
    }

    // EDGAR 8-K Refinery Operator Monitor pass (Issue #129)
    await pollEdgar8KFeeds(env, ctx);

    const dispatches: DispatchResult[] = [];
    for (const anomaly of anomalies) {
      const alreadyDispatched = await isHeadlineDispatchedInCache(anomaly.title, env);
      if (alreadyDispatched) {
        continue;
      }

      if (env.INTRADAY_QUEUE) {
        const enqueued = await enqueueIntradayEvent(env, ctx, {
          headline: anomaly.title,
          url: anomaly.link,
          source: "Cloudflare_Worker_Queue"
        });
        if (enqueued) {
          await markHeadlineDispatchedInCache(anomaly.title, env);
          dispatches.push({
            headline: anomaly.title,
            url: anomaly.link,
            dispatched: true
          });
          break; // Enforce single dispatch per 15-minute cycle
        }
      }

      // Direct fallback dispatch if INTRADAY_QUEUE is absent or enqueue failed
      const res = await dispatchGitHubEvent(env, anomaly.title, anomaly.link);
      if (res.dispatched) {
        console.log(`[GitHub Dispatch Success] Event dispatched for: "${anomaly.title}"`);
        await markHeadlineDispatchedInCache(anomaly.title, env);
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
      headlines: parsedHeadlines,
      dispatches
    };

    console.log(`[Cycle Summary] ${JSON.stringify(summary)}`);

    // Telemetry Ingestion to Axiom (Option A2)
    await logToAxiom(env, ctx, {
      event: "intraday_monitoring_cycle",
      ...summary
    });

    // 2. Send Sentry Cron Check-In (ok at completion with matching ID)
    await sendSentryCronCheckIn(env, ctx, "ok", checkInId1);
    await sendSentryCronCheckIn(env, ctx, "ok", checkInId2, "new-monitor");

    return summary;
  } catch (err: any) {
    // Send Sentry Cron Check-In (error at failure with matching ID)
    await sendSentryCronCheckIn(env, ctx, "error", checkInId1);
    await sendSentryCronCheckIn(env, ctx, "error", checkInId2, "new-monitor");
    throw err;
  }
}

const DEFAULT_DISCORD_PUBLIC_KEY = "23fd56cafbd2e02e99e228ef545bb7a350719b086537410ba5ce092170e56e9b";
const DEFAULT_PROJECT_V2_ID = "PVT_kwHOAVnZGM4BhxKn";

function hexToUint8Array(hex: string): Uint8Array {
  const match = hex.match(/.{1,2}/g);
  return new Uint8Array(match ? match.map(byte => parseInt(byte, 16)) : []);
}

function verifyDiscordSignature(
  publicKeyHex: string,
  signatureHex: string,
  timestamp: string,
  body: string
): boolean {
  try {
    const rawKey = hexToUint8Array(publicKeyHex);
    const signature = hexToUint8Array(signatureHex);
    const data = new TextEncoder().encode(timestamp + body);

    return nacl.sign.detached.verify(data, signature, rawKey);
  } catch (err) {
    console.error("[Discord Signature Verification Error]", err);
    return false;
  }
}

async function handleDiscordInteraction(request: Request, env: Env, ctx: any): Promise<Response> {
  const signature = request.headers.get("X-Signature-Ed25519");
  const timestamp = request.headers.get("X-Signature-Timestamp");

  if (!signature || !timestamp) {
    return new Response("Missing signature headers", { status: 401 });
  }

  const bodyText = await request.text();
  const publicKey = env.DISCORD_PUBLIC_KEY || DEFAULT_DISCORD_PUBLIC_KEY;

  const isValid = await verifyDiscordSignature(publicKey, signature, timestamp, bodyText);
  if (!isValid) {
    return new Response("Invalid request signature", { status: 401 });
  }

  let interaction: any;
  try {
    interaction = JSON.parse(bodyText);
  } catch {
    return new Response("Invalid JSON payload", { status: 400 });
  }

  // Type 1: PING -> Respond with PONG
  if (interaction.type === 1) {
    return new Response(JSON.stringify({ type: 1 }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  // Type 3: MESSAGE_COMPONENT (User clicked "🚩 Flag False Positive" button)
  if (interaction.type === 3) {
    const customId = interaction.data?.custom_id || "";
    if (customId.startsWith("flag_fp:")) {
      const eventHash = customId.replace("flag_fp:", "");

      // Return Discord Modal (Type 9)
      const modalResponse = {
        type: 9,
        data: {
          title: "Flag False Positive Anomaly",
          custom_id: `modal_flag_fp:${eventHash}`,
          components: [
            {
              type: 1,
              components: [
                {
                  type: 4,
                  custom_id: "category",
                  label: "False Positive Category",
                  style: 1,
                  min_length: 3,
                  max_length: 100,
                  placeholder: "e.g., Non-Energy Tariff, Agricultural Oil, Geopolitical Noise",
                  required: true
                }
              ]
            },
            {
              type: 1,
              components: [
                {
                  type: 4,
                  custom_id: "notes",
                  label: "Context / Reason for Review",
                  style: 2,
                  min_length: 3,
                  max_length: 1000,
                  placeholder: "Explain why this headline is unrelated to crude oil or RBOB price impact...",
                  required: false
                }
              ]
            }
          ]
        }
      };

      return new Response(JSON.stringify(modalResponse), {
        headers: { "Content-Type": "application/json" }
      });
    }
  }

  // Type 5: MODAL_SUBMIT (User submitted the review modal)
  if (interaction.type === 5) {
    const customId = interaction.data?.custom_id || "";
    if (customId.startsWith("modal_flag_fp:")) {
      const eventHash = customId.replace("modal_flag_fp:", "");

      // Extract form values
      let category = "Uncategorized False Positive";
      let notes = "";
      const rows = interaction.data?.components || [];
      for (const row of rows) {
        for (const comp of row.components || []) {
          if (comp.custom_id === "category") category = comp.value || category;
          if (comp.custom_id === "notes") notes = comp.value || "";
        }
      }

      // Extract telemetry from message embed if available
      const embed = interaction.message?.embeds?.[0];
      let headline = "Intraday Anomaly";
      let source = "Intraday_Monitor";
      let pricePressure = "N/A";
      let supplyDisruption = "N/A";
      let geopoliticalRisk = "N/A";
      let originalUrl = "";

      if (embed) {
        if (embed.description) {
          const match = embed.description.match(/> \*"(.*?)"\*/s) || embed.description.match(/> (.*?)$/m);
          if (match) headline = match[1].trim();
        }
        for (const field of embed.fields || []) {
          const fName = field.name || "";
          const fVal = (field.value || "").replace(/`/g, "").trim();
          if (fName.includes("Ingestion Source")) source = fVal;
          if (fName.includes("Price Pressure")) pricePressure = fVal;
          if (fName.includes("Supply Disruption")) supplyDisruption = fVal;
          if (fName.includes("Geopolitical Risk")) geopoliticalRisk = fVal;
          if (fName.includes("Intelligence Sources")) {
            const urlMatch = field.value.match(/\[Original Article\]\((.*?)\)/);
            if (urlMatch) originalUrl = urlMatch[1].trim();
          }
        }
      }

      const owner = env.REPO_OWNER || "KoshiirRa";
      const repo = env.REPO_NAME || "midgley";
      const token = env.GH_PAT;

      let issueNumber: number | null = null;
      let issueUrl = "https://github.com/KoshiirRa/midgley/issues/258";
      let projectAssigned = false;

      if (token) {
        const issueTitle = `[False Positive] ${headline.slice(0, 80)}`;
        const issueBody = `## False Positive Anomaly Report (#258)\n\n` +
          `**Parent Tracking Thread:** #258\n` +
          `**Anomaly Fingerprint ID:** \`${eventHash}\`\n\n` +
          `### 🚨 Trigger Catalyst\n` +
          `> *\"${headline}\"*\n\n` +
          `- **Ingestion Source:** \`${source}\`\n` +
          `- **Flagged Category:** **${category}**\n` +
          `- **Reporter Notes:** ${notes || "_No additional context provided._"}\n` +
          (originalUrl ? `- **Source URL:** ${originalUrl}\n` : "") +
          `\n### 📊 Extracted Catalyst Telemetry\n` +
          `- **Price Pressure (ΔP):** \`${pricePressure}\`\n` +
          `- **Supply Disruption (S):** \`${supplyDisruption}\`\n` +
          `- **Geopolitical Risk (G):** \`${geopoliticalRisk}\`\n\n` +
          `### 🤖 Automated Agent Review\n` +
          `The automated false-positive agent reviewer will analyze the keyword gate rules in \`src/intraday_event_monitor.py\` and post diagnostic root-cause analysis and proposed exclusion rules.`;

        try {
          const createIssueRes = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
            method: "POST",
            headers: {
              "Authorization": `Bearer ${token}`,
              "User-Agent": "Midgley-Discord-Worker",
              "Accept": "application/vnd.github.v3+json",
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              title: issueTitle,
              body: issueBody,
              labels: ["data-ingestion", "false-positive", "intraday-monitor", "token-efficiency"]
            })
          });

          if (createIssueRes.ok) {
            const issueData: any = await createIssueRes.json();
            issueNumber = issueData.number;
            issueUrl = issueData.html_url;
            const issueNodeId = issueData.node_id;

            // Assign to Project V2 via GraphQL API
            const projectId = env.PROJECT_V2_ID || DEFAULT_PROJECT_V2_ID;
            if (issueNodeId && projectId) {
              try {
                const graphqlQuery = {
                  query: `mutation AddProjectCard($projectId: ID!, $contentId: ID!) {
                    addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
                      item {
                        id
                      }
                    }
                  }`,
                  variables: {
                    projectId: projectId,
                    contentId: issueNodeId
                  }
                };

                const gqlRes = await fetch("https://api.github.com/graphql", {
                  method: "POST",
                  headers: {
                    "Authorization": `Bearer ${token}`,
                    "User-Agent": "Midgley-Discord-Worker",
                    "Content-Type": "application/json"
                  },
                  body: JSON.stringify(graphqlQuery)
                });
                if (gqlRes.ok) {
                  projectAssigned = true;
                }
              } catch (gqlErr) {
                console.warn("[Project V2 Assignment Warning]", gqlErr);
              }
            }
          }
        } catch (issueErr) {
          console.error("[GitHub Issue Creation Error]", issueErr);
        }
      }

      await logToAxiom(env, ctx, {
        event: "discord_false_positive_flagged",
        eventHash,
        category,
        headline,
        issueNumber,
        issueUrl,
        projectAssigned
      });

      const confirmationContent = issueNumber
        ? `✅ **False Positive Logged to Issue #${issueNumber}!**\n\n` +
          `📋 **GitHub Issue:** [${headline.slice(0, 60)}...](${issueUrl})\n` +
          `🏷️ **Labels:** \`data-ingestion\`, \`false-positive\`, \`intraday-monitor\`, \`token-efficiency\`\n` +
          `📌 **Project Board:** \`Project Midgley - Master Roadmap\` ${projectAssigned ? "*(Card Added)*" : ""}\n` +
          `🔗 **Parent Tracking Thread:** https://github.com/KoshiirRa/midgley/issues/258\n\n` +
          `*The automated agent reviewer will analyze the trigger keywords and post diagnostic feedback shortly.*`
        : `⚠️ **Flagged Alert Recorded** (Fingerprint: \`${eventHash}\`)\n` +
          `Note: Linked to parent tracking thread [#258](https://github.com/KoshiirRa/midgley/issues/258).`;

      return new Response(JSON.stringify({
        type: 4,
        data: {
          flags: 64,
          content: confirmationContent
        }
      }), {
        headers: { "Content-Type": "application/json" }
      });
    }
  }

  return new Response(JSON.stringify({ type: 4, data: { flags: 64, content: "Interaction acknowledged." } }), {
    headers: { "Content-Type": "application/json" }
  });
}

async function handleFlagWebRequest(request: Request, env: Env, ctx: any): Promise<Response> {
  const url = new URL(request.url);

  if (request.method === "GET") {
    const id = url.searchParams.get("id") || "";
    const headline = url.searchParams.get("headline") || "Intraday Anomaly Trigger";
    const source = url.searchParams.get("source") || "Intraday_Monitor";
    const p = url.searchParams.get("p") || "+0.00";
    const s = url.searchParams.get("s") || "0.00";
    const g = url.searchParams.get("g") || "0.00";
    const sourceUrl = url.searchParams.get("url") || "";

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Flag False Positive Alert • Midgley Forecasting</title>
  <style>
    :root {
      --bg-dark: #12141a;
      --card-bg: #1c202a;
      --card-border: #2e3446;
      --text-main: #f0f3f8;
      --text-muted: #8b94a8;
      --accent-red: #e74c3c;
      --accent-blue: #3498db;
      --accent-green: #2ecc71;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-dark);
      color: var(--text-main);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 16px;
      box-sizing: border-box;
    }
    .modal-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
      width: 100%;
      max-width: 540px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .header {
      display: flex;
      align-items: center;
      gap: 10px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 16px;
      margin-bottom: 20px;
    }
    .header h2 {
      margin: 0;
      font-size: 1.25rem;
      color: var(--text-main);
    }
    .headline-box {
      background: #141720;
      border-left: 4px solid var(--accent-red);
      padding: 12px 16px;
      border-radius: 6px;
      margin-bottom: 20px;
      font-style: italic;
      color: #e2e8f0;
      font-size: 0.95rem;
      line-height: 1.4;
    }
    .meta-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 20px;
      background: #141720;
      padding: 10px;
      border-radius: 6px;
      font-size: 0.85rem;
    }
    .meta-item {
      text-align: center;
    }
    .meta-label {
      color: var(--text-muted);
      font-size: 0.75rem;
      text-transform: uppercase;
    }
    .meta-value {
      font-weight: 600;
      margin-top: 2px;
    }
    .form-group {
      margin-bottom: 16px;
    }
    label {
      display: block;
      margin-bottom: 6px;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-muted);
    }
    select, textarea {
      width: 100%;
      background: #141720;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 10px 12px;
      border-radius: 6px;
      font-size: 0.9rem;
      box-sizing: border-box;
      outline: none;
    }
    select:focus, textarea:focus {
      border-color: var(--accent-blue);
    }
    textarea {
      resize: vertical;
      min-height: 80px;
    }
    .btn-submit {
      width: 100%;
      background: var(--accent-red);
      color: #fff;
      border: none;
      padding: 12px;
      border-radius: 6px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-submit:hover {
      background: #c0392b;
    }
    .footer-note {
      margin-top: 14px;
      text-align: center;
      font-size: 0.78rem;
      color: var(--text-muted);
    }
    .footer-note a {
      color: var(--accent-blue);
      text-decoration: none;
    }
  </style>
</head>
<body>
  <div class="modal-card">
    <div class="header">
      <span style="font-size: 1.5rem;">🚩</span>
      <h2>Flag False Positive Alert (#258)</h2>
    </div>

    <div class="headline-box">
      "${headline}"
    </div>

    <div class="meta-grid">
      <div class="meta-item">
        <div class="meta-label">Pressure (ΔP)</div>
        <div class="meta-value" style="color: ${p.startsWith('+') ? '#e74c3c' : '#2ecc71'};">${p}/gal</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Supply Shock</div>
        <div class="meta-value">${s}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Source</div>
        <div class="meta-value">${source}</div>
      </div>
    </div>

    <form method="POST" action="/flag">
      <input type="hidden" name="id" value="${id}">
      <input type="hidden" name="headline" value="${encodeURIComponent(headline)}">
      <input type="hidden" name="source" value="${source}">
      <input type="hidden" name="p" value="${p}">
      <input type="hidden" name="s" value="${s}">
      <input type="hidden" name="g" value="${g}">
      <input type="hidden" name="url" value="${encodeURIComponent(sourceUrl)}">

      <div class="form-group">
        <label for="category">False Positive Category</label>
        <select name="category" id="category" required>
          <option value="Non-Energy Macro Tariff">Non-Energy Macro Tariff / Consumer Goods</option>
          <option value="Agricultural / Edible Oil">Agricultural / Edible Oil (Canola, Palm, Olive)</option>
          <option value="Macro Diplomatic Rhetoric">Macro Diplomatic / Political Rhetoric (No Crude Impact)</option>
          <option value="Non-Refinery Infrastructure Outage">Non-Refinery Infrastructure Outage (IT / Aviation)</option>
          <option value="Other False Positive">Other (Explain below)</option>
        </select>
      </div>

      <div class="form-group">
        <label for="notes">Reviewer Context / Notes (Optional)</label>
        <textarea name="notes" id="notes" placeholder="Explain why this headline is unrelated to crude oil or RBOB price elasticity..."></textarea>
      </div>

      <button type="submit" class="btn-submit">🚀 Create Tracked GitHub Issue</button>
    </form>

    <div class="footer-note">
      Linked to <a href="https://github.com/KoshiirRa/midgley/issues/258" target="_blank">Parent Tracking Thread #258</a> & Project Midgley Roadmap.
    </div>
  </div>
</body>
</html>`;
    return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
  }

  if (request.method === "POST") {
    const formData = await request.formData();
    const eventHash = formData.get("id")?.toString() || "";
    const rawHeadline = formData.get("headline")?.toString() || "Intraday Anomaly";
    let headline = rawHeadline;
    try {
      headline = decodeURIComponent(rawHeadline);
    } catch {}

    const source = formData.get("source")?.toString() || "Intraday_Monitor";
    const pricePressure = formData.get("p")?.toString() || "N/A";
    const supplyDisruption = formData.get("s")?.toString() || "N/A";
    const geopoliticalRisk = formData.get("g")?.toString() || "N/A";
    const rawUrl = formData.get("url")?.toString() || "";
    let originalUrl = rawUrl;
    try {
      originalUrl = decodeURIComponent(rawUrl);
    } catch {}

    const category = formData.get("category")?.toString() || "Uncategorized False Positive";
    const notes = formData.get("notes")?.toString() || "";

    const owner = env.REPO_OWNER || "KoshiirRa";
    const repo = env.REPO_NAME || "midgley";
    const token = env.GH_PAT;

    let issueNumber: number | null = null;
    let issueUrl = "https://github.com/KoshiirRa/midgley/issues/258";

    if (token) {
      const issueTitle = `[False Positive] ${headline.slice(0, 80)}`;
      const issueBody = `## False Positive Anomaly Report (#258)\n\n` +
        `**Parent Tracking Thread:** #258\n` +
        `**Anomaly Fingerprint ID:** \`${eventHash}\`\n\n` +
        `### 🚨 Trigger Catalyst\n` +
        `> *\"${headline}\"*\n\n` +
        `- **Ingestion Source:** \`${source}\`\n` +
        `- **Flagged Category:** **${category}**\n` +
        `- **Reporter Notes:** ${notes || "_No additional context provided._"}\n` +
        (originalUrl ? `- **Source URL:** ${originalUrl}\n` : "") +
        `\n### 📊 Extracted Catalyst Telemetry\n` +
        `- **Price Pressure (ΔP):** \`${pricePressure}\`\n` +
        `- **Supply Disruption (S):** \`${supplyDisruption}\`\n` +
        `- **Geopolitical Risk (G):** \`${geopoliticalRisk}\`\n\n` +
        `### 🤖 Automated Agent Review\n` +
        `The automated false-positive agent reviewer will analyze the keyword gate rules in \`src/intraday_event_monitor.py\` and post diagnostic root-cause analysis and proposed exclusion rules.`;

      try {
        const createIssueRes = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "User-Agent": "Midgley-Discord-Worker",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            title: issueTitle,
            body: issueBody,
            labels: ["data-ingestion", "false-positive", "intraday-monitor", "token-efficiency"]
          })
        });

        if (createIssueRes.ok) {
          const issueData: any = await createIssueRes.json();
          issueNumber = issueData.number;
          issueUrl = issueData.html_url;
          const issueNodeId = issueData.node_id;

          const projectId = env.PROJECT_V2_ID || DEFAULT_PROJECT_V2_ID;
          if (issueNodeId && projectId) {
            try {
              const graphqlQuery = {
                query: `mutation AddProjectCard($projectId: ID!, $contentId: ID!) {
                  addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
                    item {
                      id
                    }
                  }
                }`,
                variables: {
                  projectId: projectId,
                  contentId: issueNodeId
                }
              };

              await fetch("https://api.github.com/graphql", {
                method: "POST",
                headers: {
                  "Authorization": `Bearer ${token}`,
                  "User-Agent": "Midgley-Discord-Worker",
                  "Content-Type": "application/json"
                },
                body: JSON.stringify(graphqlQuery)
              });
            } catch (gqlErr) {
              console.warn("[Project V2 Assignment Warning]", gqlErr);
            }
          }
        }
      } catch (err) {
        console.error("[Issue Creation Error]", err);
      }
    }

    const successHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Issue Created • Midgley Forecasting</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #12141a;
      color: #f0f3f8;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 16px;
    }
    .success-card {
      background: #1c202a;
      border: 1px solid #2e3446;
      border-radius: 12px;
      padding: 32px;
      max-width: 480px;
      text-align: center;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .badge {
      font-size: 3rem;
      margin-bottom: 12px;
    }
    h2 { margin: 0 0 12px 0; font-size: 1.4rem; color: #2ecc71; }
    p { color: #8b94a8; font-size: 0.95rem; line-height: 1.5; margin-bottom: 24px; }
    .btn {
      display: inline-block;
      background: #3498db;
      color: #fff;
      text-decoration: none;
      padding: 12px 24px;
      border-radius: 6px;
      font-weight: 600;
    }
    .btn:hover { background: #2980b9; }
  </style>
</head>
<body>
  <div class="success-card">
    <div class="badge">✅</div>
    <h2>False Positive Issue Logged!</h2>
    <p>Issue <strong>#${issueNumber || "Created"}</strong> has been submitted with labels <code>data-ingestion</code>, <code>false-positive</code>, and attached to <strong>Project Midgley - Master Roadmap</strong>.<br><br>The automated CI reviewer is analyzing the catalyst keywords now.</p>
    <a href="${issueUrl}" target="_blank" class="btn">View GitHub Issue #${issueNumber || ""} ➔</a>
  </div>
</body>
</html>`;
    return new Response(successHtml, { headers: { "Content-Type": "text/html; charset=utf-8" } });
  }

  return new Response("Method Not Allowed", { status: 405 });
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

  async queue(batch: QueueMessageBatch<QueueEventPayload>, env: Env, ctx: any): Promise<void> {
    try {
      await handleQueueBatch(batch, env, ctx);
    } catch (err: any) {
      console.error(`[Queue Exception] ${err.message || String(err)}`);
      await captureSentryException(env, ctx, err, { trigger: "queue" });
    }
  },

  async fetch(request: Request, env: Env, ctx: any): Promise<Response> {
    const url = new URL(request.url);

    try {
      // Flag Web Route (One-Click Discord Webhook Review Flow)
      if (url.pathname === "/flag") {
        return await handleFlagWebRequest(request, env, ctx);
      }

      // Discord Interactions Endpoint Route
      if (url.pathname === "/discord/interactions" || request.headers.has("X-Signature-Ed25519")) {
        return await handleDiscordInteraction(request, env, ctx);
      }

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
          endpoints: ["/run", "/trigger", "/status", "/flag", "/discord/interactions"]
        }, null, 2),
        { headers: { "Content-Type": "application/json" } }
      );
    } catch (err: any) {
      console.error(`[Fetch Exception] ${err.message || String(err)}`);
      await captureSentryException(env, ctx, err, { pathname: url.pathname });
      return new Response(JSON.stringify({ error: "Internal Server Error" }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  }
};
