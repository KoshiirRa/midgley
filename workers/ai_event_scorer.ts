/**
 * Cloudflare Workers AI & Vectorize Edge Intelligence Module
 * (workers/ai_event_scorer.ts)
 *
 * Implements:
 * 1. Zero-shot catalyst classification & severity scoring at the edge via Workers AI
 * 2. 384-dimensional dense semantic deduplication using Cloudflare Vectorize (EVENT_INDEX)
 * 3. Durable cross-system memory synchronization with Hindsight SaaS (midgley-event-dedupe)
 * 4. Grounded institutional analyst briefing synthesis for Discord bot & API endpoints
 * 5. Bounded execution (1,500ms max) with deterministic heuristic/regex fallbacks
 */

export interface ScoredCatalyst {
  is_anomaly: boolean;
  catalyst_domain: "refinery_pipeline" | "weather_hurricane" | "geopolitical_opec" | "regulatory_tax" | "noise";
  affected_hub: "Chicago_IL" | "Houston_TX" | "Los_Angeles_CA" | "Denver_CO" | "New_York_NY" | "National" | "None";
  direction: "spike" | "drop" | "neutral";
  magnitude: "low" | "medium" | "high" | "critical";
  half_life_days: number;
  confidence: number;
  reasoning: string;
  model: string;
  as_of: string;
}

export interface SemanticDedupeResult {
  status: "duplicate" | "evolving" | "novel";
  similarity: number;
  matched_id?: string;
  matched_headline?: string;
  source: "vectorize" | "hindsight" | "cache" | "none";
  as_of: string;
}

export interface AnalystBriefContext {
  hub_name: string;
  current_price?: number;
  predicted_shift?: number;
  direction?: "UP" | "DOWN" | "FLAT";
  confidence_interval?: [number, number];
  active_catalysts?: string[];
  as_of?: string;
}

export const DEFAULT_EMBEDDING_MODEL = "@cf/baai/bge-small-en-v1.5";
export const DEFAULT_CATALYST_MODEL = "@cf/meta/llama-3.2-3b-instruct";
export const DEFAULT_BRIEF_MODEL = "@cf/meta/llama-3.1-8b-instruct";

export const EDGE_AI_TIMEOUT_MS = 1500;
export const VECTORIZE_DUPLICATE_THRESHOLD = 0.88;
export const VECTORIZE_EVOLVING_THRESHOLD = 0.70;

export const DEFAULT_HINDSIGHT_API_URL = "https://api.hindsight.vectorize.io";
export const DEFAULT_HINDSIGHT_BANK_ID = "midgley-event-dedupe";

export const KNOWN_FACILITY_ENTITIES = [
  "joliet", "baytown", "baton rouge", "beaumont",
  "delaware city", "el dorado", "tulsa", "west tulsa",
  "catlettsburg", "garyville", "sweeny", "bayway",
  "richmond refinery", "el segundo", "cushing",
  "colonial pipeline", "keystone pipeline", "explorer pipeline", "plantation pipeline",
  "strait of hormuz", "red sea", "bab el-mandeb"
];

export const KNOWN_OPERATOR_ENTITIES = [
  "exxonmobil", "exxon", "pbf energy", "pbf", "hf sinclair", "holly frontier",
  "marathon petroleum", "marathon", "valero", "phillips 66", "chevron"
];

/**
 * Extracts recognized physical energy infrastructure or operator from text.
 */
export function extractMatchedEntityAtEdge(text: string): string | null {
  if (!text) return null;
  const lower = text.toLowerCase();
  for (const facility of KNOWN_FACILITY_ENTITIES) {
    const rx = new RegExp(`\\b${facility.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    if (rx.test(lower)) {
      return facility.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    }
  }
  for (const op of KNOWN_OPERATOR_ENTITIES) {
    const rx = new RegExp(`\\b${op.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    if (rx.test(lower)) {
      return op.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    }
  }
  return null;
}

/**
 * Wraps a promise with a hard timeout ceiling.
 */
export async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, timeoutMsg: string): Promise<T> {
  let timer: any;
  const timeoutPromise = new Promise<T>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`[Timeout] ${timeoutMsg} exceeded ${timeoutMs}ms`)), timeoutMs);
  });
  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Computes a 384-dimensional dense vector embedding via Workers AI.
 */
