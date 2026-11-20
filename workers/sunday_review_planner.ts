/**
 * Sunday Weekly Self-Review Action Planner & Discord Interactive Button Handler
 * (workers/sunday_review_planner.ts)
 *
 * Runs every Sunday at 9:00 AM America/Chicago via Cloudflare Workers Cron Triggers:
 * 1. Fetches the latest Saturday [dev] and [main] `weekly-review` GitHub issues.
 * 2. Cross-analyzes both reports using Gemini to synthesize a prioritized action plan.
 * 3. Persists action items in Cloudflare D1 (`midgley-cache-d1`).
 * 4. Posts one Discord message per action item to channel 1573379167452405851
 *    using the Midgley Bot (`DISCORD_BOT_TOKEN`) with interactive Approve, Deny,
 *    and Request Explanation buttons.
 * 5. Handles `MESSAGE_COMPONENT` (type 3) button clicks:
 *    - Approve: updates D1 + Discord embed, opens a labeled GitHub Issue, and fires
 *      `repository_dispatch` (`weekly-action-approved`) to spin up the dev agent.
 *    - Deny: updates D1 + Discord embed and disables Approve/Deny buttons.
 *    - Request Explanation: defers and calls Gemini for a deep-dive technical explanation.
 */

export const DEFAULT_SUNDAY_REVIEW_CHANNEL_ID = "1573379167452405851";
export const DEFAULT_DISCORD_BOT_USER_ID = "1550234222826889246";
export const DEFAULT_GEMINI_REVIEW_MODEL = "gemini-2.5-flash";
export const SUNDAY_REVIEW_CRON_EXPRESSION = "0 14,15 * * SUN";

export interface SundayReviewEnv {
  GH_PAT?: string;
  GITHUB_PAT?: string;
  GITHUB_TOKEN?: string;
  REPO_OWNER?: string;
  REPO_NAME?: string;
  DISCORD_BOT_TOKEN?: string;
  DISCORD_APP_ID?: string;
  DISCORD_SUNDAY_REVIEW_CHANNEL_ID?: string;
  GEMINI_API_KEY?: string;
  GEMINI_REVIEW_MODEL?: string;
  DB?: any;
}

export interface GitHubIssueSummary {
  number: number;
  title: string;
  html_url: string;
  body: string;
  state: string;
  created_at: string;
  branch: "dev" | "main";
}

export type ActionPriority = "critical" | "high" | "medium" | "low";
export type ActionStatus = "pending" | "approved" | "denied";

export interface WeeklyActionItem {
  action_id: string;
  run_date_key: string;
  title: string;
  priority: ActionPriority;
  target_branch: "dev" | "main" | "both";
  component: string;
  domain_label: string;
  summary: string;
  rationale: string;
  proposed_fix: string;
  source_dev_issue: number | null;
  source_main_issue: number | null;
  source_dev_url: string;
  source_main_url: string;
  source_context_excerpt: string;
  discord_channel_id: string;
  discord_message_id: string | null;
  status: ActionStatus;
  decided_by: string | null;
  decided_at: string | null;
  github_issue_number: number | null;
  github_issue_url: string | null;
  created_at: string;
}

export interface SundayPlannerRunResult {
  status: "completed" | "skipped_schedule" | "skipped_already_ran" | "error";
  run_date_key: string;
  dev_issue_number?: number | null;
  main_issue_number?: number | null;
  action_count?: number;
  posted_count?: number;
  failed_posts?: number;
  executive_summary?: string;
  error?: string;
}

const MEMORY_RUNS = new Map<string, { run_date_key: string; action_count: number }>();
const MEMORY_ACTIONS = new Map<string, WeeklyActionItem>();

export function _resetSundayPlannerMemoryForTests(): void {
  MEMORY_RUNS.clear();
  MEMORY_ACTIONS.clear();
}

function getGitHubToken(env: SundayReviewEnv): string {
  return (env.GH_PAT || env.GITHUB_PAT || env.GITHUB_TOKEN || "").trim();
}

function getRepoCoords(env: SundayReviewEnv): { owner: string; repo: string } {
  return {
    owner: (env.REPO_OWNER || "KoshiirRa").trim(),
    repo: (env.REPO_NAME || "midgley").trim()
  };
}

/**
 * Evaluates whether `now` falls on Sunday 09:00 hour in `America/Chicago` (DST-safe).
 */
