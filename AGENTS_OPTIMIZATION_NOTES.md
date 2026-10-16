# AGENTS.md optimization notes

## Adopt the files

Replace the repository's root `AGENTS.md` with the replacement. Put `MIDGLEY_AGENT_REFERENCE.md` beside it and retain these notes for migration/review. The uploaded original was not modified. The reference preserves its detailed material, diagrams, equations, and issue history, apart from the privacy substitutions below.

Load the active instructions once. Read only relevant reference sections on demand; never automatically import the large reference or treat its historical commands as execution permission.

### If you use Gemini CLI

Configure `AGENTS.md` instead of the default `GEMINI.md`; inspect `/memory show` and refresh with `/memory reload`.

Merge this fragment into existing `settings.json`, preserving unrelated settings:

```json
{"context":{"fileName":["AGENTS.md"]}}
```

Use this configuration as the single instruction entrypoint; do not also load the same rules through a wrapper or add/import the reference. Compatibility source: [official Gemini CLI documentation](https://geminicli.com/docs/cli/gemini-md/) (updated June 18, 2026).

## Measured changes

Counts use whitespace-delimited words, physical lines, and UTF-8 bytes; they are not token measurements.

| File | Words | Lines | Bytes |
| --- | ---: | ---: | ---: |
| Uploaded original (unchanged) | 23,601 | 1,101 | 212,291 |
| `AGENTS.md` | 2,030 | 129 | 16,817 |
| `MIDGLEY_AGENT_REFERENCE.md` | 23,722 | 1,110 | 213,350 |
| `AGENTS_OPTIMIZATION_NOTES.md` | 1,426 | 105 | 10,712 |

The active file is 91.40% smaller by word count and 92.08% smaller by byte count. The large archive remains available without contributing to the intended always-loaded context. No model-quality, execution-speed, or Gemini-runtime improvement was measured.

## Substantive policy clarifications

- Separate the coding assistant's duties from Midgley's application-agent descriptions. Replace catalog/history-heavy always-loaded context with scoped rules and conditional documentation obligations.
- Make pushing, deployment, release publication, remote wiki changes, SSH, and live submissions authorization-dependent. Prepare local documentation and report pending external work when authorization/tools are absent. Preserve release reconciliation obligations, including the self-hosted blank-slate scope, for authorized release tasks.
- Require genuine observed actuals and honest missingness for production evaluation. The archive's filtered/smoothed-nowcast descriptions cannot authorize relabeling estimates as observed ground truth; verify that behavior in code. Keep backtests, fixtures, simulations, and development submissions separate from prospective public results.
- Replace contradictory numeric defaults and unconditional guarantees with verified configuration, empirical calibration, and measured claims. Preserve explicit quota caps, the five-anomaly sweep cap, Python compatibility, and other genuine safety requirements.
- Preserve existing explicitly configured optional providers without authorizing new spend; reject Apify/new paid services. Consolidate repeated wiki, math, sources, telemetry, packaging, and release duties rather than deleting them.
- Move the giant root diagram into reference context; future architecture changes must update relevant reference/generator-owned diagrams, not restore it to active instructions. Regenerate affected public pages only from controlled valid-data state; never publish mocks.

## Conflicts requiring code verification

These are unresolved implementation questions, not findings from a repository audit.

| Conflict in uploaded source | Replacement rule and verification target |
| --- | --- |
| Uniform 4–5-day decay versus category values 14/7/5/4/2.5 | Use configured category half-lives and validated calibration. Inspect feature engineering, `CATEGORY_HALF_LIVES_DAYS`, and calibration before changing values. |
| UUIDv4 forecast IDs versus deterministic hashes with differing tuples in Issues #559/#602 | Identify the actual canonical ID factory across logger/import/migration paths. Verify exact-replay idempotency and preservation of distinct intra-day revisions; do not select a hash tuple from prose. |
| Region counts vary 7/8/9/10; BayArea_CA/oakland consolidation conflicts with separate descriptions; Newark_NJ versus Newark_DE | Verify registry, aliases, routing, provenance, and metadata. Do not freeze a region list/count in assistant policy. |
| Agent schedules conflict with directive 27; fixed Central/UTC offsets omit daylight saving | Read workflow, unit/timer, and worker configuration; label time zones and derive daylight-saving conversions. Do not assert one archived cron schedule is current. |
| HTTP 3.05s connect/20s read versus Hindsight 60s/two retries, inventory <=5s, and final <=2–5s budgets | Verify effective client/connector/memory configuration and enforced budgets. Retain bounded fail-fast behavior without claiming a timeout value is already implemented. |
| Connector 7-day/monthly caches versus universal 30–60-day macro TTL guidance | Verify service TTLs and freshness separately from update cadence, release lag, and point-in-time availability. |
| Hosted Vectorize Hindsight migration coexists with Cloud Run/Supabase telemetry descriptions | Verify current backend/configuration, inventory probes, fallback paths, and telemetry wiring; do not assume migration status. |
| Static prices/taxes/accuracy, exact statistical guarantees, and a “26-feed” heading with larger partitions | Keep these as unverified historical claims. Derive current figures from validated data/configuration; verify statistical assumptions and actual catalog inventory. |
| Duplicate 12/13 headings and nonsequential 1.6/1.5 | Use distinct topical headings in active instructions. Preserve original numbering only in the reference for traceability. |

## Coverage of source directives

This map covers all 29 integer section numbers. Rows 12 and 13 cover both duplicated headings. All detailed material remains in the reference; the map identifies where active duties were consolidated.

| Source number / subject | Active replacement section(s) |
| --- | --- |
| 1 — ingestion/event extraction | Project and source map; Data integrity; Storage, caching, and connectors; Conditional matrix |
| 2 — memory fusion | Features, forecasting, and evaluation; Data integrity |
| 3 — quantitative forecasting | Features, forecasting, and evaluation; Data integrity; Runtime; Test isolation |
| 4 — regions and branch reconciliation | Project/source map; Conditional matrix; Branches, packaging, and operations |
| 5 — scenario synthesis | Features, forecasting, and evaluation; Security; Conditional matrix |
| 6 — ledger/evaluation | Data integrity; Runtime; Storage; Conditional matrix |
| 7 — review/feedback | Features/evaluation; Runtime and memory; Connectors; GitHub governance |
| 8 — dashboard/presentation | Data integrity; Conditional matrix; Security |
| 9 — development services | Branches/operations; Conditional matrix; Security and external effects |
| 10 — nightly release automation | Branches/operations; GitHub governance and releases; Security |
| 11 — REST/MCP gateway | Project/source map; Connectors; Security; Conditional matrix |
| 12 — Automotive **and** Ruff gate | GitHub issue routing/client contracts; Test isolation and validation; CI gates |
| 13 — Wiki maintenance **and** credential health | Conditional matrix; Security and external effects; Connector failure handling |
| 14 — three-track issue triage | GitHub governance and releases |
| 15 — multi-tier caching | Storage, caching, and connectors |
| 16 — client repository routing | GitHub governance and releases; Conditional matrix |
| 17 — feed/wiki synchronization | Conditional matrix; authorization/local preparation rules |
| 18 — public math synchronization | Conditional matrix; Features, forecasting, and evaluation |
| 19 — GitHub Markdown payloads | GitHub governance and releases |
| 20 — single active release draft | GitHub governance and releases |
| 21 — isolated test mode | Test isolation and validation |
| 22 — sources/catalog/ledger | Conditional matrix; Storage, caching, and connectors |
| 23 — public telemetry | Runtime and memory; Conditional matrix; Test isolation |
| 24 — Headline Arena benchmark | Features/evaluation; Security; Connectors; Test isolation |
| 25 — inventory/anomaly reconciliation | Runtime and memory; Storage; Conditional matrix |
| 26 — manifest/reconciler | GitHub governance and releases; Conditional matrix |
| 27 — durable containers/schedules/links | Branches/operations; Conditional matrix; Test isolation |
| 28 — packaging/CI/concurrency | Branches, packaging, and operations; Test isolation |
| 29 — efficiency invariants | Runtime and memory efficiency; Storage, caching, and connectors |

The fractional 1.5 knowledge-graph and 1.6 Qlib/RD-Agent sections remain intact in the reference; their applicable duties route through the source map, point-in-time safety, features/evaluation, security, and documentation matrix. A coding assistant is not instructed to run or impersonate those application agents for every task.

## Privacy sanitization

Replaced four private-address occurrences, including two machine-specific SSH login pairs, with `<PRIVATE_HOST_ADDRESS>` or `<DEV_USER>@<DEV_HOST>`. Replaced six private named-host mentions with `<DEV_HOST>`, and one development loopback service URL with `http://<DEV_HOST>:8000`. No concrete raw credentials or machine-specific home paths were detected in the uploaded text. These substitutions preserve architectural intent without publishing private access details. Placeholder commands are reference-only and were not executed.

## Verification and limitations

Document-only checks passed for computed sizes/reductions, unchanged source bytes, faithful archive preservation apart from the listed substitutions, balanced fenced blocks, unique active headings, local companion links, privacy/credential-pattern screening, and directive/invariant coverage. The source's repository paths, archived documentation links, architecture, provider claims, runtime behavior, and benchmark results remain unverified.

No repository checkout or Gemini installation was supplied. No embedded source commands, repository tests/lint, generators, network probes, authentication, deployment, wiki updates, or Gemini `/memory` commands were executed. The commands in `AGENTS.md` are proposed repository validation, not checks run here. Publication/file checks do not establish actual implementation correctness or Gemini compatibility in Marty's environment.