export async function getHeadlineEmbedding(
  headline: string,
  env: any,
  timeoutMs: number = EDGE_AI_TIMEOUT_MS
): Promise<number[] | null> {
  if (!headline || !env || !env.AI || typeof env.AI.run !== "function") {
    return null;
  }

  try {
    const aiCall = env.AI.run(DEFAULT_EMBEDDING_MODEL, { text: [headline] });
    const res: any = await withTimeout(aiCall, timeoutMs, "Embedding generation");

    if (res && Array.isArray(res.data) && res.data.length > 0) {
      const vec = res.data[0];
      if (Array.isArray(vec)) return vec;
    }
    if (res && Array.isArray(res) && res.length > 0 && Array.isArray(res[0])) {
      return res[0];
    }
    return null;
  } catch (err: any) {
    console.warn(`[Edge Embedding Warning] ${err.message || String(err)}`);
    return null;
  }
}

/**
 * Queries Hindsight SaaS memories/recall for cross-environment memory deduplication.
 */
export async function queryHindsightBank(
  headline: string,
  env: any,
  timeoutMs: number = 1000
): Promise<{ matched: boolean; similarity: number; matchedHeadline?: string; docId?: string }> {
  const token = env?.HINDSIGHT_API_TOKEN;
  if (!token) return { matched: false, similarity: 0.0 };

  let apiUrl = (env?.HINDSIGHT_API_URL || DEFAULT_HINDSIGHT_API_URL).trim();
  while (apiUrl.endsWith("/")) {
    apiUrl = apiUrl.slice(0, -1);
  }
  const bankId = env?.HINDSIGHT_DEDUPE_BANK_ID || DEFAULT_HINDSIGHT_BANK_ID;

  try {
    const fetchCall = fetch(`${apiUrl}/v1/default/banks/${bankId}/memories/recall`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ query: headline, budget: "mid" })
    });

    const resp = await withTimeout(fetchCall, timeoutMs, "Hindsight memory recall");
    if (!resp.ok) return { matched: false, similarity: 0.0 };

    const data: any = await resp.json();
    const results = Array.isArray(data?.results) ? data.results : [];
    if (results.length === 0) return { matched: false, similarity: 0.0 };

    const top = results[0];
    const score = typeof top.score === "number" ? top.score : 0.85;
    return {
      matched: true,
      similarity: score,
      matchedHeadline: top.text || top.content || "",
      docId: top.document_id || top.id || ""
    };
  } catch (err: any) {
    console.warn(`[Hindsight Recall Warning] ${err.message || String(err)}`);
    return { matched: false, similarity: 0.0 };
  }
}

/**
 * Retains a confirmed anomaly into Hindsight SaaS memory bank.
 * Intended to run inside ctx.waitUntil() for zero edge latency impact.
 */