export function isSundayNineAmCentral(now: Date = new Date()): {
  shouldRun: boolean;
  localDateKey: string;
  localHour: number;
  localWeekday: string;
} {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Chicago",
    weekday: "short",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    hour12: false
  });

  const parts = formatter.formatToParts(now);
  const getPart = (type: string): string => parts.find(p => p.type === type)?.value || "";

  const localWeekday = getPart("weekday");
  const year = getPart("year");
  const month = getPart("month");
  const day = getPart("day");
  const rawHour = parseInt(getPart("hour"), 10);
  const localHour = Number.isNaN(rawHour) ? -1 : rawHour % 24;
  const localDateKey = `${year}-${month}-${day}`;

  return {
    shouldRun: localWeekday === "Sun" && localHour === 9,
    localDateKey,
    localHour,
    localWeekday
  };
}

export async function ensureSundayReviewTables(db: any): Promise<void> {
  if (!db) return;

  await db.prepare(`
    CREATE TABLE IF NOT EXISTS weekly_review_runs (
      run_date_key TEXT PRIMARY KEY,
      dev_issue_number INTEGER,
      main_issue_number INTEGER,
      dev_issue_url TEXT,
      main_issue_url TEXT,
      action_count INTEGER DEFAULT 0,
      created_at TEXT NOT NULL
    )
  `).run();

  await db.prepare(`
    CREATE TABLE IF NOT EXISTS weekly_review_action_items (
      action_id TEXT PRIMARY KEY,
      run_date_key TEXT NOT NULL,
      title TEXT NOT NULL,
      priority TEXT NOT NULL,
      target_branch TEXT NOT NULL,
      component TEXT NOT NULL,
      domain_label TEXT NOT NULL,
      summary TEXT NOT NULL,
      rationale TEXT NOT NULL,
      proposed_fix TEXT NOT NULL,
      source_dev_issue INTEGER,
      source_main_issue INTEGER,
      source_dev_url TEXT,
      source_main_url TEXT,
      source_context_excerpt TEXT,
      discord_channel_id TEXT NOT NULL,
      discord_message_id TEXT,
      status TEXT NOT NULL DEFAULT 'pending',
      decided_by TEXT,
      decided_at TEXT,
      github_issue_number INTEGER,
      github_issue_url TEXT,
      created_at TEXT NOT NULL
    )
  `).run();
}

async function hasRunAlreadyCompleted(env: SundayReviewEnv, runDateKey: string): Promise<boolean> {
  if (env.DB) {
    await ensureSundayReviewTables(env.DB);
    const row = await env.DB.prepare(
      "SELECT run_date_key FROM weekly_review_runs WHERE run_date_key = ?"
    ).bind(runDateKey).first();
    return Boolean(row);
  }
  return MEMORY_RUNS.has(runDateKey);
}

