# Axiom & Sentry Observability Dashboards & Alerting Guide

This guide provides ready-to-use **APL (Axiom Processing Language)** queries, dashboard widget templates, and **Sentry Alert Rules** for Midgley's Cloudflare Workers ([workers/intraday_monitor_worker.ts](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/intraday_monitor_worker.ts) and [workers/cache_worker.ts](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/cache_worker.ts)).

---

## 🪓 Axiom Dashboard Setup (`midgley-workers` Dataset)

In Axiom, navigate to **Dashboards -> Create Dashboard -> Add Element**:

### 1. Widget 1: Intraday Event Activity (Headlines Scanned vs Anomalies Detected)
* **Element Type:** `Chart aggregation` or `Visualize results`
* **Visualization:** Timeseries Line Chart
* **Description:** Monitors total RSS headlines parsed vs geopolitical/supply disruption anomalies detected per 1-hour bin.
* **APL Query:**
  ```kql
  ['midgley-workers']
  | where service == "midgley-intraday-monitor" and event == "intraday_monitoring_cycle"
  | summarize Headlines = sum(summary.headlines_parsed), Anomalies = sum(summary.anomalies_detected) by bin(1h)
  ```

### 2. Widget 2: GitHub Dispatch Trigger Activity
* **Element Type:** `Chart aggregation`
* **Visualization:** Bar / Stacked Column Chart
* **Description:** Tracks successful model recalibration triggers (`github_dispatch_success`) vs failed dispatches.
* **APL Query:**
  ```kql
  ['midgley-workers']
  | where service == "midgley-intraday-monitor"
  | where event in ("github_dispatch_success", "github_dispatch_failure")
  | summarize Count = count() by event, bin(1h)
  ```

### 3. Widget 3: Edge Cache Performance (`midgley-cache-worker`)
* **Element Type:** `Chart aggregation`
* **Visualization:** Stacked Area Chart
* **Description:** Tracks Tier 2 D1 Cache Hits, Misses, and Stores over 15-minute windows.
* **APL Query:**
  ```kql
  ['midgley-workers']
  | where service == "midgley-cache-worker"
  | summarize Hits = countif(event == "cache_get_hit"), Misses = countif(event == "cache_get_miss"), Stores = countif(event == "cache_store_success") by bin(15m)
  ```

### 4. Widget 4: Live Worker Log Stream
* **Element Type:** `Log stream`
* **Description:** Displays real-time structured console logs from both workers.
* **APL Query:**
  ```kql
  ['midgley-workers']
  | sort by _time desc
  | limit 100
  ```

---

## 🔔 Axiom Alert Rules (Monitors)

In Axiom, navigate to **Monitors -> New monitor** (top right dropdown):

1. **RSS Feed Fetch Error Spike:**
   * **Monitor Type:** Select **`Threshold monitor`**
   * **APL Query:**
     ```kql
     ['midgley-workers']
     | where event == "rss_fetch_error"
     | summarize count()
     ```
   * **Trigger Condition:** `count() > 5` within 30 minutes.
   * **Action:** Email / Slack notification.

2. **Geopolitical Anomaly Alert:**
   * **Monitor Type:** Select **`Threshold monitor`** or **`Match monitor`**
   * **APL Query:**
     ```kql
     ['midgley-workers']
     | where summary.anomalies_detected > 0
     | summarize count()
     ```
   * **Trigger Condition:** `count() >= 1` within 15 minutes.
   * **Action:** Slack / Discord alert.

---

## 🛡️ Sentry Alert Rules & GitHub Integration

In Sentry, navigate to **Alerts -> Create Alert Rule**:

1. **Rule 1: New Critical Worker Exception:**
   * **Condition:** When a new issue is created or changes state from resolved.
   * **Filter:** `service:midgley-intraday-monitor` OR `service:midgley-cache-worker`.
   * **Action:** Immediate Slack / Email notification.

2. **Rule 2: GitHub API Dispatch Failure Spike:**
   * **Condition:** Event count > 3 in 15 minutes.
   * **Filter:** Issue title contains `GitHub Dispatch Failed` or `GH_PAT`.
   * **Action:** High-priority developer alert.

3. **Auto-Create GitHub Issues:**
   * Navigate to **Settings -> Integrations -> GitHub**.
   * Enable **Issue Link / Auto-create** for `KoshiirRa/midgley`.