export async function retainHindsightMemory(
  event: { headline: string; url?: string; source?: string; entity?: string; locales?: string[]; magnitude?: string },
  env: any
): Promise<boolean> {
  const token = env?.HINDSIGHT_API_TOKEN;
  if (!token || !event.headline) return false;

  let apiUrl = (env?.HINDSIGHT_API_URL || DEFAULT_HINDSIGHT_API_URL).trim();
  while (apiUrl.endsWith("/")) {
    apiUrl = apiUrl.slice(0, -1);
  }
  const bankId = env?.HINDSIGHT_DEDUPE_BANK_ID || DEFAULT_HINDSIGHT_BANK_ID;

  const entity = event.entity || extractMatchedEntityAtEdge(event.headline) || "Energy Facility";
  const docId = `cf-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const ts = new Date().toISOString();

  const payload = {
    items: [
      {
        content: `${event.headline}. Impacted regional locales: ${(event.locales || ["National"]).join(", ")}.`,
        document_id: docId,
        entities: [{ text: entity, type: "FACILITY" }],
        tags: ["intraday_anomaly", "edge_worker", "petroleum_market"],
        timestamp: ts,
        metadata: {
          source: event.source || "EdgeMonitor",
          url: event.url || "",
          severity: event.magnitude || "medium"
        }
      }
    ]
  };

  try {
    const resp = await fetch(`${apiUrl}/v1/default/banks/${bankId}/memories`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    return resp.ok;
  } catch (err: any) {
    console.warn(`[Hindsight Retain Notice] ${err.message || String(err)}`);
    return false;
  }
}

/**
 * Multi-tier semantic deduplication combining Cloudflare Vectorize (Tier 1)
 * with the Hindsight midgley-event-dedupe bank (Tier 2).
 */
export async function querySemanticDedupe(
  headline: string,
  env: any,
  options?: { timeoutMs?: number; embedding?: number[] }
): Promise<SemanticDedupeResult> {
  const as_of = new Date().toISOString();
  if (!headline) {
    return { status: "novel", similarity: 0.0, source: "none", as_of };
  }

  const timeoutMs = options?.timeoutMs || EDGE_AI_TIMEOUT_MS;

  // 1. Compute embedding if not passed
  let embedding = options?.embedding;
  if (!embedding) {
    embedding = (await getHeadlineEmbedding(headline, env, timeoutMs)) || undefined;
  }

  // 2. Tier 1: Query Vectorize Index if binding is available
  if (embedding && env && env.EVENT_INDEX && typeof env.EVENT_INDEX.query === "function") {
    try {
      const queryCall = env.EVENT_INDEX.query(embedding, { topK: 3, returnMetadata: "all" });
      const vectorRes: any = await withTimeout(queryCall, timeoutMs, "Vectorize query");

      const matches = Array.isArray(vectorRes?.matches) ? vectorRes.matches : [];
      if (matches.length > 0) {
        const topMatch = matches[0];
        const score = typeof topMatch.score === "number" ? topMatch.score : 0;
        const matchedHeadline = topMatch.metadata?.headline || "";

        if (score >= VECTORIZE_DUPLICATE_THRESHOLD) {
          return {
            status: "duplicate",
            similarity: score,
            matched_id: topMatch.id,
            matched_headline: matchedHeadline,
            source: "vectorize",
            as_of
          };
        }

        if (score >= VECTORIZE_EVOLVING_THRESHOLD) {
          return {
            status: "evolving",
            similarity: score,
            matched_id: topMatch.id,
            matched_headline: matchedHeadline,
            source: "vectorize",
            as_of
          };
        }
      }
    } catch (vErr: any) {
      console.warn(`[Vectorize Query Warning] ${vErr.message || String(vErr)}`);
    }
  }

  // 3. Tier 2: Consult Hindsight SaaS memory bank for cross-environment events
  if (env && env.HINDSIGHT_API_TOKEN) {
    try {
      const hsRes = await queryHindsightBank(headline, env, 800);
      if (hsRes.matched) {
        if (hsRes.similarity >= VECTORIZE_DUPLICATE_THRESHOLD) {
          return {
            status: "duplicate",
            similarity: hsRes.similarity,
            matched_id: hsRes.docId,
            matched_headline: hsRes.matchedHeadline,
            source: "hindsight",
            as_of
          };
        }
        if (hsRes.similarity >= VECTORIZE_EVOLVING_THRESHOLD) {
          return {
            status: "evolving",
            similarity: hsRes.similarity,
            matched_id: hsRes.docId,
            matched_headline: hsRes.matchedHeadline,
            source: "hindsight",
            as_of
          };
        }
      }
    } catch (hErr: any) {
      console.warn(`[Hindsight Dedupe Warning] ${hErr.message || String(hErr)}`);
    }
  }

  return {
    status: "novel",
    similarity: 0.0,
    source: "none",
    as_of
  };
}

/**
 * Inserts a new vector record into Vectorize index.
 */
export async function indexHeadlineVector(
  headline: string,
  embedding: number[],
  metadata: Record<string, any>,
  env: any
): Promise<boolean> {
  if (!env || !env.EVENT_INDEX || typeof env.EVENT_INDEX.insert !== "function") {
    return false;
  }

  try {
    const id = `vec-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    await env.EVENT_INDEX.insert([
      {
        id,
        values: embedding,
        metadata: {
          headline,
          as_of: new Date().toISOString(),
          ...metadata
        }
      }
    ]);
    return true;
  } catch (err: any) {
    console.warn(`[Vectorize Insert Error] ${err.message || String(err)}`);
    return false;
  }
}

/**
 * Fallback regex heuristic classification when Workers AI is unconfigured or times out.
 */