async function recordRunCompletion(
  env: SundayReviewEnv,
  runDateKey: string,
  devIssue: GitHubIssueSummary | null,
  mainIssue: GitHubIssueSummary | null,
  actionCount: number
): Promise<void> {
  const nowIso = new Date().toISOString();
  if (env.DB) {
    await ensureSundayReviewTables(env.DB);
    await env.DB.prepare(`
      INSERT OR REPLACE INTO weekly_review_runs
      (run_date_key, dev_issue_number, main_issue_number, dev_issue_url, main_issue_url, action_count, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).bind(
      runDateKey,
      devIssue?.number ?? null,
      mainIssue?.number ?? null,
      devIssue?.html_url ?? "",
      mainIssue?.html_url ?? "",
      actionCount,
      nowIso
    ).run();
    return;
  }
  MEMORY_RUNS.set(runDateKey, { run_date_key: runDateKey, action_count: actionCount });
}

export async function saveWeeklyActionItem(env: SundayReviewEnv, item: WeeklyActionItem): Promise<void> {
  MEMORY_ACTIONS.set(item.action_id, { ...item });
  if (!env.DB) return;

  await ensureSundayReviewTables(env.DB);
  await env.DB.prepare(`
    INSERT OR REPLACE INTO weekly_review_action_items (
      action_id, run_date_key, title, priority, target_branch, component, domain_label,
      summary, rationale, proposed_fix, source_dev_issue, source_main_issue,
      source_dev_url, source_main_url, source_context_excerpt,
      discord_channel_id, discord_message_id, status, decided_by, decided_at,
      github_issue_number, github_issue_url, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    item.action_id,
    item.run_date_key,
    item.title,
    item.priority,
    item.target_branch,
    item.component,
    item.domain_label,
    item.summary,
    item.rationale,
    item.proposed_fix,
    item.source_dev_issue,
    item.source_main_issue,
    item.source_dev_url,
    item.source_main_url,
    item.source_context_excerpt,
    item.discord_channel_id,
    item.discord_message_id,
    item.status,
    item.decided_by,
    item.decided_at,
    item.github_issue_number,
    item.github_issue_url,
    item.created_at
  ).run();
}

export async function loadWeeklyActionItem(
  env: SundayReviewEnv,
  actionId: string
): Promise<WeeklyActionItem | null> {
  if (env.DB) {
    await ensureSundayReviewTables(env.DB);
    const row = await env.DB.prepare(
      "SELECT * FROM weekly_review_action_items WHERE action_id = ?"
    ).bind(actionId).first();
    if (row) {
      return row as WeeklyActionItem;
    }
  }
  return MEMORY_ACTIONS.get(actionId) || null;
}

/**
 * Fetches the latest `[dev]` and `[main]` `weekly-review` GitHub issues.
 */
export async function fetchLatestWeeklyReviewIssues(
  env: SundayReviewEnv
): Promise<{ dev: GitHubIssueSummary | null; main: GitHubIssueSummary | null }> {
  const { owner, repo } = getRepoCoords(env);
  const token = getGitHubToken(env);
  const url = `https://api.github.com/repos/${owner}/${repo}/issues?labels=weekly-review&state=all&sort=created&direction=desc&per_page=15`;

  const headers: Record<string, string> = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Midgley-Sunday-Review-Worker/1.0"
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { headers });
  if (!res.ok) {
    throw new Error(`GitHub issues fetch failed with HTTP ${res.status}`);
  }

  const issues = (await res.json()) as Array<any>;
  let dev: GitHubIssueSummary | null = null;
  let main: GitHubIssueSummary | null = null;

  for (const issue of issues) {
    if (!issue || issue.pull_request) continue;
    const title = String(issue.title || "");
    const body = String(issue.body || "");

    const isDev = title.startsWith("[dev]") || /\*\*Branch:\*\*\s*`dev`/i.test(body);
    const isMain = title.startsWith("[main]") || /\*\*Branch:\*\*\s*`main`/i.test(body);

    if (isDev && !dev) {
      dev = {
        number: Number(issue.number),
        title,
        html_url: String(issue.html_url || ""),
        body,
        state: String(issue.state || "open"),
        created_at: String(issue.created_at || ""),
        branch: "dev"
      };
    } else if (isMain && !main) {
      main = {
        number: Number(issue.number),
        title,
        html_url: String(issue.html_url || ""),
        body,
        state: String(issue.state || "open"),
        created_at: String(issue.created_at || ""),
        branch: "main"
      };
    }

    if (dev && main) break;
  }

  return { dev, main };
}

function truncateReportForPrompt(body: string, maxChars: number = 14000): string {
  if (body.length <= maxChars) return body;
  return `${body.slice(0, maxChars)}\n\n...[truncated ${body.length - maxChars} chars]`;
}

function normalizePriority(raw: string): ActionPriority {
  const clean = String(raw || "").trim().toLowerCase();
  if (clean === "critical" || clean === "high" || clean === "medium" || clean === "low") {
    return clean;
  }
  return "medium";
}

function normalizeTargetBranch(raw: string): "dev" | "main" | "both" {
  const clean = String(raw || "").trim().toLowerCase();
  if (clean === "dev" || clean === "main" || clean === "both") {
    return clean;
  }
  return "dev";
}

function normalizeDomainLabel(raw: string): string {
  const allowed = new Set([
    "modeling",
    "data-ingestion",
    "infrastructure",
    "dashboard",
    "integration",
    "api",
    "security",
    "mlops"
  ]);
  const clean = String(raw || "").trim().toLowerCase();
  return allowed.has(clean) ? clean : "modeling";
}

function extractJsonText(rawText: string): string {
  const trimmed = rawText.trim();
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  return fenced ? fenced[1].trim() : trimmed;
}

export interface GeminiActionPlanResponse {
  executive_summary: string;
  action_items: Array<{
    title: string;
    priority: ActionPriority;
    target_branch: "dev" | "main" | "both";
    component: string;
    domain_label: string;
    summary: string;
    rationale: string;
    proposed_fix: string;
    evidence_excerpt: string;
  }>;
}

/**
 * Calls Gemini API to cross-compare the Saturday [dev] and [main] weekly review
 * reports and return a structured JSON action plan.
 */
export async function analyzeWeeklyReviewsWithGemini(
  env: SundayReviewEnv,
  devIssue: GitHubIssueSummary | null,
  mainIssue: GitHubIssueSummary | null
): Promise<GeminiActionPlanResponse> {
  const apiKey = (env.GEMINI_API_KEY || "").trim();
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not configured on the Cloudflare Worker.");
  }

  const model = (env.GEMINI_REVIEW_MODEL || DEFAULT_GEMINI_REVIEW_MODEL).trim();
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;

  const devSection = devIssue
    ? `### [dev] Issue #${devIssue.number}: ${devIssue.title}\nURL: ${devIssue.html_url}\nCreated: ${devIssue.created_at}\n\n${truncateReportForPrompt(devIssue.body)}`
    : "### [dev] Issue: NOT FOUND";

  const mainSection = mainIssue
    ? `### [main] Issue #${mainIssue.number}: ${mainIssue.title}\nURL: ${mainIssue.html_url}\nCreated: ${mainIssue.created_at}\n\n${truncateReportForPrompt(mainIssue.body)}`
    : "### [main] Issue: NOT FOUND";

  const prompt = [
    "You are the Lead MLOps & Quant Engineering Reviewer for Midgley (a Python fuel-price forecasting system with wholesale RBOB and regional retail models).",
    "Ingest and cross-compare the latest Saturday weekly self-review GitHub issues from BOTH the `dev` and `main` branches below.",
    "Identify concrete model degradations, calibration regressions, CI coverage gaps, point-in-time (PIT) leakage warnings, test-data leaks, reporting/pipeline bugs, empty Hindsight episodic reflections, and high-impact divergences between `dev` and `main`.",
    "Return ONLY valid JSON matching this exact schema:",
    "{",
    '  "executive_summary": "2-3 sentence cross-branch summary",',
    '  "action_items": [',
    "    {",
    '      "title": "Short actionable engineering title (max 90 chars)",',
    '      "priority": "critical" | "high" | "medium" | "low",',
    '      "target_branch": "dev" | "main" | "both",',
    '      "component": "Short subsystem/file area (e.g. src/models.py, src/weekly_issue_reporter.py)",',
    '      "domain_label": "modeling" | "data-ingestion" | "infrastructure" | "dashboard" | "integration" | "api" | "security" | "mlops",',
    '      "summary": "Concise 2-3 sentence problem statement citing exact metrics from the issues",',
    '      "rationale": "Why this matters and how dev vs main compare",',
    '      "proposed_fix": "Concrete engineering steps a dev agent can execute on a branch off dev and test under TESTING=1",',
    '      "evidence_excerpt": "Verbatim key metrics/lines from the dev/main reports supporting this item (max 500 chars)"',
    "    }",
    "  ]",
    "}",
    "Produce 3 to 6 prioritized, non-overlapping action items ordered from highest to lowest urgency.",
    "",
    devSection,
    "",
    "---",
    "",
    mainSection
  ].join("\n");

  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": apiKey
    },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.2,
        responseMimeType: "application/json"
      }
    })
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`Gemini API failed with HTTP ${res.status}: ${errText.slice(0, 240)}`);
  }

  const data = (await res.json()) as any;
  const rawText = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
  if (!rawText) {
    throw new Error("Gemini API returned empty content.");
  }

  const parsed = JSON.parse(extractJsonText(rawText)) as any;
  const rawItems = Array.isArray(parsed?.action_items) ? parsed.action_items : [];
  if (rawItems.length === 0) {
    throw new Error("Gemini API returned zero action items.");
  }

  return {
    executive_summary: String(parsed?.executive_summary || "Weekly self-review action plan generated.").slice(0, 600),
    action_items: rawItems.slice(0, 7).map((item: any, idx: number) => ({
      title: String(item?.title || `Action Item ${idx + 1}`).slice(0, 120),
      priority: normalizePriority(item?.priority),
      target_branch: normalizeTargetBranch(item?.target_branch),
      component: String(item?.component || "src/").slice(0, 100),
      domain_label: normalizeDomainLabel(item?.domain_label),
      summary: String(item?.summary || "").slice(0, 800),
      rationale: String(item?.rationale || "").slice(0, 800),
      proposed_fix: String(item?.proposed_fix || "").slice(0, 900),
      evidence_excerpt: String(item?.evidence_excerpt || "").slice(0, 800)
    }))
  };
}

