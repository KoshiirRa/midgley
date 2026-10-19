/**
 * Cloudflare Worker Edge Trigger for 15-Minute Intraday Event Monitoring
 * (workers/intraday_monitor_worker.ts)
 *
 * Polls energy RSS feeds every 15 minutes, evaluates fast-path trigger keywords,
 * sends GitHub Repository Dispatch events, and exports trace/log telemetry to Axiom & Sentry.
 */

import nacl from "tweetnacl";
import { getEnverusDailyRigCount, MIDGLEY_AGENT_USER_AGENT as DEFAULT_MIDGLEY_AGENT_UA } from "./enverus_scraper";
import {
  ScoredCatalyst,
  SemanticDedupeResult,
  scoreHeadlineAtEdge,
  querySemanticDedupe,
  indexHeadlineVector,
  retainHindsightMemory,
  synthesizeAnalystBrief,
  getHeadlineEmbedding
} from "./ai_event_scorer";

export interface Env {
  GH_PAT?: string;
  REPO_OWNER?: string;
  REPO_NAME?: string;
  SENTRY_DSN?: string;
  AXIOM_TOKEN?: string;
  AXIOM_DATASET?: string;
  SEC_USER_AGENT?: string;
  MIDGLEY_AGENT_USER_AGENT?: string;
  EDGAR_8K_TICKERS?: string;
  DISCORD_PUBLIC_KEY?: string;
  DISCORD_APP_ID?: string;
  DISCORD_BOT_TOKEN?: string;
  PROJECT_V2_ID?: string;
  CLOUDFLARE_AUTH_TOKEN?: string;
  ADMIN_TOKEN?: string;
  FLAG_SIGNING_KEY?: string;
  DB?: any;
  MYBROWSER?: any;
  AI?: any;
  EVENT_INDEX?: {
    query(vector: number[], options: { topK?: number; returnMetadata?: string }): Promise<{
      matches: Array<{ id: string; score: number; metadata?: Record<string, any> }>;
    }>;
    insert(vectors: Array<{ id: string; values: number[]; metadata?: Record<string, any> }>): Promise<any>;
  };
  HINDSIGHT_API_URL?: string;
  HINDSIGHT_DEDUPE_BANK_ID?: string;
  HINDSIGHT_API_TOKEN?: string;
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
  "wikipedia", "software outage", "airline outage", "it outage", "it system outage", "it systems outage", "cloud outage", "gaming outage", "network outage",
  "canola", "cooking oil", "palm oil", "olive oil", "soybean oil",
  "rice bran", "rice bran oil", "vegetable oil", "sunflower oil", "corn oil",
  "peanut oil", "sesame oil", "edible oil", "hydrogenated oil",
  // Non-commercial / municipal local facility spills (Issue #317)
  "data center", "data centre", "backup generator", "generator spill", "building spill"
];

const EXCLUDE_REGEX = new RegExp(
  `\\b(${EXCLUDE_KEYWORDS.join("|")})\\b`,
  "i"
);

const NON_ENERGY_TARIFF_EXCLUDES = [
  "house should not transfer", "tariff authority", "steel tariff", "aluminum tariff",
  "copper tariff", "lumber tariff", "auto tariff", "solar tariff", "washing machine",
  "semiconductor tariff", "chip tariff", "reciprocal trade act", "section 301", "section 232",
  "canola", "canola oil", "rice bran", "rice bran oil", "vegetable oil", "sunflower oil",
  "corn oil", "peanut oil", "sesame oil", "edible oil", "hydrogenated oil", "cooking oil",
  "palm oil", "olive oil", "soybean oil"
];

const NON_ENERGY_TARIFF_REGEX = new RegExp(
  `\\b(${NON_ENERGY_TARIFF_EXCLUDES.join("|")})\\b`,
  "i"
);

const TRIGGER_KEYWORDS = [

  "energy tariff", "oil tariff", "fuel tariff", "crude tariff", "gasoline tariff", "retaliatory tariff", "counter-tariff",
  "opec emergency", "pipeline halt", "pipeline outage",
  "explosion", "tornado", "blackout", "blockade",
  "energy sanction", "oil sanction", "fuel sanction", "crude sanction", "petroleum sanction",
  "refinery outage", "refinery halt", "power grid outage", "plant outage", "terminal outage",
  "strait of hormuz", "red sea attack", "spill",
  // Market Technicals & Volatility
  "crack spread", "crack-spread", "ovx spike", "futures spike", "futures crash", "wti surge", "rbob surge", "barrel price",
  // Executive Policy & Geopolitics
  "executive order", "sanction threat", "strait blockade", "strategic petroleum reserve", "spr release", "opec cut", "opec quota",
  // Logistics & Infrastructure Hubs
  "colonial pipeline", "keystone pipeline", "refinery explosion", "refinery fire", "cushing inventory", "barge congestion",
  "catlettsburg", "delaware city", "west tulsa", "richmond refinery",
  // Refinery Operator 8-K Signals (Issue #129 & #332)
  "pbf energy", "hf sinclair", "holly frontier", "marathon petroleum", "valero", "phillips 66",
  "force majeure", "unplanned outage", "crude distillation unit", "fcc unit",
  "hydrocracker", "coker unit", "capacity reduction", "el dorado refinery",
  "sweeny refinery", "bayway refinery"
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
  let cleaned = title.trim();
  const sepIdx = Math.max(
    cleaned.lastIndexOf(" - "),
    cleaned.lastIndexOf(" – "),
    cleaned.lastIndexOf(" — "),
    cleaned.lastIndexOf(" | ")
  );
  if (sepIdx > 0) {
    cleaned = cleaned.slice(0, sepIdx).trim();
  }
  // Lowercase and strip non-alphanumeric for clean hashing key
  return cleaned.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 80);
}