export function fallbackRegexScore(headline: string): ScoredCatalyst {
  const as_of = new Date().toISOString();
  const lower = headline.toLowerCase();

  // Fast noise filters
  const noiseRegex = /\b(cooking oil|olive oil|palm oil|canola|soybean oil|airline outage|software outage|cloud outage|data center)\b/i;
  if (noiseRegex.test(lower)) {
    return {
      is_anomaly: false,
      catalyst_domain: "noise",
      affected_hub: "None",
      direction: "neutral",
      magnitude: "low",
      half_life_days: 0.0,
      confidence: 0.95,
      reasoning: "Excluded non-petroleum commodity or non-energy operational context",
      model: "regex_heuristic_fallback",
      as_of
    };
  }

  // Detect domain
  let domain: ScoredCatalyst["catalyst_domain"] = "noise";
  let is_anomaly = false;
  let direction: ScoredCatalyst["direction"] = "neutral";
  let magnitude: ScoredCatalyst["magnitude"] = "low";
  let half_life_days = 0.0;

  if (/\b(refiner|cdu|fcc|hydrocracker|flaring|coker|pipeline leak|colonial pipeline|shutdown|outage|unplanned turnaround)\b/i.test(lower)) {
    domain = "refinery_pipeline";
    is_anomaly = true;
    direction = "spike";
    magnitude = "high";
    half_life_days = 5.0;
  } else if (/\b(hurricane|tropical storm|gulf of mexico|evacuation|shut-in|bsee)\b/i.test(lower)) {
    domain = "weather_hurricane";
    is_anomaly = true;
    direction = "spike";
    magnitude = "high";
    half_life_days = 7.0;
  } else if (/\b(opec|saudi|russia|strait of hormuz|sanctions?|embargo|crude cut)\b/i.test(lower)) {
    domain = "geopolitical_opec";
    is_anomaly = true;
    direction = "spike";
    magnitude = "medium";
    half_life_days = 14.0;
  } else if (/\b(fuel tax|gas tax|carb|lcfs|rfs|epa mandate|statutory rate)\b/i.test(lower)) {
    domain = "regulatory_tax";
    is_anomaly = true;
    direction = "spike";
    magnitude = "medium";
    half_life_days = 30.0;
  }

  // Detect hub
  let affected_hub: ScoredCatalyst["affected_hub"] = "National";
  if (/\b(chicago|illinois|midwest|citgo lemont|joliet|bp whiting)\b/i.test(lower)) {
    affected_hub = "Chicago_IL";
  } else if (/\b(houston|texas|gulf coast|galveston|baytown|beaumont)\b/i.test(lower)) {
    affected_hub = "Houston_TX";
  } else if (/\b(los angeles|california|padd 5|bay area|richmond|torrance)\b/i.test(lower)) {
    affected_hub = "Los_Angeles_CA";
  } else if (/\b(denver|colorado|rocky mountain|suncor commerce city)\b/i.test(lower)) {
    affected_hub = "Denver_CO";
  } else if (/\b(new york|new jersey|bayway|padd 1b|harbor)\b/i.test(lower)) {
    affected_hub = "New_York_NY";
  }

  return {
    is_anomaly,
    catalyst_domain: domain,
    affected_hub,
    direction,
    magnitude,
    half_life_days,
    confidence: is_anomaly ? 0.80 : 0.90,
    reasoning: is_anomaly ? `Heuristic matched ${domain} disruption markers` : "No energy anomaly patterns matched",
    model: "regex_heuristic_fallback",
    as_of
  };
}

/**
 * Evaluates a headline using Workers AI zero-shot catalyst scoring with strict bounded timeout.
 */