function getEmbedColor(item: WeeklyActionItem): number {
  if (item.status === "approved") return 0x16a34a; // Green
  if (item.status === "denied") return 0x64748b; // Slate
  switch (item.priority) {
    case "critical":
      return 0xdc2626;
    case "high":
      return 0xea580c;
    case "medium":
      return 0xd97706;
    default:
      return 0x2563eb;
  }
}

function getPriorityBadge(priority: ActionPriority): string {
  switch (priority) {
    case "critical":
      return "🔴 CRITICAL";
    case "high":
      return "🟠 HIGH";
    case "medium":
      return "🟡 MEDIUM";
    default:
      return "🔵 LOW";
  }
}

/**
 * Builds the Discord message payload (rich embed + Approve / Deny / Request Explanation buttons).
 */
export function buildActionItemDiscordPayload(
  item: WeeklyActionItem,
  statusNote?: string
): Record<string, any> {
  const sourceLinks: string[] = [];
  if (item.source_dev_issue && item.source_dev_url) {
    sourceLinks.push(`[dev #${item.source_dev_issue}](${item.source_dev_url})`);
  }
  if (item.source_main_issue && item.source_main_url) {
    sourceLinks.push(`[main #${item.source_main_issue}](${item.source_main_url})`);
  }

  let statusLine = "⏳ Pending Review";
  if (item.status === "approved") {
    const issueLink = item.github_issue_number && item.github_issue_url
      ? ` • [Issue #${item.github_issue_number}](${item.github_issue_url})`
      : "";
    statusLine = `✅ Approved by ${item.decided_by || "reviewer"}${issueLink}`;
  } else if (item.status === "denied") {
    statusLine = `❌ Denied by ${item.decided_by || "reviewer"}`;
  }
  if (statusNote) {
    statusLine = `${statusLine}\n${statusNote}`;
  }

  const decided = item.status !== "pending";

  const fields = [
    { name: "Priority", value: getPriorityBadge(item.priority), inline: true },
    { name: "Branch / Scope", value: `\`${item.target_branch}\` • \`${item.domain_label}\``, inline: true },
    { name: "Component", value: `\`${item.component}\``, inline: true },
    { name: "Proposed Fix", value: item.proposed_fix.slice(0, 1000) || "See rationale.", inline: false },
    {
      name: "Source Reviews",
      value: sourceLinks.length > 0 ? sourceLinks.join(" | ") : "Weekly Model Review",
      inline: true
    },
    { name: "Status", value: statusLine.slice(0, 1000), inline: true }
  ];

  return {
    embeds: [
      {
        title: `[${item.run_date_key}] ${item.title}`.slice(0, 250),
        description: item.summary.slice(0, 2000),
        color: getEmbedColor(item),
        fields,
        footer: {
          text: `Midgley Weekly Self-Review Action • ID: ${item.action_id}`
        },
        timestamp: item.created_at
      }
    ],
    components: [
      {
        type: 1,
        components: [
          {
            type: 2,
            style: 3,
            label: "Approve",
            emoji: { name: "✅" },
            custom_id: `weekly_action:approve:${item.action_id}`,
            disabled: decided
          },
          {
            type: 2,
            style: 4,
            label: "Deny",
            emoji: { name: "❌" },
            custom_id: `weekly_action:deny:${item.action_id}`,
            disabled: decided
          },
          {
            type: 2,
            style: 2,
            label: "Request Explanation",
            emoji: { name: "❓" },
            custom_id: `weekly_action:explain:${item.action_id}`,
            disabled: false
          }
        ]
      }
    ]
  };
}