export function isAnomalyHeadline(title: string): boolean {
  if (EXCLUDE_REGEX.test(title)) {
    return false;
  }
  if (NON_ENERGY_TARIFF_REGEX.test(title)) {
    return false;
  }
  if (TRIGGER_REGEX.test(title)) {
    return true;
  }
  // Check if headline mentions tariff/tariffs alongside energy context
  if (/\btariffs?\b/i.test(title)) {
    const hasEnergyContext = /(?:oil|crude|gasoline|fuel|petroleum|refin|diesel|energy|opec|tanker|pipeline|barrel)/i.test(title);
    if (hasEnergyContext) {
      return true;
    }
  }
  // Check if headline mentions sanction/sanctions alongside energy context (Issues #258, #312, #318)
  if (/\bsanctions?\b/i.test(title)) {
    const hasEnergyContext = /(?:oil|crude|gasoline|fuel|petroleum|refin|diesel|energy|opec|tanker|pipeline|barrel)/i.test(title);
    if (hasEnergyContext) {
      return true;
    }
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
        "SELECT 1 FROM seen_rss_headlines WHERE clean_key = ? AND datetime(created_at, '+72 hours') > datetime('now') LIMIT 1"
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

  // 2. Also write to Edge Cache (72h TTL)
  try {
    if (typeof caches === "undefined" || !caches.default) return;
    const dummyUrl = `https://midgley-cache.internal/dispatched/${cleanKey}`;
    const req = new Request(dummyUrl);
    const resp = new Response("dispatched", {
      headers: {
        "Cache-Control": "public, max-age=259200"
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

      // Check Vectorize & Hindsight multi-tier semantic deduplication
      const dedupeRes = await querySemanticDedupe(headline, env);
      if (dedupeRes.status === "duplicate") {
        console.log(`[Queue Semantic Dedupe] Suppressing duplicate event (${dedupeRes.source}): "${headline}"`);
        await markHeadlineDispatchedInCache(headline, env);
        message.ack();
        acked++;
        continue;
      }

      // Zero-shot catalyst scoring at the edge via Workers AI
      const scored = await scoreHeadlineAtEdge(headline, env);
      if (!scored.is_anomaly) {
        console.log(`[Queue Catalyst Filter] Noise classified by ${scored.model}: "${headline}"`);
        await markHeadlineDispatchedInCache(headline, env);
        message.ack();
        acked++;
        continue;
      }

      const res = await dispatchGitHubEvent(env, headline, url);
      if (res.dispatched) {
        console.log(`[Queue Consumer Dispatch Success] Event dispatched for: "${headline}"`);
        await markHeadlineDispatchedInCache(headline, env);

        // Background multi-store persistence to Vectorize and Hindsight midgley-event-dedupe
        const persistTask = async () => {
          try {
            const embedding = await getHeadlineEmbedding(headline, env);
            if (embedding) {
              await indexHeadlineVector(headline, embedding, {
                domain: scored.catalyst_domain,
                hub: scored.affected_hub,
                magnitude: scored.magnitude,
                model: scored.model
              }, env);
            }
            await retainHindsightMemory({
              headline,
              url,
              source: message.body?.source || "QueueConsumer",
              magnitude: scored.magnitude,
              locales: [scored.affected_hub]
            }, env);
          } catch (pErr: any) {
            console.warn(`[Background Persistence Notice] ${pErr?.message || String(pErr)}`);
          }
        };

        if (ctx && typeof ctx.waitUntil === "function") {
          ctx.waitUntil(persistTask());
        } else {
          await persistTask();
        }

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

        // Multi-tier semantic deduplication check (Vectorize + Hindsight)
        const dedupeRes = await querySemanticDedupe(headline, env);
        if (dedupeRes.status === "duplicate") {
          console.log(`[EDGAR Semantic Dedupe] Suppressed duplicate 8-K (${dedupeRes.source}): "${headline}"`);
          await markHeadlineDispatchedInCache(`edgar:${accessionId}`, env);
          continue;
        }

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

      // Check Vectorize & Hindsight multi-tier semantic deduplication
      const dedupeRes = await querySemanticDedupe(anomaly.title, env);
      if (dedupeRes.status === "duplicate") {
        console.log(`[RSS Semantic Dedupe] Suppressed duplicate anomaly (${dedupeRes.source}): "${anomaly.title}"`);
        await markHeadlineDispatchedInCache(anomaly.title, env);
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

        const persistTask = async () => {
          try {
            const embedding = await getHeadlineEmbedding(anomaly.title, env);
            if (embedding) {
              await indexHeadlineVector(anomaly.title, embedding, {
                source: "RSS",
                as_of: new Date().toISOString()
              }, env);
            }
            await retainHindsightMemory({
              headline: anomaly.title,
              url: anomaly.link,
              source: "RSS"
            }, env);
          } catch (pErr: any) {
            console.warn(`[Background Persistence Notice] ${pErr?.message || String(pErr)}`);
          }
        };

        if (ctx && typeof ctx.waitUntil === "function") {
          ctx.waitUntil(persistTask());
        } else {
          await persistTask();
        }
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

export const SUPPORTED_DISCORD_LOCALES = [
  { name: "National (US Wholesale & Retail Benchmark)", value: "National", slug: "index.html", padd: "US National" },
  { name: "Tulsa Metro, OK (PADD 2)", value: "Tulsa", slug: "tulsa.html", padd: "PADD 2 Midwest" },
  { name: "Newark Metro, DE (PADD 1B)", value: "Newark", slug: "newark.html", padd: "PADD 1B Central Atlantic" },
  { name: "Cincinnati Tri-State, OH/KY (PADD 2)", value: "Cincinnati", slug: "cincinnati.html", padd: "PADD 2 Midwest" },
  { name: "Greenville Metro, NC (PADD 1C)", value: "Greenville", slug: "greenville.html", padd: "PADD 1C South Atlantic" },
  { name: "Charlotte Metro, NC (PADD 1C)", value: "Charlotte", slug: "charlotte.html", padd: "PADD 1C South Atlantic" },
  { name: "SF Bay Area / Oakland, CA (PADD 5)", value: "Oakland", slug: "bay_area.html", padd: "PADD 5 West Coast" },
  { name: "Port St. Lucie Metro, FL (PADD 1C)", value: "Port_St_Lucie", slug: "port_st_lucie.html", padd: "PADD 1C South Atlantic" },
  { name: "Greater Chicago Metro, IL/IN (PADD 2)", value: "Chicago", slug: "chicago.html", padd: "PADD 2 Midwest" },
  { name: "Houston Metro, TX (PADD 3)", value: "Houston", slug: "houston.html", padd: "PADD 3 Gulf Coast" },
  { name: "Los Angeles Basin, CA (PADD 5)", value: "Los_Angeles", slug: "los_angeles.html", padd: "PADD 5 West Coast" },
  { name: "Denver Metro & Rocky Mountain, CO (PADD 4)", value: "Denver", slug: "denver.html", padd: "PADD 4 Rocky Mountain" },
  { name: "New York Harbor & NY State, NY (PADD 1B)", value: "New_York", slug: "new_york.html", padd: "PADD 1B Central Atlantic" },
  { name: "Boston Metro & New England, MA (PADD 1A)", value: "Boston", slug: "boston.html", padd: "PADD 1A New England" },
  { name: "Seattle-Tacoma & Puget Sound, WA (PADD 5B)", value: "Seattle", slug: "seattle.html", padd: "PADD 5B Pacific Northwest" },
  { name: "Phoenix Metro & Desert Southwest, AZ (PADD 5C)", value: "Phoenix", slug: "phoenix.html", padd: "PADD 5C Desert Southwest" },
  { name: "Anchorage & Southcentral Alaska, AK (PADD 5D)", value: "Anchorage", slug: "anchorage.html", padd: "PADD 5D Alaska" },
  { name: "Honolulu & Oahu Island System, HI (PADD 5D)", value: "Honolulu", slug: "honolulu.html", padd: "PADD 5D Hawaii" },
  { name: "San Juan Metro & Caribbean Territories, PR (PADD 6)", value: "San_Juan", slug: "san_juan.html", padd: "PADD 6 Caribbean" },
  { name: "Hagåtña & U.S. Pacific Territories, GU (PADD 7)", value: "Guam", slug: "guam.html", padd: "PADD 7 Pacific Islands" }
];

export interface WorkerDMSubscriptionRecord {
  subscription_id: string;
  discord_user_id: string;
  dm_channel_id?: string | null;
  target_locales: string[];
  zip_codes?: string[];
  min_shock_threshold: number;
  direction_filter: string;
  delivery_mode: string;
  is_active: boolean;
  muted_until?: string | null;
  created_at: string;
}

export interface WorkerZipResolution {
  status: "success" | "fallback";
  zip_code: string;
  prefix_3: string;
  resolution_tier: "METRO_CLUSTER_HIT" | "STATE_PADD_FALLBACK" | "INVALID_INPUT_FALLBACK";
  is_metro_cluster_hit: boolean;
  locale_code: string;
  canonical_hub: string;
  location_name: string;
  state: string;
  padd_region: string;
  padd_name: string;
  calibrated_model_used: string;
  state_tax_rate_per_gal: number;
  hub_baseline_tax_rate: number;
  tax_delta_per_gal: number;
  is_significant_departure: boolean;
  departure_reason: string;
  estimated_basis_delta: number;
  tracking_issue_number?: number | null;
}

export interface WorkerUnmappedZipTelemetryRecord {
  zip_code: string;
  state: string;
  padd_region: string;
  calibrated_model_used: string;
  hit_count: number;
  first_searched_at: string;
  last_searched_at: string;
}

const WORKER_DM_SUBSCRIPTIONS = new Map<string, WorkerDMSubscriptionRecord>();
const WORKER_UNMAPPED_ZIPS = new Map<string, WorkerUnmappedZipTelemetryRecord>();
const WORKER_DEPARTURE_ISSUES_CACHE = new Map<string, { issueNumber: number; issueUrl: string }>();

let flagReplaySchemaInitialized = false;

export function clearWorkerSubscriptionsMemoryForTesting(): void {
  WORKER_DM_SUBSCRIPTIONS.clear();
  flagReplaySchemaInitialized = false;
}

export async function ensureFlagReplaySchema(env: Env): Promise<void> {
  if (!env.DB || flagReplaySchemaInitialized) return;
  try {
    await env.DB.prepare(
      "CREATE TABLE IF NOT EXISTS flag_replay_tokens (clean_key TEXT PRIMARY KEY, value TEXT, used_at TEXT NOT NULL DEFAULT (datetime('now')))"
    ).run();

    try {
      const tableInfo = await env.DB.prepare("PRAGMA table_info(flag_replay_tokens)").all();
      const cols = new Set(((tableInfo && tableInfo.results) || []).map((c: any) => c.name));
      if (cols.size > 0 && !cols.has("value")) {
        await env.DB.prepare("ALTER TABLE flag_replay_tokens ADD COLUMN value TEXT").run();
      }
    } catch {
      // PRAGMA table_info might fail in certain environments or mocks
    }

    flagReplaySchemaInitialized = true;
  } catch (err: any) {
    console.warn(`[D1 Schema Init Notice] ensureFlagReplaySchema: ${err?.message || String(err)}`);
  }
}

// Baseline statutory motor fuel excise taxes ($/gal) for calibrated reference hubs
export const WORKER_HUB_BASELINE_TAXES: Record<string, number> = {
  Newark: 0.230,
  Tulsa: 0.190,
  Cincinnati: 0.385,
  Greenville: 0.404,
  Charlotte: 0.404,
  Port_St_Lucie: 0.362,
  Chicago: 0.550,
  Houston: 0.200,
  Los_Angeles: 0.953,
  Oakland: 0.634,
  Denver: 0.280,
  New_York: 0.472,
  Boston: 0.240,
  Seattle: 0.494,
  Phoenix: 0.180,
  Anchorage: 0.0895,
  Honolulu: 0.330,
  San_Juan: 0.160,
  Guam: 0.190,
  National: 0.184
};

// Baseline retail pump benchmark prices ($/gal) for calibrated reference hubs
export const WORKER_HUB_BASELINE_PRICES: Record<string, number> = {
  National: 3.184,
  Tulsa: 3.962,
  Newark: 4.134,
  Cincinnati: 3.991,
  Greenville: 3.705,
  Charlotte: 3.711,
  Oakland: 6.287,
  Port_St_Lucie: 4.250,
  Chicago: 3.850,
  Houston: 2.850,
  Los_Angeles: 4.890,
  Denver: 3.150,
  New_York: 3.480,
  Boston: 3.450,
  Seattle: 4.250,
  Phoenix: 3.550,
  Anchorage: 3.750,
  Honolulu: 4.650,
  San_Juan: 3.490,
  Guam: 4.150
};

// API endpoint mappings to static JSON published on GitHub Pages
export const WORKER_HUB_API_SLUGS: Record<string, string> = {
  National: "national",
  Tulsa: "tulsa",
  Newark: "newark",
  Cincinnati: "cincinnati",
  Greenville: "greenville",
  Charlotte: "charlotte",
  Oakland: "oakland",
  Port_St_Lucie: "port_st_lucie",
  BayArea: "bayarea"
};

export interface WorkerForecastRecord {
  basePrice: number;
  predictedPrice: number;
  expectedChangeDollars: number;
  expectedChangePercent: number;
  direction: "UP" | "DOWN" | "FLAT";
  lower95ci: number;
  upper95ci: number;
  modelVersion: string;
  targetDate: string;
  trajectory: Array<{ day: number; price: number }>;
  source: string;
}

/**
 * Retrieves the latest point-in-time quantitative price forecast for a locale and horizon.
 * Follows defensive fallback cascade:
 * 1. Cloudflare D1 prediction_history table (if DB binding is active and populated)
 * 2. Static JSON API payload from GitHub Pages (docs/api/v1/*.json)
 * 3. Calibrated econometric baseline anchors and multi-day persistence path
 */
export async function getWorkerForecastData(
  locale: string,
  horizon: number,
  env?: Env
): Promise<WorkerForecastRecord> {
  const normLocale = normalizeWorkerLocale(locale);
  const fallbackBase = WORKER_HUB_BASELINE_PRICES[normLocale] ?? WORKER_HUB_BASELINE_PRICES["National"] ?? 3.184;

  // 1. Try D1 prediction_history table if DB binding is available
  if (env && env.DB) {
    try {
      const rows = await env.DB.prepare(`
        SELECT forecast_horizon_days, current_base_price, predicted_5d_price,
               predicted_direction, prediction_lower_95ci, prediction_upper_95ci,
               forecast_target_date, model_version, log_timestamp
        FROM prediction_history
        WHERE (region = ? OR region = ? OR region LIKE ?)
          AND (is_retroactive_backtest IS NULL OR is_retroactive_backtest = 0)
        ORDER BY log_timestamp DESC
        LIMIT 25
      `).bind(normLocale, `${normLocale}_OK`, `${normLocale}%`).all();

      if (rows && rows.results && rows.results.length > 0) {
        const horizonMap = new Map<number, any>();
        for (const r of rows.results) {
          const h = Number(r.forecast_horizon_days);
          if (h >= 1 && h <= 5 && !horizonMap.has(h)) {
            horizonMap.set(h, r);
          }
        }

        const targetRow = horizonMap.get(horizon) || horizonMap.get(5) || rows.results[0];
        const baseP = Number(targetRow.current_base_price || fallbackBase);
        const predP = Number(targetRow.predicted_5d_price || baseP);
        const delta = Number((predP - baseP).toFixed(3));
        const pct = baseP > 0 ? Number(((delta / baseP) * 100).toFixed(2)) : 0;
        const dir = delta > 0.005 ? "UP" : delta < -0.005 ? "DOWN" : "FLAT";
        const lower = Number(targetRow.prediction_lower_95ci ?? (predP - 0.12));
        const upper = Number(targetRow.prediction_upper_95ci ?? (predP + 0.12));
        const modelVer = String(targetRow.model_version || "v1.6 Ipatieff");
        const targetDate = String(targetRow.forecast_target_date || "");

        const trajectory: Array<{ day: number; price: number }> = [];
        for (let d = 1; d <= 5; d++) {
          if (horizonMap.has(d)) {
            trajectory.push({ day: d, price: Number(Number(horizonMap.get(d).predicted_5d_price).toFixed(3)) });
          } else {
            const step = delta / (horizon || 5);
            trajectory.push({ day: d, price: Number((baseP + step * d).toFixed(3)) });
          }
        }

        return {
          basePrice: baseP,
          predictedPrice: predP,
          expectedChangeDollars: delta,
          expectedChangePercent: pct,
          direction: dir,
          lower95ci: lower,
          upper95ci: upper,
          modelVersion: modelVer,
          targetDate,
          trajectory,
          source: "cloudflare_d1"
        };
      }
    } catch (d1Err) {
      console.warn("[Worker Forecast D1 Notice]", d1Err);
    }
  }

  // 2. Try fetching static JSON from GitHub Pages with a short timeout
  const apiSlug = WORKER_HUB_API_SLUGS[normLocale];
  if (apiSlug && typeof fetch !== "undefined") {
    try {
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timeoutId = controller ? setTimeout(() => controller.abort(), 1800) : null;
      const res = await fetch(`https://koshiirra.github.io/midgley/api/v1/${apiSlug}.json`, {
        signal: controller ? controller.signal : undefined
      });
      if (timeoutId) clearTimeout(timeoutId);

      if (res && res.ok) {
        const payload: any = await res.json();
        const fc = payload && payload.forecast;
        if (fc && typeof fc === "object") {
          const live = payload.live_lookup || {};
          const baseP = Number(fc.current_base_price ?? live.current_price_per_gal ?? fallbackBase);
          const predP = Number(
            horizon === 5
              ? (fc.predicted_price_per_gal ?? baseP)
              : (fc[`day_${horizon}_price`] ?? fc.predicted_price_per_gal ?? baseP)
          );
          const delta = Number((predP - baseP).toFixed(3));
          const pct = baseP > 0 ? Number(((delta / baseP) * 100).toFixed(2)) : 0;
          const dir = delta > 0.005 ? "UP" : delta < -0.005 ? "DOWN" : "FLAT";
          const lower = Number(fc.prediction_lower_95ci ?? (predP - 0.12));
          const upper = Number(fc.prediction_upper_95ci ?? (predP + 0.12));
          const modelVer = String(fc.model_version || "v1.6 Ipatieff");
          const targetDate = String(fc.target_date || "");

          const trajectory: Array<{ day: number; price: number }> = [];
          for (let d = 1; d <= 5; d++) {
            const dayVal = fc[`day_${d}_price`];
            if (typeof dayVal === "number") {
              trajectory.push({ day: d, price: Number(dayVal.toFixed(3)) });
            } else {
              const step = delta / (horizon || 5);
              trajectory.push({ day: d, price: Number((baseP + step * d).toFixed(3)) });
            }
          }

          return {
            basePrice: baseP,
            predictedPrice: predP,
            expectedChangeDollars: delta,
            expectedChangePercent: pct,
            direction: dir,
            lower95ci: lower,
            upper95ci: upper,
            modelVersion: modelVer,
            targetDate,
            trajectory,
            source: "github_pages_static_api"
          };
        }
      }
    } catch (fetchErr) {
      console.warn("[Worker Forecast Static API Notice]", fetchErr);
    }
  }

  // 3. Deterministic calibrated baseline anchor fallback
  const now = new Date();
  const targetDateObj = new Date(now.getTime() + horizon * 86400000);
  const targetDateStr = targetDateObj.toISOString().split("T")[0];
  const delta = 0.0;
  const lower = Number((fallbackBase - 0.120).toFixed(3));
  const upper = Number((fallbackBase + 0.120).toFixed(3));
  const trajectory = [1, 2, 3, 4, 5].map(d => ({ day: d, price: fallbackBase }));

  return {
    basePrice: fallbackBase,
    predictedPrice: fallbackBase,
    expectedChangeDollars: delta,
    expectedChangePercent: 0.0,
    direction: "FLAT",
    lower95ci: lower,
    upper95ci: upper,
    modelVersion: "v1.6 Ipatieff",
    targetDate: targetDateStr,
    trajectory,
    source: "calibrated_anchor_fallback"
  };
}

// Known regional locality names to preserve true human-readable geographic identity
export const WORKER_KNOWN_ZIP_LOCALITIES: Record<string, string> = {
  "12946": "Lake Placid, NY",
  "129": "Adirondacks / Plattsburgh, NY",
  "100": "Manhattan, NYC",
  "101": "Manhattan, NYC",
  "102": "Manhattan, NYC",
  "103": "Staten Island, NYC",
  "104": "Bronx, NYC",
  "112": "Brooklyn, NYC",
  "111": "Queens, NYC",
  "113": "Queens, NYC",
  "114": "Queens, NYC",
  "115": "Nassau County, Long Island",
  "117": "Suffolk County, Long Island",
  "119": "Hamptons, Long Island",
  "120": "Capital District, NY",
  "122": "Albany, NY",
  "128": "Glens Falls / Adirondacks, NY",
  "132": "Syracuse, NY",
  "142": "Buffalo, NY",
  "146": "Rochester, NY",
  "191": "Philadelphia, PA",
  "152": "Pittsburgh, PA",
  "021": "Boston, MA",
  "029": "Providence, RI",
  "061": "Hartford, CT",
  "031": "Manchester, NH",
  "054": "Burlington, VT",
  "041": "Portland, ME",
  "802": "Denver, CO",
  "841": "Salt Lake City, UT",
  "820": "Cheyenne, WY",
  "591": "Billings, MT",
  "837": "Boise, ID",
  "74103": "Tulsa Metro, OK",
  "64101": "Kansas City, MO",
};

export function resolveWorkerLocationName(zipCode: string, prefix3: string, state: string): string {
  if (WORKER_KNOWN_ZIP_LOCALITIES[zipCode]) return WORKER_KNOWN_ZIP_LOCALITIES[zipCode];
  if (WORKER_KNOWN_ZIP_LOCALITIES[prefix3]) return WORKER_KNOWN_ZIP_LOCALITIES[prefix3];
  return `ZIP ${zipCode} (${state})`;
}

const WORKER_ZIP_METRO_PREFIX_MAP: Record<string, string> = {
  "740": "Tulsa", "741": "Tulsa", "742": "Tulsa", "743": "Tulsa",
  "197": "Newark", "198": "Newark", "199": "Newark",
  "450": "Cincinnati", "451": "Cincinnati", "452": "Cincinnati",
  "278": "Greenville", "279": "Greenville",
  "280": "Charlotte", "281": "Charlotte", "282": "Charlotte",
  "940": "Oakland", "941": "Oakland", "942": "Oakland", "943": "Oakland", "944": "Oakland",
  "945": "Oakland", "946": "Oakland",
  "349": "Port_St_Lucie",
  "600": "Chicago", "601": "Chicago", "602": "Chicago", "603": "Chicago", "604": "Chicago",
  "605": "Chicago", "606": "Chicago", "607": "Chicago", "608": "Chicago", "463": "Chicago", "464": "Chicago",
  "770": "Houston", "772": "Houston", "773": "Houston", "774": "Houston", "775": "Houston", "776": "Houston", "777": "Houston",
  "900": "Los_Angeles", "901": "Los_Angeles", "902": "Los_Angeles", "903": "Los_Angeles", "904": "Los_Angeles",
  "905": "Los_Angeles", "906": "Los_Angeles", "907": "Los_Angeles", "908": "Los_Angeles", "910": "Los_Angeles",
  "911": "Los_Angeles", "912": "Los_Angeles", "913": "Los_Angeles", "914": "Los_Angeles", "915": "Los_Angeles",
  "916": "Los_Angeles", "917": "Los_Angeles", "918": "Los_Angeles", "926": "Los_Angeles", "927": "Los_Angeles", "928": "Los_Angeles",
  "800": "Denver", "801": "Denver", "802": "Denver", "803": "Denver", "804": "Denver", "805": "Denver", "806": "Denver",
  "021": "Boston", "022": "Boston", "024": "Boston",
  "980": "Seattle", "981": "Seattle", "982": "Seattle", "983": "Seattle", "984": "Seattle", "985": "Seattle",
  "850": "Phoenix", "851": "Phoenix", "852": "Phoenix", "853": "Phoenix", "890": "Phoenix", "891": "Phoenix",
  "995": "Anchorage", "996": "Anchorage",
  "967": "Honolulu", "968": "Honolulu",
  "969": "Guam",
  "006": "San_Juan", "007": "San_Juan", "008": "San_Juan", "009": "San_Juan"
};

// 100-149: New York Harbor & New York State Metro Calibration Hub (Issue #635)
for (let i = 100; i < 150; i++) {
  WORKER_ZIP_METRO_PREFIX_MAP[String(i)] = "New_York";
}

const WORKER_STATE_PADD_MAP: Record<string, { padd: string; paddName: string; hub: string; model: string; tax: number }> = {
  // PADD 6 (U.S. Caribbean Territories - Issue #620)
  PR: { padd: "PADD 6", paddName: "U.S. Caribbean Territories", hub: "San_Juan", model: "San_Juan_PR (PADD 6)", tax: 0.160 },
  VI: { padd: "PADD 6", paddName: "U.S. Virgin Islands", hub: "San_Juan", model: "San_Juan_PR (PADD 6)", tax: 0.160 },
  // PADD 7 (U.S. Pacific Island Territories - Issue #621)
  GU: { padd: "PADD 7", paddName: "U.S. Pacific Island Territories", hub: "Guam", model: "Guam_GU (PADD 7)", tax: 0.190 },
  MP: { padd: "PADD 7", paddName: "Northern Mariana Islands", hub: "Guam", model: "Guam_GU (PADD 7)", tax: 0.190 },
  AS: { padd: "PADD 7", paddName: "American Samoa", hub: "Guam", model: "Guam_GU (PADD 7)", tax: 0.190 },
  // PADD 5 (West Coast Sub-Districts - Issue #622 Decoupling)
  CA: { padd: "PADD 5", paddName: "West Coast (California CARB)", hub: "Oakland", model: "Oakland_CA (PADD 5 CARB)", tax: 0.596 },
  OR: { padd: "PADD 5", paddName: "Pacific Northwest", hub: "Seattle", model: "Seattle_WA (PADD 5B PNW)", tax: 0.400 },
  WA: { padd: "PADD 5", paddName: "Pacific Northwest", hub: "Seattle", model: "Seattle_WA (PADD 5B PNW)", tax: 0.494 },
  NV: { padd: "PADD 5", paddName: "Desert Southwest", hub: "Phoenix", model: "Phoenix_AZ (PADD 5C Desert SW)", tax: 0.505 },
  AZ: { padd: "PADD 5", paddName: "Desert Southwest", hub: "Phoenix", model: "Phoenix_AZ (PADD 5C Desert SW)", tax: 0.180 },
  AK: { padd: "PADD 5", paddName: "Alaska", hub: "Anchorage", model: "Anchorage_AK (PADD 5D Alaska)", tax: 0.089 },
  HI: { padd: "PADD 5", paddName: "Hawaii", hub: "Honolulu", model: "Honolulu_HI (PADD 5D Hawaii)", tax: 0.160 },
  // PADD 1A (New England)
  ME: { padd: "PADD 1A", paddName: "New England", hub: "Boston", model: "Boston_MA (PADD 1A)", tax: 0.300 },
  NH: { padd: "PADD 1A", paddName: "New England", hub: "Boston", model: "Boston_MA (PADD 1A)", tax: 0.222 },
  VT: { padd: "PADD 1A", paddName: "New England", hub: "Boston", model: "Boston_MA (PADD 1A)", tax: 0.310 },
  MA: { padd: "PADD 1A", paddName: "New England", hub: "Boston", model: "Boston_MA (PADD 1A)", tax: 0.240 },
  RI: { padd: "PADD 1A", paddName: "New England", hub: "Boston", model: "Boston_MA (PADD 1A)", tax: 0.370 },
  CT: { padd: "PADD 1A", paddName: "New England", hub: "Boston", model: "Boston_MA (PADD 1A)", tax: 0.250 },
  // PADD 1B (Central Atlantic)
  NY: { padd: "PADD 1B", paddName: "Central Atlantic", hub: "New_York", model: "New_York_NY (PADD 1B)", tax: 0.472 },
  NJ: { padd: "PADD 1B", paddName: "Central Atlantic", hub: "Newark", model: "Newark_DE (PADD 1B)", tax: 0.423 },
  PA: { padd: "PADD 1B", paddName: "Central Atlantic", hub: "Newark", model: "Newark_DE (PADD 1B)", tax: 0.576 },
  DE: { padd: "PADD 1B", paddName: "Central Atlantic", hub: "Newark", model: "Newark_DE (PADD 1B)", tax: 0.230 },
  MD: { padd: "PADD 1B", paddName: "Central Atlantic", hub: "Newark", model: "Newark_DE (PADD 1B)", tax: 0.470 },
  DC: { padd: "PADD 1B", paddName: "Central Atlantic", hub: "Newark", model: "Newark_DE (PADD 1B)", tax: 0.348 },
  // PADD 1C (Lower Atlantic)
  NC: { padd: "PADD 1C", paddName: "Lower Atlantic", hub: "Charlotte", model: "Charlotte_NC (PADD 1C)", tax: 0.404 },
  SC: { padd: "PADD 1C", paddName: "Lower Atlantic", hub: "Charlotte", model: "Charlotte_NC (PADD 1C)", tax: 0.280 },
  FL: { padd: "PADD 1C", paddName: "Lower Atlantic", hub: "Port_St_Lucie", model: "Port_St_Lucie_FL (PADD 1C)", tax: 0.362 },
  GA: { padd: "PADD 1C", paddName: "Lower Atlantic", hub: "Charlotte", model: "Charlotte_NC (PADD 1C)", tax: 0.312 },
  VA: { padd: "PADD 1C", paddName: "Lower Atlantic", hub: "Charlotte", model: "Charlotte_NC (PADD 1C)", tax: 0.298 },
  WV: { padd: "PADD 1C", paddName: "Lower Atlantic", hub: "Charlotte", model: "Charlotte_NC (PADD 1C)", tax: 0.357 },
  // PADD 2 (Midwest)
  OK: { padd: "PADD 2", paddName: "Midwest", hub: "Tulsa", model: "Tulsa_OK (PADD 2)", tax: 0.190 },
  OH: { padd: "PADD 2", paddName: "Midwest", hub: "Cincinnati", model: "Cincinnati_OH (PADD 2)", tax: 0.385 },
  IL: { padd: "PADD 2", paddName: "Midwest", hub: "Chicago", model: "Chicago_IL (PADD 2)", tax: 0.470 },
  IN: { padd: "PADD 2", paddName: "Midwest", hub: "Chicago", model: "Chicago_IL (PADD 2)", tax: 0.350 },
  MI: { padd: "PADD 2", paddName: "Midwest", hub: "Chicago", model: "Chicago_IL (PADD 2)", tax: 0.300 },
  WI: { padd: "PADD 2", paddName: "Midwest", hub: "Chicago", model: "Chicago_IL (PADD 2)", tax: 0.309 },
  MN: { padd: "PADD 2", paddName: "Midwest", hub: "Chicago", model: "Chicago_IL (PADD 2)", tax: 0.285 },
  IA: { padd: "PADD 2", paddName: "Midwest", hub: "Tulsa", model: "Tulsa_OK (PADD 2)", tax: 0.300 },
  MO: { padd: "PADD 2", paddName: "Midwest", hub: "Tulsa", model: "Tulsa_OK (PADD 2)", tax: 0.245 },
  KS: { padd: "PADD 2", paddName: "Midwest", hub: "Tulsa", model: "Tulsa_OK (PADD 2)", tax: 0.240 },
  NE: { padd: "PADD 2", paddName: "Midwest", hub: "Tulsa", model: "Tulsa_OK (PADD 2)", tax: 0.296 },
  ND: { padd: "PADD 2", paddName: "Midwest", hub: "Chicago", model: "Chicago_IL (PADD 2)", tax: 0.230 },
  SD: { padd: "PADD 2", paddName: "Midwest", hub: "Tulsa", model: "Tulsa_OK (PADD 2)", tax: 0.280 },
  KY: { padd: "PADD 2", paddName: "Midwest", hub: "Cincinnati", model: "Cincinnati_OH (PADD 2)", tax: 0.287 },
  TN: { padd: "PADD 2", paddName: "Midwest", hub: "Cincinnati", model: "Cincinnati_OH (PADD 2)", tax: 0.274 },
  // PADD 3 (Gulf Coast)
  TX: { padd: "PADD 3", paddName: "Gulf Coast", hub: "Houston", model: "Houston_TX (PADD 3)", tax: 0.200 },
  LA: { padd: "PADD 3", paddName: "Gulf Coast", hub: "Houston", model: "Houston_TX (PADD 3)", tax: 0.200 },
  AR: { padd: "PADD 3", paddName: "Gulf Coast", hub: "Houston", model: "Houston_TX (PADD 3)", tax: 0.248 },
  MS: { padd: "PADD 3", paddName: "Gulf Coast", hub: "Houston", model: "Houston_TX (PADD 3)", tax: 0.184 },
  AL: { padd: "PADD 3", paddName: "Gulf Coast", hub: "Houston", model: "Houston_TX (PADD 3)", tax: 0.290 },
  NM: { padd: "PADD 3", paddName: "Gulf Coast", hub: "Houston", model: "Houston_TX (PADD 3)", tax: 0.189 },
  // PADD 4 (Rocky Mountain)
  CO: { padd: "PADD 4", paddName: "Rocky Mountain", hub: "Denver", model: "Denver_CO (PADD 4)", tax: 0.280 },
  UT: { padd: "PADD 4", paddName: "Rocky Mountain", hub: "Denver", model: "Denver_CO (PADD 4)", tax: 0.365 },
  WY: { padd: "PADD 4", paddName: "Rocky Mountain", hub: "Denver", model: "Denver_CO (PADD 4)", tax: 0.240 },
  MT: { padd: "PADD 4", paddName: "Rocky Mountain", hub: "Denver", model: "Denver_CO (PADD 4)", tax: 0.330 },
  ID: { padd: "PADD 4", paddName: "Rocky Mountain", hub: "Denver", model: "Denver_CO (PADD 4)", tax: 0.320 }
};

function resolveStateFromZipPrefix(prefix3: string): string {
  const p = parseInt(prefix3, 10);
  if (isNaN(p)) return "US";
  if (p >= 6 && p <= 9) return p === 8 ? "VI" : "PR";
  if (p >= 10 && p <= 27) return "MA";
  if (p >= 28 && p <= 29) return "RI";
  if (p >= 30 && p <= 38) return "NH";
  if (p >= 39 && p <= 49) return "ME";
  if (p >= 50 && p <= 59) return "VT";
  if (p >= 60 && p <= 69) return "CT";
  if (p >= 70 && p <= 89) return "NJ";
  if (p >= 100 && p <= 149) return "NY";
  if (p >= 150 && p <= 196) return "PA";
  if (p >= 197 && p <= 199) return "DE";
  if (p >= 200 && p <= 205) return "DC";
  if (p >= 206 && p <= 219) return "MD";
  if (p >= 220 && p <= 246) return "VA";
  if (p >= 247 && p <= 268) return "WV";
  if (p >= 270 && p <= 289) return "NC";
  if (p >= 290 && p <= 299) return "SC";
  if (p >= 300 && p <= 319 || p === 398 || p === 399) return "GA";
  if (p >= 320 && p <= 349) return "FL";
  if (p >= 350 && p <= 369) return "AL";
  if (p >= 370 && p <= 385) return "TN";
  if (p >= 386 && p <= 397) return "MS";
  if (p >= 400 && p <= 427) return "KY";
  if (p >= 430 && p <= 458) return "OH";
  if (p >= 460 && p <= 479) return "IN";
  if (p >= 480 && p <= 499) return "MI";
  if (p >= 500 && p <= 528) return "IA";
  if (p >= 530 && p <= 549) return "WI";
  if (p >= 550 && p <= 567) return "MN";
  if (p >= 570 && p <= 577) return "SD";
  if (p >= 580 && p <= 588) return "ND";
  if (p >= 590 && p <= 599) return "MT";
  if (p >= 600 && p <= 629) return "IL";
  if (p >= 630 && p <= 658) return "MO";
  if (p >= 660 && p <= 679) return "KS";
  if (p >= 680 && p <= 693) return "NE";
  if (p >= 700 && p <= 714) return "LA";
  if (p >= 716 && p <= 729) return "AR";
  if (p >= 730 && p <= 749) return "OK";
  if (p >= 750 && p <= 799) return "TX";
  if (p >= 800 && p <= 816) return "CO";
  if (p >= 820 && p <= 831) return "WY";
  if (p >= 832 && p <= 838) return "ID";
  if (p >= 840 && p <= 847) return "UT";
  if (p >= 850 && p <= 865) return "AZ";
  if (p >= 870 && p <= 884) return "NM";
  if (p >= 889 && p <= 898) return "NV";
  if (p >= 900 && p <= 961) return "CA";
  if (p >= 967 && p <= 968) return "HI";
  if (p === 969) return "GU";
  if (p >= 970 && p <= 979) return "OR";
  if (p >= 980 && p <= 994) return "WA";
  if (p >= 995 && p <= 999) return "AK";
  return "US";
}

export function looksLikeZipCode(rawInput?: string): boolean {
  if (!rawInput) return false;
  const base = String(rawInput).trim().split("-")[0].trim();
  return /^\d{3,5}$/.test(base);
}

export function resolveWorkerZipCode(rawZip: string): WorkerZipResolution {
  const base = String(rawZip || "").trim().split("-")[0].trim();
  if (!/^\d{3,5}$/.test(base)) {
    return {
      status: "fallback",
      zip_code: base.slice(0, 5),
      prefix_3: "",
      resolution_tier: "INVALID_INPUT_FALLBACK",
      is_metro_cluster_hit: false,
      locale_code: "national",
      canonical_hub: "National",
      location_name: `ZIP ${base.slice(0, 5)} (US)`,
      state: "US",
      padd_region: "PADD 2",
      padd_name: "Midwest",
      calibrated_model_used: "National Wholesale",
      state_tax_rate_per_gal: 0.184,
      hub_baseline_tax_rate: 0.184,
      tax_delta_per_gal: 0.0,
      is_significant_departure: false,
      departure_reason: "",
      estimated_basis_delta: 0.0
    };
  }

  const zipClean = base.padStart(5, "0").slice(0, 5);
  const prefix3 = zipClean.slice(0, 3);
  const stateCode = resolveStateFromZipPrefix(prefix3);
  const stateMeta = WORKER_STATE_PADD_MAP[stateCode] || {
    padd: "PADD 2",
    paddName: "Midwest",
    hub: "National",
    model: "National Wholesale",
    tax: 0.250
  };

  const locName = resolveWorkerLocationName(zipClean, prefix3, stateCode);

  if (prefix3 in WORKER_ZIP_METRO_PREFIX_MAP) {
    const metroHub = WORKER_ZIP_METRO_PREFIX_MAP[prefix3];
    const hubTax = WORKER_HUB_BASELINE_TAXES[metroHub] || 0.250;
    return {
      status: "success",
      zip_code: zipClean,
      prefix_3: prefix3,
      resolution_tier: "METRO_CLUSTER_HIT",
      is_metro_cluster_hit: true,
      locale_code: metroHub.toLowerCase(),
      canonical_hub: metroHub,
      location_name: locName,
      state: stateCode,
      padd_region: stateMeta.padd,
      padd_name: stateMeta.paddName,
      calibrated_model_used: `${metroHub} (Direct Metro Cluster)`,
      state_tax_rate_per_gal: stateMeta.tax,
      hub_baseline_tax_rate: hubTax,
      tax_delta_per_gal: 0.0,
      is_significant_departure: false,
      departure_reason: "",
      estimated_basis_delta: 0.0
    };
  }

  const fallbackHub = stateMeta.hub;
  const hubTax = WORKER_HUB_BASELINE_TAXES[fallbackHub] || 0.250;
  const taxDelta = Number((stateMeta.tax - hubTax).toFixed(3));
  const isDeparture = Math.abs(taxDelta) >= 0.15;

  let departureReason = "";
  if (isDeparture) {
    departureReason = `Statutory tax wedge of ${taxDelta >= 0 ? "+" : ""}${taxDelta.toFixed(3)}/gal vs hub baseline (${fallbackHub})`;
  }

  const estBasis = Number(taxDelta.toFixed(3));

  return {
    status: "success",
    zip_code: zipClean,
    prefix_3: prefix3,
    resolution_tier: "STATE_PADD_FALLBACK",
    is_metro_cluster_hit: false,
    locale_code: fallbackHub.toLowerCase(),
    canonical_hub: fallbackHub,
    location_name: locName,
    state: stateCode,
    padd_region: stateMeta.padd,
    padd_name: stateMeta.paddName,
    calibrated_model_used: stateMeta.model,
    state_tax_rate_per_gal: stateMeta.tax,
    hub_baseline_tax_rate: hubTax,
    tax_delta_per_gal: taxDelta,
    is_significant_departure: isDeparture,
    departure_reason: departureReason,
    estimated_basis_delta: estBasis,
    tracking_issue_number: null
  };
}

export async function maybeTriggerHubDepartureIssue(
  res: WorkerZipResolution,
  env: Env
): Promise<{ triggered: boolean; issueNumber?: number; issueUrl?: string }> {
  if (!res.is_significant_departure || res.is_metro_cluster_hit) {
    return { triggered: false };
  }

  const cacheKey = res.state;
  const cached = WORKER_DEPARTURE_ISSUES_CACHE.get(cacheKey);
  if (cached) {
    return { triggered: true, issueNumber: cached.issueNumber, issueUrl: cached.issueUrl };
  }

  const d1Key = `departure_issue:${res.state}`;
  if (env.DB) {
    try {
      await ensureFlagReplaySchema(env);
      const row = await env.DB.prepare("SELECT value FROM flag_replay_tokens WHERE clean_key = ?").bind(d1Key).first();
      if (row && (row as any).value) {
        const parsed = JSON.parse((row as any).value) as { issue_number: number; issue_url: string };
        WORKER_DEPARTURE_ISSUES_CACHE.set(cacheKey, { issueNumber: parsed.issue_number, issueUrl: parsed.issue_url });
        return { triggered: true, issueNumber: parsed.issue_number, issueUrl: parsed.issue_url };
      }
    } catch (e) {
      console.warn("[Departure Issue D1 Query Error]", e);
    }
  }

  const token = (env as any).GH_PAT || (env as any).GITHUB_PAT || (env as any).GITHUB_TOKEN;
  if (!token) {
    return { triggered: false };
  }

  const owner = "KoshiirRa";
  const repo = "midgley";
  const title = `feat(regions): Implement ${res.state} Regional Calibration Hub (Triggered by Out-of-Metro Demand for ZIP ${res.zip_code})`;
  const body = `### 📮 Automated Region Departure Trigger\n` +
    `A subscriber requested shock notifications for **ZIP ${res.zip_code} (${res.location_name})**, which departs significantly from its current PADD calibration hub (**${res.calibrated_model_used}**).\n\n` +
    `### 📊 Calibration Gap Diagnostics\n` +
    `- **Requested Location:** \`${res.location_name}\` (ZIP \`${res.zip_code}\`, \`${res.state}\`)\n` +
    `- **Assigned Fallback Hub:** \`${res.canonical_hub}\` (\`${res.calibrated_model_used}\`)\n` +
    `- **State Statutory Tax:** \`$${res.state_tax_rate_per_gal.toFixed(3)}/gal\`\n` +
    `- **Hub Baseline Tax:** \`$${res.hub_baseline_tax_rate.toFixed(3)}/gal\`\n` +
    `- **Statutory Tax Wedge (Δτ):** \`${res.tax_delta_per_gal >= 0 ? "+" : ""}$${res.tax_delta_per_gal.toFixed(3)}/gal\`\n` +
    `- **Estimated Basis Spread:** \`${res.estimated_basis_delta >= 0 ? "+" : ""}$${res.estimated_basis_delta.toFixed(2)}/gal\` over rack\n` +
    `- **Departure Reason:** ${res.departure_reason}\n\n` +
    `### 🎯 Action Item\n` +
    `Evaluate adding a native regional calibration hub for **${res.state}** (or incorporating a sub-PADD basis adjustment model) to prevent pricing distortion when serving out-of-metro subscribers.`;

  try {
    const postRes = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "User-Agent": "Midgley-Discord-Worker",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        title,
        body,
        labels: ["enhancement", "modeling", "regions"]
      })
    });

    if (postRes.ok) {
      const issueData: any = await postRes.json();
      const issueNumber = issueData.number as number;
      const issueUrl = issueData.html_url as string;

      WORKER_DEPARTURE_ISSUES_CACHE.set(cacheKey, { issueNumber, issueUrl });
      if (env.DB) {
        try {
          await ensureFlagReplaySchema(env);
          await env.DB.prepare("INSERT INTO flag_replay_tokens (clean_key, value, used_at) VALUES (?, ?, datetime('now')) ON CONFLICT(clean_key) DO UPDATE SET value = excluded.value")
            .bind(d1Key, JSON.stringify({ issue_number: issueNumber, issue_url: issueUrl, created_at: new Date().toISOString() }))
            .run();
        } catch (dbErr) {
          console.warn("[Departure Issue D1 Store Error]", dbErr);
        }
      }
      return { triggered: true, issueNumber, issueUrl };
    }
  } catch (err) {
    console.warn("[Departure Issue Creation Error]", err);
  }

  return { triggered: false };
}

export async function recordWorkerUnmappedZip(res: WorkerZipResolution, env: Env): Promise<void> {
  if (res.is_metro_cluster_hit || res.resolution_tier === "INVALID_INPUT_FALLBACK") {
    return;
  }
  const nowIso = new Date().toISOString();
  const zKey = res.zip_code;
  const existingMem = WORKER_UNMAPPED_ZIPS.get(zKey);

  let record: WorkerUnmappedZipTelemetryRecord = existingMem
    ? {
        ...existingMem,
        hit_count: existingMem.hit_count + 1,
        last_searched_at: nowIso
      }
    : {
        zip_code: zKey,
        state: res.state,
        padd_region: res.padd_region,
        calibrated_model_used: res.calibrated_model_used,
        hit_count: 1,
        first_searched_at: nowIso,
        last_searched_at: nowIso
      };

  if (env.DB) {
    try {
      await ensureFlagReplaySchema(env);
      const dbKey = `unmapped_zip:${zKey}`;
      const row = await env.DB.prepare("SELECT value FROM flag_replay_tokens WHERE clean_key = ?").bind(dbKey).first();
      if (row && (row as any).value) {
        const parsed = JSON.parse((row as any).value) as WorkerUnmappedZipTelemetryRecord;
        record = {
          ...parsed,
          hit_count: (parsed.hit_count || 0) + 1,
          last_searched_at: nowIso
        };
      }
      await env.DB.prepare(
        "INSERT INTO flag_replay_tokens (clean_key, value, used_at) VALUES (?, ?, datetime('now')) ON CONFLICT(clean_key) DO UPDATE SET value = excluded.value"
      )
        .bind(dbKey, JSON.stringify(record))
        .run();
    } catch (d1Err: any) {
      console.warn(`[D1 RecordUnmappedZip Notice] ${d1Err?.message || String(d1Err)}`);
    }
  }
  WORKER_UNMAPPED_ZIPS.set(zKey, record);
}

export async function getWorkerUnmappedZips(env: Env): Promise<WorkerUnmappedZipTelemetryRecord[]> {
  const merged = new Map<string, WorkerUnmappedZipTelemetryRecord>(WORKER_UNMAPPED_ZIPS);
  if (env.DB) {
    try {
      await ensureFlagReplaySchema(env);
      const res = await env.DB.prepare(
        "SELECT value FROM flag_replay_tokens WHERE clean_key LIKE 'unmapped_zip:%'"
      ).all();
      const rows = (res?.results || []) as Array<{ value?: string }>;
      for (const r of rows) {
        if (!r.value) continue;
        const parsed = JSON.parse(r.value) as WorkerUnmappedZipTelemetryRecord;
        if (parsed && parsed.zip_code) {
          merged.set(parsed.zip_code, parsed);
        }
      }
    } catch (d1Err: any) {
      console.warn(`[D1 GetUnmappedZips Notice] ${d1Err?.message || String(d1Err)}`);
    }
  }
  return Array.from(merged.values()).sort((a, b) => b.hit_count - a.hit_count);
}

export function normalizeWorkerLocale(rawLocale?: string): string {
  if (!rawLocale) return "National";
  if (looksLikeZipCode(rawLocale)) {
    return resolveWorkerZipCode(rawLocale).canonical_hub;
  }
  const clean = rawLocale.trim().toLowerCase().replace(/[\s.-]+/g, "_");
  const aliases: Record<string, string> = {
    national: "National",
    us: "National",
    tulsa: "Tulsa",
    tulsa_ok: "Tulsa",
    newark: "Newark",
    newark_de: "Newark",
    cincinnati: "Cincinnati",
    cincinnati_oh: "Cincinnati",
    cincinnati_ky: "Cincinnati",
    greenville: "Greenville",
    greenville_nc: "Greenville",
    charlotte: "Charlotte",
    charlotte_nc: "Charlotte",
    oakland: "Oakland",
    oakland_ca: "Oakland",
    bay_area: "Oakland",
    bayarea: "Oakland",
    sf: "Oakland",
    port_st_lucie: "Port_St_Lucie",
    port_st_lucie_fl: "Port_St_Lucie",
    psl: "Port_St_Lucie",
    chicago: "Chicago",
    chicago_il: "Chicago",
    houston: "Houston",
    houston_tx: "Houston",
    los_angeles: "Los_Angeles",
    los_angeles_ca: "Los_Angeles",
    la: "Los_Angeles",
    denver: "Denver",
    denver_co: "Denver",
    rocky_mountain: "Denver",
    padd4: "Denver",
    padd_4: "Denver",
    new_york: "New_York",
    new_york_ny: "New_York",
    nyc: "New_York",
    ny: "New_York",
    ny_harbor: "New_York",
    ny_state: "New_York",
    new_york_metro: "New_York",
    boston: "Boston",
    boston_ma: "Boston",
    bos: "Boston",
    new_england: "Boston",
    padd1a: "Boston",
    padd_1a: "Boston",
    seattle: "Seattle",
    seattle_wa: "Seattle",
    puget_sound: "Seattle",
    pnw: "Seattle",
    phoenix: "Phoenix",
    phoenix_az: "Phoenix",
    desert_southwest: "Phoenix",
    phx: "Phoenix",
    anchorage: "Anchorage",
    anchorage_ak: "Anchorage",
    alaska: "Anchorage",
    honolulu: "Honolulu",
    honolulu_hi: "Honolulu",
    hawaii: "Honolulu",
    oahu: "Honolulu",
    guam: "Guam",
    guam_gu: "Guam",
    padd7: "Guam",
    padd_7: "Guam",
    san_juan: "San_Juan",
    san_juan_pr: "San_Juan",
    puerto_rico: "San_Juan",
    pr: "San_Juan",
    padd6: "San_Juan",
    padd_6: "San_Juan"
  };
  return aliases[clean] || SUPPORTED_DISCORD_LOCALES.find(l => l.value.toLowerCase() === clean)?.value || "National";
}

export async function getWorkerUserSubscription(userId: string, env: Env): Promise<WorkerDMSubscriptionRecord | null> {
  if (WORKER_DM_SUBSCRIPTIONS.has(userId)) {
    return WORKER_DM_SUBSCRIPTIONS.get(userId) || null;
  }
  if (env.DB) {
    const key = `discord_sub:${userId}`;
    try {
      await ensureFlagReplaySchema(env);
      const row = await env.DB.prepare("SELECT value FROM flag_replay_tokens WHERE clean_key = ?").bind(key).first();
      if (row && (row as any).value) {
        const parsed = JSON.parse((row as any).value) as WorkerDMSubscriptionRecord;
        WORKER_DM_SUBSCRIPTIONS.set(userId, parsed);
        return parsed;
      }
    } catch (d1Err: any) {
      console.warn(`[D1 Subscription Get Retry] ${d1Err?.message || String(d1Err)}`);
      try {
        flagReplaySchemaInitialized = false;
        await ensureFlagReplaySchema(env);
        const row = await env.DB.prepare("SELECT value FROM flag_replay_tokens WHERE clean_key = ?").bind(key).first();
        if (row && (row as any).value) {
          const parsed = JSON.parse((row as any).value) as WorkerDMSubscriptionRecord;
          WORKER_DM_SUBSCRIPTIONS.set(userId, parsed);
          return parsed;
        }
      } catch (retryErr: any) {
        console.error(`[D1 Subscription Get Failed] ${retryErr?.message || String(retryErr)}`);
      }
    }
  }
  return null;
}

export async function getAllWorkerSubscriptions(env: Env): Promise<WorkerDMSubscriptionRecord[]> {
  const merged = new Map<string, WorkerDMSubscriptionRecord>(WORKER_DM_SUBSCRIPTIONS);
  if (env.DB) {
    try {
      await ensureFlagReplaySchema(env);
      const res = await env.DB.prepare(
        "SELECT value FROM flag_replay_tokens WHERE clean_key LIKE 'discord_sub:%'"
      ).all();
      const rows = (res?.results || []) as Array<{ value?: string }>;
      for (const r of rows) {
        if (!r.value) continue;
        const parsed = JSON.parse(r.value) as WorkerDMSubscriptionRecord;
        if (parsed && parsed.discord_user_id) {
          merged.set(parsed.discord_user_id, parsed);
        }
      }
    } catch (d1Err: any) {
      console.warn(`[D1 GetAllSubscriptions Notice] ${d1Err?.message || String(d1Err)}`);
    }
  }
  return Array.from(merged.values());
}

export async function saveWorkerUserSubscription(record: WorkerDMSubscriptionRecord, env: Env): Promise<void> {
  WORKER_DM_SUBSCRIPTIONS.set(record.discord_user_id, record);
  if (env.DB) {
    const key = `discord_sub:${record.discord_user_id}`;
    const valueJson = JSON.stringify(record);
    try {
      await ensureFlagReplaySchema(env);
      await env.DB.prepare(
        "INSERT INTO flag_replay_tokens (clean_key, value, used_at) VALUES (?, ?, datetime('now')) ON CONFLICT(clean_key) DO UPDATE SET value = excluded.value"
      )
        .bind(key, valueJson)
        .run();
    } catch (d1Err: any) {
      console.warn(`[D1 Subscription Save Retry] ${d1Err?.message || String(d1Err)}`);
      try {
        flagReplaySchemaInitialized = false;
        await ensureFlagReplaySchema(env);
        await env.DB.prepare(
          "INSERT INTO flag_replay_tokens (clean_key, value, used_at) VALUES (?, ?, datetime('now')) ON CONFLICT(clean_key) DO UPDATE SET value = excluded.value"
        )
          .bind(key, valueJson)
          .run();
      } catch (retryErr: any) {
        console.error(`[D1 Subscription Save Failed] ${retryErr?.message || String(retryErr)}`);
      }
    }
  }
}

export async function deleteWorkerUserSubscription(userId: string, env: Env): Promise<void> {
  WORKER_DM_SUBSCRIPTIONS.delete(userId);
  if (env.DB) {
    try {
      await ensureFlagReplaySchema(env);
      const key = `discord_sub:${userId}`;
      await env.DB.prepare("DELETE FROM flag_replay_tokens WHERE clean_key = ?").bind(key).run();
    } catch (d1Err: any) {
      console.warn(`[D1 DeleteSubscription Notice] ${d1Err?.message || String(d1Err)}`);
    }
  }
}


export async function sendDiscordDirectMessage(
  userId: string,
  payload: Record<string, any>,
  env: Env,
  existingChannelId?: string | null
): Promise<{ sent: boolean; dmChannelId?: string | null; blockedByPrivacy?: boolean; error?: string }> {
  const botToken = (env.DISCORD_BOT_TOKEN || "").trim();
  if (!botToken) {
    return { sent: false, dmChannelId: existingChannelId, error: "DISCORD_BOT_TOKEN unconfigured" };
  }

  let dmChannelId = existingChannelId || null;
  try {
    if (!dmChannelId) {
      const createRes = await fetch("https://discord.com/api/v10/users/@me/channels", {
        method: "POST",
        headers: {
          "Authorization": `Bot ${botToken}`,
          "Content-Type": "application/json",
          "User-Agent": "Midgley-Discord-Worker/1.0"
        },
        body: JSON.stringify({ recipient_id: userId })
      });
      if (!createRes.ok) {
        const errText = await createRes.text();
        const isPrivacyBlock = createRes.status === 403 || errText.includes("50007");
        return {
          sent: false,
          blockedByPrivacy: isPrivacyBlock,
          error: `DM channel open HTTP ${createRes.status}: ${errText}`
        };
      }
      const chData: any = await createRes.json();
      dmChannelId = chData.id || null;
    }

    if (!dmChannelId) {
      return { sent: false, error: "Could not resolve Discord DM channel ID" };
    }

    const msgRes = await fetch(`https://discord.com/api/v10/channels/${dmChannelId}/messages`, {
      method: "POST",
      headers: {
        "Authorization": `Bot ${botToken}`,
        "Content-Type": "application/json",
        "User-Agent": "Midgley-Discord-Worker/1.0"
      },
      body: JSON.stringify(payload)
    });

    if (!msgRes.ok) {
      const errText = await msgRes.text();
      const isPrivacyBlock = msgRes.status === 403 || errText.includes("50007");
      return {
        sent: false,
        dmChannelId,
        blockedByPrivacy: isPrivacyBlock,
        error: `DM message HTTP ${msgRes.status}: ${errText}`
      };
    }

    return { sent: true, dmChannelId };
  } catch (err: any) {
    return { sent: false, dmChannelId, error: err?.message || String(err) };
  }
}

function extractCommandOptions(interaction: any): { subcommand: string; options: Record<string, any> } {
  const rawOptions = interaction.data?.options || [];
  const opts: Record<string, any> = {};
  let subcommand = "";

  if (rawOptions.length > 0 && rawOptions[0].type === 1) {
    subcommand = rawOptions[0].name;
    for (const subOpt of rawOptions[0].options || []) {
      opts[subOpt.name] = subOpt.value;
    }
  } else {
    subcommand = interaction.data?.name || "";
    for (const opt of rawOptions) {
      opts[opt.name] = opt.value;
    }
  }
  return { subcommand: subcommand.toLowerCase(), options: opts };
}

export function hexToUint8Array(hex: string): Uint8Array {
  const match = hex.match(/.{1,2}/g);
  return new Uint8Array(match ? match.map(byte => parseInt(byte, 16)) : []);
}

export function verifyDiscordSignature(
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

export async function handleDiscordInteraction(request: Request, env: Env, ctx: any): Promise<Response> {
  const signature = request.headers.get("X-Signature-Ed25519");
  const timestamp = request.headers.get("X-Signature-Timestamp");

  if (!signature || !timestamp) {
    return new Response("Missing signature headers", { status: 401 });
  }

  const now = Math.floor(Date.now() / 1000);
  const reqTime = parseInt(timestamp, 10);
  if (isNaN(reqTime) || Math.abs(now - reqTime) > 300) {
    return new Response("Expired or invalid timestamp", { status: 401 });
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

  // Type 4: APPLICATION_COMMAND_AUTOCOMPLETE (Autocomplete for `locale` or `zip_code` parameter)
  if (interaction.type === 4) {
    const { options } = extractCommandOptions(interaction);
    const rawQuery = String(options.locale || options.zip_code || "").trim();
    const query = rawQuery.toLowerCase();
    const choices: Array<{ name: string; value: string }> = [];

    if (looksLikeZipCode(rawQuery)) {
      const zRes = resolveWorkerZipCode(rawQuery);
      const tierLabel = zRes.is_metro_cluster_hit
        ? `Direct Metro Cluster → ${zRes.canonical_hub}`
        : `${zRes.padd_region} ${zRes.padd_name} Corridor → via ${zRes.canonical_hub}`;
      choices.push({
        name: `📮 ZIP ${zRes.zip_code} (${zRes.state} • ${tierLabel})`,
        value: zRes.zip_code
      });
    }

    const localeChoices = SUPPORTED_DISCORD_LOCALES.filter(
      l => !query || l.name.toLowerCase().includes(query) || l.value.toLowerCase().includes(query)
    )
      .slice(0, 25 - choices.length)
      .map(l => ({ name: l.name, value: l.value }));

    choices.push(...localeChoices);
    return new Response(JSON.stringify({ type: 8, data: { choices } }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  // Type 2: APPLICATION_COMMAND (`/midgley subscribe`, `unsubscribe`, `status`, `forecast`, `test-alert`)
  if (interaction.type === 2) {
    const userObj = interaction.member?.user || interaction.user || {};
    const userId = String(userObj.id || "anonymous_user");
    const username = String(userObj.username || "Discord User");
    const { subcommand, options } = extractCommandOptions(interaction);

    if (subcommand === "subscribe") {
      const rawInput = String(options.zip_code || options.locale || "National").trim();
      const isZip = looksLikeZipCode(rawInput);
      const zipRes = isZip ? resolveWorkerZipCode(rawInput) : null;
      if (zipRes) {
        await recordWorkerUnmappedZip(zipRes, env);
      }

      const locale = zipRes ? zipRes.canonical_hub : normalizeWorkerLocale(rawInput);
      const minShock = typeof options.min_shock === "number" ? Math.max(0, Math.min(5, options.min_shock)) : 0.25;
      const direction = String(options.direction || "all_shocks").toLowerCase();
      const delivery = String(options.delivery || "dm").toLowerCase();

      const depIssue = zipRes ? await maybeTriggerHubDepartureIssue(zipRes, env) : null;

      const existing = await getWorkerUserSubscription(userId, env);
      const mergedLocales = existing?.target_locales ? Array.from(new Set([...existing.target_locales, locale])) : [locale];
      const mergedZips = existing?.zip_codes ? [...existing.zip_codes] : [];
      if (zipRes && !mergedZips.includes(zipRes.zip_code)) {
        mergedZips.push(zipRes.zip_code);
      }
      const subId = existing?.subscription_id || `sub_dm_${userId.slice(-8)}`;

      const targetDisplayName = zipRes ? zipRes.location_name : mergedLocales.join(", ");

      const embedFields: Array<{ name: string; value: string; inline: boolean }> = [
        { name: "📍 Subscribed Location", value: `\`${targetDisplayName}\``, inline: true },
        { name: "🛢️ Wholesale Supply Corridor", value: `\`${zipRes ? `${zipRes.padd_region} (${zipRes.padd_name})` : mergedLocales.join(", ")}\``, inline: true },
        { name: "⚡ Min Shock (|ΔP|)", value: `\`>= $${minShock.toFixed(2)}/gal\``, inline: true },
        { name: "🧭 Direction Bias", value: `\`${direction}\``, inline: true },
        { name: "📬 Delivery Channel", value: delivery === "dm" ? "`Private Direct Message (DM)`" : "`Ephemeral Server Reply`", inline: true }
      ];

      if (zipRes) {
        const tierBadge = zipRes.is_metro_cluster_hit
          ? `Direct Metro Cluster Hit (\`${zipRes.canonical_hub}\` • \`${zipRes.resolution_tier}\`)`
          : `${zipRes.padd_region} ${zipRes.padd_name} Corridor Fallback (routed via \`${zipRes.canonical_hub}\` • \`${zipRes.resolution_tier}\`)`;
        const taxDetails = zipRes.tax_delta_per_gal !== 0
          ? `State Tax: \`$${zipRes.state_tax_rate_per_gal.toFixed(3)}/gal\` (Coastal Base: \`$${zipRes.hub_baseline_tax_rate.toFixed(3)}/gal\` • Wedge: \`${zipRes.tax_delta_per_gal >= 0 ? "+" : ""}$${zipRes.tax_delta_per_gal.toFixed(3)}/gal\`)`
          : `State Tax: \`$${zipRes.state_tax_rate_per_gal.toFixed(3)}/gal\``;

        embedFields.push({
          name: "📮 Subscribed ZIP Code Routing",
          value: `\`${zipRes.location_name}\` (ZIP \`${zipRes.zip_code}\`, ${zipRes.state}) • ${tierBadge}\n${taxDetails}`,
          inline: false
        });

        if (zipRes.is_significant_departure) {
          const wedgeSign = zipRes.tax_delta_per_gal >= 0 ? "+" : "";
          const basisSign = zipRes.estimated_basis_delta >= 0 ? "+" : "";
          embedFields.push({
            name: "⚠️ Regional Basis & Tax Departure",
            value: `State fuel taxes in **${zipRes.state}** (\`$${zipRes.state_tax_rate_per_gal.toFixed(3)}/gal\`) depart from the \`${zipRes.canonical_hub}\` coastal rack baseline (\`$${zipRes.hub_baseline_tax_rate.toFixed(3)}/gal\`) by \`${wedgeSign}$${zipRes.tax_delta_per_gal.toFixed(3)}/gal\`. Local pump prices trade at an estimated \`${basisSign}$${zipRes.estimated_basis_delta.toFixed(2)}/gal\` basis spread over coastal rack benchmarks. Shock alerts (|ΔP|) will track wholesale transmission from **${zipRes.padd_name}** wholesale racks.`,
            inline: false
          });

          if (depIssue?.issueNumber) {
            embedFields.push({
              name: "🏛️ Regional Calibration Hub Tracking",
              value: `A dedicated calibration hub tracking issue is open on the Midgley repository: [#${depIssue.issueNumber}](${depIssue.issueUrl || `https://github.com/KoshiirRa/midgley/issues/${depIssue.issueNumber}`})`,
              inline: false
            });
          }
        }
      } else if (mergedZips.length > 0) {
        embedFields.push({
          name: "📮 Active ZIP Codes",
          value: `\`${mergedZips.join(", ")}\``,
          inline: true
        });
      }

      const embed = {
        title: zipRes ? `✅ Midgley Alert Subscription Active — ${zipRes.location_name}` : "✅ Midgley Direct Message Alert Subscription Active",
        description: `Subscribed **@${username}** to real-time intraday gasoline shock alerts without cluttering shared server chat.`,
        url: "https://koshiirRa.github.io/midgley/",
        color: 3066993,
        fields: embedFields,
        footer: { text: `Midgley Notification Gateway • Subscription ID: ${subId}` },
        timestamp: new Date().toISOString()
      };

      let dmResult: { sent: boolean; dmChannelId?: string | null; blockedByPrivacy?: boolean; error?: string } = {
        sent: false
      };
      if (delivery === "dm") {
        dmResult = await sendDiscordDirectMessage(userId, { embeds: [embed] }, env, existing?.dm_channel_id);
      }

      const subRecord: WorkerDMSubscriptionRecord = {
        subscription_id: subId,
        discord_user_id: userId,
        dm_channel_id: dmResult.dmChannelId || existing?.dm_channel_id || null,
        target_locales: mergedLocales,
        zip_codes: mergedZips,
        min_shock_threshold: minShock,
        direction_filter: direction,
        delivery_mode: "realtime",
        is_active: true,
        muted_until: null,
        created_at: existing?.created_at || new Date().toISOString()
      };
      await saveWorkerUserSubscription(subRecord, env);

      const privacyNotice = dmResult.blockedByPrivacy
        ? "\n⚠️ **Note:** Could not open a Direct Message because your Discord privacy settings block DMs from server members (`Error 50007`). Please enable **Allow Direct Messages from server members** in this server's Privacy Settings so background alerts can reach your inbox."
        : dmResult.sent
        ? "\n📬 *A confirmation card has been delivered to your Direct Messages.*"
        : "";

      const zipSummary = zipRes
        ? ` (ZIP \`${zipRes.zip_code}\` → \`${zipRes.canonical_hub}\` • \`${zipRes.resolution_tier}\`${zipRes.is_metro_cluster_hit ? "" : " • logged to Out-of-Metro Demand Heatmap"})`
        : "";
      const issueNote = depIssue?.issueNumber ? ` • [Hub Issue #${depIssue.issueNumber}]` : "";

      return new Response(
        JSON.stringify({
          type: 4,
          data: {
            flags: 64, // Ephemeral: only visible to the command caller
            content: `✅ **Subscription updated for \`${targetDisplayName}\`${zipSummary}** (|ΔP| >= $${minShock.toFixed(2)}/gal, \`${direction}\`)${issueNote}.${privacyNotice}`,
            embeds: [embed]
          }
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    if (subcommand === "unsubscribe") {
      const rawLocale = options.zip_code ? String(options.zip_code).trim() : options.locale ? String(options.locale).trim() : "all";
      const existing = await getWorkerUserSubscription(userId, env);
      if (!existing || !existing.is_active) {
        return new Response(
          JSON.stringify({
            type: 4,
            data: {
              flags: 64,
              content: "ℹ️ You do not currently have any active Midgley Direct Message alert subscriptions."
            }
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      }

      if (rawLocale.toLowerCase() === "all") {
        await deleteWorkerUserSubscription(userId, env);
        return new Response(
          JSON.stringify({
            type: 4,
            data: {
              flags: 64,
              content: "🗑️ **Unsubscribed** from all Midgley Direct Message intraday shock alerts."
            }
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      }

      if (looksLikeZipCode(rawLocale) && existing.zip_codes && existing.zip_codes.length > 0) {
        const zClean = resolveWorkerZipCode(rawLocale).zip_code;
        if (existing.zip_codes.includes(zClean)) {
          existing.zip_codes = existing.zip_codes.filter(z => z !== zClean);
          await saveWorkerUserSubscription(existing, env);
          return new Response(
            JSON.stringify({
              type: 4,
              data: {
                flags: 64,
                content: `✅ Removed ZIP \`${zClean}\` from your subscription. Active hubs: \`${existing.target_locales.join(", ")}\`.`
              }
            }),
            { headers: { "Content-Type": "application/json" } }
          );
        }
      }

      const targetLoc = normalizeWorkerLocale(rawLocale);
      const remaining = existing.target_locales.filter(l => l !== targetLoc);
      if (remaining.length === 0) {
        await deleteWorkerUserSubscription(userId, env);
      } else {
        existing.target_locales = remaining;
        await saveWorkerUserSubscription(existing, env);
      }

      return new Response(
        JSON.stringify({
          type: 4,
          data: {
            flags: 64,
            content:
              remaining.length > 0
                ? `✅ Removed \`${targetLoc}\` from your DM alerts. Remaining subscribed hubs: \`${remaining.join(", ")}\`.`
                : `🗑️ Removed \`${targetLoc}\`. You have no remaining active DM subscriptions.`
          }
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    if (subcommand === "status") {
      const existing = await getWorkerUserSubscription(userId, env);
      const statusFields =
        existing && existing.is_active
          ? [
              { name: "🆔 Subscription ID", value: `\`${existing.subscription_id}\``, inline: true },
              { name: "📍 Subscribed Hubs", value: `\`${existing.target_locales.join(", ")}\``, inline: true },
              ...(existing.zip_codes && existing.zip_codes.length > 0
                ? [{ name: "📮 Subscribed ZIPs", value: `\`${existing.zip_codes.join(", ")}\``, inline: true }]
                : []),
              { name: "⚡ Shock Threshold", value: `\`>= $${existing.min_shock_threshold.toFixed(2)}/gal\``, inline: true },
              { name: "🧭 Direction Filter", value: `\`${existing.direction_filter}\``, inline: true },
              { name: "🔕 Mute Status", value: existing.muted_until ? `\`Muted until ${existing.muted_until}\`` : "`Active (Unmuted)`", inline: true }
            ]
          : [
              {
                name: "💡 Quick Start",
                value: "Run `/midgley subscribe locale:Tulsa min_shock:0.25` or `/midgley subscribe locale:74103` to receive private DM alerts.",
                inline: false
              }
            ];

      const statusEmbed = {
        title: "📊 Midgley Discord Alert Subscription Status",
        description: existing && existing.is_active
          ? `Active Direct Message alert profile for **@${username}**:`
          : `No active Direct Message subscriptions found for **@${username}**. Use \`/midgley subscribe\` to register.`,
        url: "https://koshiirRa.github.io/midgley/",
        color: existing && existing.is_active ? 3447003 : 9807270,
        fields: statusFields,
        timestamp: new Date().toISOString()
      };

      const dmRes = await sendDiscordDirectMessage(userId, { embeds: [statusEmbed] }, env, existing?.dm_channel_id);
      return new Response(
        JSON.stringify({
          type: 4,
          data: {
            flags: 64,
            content: dmRes.sent ? "📬 Sent your subscription status card via Direct Message." : undefined,
            embeds: [statusEmbed]
          }
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    if (subcommand === "forecast") {
      const rawInput = String(options.zip_code || options.locale || "National").trim();
      const isZip = looksLikeZipCode(rawInput);
      const zipRes = isZip ? resolveWorkerZipCode(rawInput) : null;
      if (zipRes) {
        await recordWorkerUnmappedZip(zipRes, env);
      }

      const locale = zipRes ? zipRes.canonical_hub : normalizeWorkerLocale(rawInput);
      const horizon = Math.min(5, Math.max(1, Number(options.horizon || 5)));
      const localeMeta = SUPPORTED_DISCORD_LOCALES.find(l => l.value === locale) || SUPPORTED_DISCORD_LOCALES[0];
      const dashboardUrl = `https://koshiirRa.github.io/midgley/${localeMeta.slug}`;
      const targetDisplayName = zipRes ? zipRes.location_name : locale.replace(/_/g, " ");

      const rawForecast = await getWorkerForecastData(locale, horizon, env);

      const basisAdj = zipRes ? zipRes.estimated_basis_delta : 0;
      const effectiveBasePrice = Number((rawForecast.basePrice + basisAdj).toFixed(3));
      const effectivePredictedPrice = Number((rawForecast.predictedPrice + basisAdj).toFixed(3));
      const effectiveLower95 = Number((rawForecast.lower95ci + basisAdj).toFixed(3));
      const effectiveUpper95 = Number((rawForecast.upper95ci + basisAdj).toFixed(3));
      const effectiveDelta = Number((effectivePredictedPrice - effectiveBasePrice).toFixed(3));
      const effectivePct = effectiveBasePrice > 0 ? Number(((effectiveDelta / effectiveBasePrice) * 100).toFixed(2)) : 0;
      const effectiveTrajectory = rawForecast.trajectory.map(t => ({
        day: t.day,
        price: Number((t.price + basisAdj).toFixed(3))
      }));

      let dirEmoji = "➔ FLAT";
      if (effectiveDelta > 0.005) {
        dirEmoji = "↗ UP";
      } else if (effectiveDelta < -0.005) {
        dirEmoji = "↘ DOWN";
      }

      const forecastFields: Array<{ name: string; value: string; inline: boolean }> = [
        { name: "📍 Target Location", value: `\`${targetDisplayName}\``, inline: true },
        { name: "🛢️ PADD Supply Corridor", value: `\`${zipRes ? `${zipRes.padd_region} (${zipRes.padd_name})` : localeMeta.padd}\``, inline: true },
        { name: "📅 Forecast Horizon", value: `\`1D – ${horizon}D Out-of-Time\``, inline: true },

        {
          name: `⛽ Projected Pump Price (${horizon}D)`,
          value: `**$${effectivePredictedPrice.toFixed(3)}/gal**`,
          inline: true
        },
        {
          name: "📊 Expected Shift (ΔP)",
          value: `\`${effectiveDelta >= 0 ? "+" : ""}$${effectiveDelta.toFixed(3)}/gal\` (\`${effectivePct >= 0 ? "+" : ""}${effectivePct.toFixed(2)}%\`) ${dirEmoji}`,
          inline: true
        },
        {
          name: "🎯 95% Confidence Interval",
          value: `\`$${effectiveLower95.toFixed(3)} – $${effectiveUpper95.toFixed(3)}/gal\``,
          inline: true
        },

        {
          name: "🏷️ Current Base Price",
          value: zipRes && zipRes.estimated_basis_delta !== 0
            ? `\`$${effectiveBasePrice.toFixed(3)}/gal\` (vs \`$${rawForecast.basePrice.toFixed(3)}\` ${zipRes.canonical_hub} hub)`
            : `\`$${effectiveBasePrice.toFixed(3)}/gal\` (${localeMeta.name.split(" ")[0]} Baseline)`,
          inline: true
        },
        {
          name: "🧠 Quantitative Engine",
          value: `\`${rawForecast.modelVersion}\`${rawForecast.targetDate ? ` (Target: \`${rawForecast.targetDate}\`)` : ""}`,
          inline: true
        }
      ];

      if (zipRes) {
        forecastFields.push({
          name: "🏛️ State Statutory Fuel Tax",
          value: `\`$${zipRes.state_tax_rate_per_gal.toFixed(3)}/gal\` (${zipRes.state})`,
          inline: true
        });
      }

      forecastFields.push({
        name: `📈 Multi-Day Trajectory (1D – ${horizon}D Path)`,
        value: effectiveTrajectory
          .slice(0, horizon)
          .map(t => `\`${t.day}D: $${t.price.toFixed(3)}\``)
          .join(" ➔ "),
        inline: false
      });

      if (zipRes) {
        const tierDesc = zipRes.is_metro_cluster_hit
          ? `Direct Metro Cluster Hit (\`${zipRes.canonical_hub}\` • \`${zipRes.resolution_tier}\`)`
          : `State/PADD Supply Corridor Fallback (\`${zipRes.calibrated_model_used}\` • \`${zipRes.resolution_tier}\`)`;
        forecastFields.push(
          { name: "📮 Regional Supply Routing", value: `\`${zipRes.location_name}\` (ZIP \`${zipRes.zip_code}\`, ${zipRes.state}) — ${tierDesc}`, inline: false }
        );

        if (zipRes.is_significant_departure) {
          const wedgeSign = zipRes.tax_delta_per_gal >= 0 ? "+" : "";
          const basisSign = zipRes.estimated_basis_delta >= 0 ? "+" : "";
          forecastFields.push(
            { name: "⚖️ Statutory Tax Wedge", value: `\`${wedgeSign}$${zipRes.tax_delta_per_gal.toFixed(3)}/gal\` vs ${zipRes.canonical_hub} rack baseline (\`$${zipRes.hub_baseline_tax_rate.toFixed(3)}/gal\`)`, inline: true },
            {
              name: "🏷️ Estimated Basis & Price Synthesis",
              value: `Local pump prices in **${zipRes.state}** trade at an estimated **${basisSign}$${zipRes.estimated_basis_delta.toFixed(2)}/gal** basis differential over ${zipRes.canonical_hub} coastal rack benchmarks due to state tax differentials and regional/mountain distribution logistics. Point-in-time quantitative shocks (|ΔP|) track wholesale transmission down the **${zipRes.padd_name}** corridor.`,
              inline: false
            }
          );
        }
      }

      const analystBrief = await synthesizeAnalystBrief({
        hub_name: targetDisplayName,
        current_price: effectiveBasePrice,
        predicted_shift: effectiveDelta,
        direction: effectiveDelta > 0.005 ? "UP" : (effectiveDelta < -0.005 ? "DOWN" : "FLAT"),
        confidence_interval: [effectiveLower95, effectiveUpper95],
        active_catalysts: zipRes?.is_significant_departure ? [`State tax wedge: ${zipRes.tax_delta_per_gal.toFixed(3)}$/gal`] : []
      }, env);

      forecastFields.push({
        name: "📝 Institutional Analyst Brief",
        value: analystBrief,
        inline: false
      });

      forecastFields.push({
        name: "🔗 Live Interactive Views",
        value: `[📊 Regional Dashboard](${dashboardUrl}) • [📈 Technical Attribution](https://koshiirRa.github.io/midgley/technical_breakdown.html) • [🗺️ ZIP Demand Heatmap](https://koshiirRa.github.io/midgley/telemetry.html)`,
        inline: false
      });

      let embedColor = 3447003;
      if (effectiveDelta > 0.05) {
        embedColor = 15158332;
      } else if (effectiveDelta < -0.02) {
        embedColor = 3066993;
      }

      const forecastEmbed = {
        title: `⛽ Midgley ${horizon}D Forecast — ${targetDisplayName}${zipRes && !targetDisplayName.includes(zipRes.zip_code) ? ` (ZIP ${zipRes.zip_code})` : ""}`,
        description: `**${horizon}D Out-of-Time Outlook**: Point-in-time quantitative regime & price projection for **${targetDisplayName}** (${zipRes ? `${zipRes.padd_region} corridor` : localeMeta.name}).`,
        url: dashboardUrl,
        color: embedColor,
        fields: forecastFields,
        footer: { text: "Midgley Energy Complex Forecasting • Delivered Privately via Slash Command" },
        timestamp: new Date().toISOString()
      };

      const existing = await getWorkerUserSubscription(userId, env);
      const dmRes = await sendDiscordDirectMessage(userId, { embeds: [forecastEmbed] }, env, existing?.dm_channel_id);
      const dmNote = dmRes.sent
        ? "📬 **Forecast brief delivered to your Direct Messages** (and shown ephemerally below)."
        : dmRes.blockedByPrivacy
        ? "⚠️ **DMs are blocked by your server privacy settings (`50007`)** — displaying your forecast ephemerally below instead:"
        : "📊 **Displaying your forecast ephemerally below** (invisible to the rest of the server):";

      return new Response(
        JSON.stringify({
          type: 4,
          data: {
            flags: 64,
            content: dmNote,
            embeds: [forecastEmbed]
          }
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }


    if (subcommand === "test-alert") {
      const locale = normalizeWorkerLocale(options.locale);
      const testEmbed = {
        title: "🧪 [DRY-RUN TEST] Midgley Direct Message Intraday Shock Alert",
        description: "**Trigger Catalyst (Synthetic Diagnostic):**\n> *\"Unplanned FCC unit outage reported at regional refining complex\"*",
        url: "https://koshiirRa.github.io/midgley/",
        color: 15105570,
        fields: [
          { name: "📍 Target Metro Hubs", value: `\`${locale}\``, inline: true },
          { name: "📊 Price Pressure (ΔP)", value: "`+0.35/gal`", inline: true },
          { name: "🛢️ Supply Disruption (S)", value: "`0.65`", inline: true }
        ],
        footer: { text: "Midgley Self-Service DM Reachability Diagnostic" },
        timestamp: new Date().toISOString()
      };

      const existing = await getWorkerUserSubscription(userId, env);
      const dmRes = await sendDiscordDirectMessage(userId, { embeds: [testEmbed] }, env, existing?.dm_channel_id);
      if (dmRes.sent) {
        return new Response(
          JSON.stringify({
            type: 4,
            data: {
              flags: 64,
              content: `✅ **Direct Message test succeeded!** Check your Discord DMs for the synthetic \`${locale}\` alert card.`
            }
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      }

      const reason = dmRes.blockedByPrivacy
        ? "Discord rejected the DM (`Error 50007: Cannot send messages to this user`). Please enable **Allow Direct Messages from server members** in your server Privacy Settings."
        : `DM dispatch could not be completed (${dmRes.error || "DISCORD_BOT_TOKEN not configured"}). Showing preview ephemerally below:`;

      return new Response(
        JSON.stringify({
          type: 4,
          data: {
            flags: 64,
            content: `⚠️ ${reason}`,
            embeds: [testEmbed]
          }
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({
        type: 4,
        data: {
          flags: 64,
          content: "ℹ️ Unknown `/midgley` command. Available subcommands: `subscribe`, `unsubscribe`, `status`, `forecast`, `test-alert`."
        }
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  // Type 3: MESSAGE_COMPONENT (User clicked "🚩 Flag False Positive" or "🔕 Mute This Hub (24h)" button)
  if (interaction.type === 3) {
    const customId = interaction.data?.custom_id || "";
    if (customId.startsWith("mute_hub:")) {
      const userObj = interaction.member?.user || interaction.user || {};
      const userId = String(userObj.id || "");
      const existing = userId ? await getWorkerUserSubscription(userId, env) : null;
      const mutedUntil = new Date(Date.now() + 24 * 3600 * 1000).toISOString();
      if (existing) {
        existing.muted_until = mutedUntil;
        await saveWorkerUserSubscription(existing, env);
      }
      return new Response(
        JSON.stringify({
          type: 4,
          data: {
            flags: 64,
            content: `🔕 **Alerts snoozed for 24 hours** (until \`${mutedUntil}\`). Run \`/midgley subscribe\` at any time to unmute early.`
          }
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }
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
          const match = embed.description.match(/> \*"([^"\r\n]+)"\*/) || embed.description.match(/> ([^\r\n]+)/);
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
            const urlMatch = field.value.match(/\[Original Article\]\(([^)\s]+)\)/);
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

export function getWorkerSigningSecret(env: Env): string | null {
  return env.FLAG_SIGNING_KEY || env.ADMIN_TOKEN || env.CLOUDFLARE_AUTH_TOKEN || null;
}

export async function computeSha256Hex(str: string): Promise<string> {
  const enc = new TextEncoder();
  const data = enc.encode(str);
  const hashBuf = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hashBuf))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function generateEventToken(eventId: string, exp: number, secret: string, headline?: string): Promise<string> {
  if (!secret) return "";
  const enc = new TextEncoder();
  const keyData = enc.encode(secret);
  const key = await crypto.subtle.importKey(
    "raw",
    keyData,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const headlineHash = headline ? (await computeSha256Hex(headline)).slice(0, 16) : "";
  const data = enc.encode(`flag_fp:v2|${eventId}|${headlineHash}|${exp}`);
  const signature = await crypto.subtle.sign("HMAC", key, data);
  return Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 32);
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

export async function verifyEventToken(eventId: string, exp: number, sig: string, secret: string, headline?: string): Promise<boolean> {
  if (!sig || !eventId || !secret || !exp) return false;
  if (!/^[0-9a-f]{16}$/i.test(eventId)) return false;
  if (!/^\d{10}$/.test(String(exp))) return false;
  const now = Math.floor(Date.now() / 1000);
  if (exp < now) return false;
  
  const expectedSigBound = await generateEventToken(eventId, exp, secret, headline);
  return timingSafeEqual(sig, expectedSigBound);
}

const USED_TOKENS_CACHE = new Set<string>();

export async function isTokenUsed(tokenKey: string, env: Env): Promise<boolean> {
  if (USED_TOKENS_CACHE.has(tokenKey)) return true;
  if (env.DB) {
    try {
      await ensureFlagReplaySchema(env);
      const row = await env.DB.prepare("SELECT clean_key FROM flag_replay_tokens WHERE clean_key = ?").bind(tokenKey).first();
      if (row) return true;
    } catch {
      // D1 schema table may not exist, fallback to in-memory cache
    }
  }
  return false;
}

export async function markTokenUsed(tokenKey: string, env: Env): Promise<void> {
  USED_TOKENS_CACHE.add(tokenKey);
  if (env.DB) {
    try {
      await ensureFlagReplaySchema(env);
      await env.DB.prepare("INSERT INTO flag_replay_tokens (clean_key, used_at) VALUES (?, datetime('now')) ON CONFLICT(clean_key) DO NOTHING").bind(tokenKey).run();
    } catch {
      // D1 schema table may not exist
    }
  }
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function handleFlagWebRequest(request: Request, env: Env, ctx: any): Promise<Response> {
  const url = new URL(request.url);

  if (request.method === "GET") {
    const id = url.searchParams.get("id") || "";
    const expStr = url.searchParams.get("exp") || "0";
    const sig = url.searchParams.get("sig") || url.searchParams.get("token") || "";
    const exp = parseInt(expStr, 10) || 0;
    const headline = url.searchParams.get("headline") || "Intraday Anomaly Trigger";
    const source = url.searchParams.get("source") || "Intraday_Monitor";
    const p = url.searchParams.get("p") || "+0.00";
    const s = url.searchParams.get("s") || "0.00";
    const g = url.searchParams.get("g") || "0.00";
    const sourceUrl = url.searchParams.get("url") || "";

    const eventId = id || normalizeHeadline(headline) || "default_event";
    const signingSecret = getWorkerSigningSecret(env);

    // Fail closed: GET must verify link signature; never generate tokens for unauthenticated visitors (Issues #574, #581)
    if (!signingSecret || !sig || !exp || !(await verifyEventToken(eventId, exp, sig, signingSecret, headline))) {
      return new Response(
        JSON.stringify({ error: "Forbidden: Missing, invalid, or expired signed flag link" }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      );
    }

    const idEsc = escapeHtml(id || eventId);
    const headlineEsc = escapeHtml(headline);
    const sourceEsc = escapeHtml(source);
    const pEsc = escapeHtml(p);
    const sEsc = escapeHtml(s);
    const gEsc = escapeHtml(g);
    const sourceUrlEsc = escapeHtml(sourceUrl);
    const sigEsc = escapeHtml(sig);
    const expEsc = escapeHtml(expStr);

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
      "${headlineEsc}"
    </div>

    <div class="meta-grid">
      <div class="meta-item">
        <div class="meta-label">Pressure (ΔP)</div>
        <div class="meta-value" style="color: ${pEsc.startsWith('+') ? '#e74c3c' : '#2ecc71'};">${pEsc}/gal</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Supply Shock</div>
        <div class="meta-value">${sEsc}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Source</div>
        <div class="meta-value">${sourceEsc}</div>
      </div>
    </div>

    <form method="POST" action="/flag">
      <input type="hidden" name="id" value="${idEsc}">
      <input type="hidden" name="exp" value="${expEsc}">
      <input type="hidden" name="sig" value="${sigEsc}">
      <input type="hidden" name="headline" value="${encodeURIComponent(headline)}">
      <input type="hidden" name="source" value="${sourceEsc}">
      <input type="hidden" name="p" value="${pEsc}">
      <input type="hidden" name="s" value="${sEsc}">
      <input type="hidden" name="g" value="${gEsc}">
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
    const expStr = formData.get("exp")?.toString() || "0";
    const sig = formData.get("sig")?.toString() || formData.get("token")?.toString() || "";
    const exp = parseInt(expStr, 10) || 0;
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

    const authHeader = request.headers.get("Authorization")?.replace("Bearer ", "").trim();
    const signingSecret = getWorkerSigningSecret(env);

    // 1. Direct Admin Auth (via Authorization: Bearer <ADMIN_TOKEN> header only)
    const isDirectAdminAuth = Boolean(env.ADMIN_TOKEN && authHeader && timingSafeEqual(authHeader, env.ADMIN_TOKEN));

    // 2. Cryptographic Signed Event Link Auth (via valid id + exp + sig from Discord embed)
    const isSignedEventAuth = (Boolean(eventHash && sig && exp && signingSecret))
      ? await verifyEventToken(eventHash, exp, sig, signingSecret!, headline)
      : false;

    // Reject unauthenticated issue creation requests (Fail-Closed, Issues #438, #574)
    if (!isDirectAdminAuth && !isSignedEventAuth) {
      return new Response(JSON.stringify({ error: "Unauthorized: Missing or invalid authentication token for issue creation" }), {
        status: 401,
        headers: { "Content-Type": "application/json" }
      });
    }

    // Replay attack prevention: ensure signed token can only be used once (Issue #581)
    if (isSignedEventAuth && !isDirectAdminAuth) {
      const replayKey = `flag_replay:${eventHash}:${sig}`;
      if (await isTokenUsed(replayKey, env)) {
        return new Response(JSON.stringify({ error: "Conflict: This signed flag link has already been used" }), {
          status: 409,
          headers: { "Content-Type": "application/json" }
        });
      }
      await markTokenUsed(replayKey, env);
    }

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

function renderReviewActionHtml(title: string, message: string, headline: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)} • Midgley Forecasting</title>
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
    .card {
      background: #1c202a;
      border: 1px solid #2e3446;
      border-radius: 12px;
      padding: 32px;
      max-width: 500px;
      text-align: center;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    h2 { margin: 0 0 16px 0; font-size: 1.3rem; color: #f39c12; }
    p { color: #8b94a8; font-size: 0.95rem; line-height: 1.5; margin-bottom: 24px; }
    .btn {
      display: inline-block;
      background: #3498db;
      color: #fff;
      text-decoration: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-weight: 600;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>${escapeHtml(title)}</h2>
    <p>${message}</p>
    <a href="https://koshiirRa.github.io/midgley/" target="_blank" class="btn">View Forecasting Dashboard ➔</a>
  </div>
</body>
</html>`;
}

export async function handleReviewWebRequest(request: Request, env: Env, ctx: any): Promise<Response> {
  const url = new URL(request.url);
  const id = url.searchParams.get("id") || "";
  const priorId = url.searchParams.get("prior_id") || "";
  const decision = (url.searchParams.get("decision") || "duplicate").toLowerCase();
  const expStr = url.searchParams.get("exp") || "0";
  const sig = url.searchParams.get("sig") || "";
  const headline = url.searchParams.get("headline") || "Intraday Anomaly Event";
  const exp = parseInt(expStr, 10) || 0;

  const signingSecret = getWorkerSigningSecret(env);
  if (!signingSecret || !sig || !exp) {
    return new Response(
      JSON.stringify({ error: "Forbidden: Missing signature parameters" }),
      { status: 403, headers: { "Content-Type": "application/json" } }
    );
  }

  const now = Math.floor(Date.now() / 1000);
  if (exp < now) {
    return new Response(
      JSON.stringify({ error: "Forbidden: Link expired" }),
      { status: 403, headers: { "Content-Type": "application/json" } }
    );
  }

  // Verify HMAC signature
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(signingSecret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const prefix = decision === "distinct" ? "review_dist:v1" : "review_dup:v1";
  const data = enc.encode(`${prefix}|${id}|${priorId}|${decision}|${exp}`);
  const expectedSigBuf = await crypto.subtle.sign("HMAC", key, data);
  const expectedSig = Array.from(new Uint8Array(expectedSigBuf))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 32);

  const isValid = timingSafeEqual(sig, expectedSig) || (await verifyEventToken(id, exp, sig, signingSecret, headline));
  if (!isValid) {
    return new Response(
      JSON.stringify({ error: "Forbidden: Invalid review signature" }),
      { status: 403, headers: { "Content-Type": "application/json" } }
    );
  }

  const replayKey = `review:${id}:${priorId}:${decision}`;
  if (await isTokenUsed(replayKey, env)) {
    return new Response(
      renderReviewActionHtml("Already Applied", "This operator decision has already been executed previously.", headline),
      { headers: { "Content-Type": "text/html; charset=utf-8" } }
    );
  }
  await markTokenUsed(replayKey, env);

  if (decision === "duplicate") {
    if (headline) {
      await markHeadlineDispatchedInCache(headline, env);
    }
    return new Response(
      renderReviewActionHtml(
        "✅ Confirmed Duplicate / Follow-Up",
        `Headline <strong>"${escapeHtml(headline)}"</strong> has been clustered with active prior incident <code>${escapeHtml(priorId)}</code>.<br><br>Secondary price shock suppressed. No duplicate revision logged.`,
        headline
      ),
      { headers: { "Content-Type": "text/html; charset=utf-8" } }
    );
  } else {
    // Distinct incident: trigger forecast revision dispatch
    const dispatchRes = await dispatchGitHubEvent(env, headline, url.searchParams.get("url") || "");
    const dispatchMsg = dispatchRes.dispatched
      ? "Forecast revision pipeline dispatched to GitHub Actions successfully."
      : `Dispatched recorded (Note: ${dispatchRes.error || "Queued"}).`;

    return new Response(
      renderReviewActionHtml(
        "⚡ Confirmed New / Distinct Incident",
        `Headline <strong>"${escapeHtml(headline)}"</strong> released as a distinct operational event.<br><br>${dispatchMsg}`,
        headline
      ),
      { headers: { "Content-Type": "text/html; charset=utf-8" } }
    );
  }
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

      // Duplicate / Distinct Review Route (Human-in-the-Loop Disambiguation Flow)
      if (url.pathname === "/review") {
        return await handleReviewWebRequest(request, env, ctx);
      }

      // Discord Interactions Endpoint Route
      if (url.pathname === "/discord/interactions" || request.headers.has("X-Signature-Ed25519")) {
        return await handleDiscordInteraction(request, env, ctx);
      }

      // Edge Unmapped ZIP Demand Telemetry Sync Route (Issue #50, #195, #235)
      if (url.pathname === "/telemetry/unmapped-zips") {
        const topUnmapped = await getWorkerUnmappedZips(env);
        return new Response(
          JSON.stringify({
            status: "success",
            timestamp: new Date().toISOString(),
            unique_unmapped_zips: topUnmapped.length,
            total_unmapped_queries: topUnmapped.reduce((acc, r) => acc + (r.hit_count || 1), 0),
            top_unmapped_zips: topUnmapped
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      }

      // Authenticated Edge Discord Subscriptions Sync Route (Issue #235)
      if (url.pathname === "/discord/subscriptions") {
        const authHeader = request.headers.get("Authorization")?.replace("Bearer ", "").trim() || "";
        const adminOk = Boolean(env.ADMIN_TOKEN && authHeader && timingSafeEqual(authHeader, env.ADMIN_TOKEN));
        const botOk = Boolean(env.DISCORD_BOT_TOKEN && authHeader && timingSafeEqual(authHeader, env.DISCORD_BOT_TOKEN));
        if (!adminOk && !botOk) {
          return new Response(JSON.stringify({ error: "Unauthorized" }), {
            status: 401,
            headers: { "Content-Type": "application/json" }
          });
        }
        const subs = await getAllWorkerSubscriptions(env);
        return new Response(
          JSON.stringify({
            status: "success",
            timestamp: new Date().toISOString(),
            subscriptions: subs
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      }

      // Enverus / Drillinginfo Daily Rig Count Route (Issues #533, #640)
      if (url.pathname === "/api/v1/energy/rig-count/enverus" || url.pathname === "/scraping/enverus-rig-count") {
        const forceRefresh = url.searchParams.get("force_refresh") === "true";
        const rigData = await getEnverusDailyRigCount(env, { force_refresh: forceRefresh });
        return new Response(JSON.stringify(rigData, null, 2), {
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
          }
        });
      }

      // Secure manual run & trigger endpoints (Fail-Closed, Issues #438, #574)
      if (url.pathname === "/run" || url.pathname === "/trigger") {
        const authHeader = request.headers.get("Authorization")?.replace("Bearer ", "").trim();
        const expectedToken = env.ADMIN_TOKEN;
        if (!expectedToken || !authHeader || !timingSafeEqual(authHeader, expectedToken)) {
          return new Response(JSON.stringify({ error: "Unauthorized: Valid ADMIN_TOKEN Authorization header required" }), {
            status: 401,
            headers: { "Content-Type": "application/json" }
          });
        }
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
          endpoints: [
            "/run",
            "/trigger",
            "/status",
            "/flag",
            "/discord/interactions",
            "/telemetry/unmapped-zips",
            "/discord/subscriptions",
            "/api/v1/energy/rig-count/enverus"
          ]
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