export async function scoreHeadlineAtEdge(
  headline: string,
  env: any,
  timeoutMs: number = EDGE_AI_TIMEOUT_MS
): Promise<ScoredCatalyst> {
  const as_of = new Date().toISOString();
  if (!headline) {
    return fallbackRegexScore("");
  }

  if (!env || !env.AI || typeof env.AI.run !== "function") {
    return fallbackRegexScore(headline);
  }

  const systemPrompt = `You are Midgley's edge quantitative energy catalyst classifier.
Analyze the given headline and return a strict JSON object with:
{
  "is_anomaly": boolean,
  "catalyst_domain": "refinery_pipeline" | "weather_hurricane" | "geopolitical_opec" | "regulatory_tax" | "noise",
  "affected_hub": "Chicago_IL" | "Houston_TX" | "Los_Angeles_CA" | "Denver_CO" | "New_York_NY" | "National" | "None",
  "direction": "spike" | "drop" | "neutral",
  "magnitude": "low" | "medium" | "high" | "critical",
  "half_life_days": number (0 to 30),
  "confidence": number (0.0 to 1.0),
  "reasoning": string (max 15 words)
}
Classify general tariffs, food oils, cloud/IT outages, or politics without physical fuel supply impact as "noise".
Respond ONLY with raw JSON.`;

  try {
    const aiCall = env.AI.run(DEFAULT_CATALYST_MODEL, {
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: `Headline: "${headline}"` }
      ],
      max_tokens: 220,
      temperature: 0.0
    });

    const res: any = await withTimeout(aiCall, timeoutMs, "Workers AI catalyst scoring");
    const rawText = res?.response || res?.output || (typeof res === "string" ? res : "");

    // Extract JSON block
    const jsonMatch = rawText.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return fallbackRegexScore(headline);
    }

    const parsed = JSON.parse(jsonMatch[0]);
    if (typeof parsed.is_anomaly !== "boolean" || !parsed.catalyst_domain) {
      return fallbackRegexScore(headline);
    }

    return {
      is_anomaly: parsed.is_anomaly,
      catalyst_domain: parsed.catalyst_domain,
      affected_hub: parsed.affected_hub || "National",
      direction: parsed.direction || "neutral",
      magnitude: parsed.magnitude || "low",
      half_life_days: typeof parsed.half_life_days === "number" ? parsed.half_life_days : 5.0,
      confidence: typeof parsed.confidence === "number" ? parsed.confidence : 0.85,
      reasoning: parsed.reasoning || "Workers AI classification",
      model: DEFAULT_CATALYST_MODEL,
      as_of
    };
  } catch (err: any) {
    console.warn(`[Workers AI Scorer Fallback] ${err.message || String(err)} - falling back to regex`);
    return fallbackRegexScore(headline);
  }
}

/**
 * Synthesizes a grounded 2-sentence institutional analyst brief for Discord /midgley forecast or DM alerts.
 */
export async function synthesizeAnalystBrief(
  context: AnalystBriefContext,
  env: any,
  timeoutMs: number = EDGE_AI_TIMEOUT_MS
): Promise<string> {
  const hub = context.hub_name || "National";
  const shiftText = context.predicted_shift !== undefined
    ? `${context.predicted_shift >= 0 ? "+" : ""}${context.predicted_shift.toFixed(3)} $/gal`
    : "flat";
  const catalysts = (context.active_catalysts && context.active_catalysts.length > 0)
    ? context.active_catalysts.join("; ")
    : "Baseline crack spread equilibrium and seasonal demand curves.";

  const fallbackTemplate = `${hub} fuel forecast projects a ${context.direction || "steady"} trajectory with expected basis shift of ${shiftText}. Operational drivers remain anchored by prevailing regional refinery logistics and storage inventory levels.`;

  if (!env || !env.AI || typeof env.AI.run !== "function") {
    return fallbackTemplate;
  }

  const prompt = `You are Midgley's institutional energy analyst.
Generate exactly TWO concise, professional sentences explaining today's retail fuel forecast.
Data:
- Hub: ${hub}
- Projected shift: ${shiftText} (${context.direction || "FLAT"})
- 95% Confidence Interval: ${context.confidence_interval ? `[${context.confidence_interval[0].toFixed(3)}, ${context.confidence_interval[1].toFixed(3)}]` : "N/A"}
- Operational Catalysts: ${catalysts}

Rules:
1. Exactly two sentences.
2. Ground strictly in the provided data. NEVER invent external numbers, OPEC quotes, or unmentioned events.
3. Plain text only.`;

  try {
    const aiCall = env.AI.run(DEFAULT_BRIEF_MODEL, {
      prompt,
      max_tokens: 120,
      temperature: 0.1
    });

    const res: any = await withTimeout(aiCall, timeoutMs, "Briefing synthesis");
    const rawText = (res?.response || res?.output || (typeof res === "string" ? res : "")).trim();
    if (rawText && rawText.length > 20) {
      return rawText;
    }
    return fallbackTemplate;
  } catch (err: any) {
    console.warn(`[Brief Synthesis Warning] ${err.message || String(err)}`);
    return fallbackTemplate;
  }
}