export async function postActionItemToDiscord(
  env: SundayReviewEnv,
  channelId: string,
  item: WeeklyActionItem
): Promise<{ ok: boolean; messageId: string | null; error?: string }> {
  const token = (env.DISCORD_BOT_TOKEN || "").trim();
  if (!token) {
    return { ok: false, messageId: null, error: "DISCORD_BOT_TOKEN is not configured." };
  }

  const payload = buildActionItemDiscordPayload(item);
  const res = await fetch(`https://discord.com/api/v10/channels/${encodeURIComponent(channelId)}/messages`, {
    method: "POST",
    headers: {
      "Authorization": `Bot ${token}`,
      "Content-Type": "application/json",
      "User-Agent": "Midgley-Discord-Worker/1.0"
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errBody = await res.text().catch(() => "");
    return { ok: false, messageId: null, error: `Discord HTTP ${res.status}: ${errBody.slice(0, 200)}` };
  }

  const msg = (await res.json()) as any;
  return { ok: true, messageId: msg?.id ? String(msg.id) : null };
}

/**
 * Main Sunday 9:00 AM America/Chicago planner entry point.
 */
export async function runSundayWeeklyReviewPlanner(
  env: SundayReviewEnv,
  _ctx?: any,
  options: { force?: boolean; now?: Date } = {}
): Promise<SundayPlannerRunResult> {
  const now = options.now || new Date();
  const sched = isSundayNineAmCentral(now);

  if (!options.force && !sched.shouldRun) {
    return {
      status: "skipped_schedule",
      run_date_key: sched.localDateKey
    };
  }

  if (!options.force && (await hasRunAlreadyCompleted(env, sched.localDateKey))) {
    return {
      status: "skipped_already_ran",
      run_date_key: sched.localDateKey
    };
  }

  const channelId = (env.DISCORD_SUNDAY_REVIEW_CHANNEL_ID || DEFAULT_SUNDAY_REVIEW_CHANNEL_ID).trim();

  try {
    const { dev, main } = await fetchLatestWeeklyReviewIssues(env);
    if (!dev && !main) {
      return {
        status: "error",
        run_date_key: sched.localDateKey,
        error: "No weekly-review GitHub issues found for dev or main."
      };
    }

    const plan = await analyzeWeeklyReviewsWithGemini(env, dev, main);
    const createdAt = now.toISOString();
    const compactDate = sched.localDateKey.replace(/-/g, "");

    let postedCount = 0;
    let failedPosts = 0;

    for (let i = 0; i < plan.action_items.length; i++) {
      const raw = plan.action_items[i];
      const suffix = Math.random().toString(36).slice(2, 6);
      const actionId = `wr_${compactDate}_${String(i + 1).padStart(2, "0")}_${suffix}`;

      const item: WeeklyActionItem = {
        action_id: actionId,
        run_date_key: sched.localDateKey,
        title: raw.title,
        priority: raw.priority,
        target_branch: raw.target_branch,
        component: raw.component,
        domain_label: raw.domain_label,
        summary: raw.summary,
        rationale: raw.rationale,
        proposed_fix: raw.proposed_fix,
        source_dev_issue: dev?.number ?? null,
        source_main_issue: main?.number ?? null,
        source_dev_url: dev?.html_url ?? "",
        source_main_url: main?.html_url ?? "",
        source_context_excerpt: raw.evidence_excerpt,
        discord_channel_id: channelId,
        discord_message_id: null,
        status: "pending",
        decided_by: null,
        decided_at: null,
        github_issue_number: null,
        github_issue_url: null,
        created_at: createdAt
      };

      const postRes = await postActionItemToDiscord(env, channelId, item);
      if (postRes.ok) {
        item.discord_message_id = postRes.messageId;
        postedCount++;
      } else {
        failedPosts++;
        console.error(`[SundayReviewPlanner] Failed to post ${actionId}: ${postRes.error}`);
      }

      await saveWeeklyActionItem(env, item);
    }

    await recordRunCompletion(env, sched.localDateKey, dev, main, plan.action_items.length);

    return {
      status: "completed",
      run_date_key: sched.localDateKey,
      dev_issue_number: dev?.number ?? null,
      main_issue_number: main?.number ?? null,
      action_count: plan.action_items.length,
      posted_count: postedCount,
      failed_posts: failedPosts,
      executive_summary: plan.executive_summary
    };
  } catch (err: any) {
    console.error(`[SundayReviewPlanner] Error: ${err?.message || String(err)}`);
    return {
      status: "error",
      run_date_key: sched.localDateKey,
      error: err?.message || String(err)
    };
  }
}

async function openGitHubIssueForApprovedAction(
  env: SundayReviewEnv,
  item: WeeklyActionItem,
  reviewerDisplay: string
): Promise<{ number: number; html_url: string }> {
  const token = getGitHubToken(env);
  if (!token) {
    throw new Error("GitHub token (GH_PAT / GITHUB_TOKEN) is not configured.");
  }
  const { owner, repo } = getRepoCoords(env);

  const sourceRefs: string[] = [];
  if (item.source_dev_issue) {
    sourceRefs.push(`- **dev weekly review:** [#${item.source_dev_issue}](${item.source_dev_url})`);
  }
  if (item.source_main_issue) {
    sourceRefs.push(`- **main weekly review:** [#${item.source_main_issue}](${item.source_main_url})`);
  }

  const issueBody = [
    `## Weekly Self-Review Action Item (\`${item.action_id}\`)`,
    "",
    `- **Approved By:** ${reviewerDisplay}`,
    `- **Priority:** \`${item.priority}\``,
    `- **Target Branch / Scope:** \`${item.target_branch}\``,
    `- **Component:** \`${item.component}\``,
    ...sourceRefs,
    "",
    "### Problem Statement",
    item.summary,
    "",
    "### Cross-Branch Rationale (`dev` vs `main`)",
    item.rationale,
    "",
    "### Proposed Fix",
    item.proposed_fix,
    "",
    "### Evidence Excerpt",
    "```text",
    item.source_context_excerpt || "See linked weekly review issues.",
    "```",
    "",
    "### Agent Execution Guardrails",
    "- Base your feature branch off `dev` and open a **Draft PR targeting `dev`**.",
    "- Follow `AGENTS.md` and relevant `.agents/skills/` runbooks (Point-in-Time safety, `TESTING=1` isolation, LF line endings).",
    "- Run `ruff check .` and targeted `TESTING=1 pytest` checks before opening the PR."
  ].join("\n");

  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "Midgley-Sunday-Review-Worker/1.0"
    },
    body: JSON.stringify({
      title: `[Weekly Action] ${item.title}`.slice(0, 240),
      body: issueBody,
      labels: ["weekly-action-approved", item.domain_label]
    })
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`GitHub issue creation failed (HTTP ${res.status}): ${errText.slice(0, 200)}`);
  }

  const created = (await res.json()) as any;
  return {
    number: Number(created.number),
    html_url: String(created.html_url || "")
  };
}

