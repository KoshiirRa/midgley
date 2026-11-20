import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  DEFAULT_SUNDAY_REVIEW_CHANNEL_ID,
  isSundayNineAmCentral,
  buildActionItemDiscordPayload,
  runSundayWeeklyReviewPlanner,
  handleWeeklyActionComponentInteraction,
  saveWeeklyActionItem,
  loadWeeklyActionItem,
  _resetSundayPlannerMemoryForTests,
  WeeklyActionItem
} from "../workers/sunday_review_planner";
import worker from "../workers/intraday_monitor_worker";

describe("Sunday Weekly Self-Review Action Planner", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    _resetSundayPlannerMemoryForTests();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("enforces DST-safe Sunday 9:00 AM America/Chicago gating", () => {
    // CST (Standard Time, UTC-6): Sunday 2026-11-15 15:00 UTC === 09:00 America/Chicago
    const cst9am = isSundayNineAmCentral(new Date("2026-11-15T15:00:00Z"));
    expect(cst9am.shouldRun).toBe(true);
    expect(cst9am.localDateKey).toBe("2026-11-15");

    // CST 14:00 UTC === 08:00 America/Chicago -> must NOT run
    const cst8am = isSundayNineAmCentral(new Date("2026-11-15T14:00:00Z"));
    expect(cst8am.shouldRun).toBe(false);

    // CDT (Daylight Time, UTC-5): Sunday 2026-07-12 14:00 UTC === 09:00 America/Chicago
    const cdt9am = isSundayNineAmCentral(new Date("2026-07-12T14:00:00Z"));
    expect(cdt9am.shouldRun).toBe(true);
    expect(cdt9am.localDateKey).toBe("2026-07-12");

    // Monday 15:00 UTC -> must NOT run
    const monday = isSundayNineAmCentral(new Date("2026-11-16T15:00:00Z"));
    expect(monday.shouldRun).toBe(false);
  });

  it("builds Discord embed with Approve, Deny, and Request Explanation buttons", () => {
    const sample: WeeklyActionItem = {
      action_id: "wr_20261115_01_abcd",
      run_date_key: "2026-11-15",
      title: "Fix Oakland_CA $2.13/gal MAE calibration offset on dev",
      priority: "critical",
      target_branch: "dev",
      component: "src/metro_nowcast.py",
      domain_label: "modeling",
      summary: "Oakland_CA and BayArea_CA show ~$2.13/gal MAE on dev.",
      rationale: "Likely wholesale-vs-retail spread offset.",
      proposed_fix: "Audit metro calibration base offset and add regression test.",
      source_dev_issue: 712,
      source_main_issue: 713,
      source_dev_url: "https://github.com/KoshiirRa/midgley/issues/712",
      source_main_url: "https://github.com/KoshiirRa/midgley/issues/713",
      source_context_excerpt: "Oakland_CA MAE $2.1297/gal",
      discord_channel_id: DEFAULT_SUNDAY_REVIEW_CHANNEL_ID,
      discord_message_id: null,
      status: "pending",
      decided_by: null,
      decided_at: null,
      github_issue_number: null,
      github_issue_url: null,
      created_at: "2026-11-15T15:00:00.000Z"
    };

    const payload = buildActionItemDiscordPayload(sample);
    expect(payload.embeds).toHaveLength(1);
    expect(payload.embeds[0].title).toContain("Fix Oakland_CA");
    expect(payload.components).toHaveLength(1);

    const buttons = payload.components[0].components;
    expect(buttons).toHaveLength(3);
    expect(buttons[0].custom_id).toBe("weekly_action:approve:wr_20261115_01_abcd");
    expect(buttons[0].style).toBe(3);
    expect(buttons[0].disabled).toBe(false);
    expect(buttons[1].custom_id).toBe("weekly_action:deny:wr_20261115_01_abcd");
    expect(buttons[1].style).toBe(4);
    expect(buttons[1].disabled).toBe(false);
    expect(buttons[2].custom_id).toBe("weekly_action:explain:wr_20261115_01_abcd");
    expect(buttons[2].style).toBe(2);
    expect(buttons[2].disabled).toBe(false);
  });

  it("ingests dev + main weekly issues, analyzes via Gemini, posts to Discord, and deduplicates same-day runs", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/issues?labels=weekly-review")) {
        return new Response(
          JSON.stringify([
            {
              number: 713,
              title: "[main] Weekly Model Review Report (2026-11-14)",
              html_url: "https://github.com/KoshiirRa/midgley/issues/713",
              body: "95% CI coverage: 35.4%",
              state: "open",
              created_at: "2026-11-14T19:21:24Z"
            },
            {
              number: 712,
              title: "[dev] Weekly Model Review Report (2026-11-14)",
              html_url: "https://github.com/KoshiirRa/midgley/issues/712",
              body: "Oakland_CA MAE $2.1297/gal; Test_Region present",
              state: "open",
              created_at: "2026-11-14T13:27:56Z"
            }
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.includes("generativelanguage.googleapis.com")) {
        return new Response(
          JSON.stringify({
            candidates: [
              {
                content: {
                  parts: [
                    {
                      text: JSON.stringify({
                        executive_summary: "Two critical regressions found across dev and main.",
                        action_items: [
                          {
                            title: "Purge Test_Region leak from dev ledger",
                            priority: "critical",
                            target_branch: "dev",
                            component: "src/prediction_logger.py",
                            domain_label: "mlops",
                            summary: "Test_Region appeared in dev weekly report.",
                            rationale: "Violates test isolation.",
                            proposed_fix: "Filter Test_Region and guard TESTING=1.",
                            evidence_excerpt: "Test_Region 0/10 Pending"
                          }
                        ]
                      })
                    }
                  ]
                }
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.includes(`/channels/${DEFAULT_SUNDAY_REVIEW_CHANNEL_ID}/messages`)) {
        const body = JSON.parse(String(init?.body || "{}"));
        expect(body.components[0].components).toHaveLength(3);
        return new Response(JSON.stringify({ id: "999888777" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }
      return new Response("Not Found", { status: 404 });
    });

    globalThis.fetch = fetchMock as any;

    const env = {
      GH_PAT: "gh-test-token",
      GEMINI_API_KEY: "gemini-test-key",
      DISCORD_BOT_TOKEN: "discord-test-token"
    };

    const sundayNineAm = new Date("2026-11-15T15:00:00Z");
    const firstRun = await runSundayWeeklyReviewPlanner(env, undefined, { now: sundayNineAm });
    expect(firstRun.status).toBe("completed");
    expect(firstRun.dev_issue_number).toBe(712);
    expect(firstRun.main_issue_number).toBe(713);
    expect(firstRun.action_count).toBe(1);
    expect(firstRun.posted_count).toBe(1);

    // Second invocation on the same Sunday must be deduplicated
    const secondRun = await runSundayWeeklyReviewPlanner(env, undefined, { now: sundayNineAm });
    expect(secondRun.status).toBe("skipped_already_ran");
  });

  it("handles Approve, Deny, and Request Explanation button interactions", async () => {
    const baseItem: WeeklyActionItem = {
      action_id: "wr_20261115_01_test",
      run_date_key: "2026-11-15",
      title: "Restore main 95% CI coverage",
      priority: "high",
      target_branch: "main",
      component: "src/models.py",
      domain_label: "modeling",
      summary: "Main 95% CI coverage dropped to 35.4%.",
      rationale: "Residual variance calibration drifted.",
      proposed_fix: "Recalibrate quantile intervals by region and horizon.",
      source_dev_issue: 712,
      source_main_issue: 713,
      source_dev_url: "https://github.com/KoshiirRa/midgley/issues/712",
      source_main_url: "https://github.com/KoshiirRa/midgley/issues/713",
      source_context_excerpt: "95% Confidence Interval Coverage: 35.4%",
      discord_channel_id: DEFAULT_SUNDAY_REVIEW_CHANNEL_ID,
      discord_message_id: "111222333",
      status: "pending",
      decided_by: null,
      decided_at: null,
      github_issue_number: null,
      github_issue_url: null,
      created_at: "2026-11-15T15:00:00.000Z"
    };

    const env = {
      GH_PAT: "gh-test-token",
      GEMINI_API_KEY: "gemini-test-key",
      DISCORD_BOT_TOKEN: "discord-test-token",
      DISCORD_APP_ID: "1550234222826889246"
    };

    await saveWeeklyActionItem(env, { ...baseItem });

    const calls: string[] = [];
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push(`${init?.method || "GET"} ${url}`);
      if (url.endsWith("/repos/KoshiirRa/midgley/issues")) {
        return new Response(
          JSON.stringify({ number: 720, html_url: "https://github.com/KoshiirRa/midgley/issues/720" }),
          { status: 201, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.endsWith("/repos/KoshiirRa/midgley/dispatches")) {
        const body = JSON.parse(String(init?.body || "{}"));
        expect(body.event_type).toBe("weekly-action-approved");
        expect(body.client_payload.issue_number).toBe(720);
        expect(Object.keys(body.client_payload).length).toBeLessThanOrEqual(10);
        return new Response(null, { status: 204 });
      }
      if (url.includes("generativelanguage.googleapis.com")) {
        return new Response(
          JSON.stringify({
            candidates: [{ content: { parts: [{ text: "Detailed root cause explanation for CI coverage." }] } }]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.includes("/messages/@original")) {
        return new Response(JSON.stringify({ id: "orig" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }
      return new Response("Not Found", { status: 404 });
    }) as any;

    // 1. Approve flow
    const approveRes = await handleWeeklyActionComponentInteraction(
      {
        type: 3,
        application_id: "1550234222826889246",
        token: "tok-approve",
        member: { user: { id: "42", username: "marty" } },
        data: { custom_id: "weekly_action:approve:wr_20261115_01_test" }
      },
      env
    );
    const approveJson = (await approveRes.json()) as any;
    expect(approveJson.type).toBe(6);

    const updated = await loadWeeklyActionItem(env, "wr_20261115_01_test");
    expect(updated?.status).toBe("approved");
    expect(updated?.github_issue_number).toBe(720);
    expect(calls.some(c => c.includes("/dispatches"))).toBe(true);
    expect(calls.some(c => c.includes("PATCH") && c.includes("/messages/@original"))).toBe(true);

    // 2. Request Explanation flow
    const explainRes = await handleWeeklyActionComponentInteraction(
      {
        type: 3,
        application_id: "1550234222826889246",
        token: "tok-explain",
        member: { user: { id: "42", username: "marty" } },
        data: { custom_id: "weekly_action:explain:wr_20261115_01_test" }
      },
      env
    );
    const explainJson = (await explainRes.json()) as any;
    expect(explainJson.type).toBe(5);

    // 3. Deny flow on a fresh item
    const denyItem: WeeklyActionItem = { ...baseItem, action_id: "wr_20261115_02_deny", status: "pending" };
    await saveWeeklyActionItem(env, denyItem);
    const denyRes = await handleWeeklyActionComponentInteraction(
      {
        type: 3,
        application_id: "1550234222826889246",
        token: "tok-deny",
        member: { user: { id: "42", username: "marty" } },
        data: { custom_id: "weekly_action:deny:wr_20261115_02_deny" }
      },
      env
    );
    const denyJson = (await denyRes.json()) as any;
    expect(denyJson.type).toBe(7);
    expect(denyJson.data.components[0].components[0].disabled).toBe(true);
    expect(denyJson.data.components[0].components[1].disabled).toBe(true);
    expect(denyJson.data.components[0].components[2].disabled).toBe(false);
  });

  it("enforces fail-closed auth on POST /run-sunday-review", async () => {
    const req = new Request("https://worker.example.com/run-sunday-review", {
      method: "POST"
    });
    const res = await worker.fetch(req, { ADMIN_TOKEN: "secret-admin" } as any, {});
    expect(res.status).toBe(401);
  });
});