async function dispatchDevAgentWorkflow(
  env: SundayReviewEnv,
  item: WeeklyActionItem,
  issueNumber: number,
  issueUrl: string,
  reviewerDisplay: string
): Promise<{ dispatched: boolean; error?: string }> {
  const token = getGitHubToken(env);
  if (!token) {
    return { dispatched: false, error: "GitHub token not configured." };
  }
  const { owner, repo } = getRepoCoords(env);

  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/dispatches`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "Midgley-Sunday-Review-Worker/1.0"
    },
    body: JSON.stringify({
      event_type: "weekly-action-approved",
      // GitHub repository_dispatch enforces a strict max of 10 top-level keys in client_payload
      client_payload: {
        action_id: item.action_id,
        issue_number: issueNumber,
        issue_url: issueUrl,
        priority: item.priority,
        discord_channel_id: item.discord_channel_id,
        approved_by: reviewerDisplay
      }
    })
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    return { dispatched: false, error: `GitHub dispatch failed (HTTP ${res.status}): ${errText.slice(0, 200)}` };
  }
  return { dispatched: true };
}

async function generateActionExplanationWithGemini(
  env: SundayReviewEnv,
  item: WeeklyActionItem
): Promise<string> {
  const apiKey = (env.GEMINI_API_KEY || "").trim();
  if (!apiKey) {
    return [
      `**Rationale:** ${item.rationale}`,
      `**Proposed Fix:** ${item.proposed_fix}`,
      `**Evidence:** ${item.source_context_excerpt || "See linked weekly review issues."}`
    ].join("\n\n");
  }

  const model = (env.GEMINI_REVIEW_MODEL || DEFAULT_GEMINI_REVIEW_MODEL).trim();
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;

  const prompt = [
    "You are explaining a Midgley weekly self-review action item to the repository maintainer in Discord.",
    "Be concise, technical, and concrete (under 300 words). Cover:",
    "1. Exact root cause & why dev and main behave differently here",
    "2. Which files/components are likely involved",
    "3. Risk of deferring vs. approving now",
    "4. How the dev agent will verify the fix safely under TESTING=1",
    "",
    `Title: ${item.title}`,
    `Priority: ${item.priority} | Target Branch: ${item.target_branch} | Component: ${item.component}`,
    `Summary: ${item.summary}`,
    `Rationale: ${item.rationale}`,
    `Proposed Fix: ${item.proposed_fix}`,
    `Evidence Excerpt: ${item.source_context_excerpt}`
  ].join("\n");

  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": apiKey
    },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.25 }
    })
  });

  if (!res.ok) {
    return `**Rationale:** ${item.rationale}\n\n**Proposed Fix:** ${item.proposed_fix}`;
  }

  const data = (await res.json()) as any;
  const text = String(data?.candidates?.[0]?.content?.parts?.[0]?.text || "").trim();
  return text || `**Rationale:** ${item.rationale}\n\n**Proposed Fix:** ${item.proposed_fix}`;
}

async function patchDiscordOriginalInteractionMessage(
  appId: string,
  interactionToken: string,
  payload: Record<string, any>
): Promise<void> {
  if (!appId || !interactionToken) return;
  const url = `https://discord.com/api/v10/webhooks/${encodeURIComponent(appId)}/${encodeURIComponent(interactionToken)}/messages/@original`;
  await fetch(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "Midgley-Discord-Worker/1.0"
    },
    body: JSON.stringify(payload)
  });
}

/**
 * Handles Discord `MESSAGE_COMPONENT` (type 3) clicks for `weekly_action:(approve|deny|explain):<action_id>`.
 */
export async function handleWeeklyActionComponentInteraction(
  interaction: any,
  env: SundayReviewEnv,
  ctx?: any
): Promise<Response> {
  const customId = String(interaction?.data?.custom_id || "");
  const parts = customId.split(":");
  if (parts.length < 3 || parts[0] !== "weekly_action") {
    return new Response(
      JSON.stringify({
        type: 4,
        data: { flags: 64, content: "⚠️ Unrecognized weekly action button payload." }
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  const verb = parts[1];
  const actionId = parts.slice(2).join(":");
  const item = await loadWeeklyActionItem(env, actionId);

  if (!item) {
    return new Response(
      JSON.stringify({
        type: 4,
        data: {
          flags: 64,
          content: `⚠️ Could not find weekly action item \`${actionId}\` in D1 storage.`
        }
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  const userObj = interaction?.member?.user || interaction?.user || {};
  const reviewerDisplay = userObj.id ? `<@${userObj.id}>` : `@${userObj.username || "reviewer"}`;
  const appId = String(interaction?.application_id || env.DISCORD_APP_ID || DEFAULT_DISCORD_BOT_USER_ID);
  const interactionToken = String(interaction?.token || "");

  if (verb === "deny") {
    item.status = "denied";
    item.decided_by = reviewerDisplay;
    item.decided_at = new Date().toISOString();
    await saveWeeklyActionItem(env, item);

    return new Response(
      JSON.stringify({
        type: 7,
        data: buildActionItemDiscordPayload(item)
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  if (verb === "approve") {
    if (item.status === "approved") {
      const existingRef = item.github_issue_url
        ? `[Issue #${item.github_issue_number}](${item.github_issue_url})`
        : "already approved";
      return new Response(
        JSON.stringify({
          type: 4,
          data: { flags: 64, content: `✅ Action \`${actionId}\` was already approved (${existingRef}).` }
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    const workPromise = (async () => {
      try {
        const ghIssue = await openGitHubIssueForApprovedAction(env, item, reviewerDisplay);
        item.status = "approved";
        item.decided_by = reviewerDisplay;
        item.decided_at = new Date().toISOString();
        item.github_issue_number = ghIssue.number;
        item.github_issue_url = ghIssue.html_url;
        await saveWeeklyActionItem(env, item);

        const dispatchRes = await dispatchDevAgentWorkflow(
          env,
          item,
          ghIssue.number,
          ghIssue.html_url,
          reviewerDisplay
        );

        const note = dispatchRes.dispatched
          ? "🤖 Dev agent dispatched (`dev-vm` primary → GitHub Cloud `agy` fallback)."
          : `⚠️ Issue opened, but dev agent dispatch failed: ${dispatchRes.error}`;

        await patchDiscordOriginalInteractionMessage(
          appId,
          interactionToken,
          buildActionItemDiscordPayload(item, note)
        );
      } catch (err: any) {
        const errMsg = err?.message || String(err);
        console.error(`[SundayReviewPlanner] Approve flow failed for ${actionId}: ${errMsg}`);
        await patchDiscordOriginalInteractionMessage(
          appId,
          interactionToken,
          buildActionItemDiscordPayload(item, `⚠️ Approval failed: ${errMsg.slice(0, 180)}`)
        );
      }
    })();

    if (ctx && typeof ctx.waitUntil === "function") {
      ctx.waitUntil(workPromise);
    } else {
      await workPromise;
    }

    // Type 6: DEFERRED_UPDATE_MESSAGE — acknowledges immediately within Discord's 3s window
    return new Response(JSON.stringify({ type: 6 }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  if (verb === "explain") {
    const workPromise = (async () => {
      try {
        const explanation = await generateActionExplanationWithGemini(env, item);
        await patchDiscordOriginalInteractionMessage(appId, interactionToken, {
          embeds: [
            {
              title: `❓ Deep-Dive Explanation: ${item.title}`.slice(0, 250),
              description: explanation.slice(0, 4000),
              color: 0x3b82f6,
              footer: { text: `Requested by ${userObj.username || "reviewer"} • Action ID: ${item.action_id}` },
              timestamp: new Date().toISOString()
            }
          ]
        });
      } catch (err: any) {
        await patchDiscordOriginalInteractionMessage(appId, interactionToken, {
          content: `⚠️ Could not generate explanation for \`${item.action_id}\`: ${err?.message || String(err)}`
        });
      }
    })();

    if (ctx && typeof ctx.waitUntil === "function") {
      ctx.waitUntil(workPromise);
    } else {
      await workPromise;
    }

    // Type 5: DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
    return new Response(JSON.stringify({ type: 5 }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  return new Response(
    JSON.stringify({
      type: 4,
      data: { flags: 64, content: `⚠️ Unsupported weekly action verb \`${verb}\`.` }
    }),
    { headers: { "Content-Type": "application/json" } }
  );
}
