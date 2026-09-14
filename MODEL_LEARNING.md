# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-09-14 01:42 UTC` | **Repository Architecture:** `v1.4 Finlight-LLM`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 50 | `$0.2550/gal` | `$0.2645/gal` | **`+3.61%`** | **`50.00%`** | `50.0%` | 🟢 Optimal |
| **14-Day Window** | 100 | `$0.2589/gal` | `$0.2578/gal` | `-0.44%` | **`54.00%`** | `53.0%` | ⚠️ Calibration Active |
| **30-Day Window** | 220 | `$0.2419/gal` | `$0.2350/gal` | `-2.93%` | **`50.00%`** | `45.9%` | ⚠️ Calibration Active |
| **90-Day Window** | 600 | `$0.2471/gal` | `$0.2456/gal` | `-0.62%` | **`51.83%`** | `48.5%` | ⚠️ Calibration Active |
| **All-Time Window** | 2311 | `$0.2384/gal` | `$0.2293/gal` | `-3.96%` | **`50.32%`** | `44.9%` | ⚠️ Calibration Active |

---

## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger

- **Total Hypotheses Evaluated:** `2`
- **Accepted Hypotheses in Production:** `0`
- **Active Calibrated Baseline Parameters:**
  - Exogenous Shock Half-Life ($t_{1/2}$): **`4.5 days`**
  - Geopolitical Shock Weight: **`0.35`**
  - Supply Disruption Weight: **`0.4`**
  - OPEC Action Weight: **`0.25`**
  - Weekend Gap Multiplier: **`1.42x`**

### 📜 Evaluated Hypothesis History

| Timestamp | Hypothesis Name | Candidate Parameters | Baseline MAE | Candidate MAE | Delta ($\Delta$) | $t$-Statistic ($p$-value) | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `2026-09-10` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-12` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |

---

## 🧠 Episodic Qualitative Failure Modes & Reflection Archive

Total indexed episodic memories in local store: **`22`** | Total synthesized reflections: **`3`**

### 📂 Categorized Anomaly Case Studies

#### 🏷️ Seasonal Transition (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Refinery Outage (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Pipeline / Waterway Constraint (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Geopolitical & OPEC Shock (3 case studies)
- **Newark_DE Price Discrepancy ($+1.1197/gal)** (`Newark_DE` | `2026-09-11`)
  - **Root Cause:** Model underestimated price surge by -$1.1197/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-03-17 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **Newark_DE Price Discrepancy ($+1.1232/gal)** (`Newark_DE` | `2026-09-11`)
  - **Root Cause:** Model underestimated price surge by -$1.1232/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-03-13 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **Newark_DE Price Discrepancy ($+1.1404/gal)** (`Newark_DE` | `2026-09-11`)
  - **Root Cause:** Model underestimated price surge by -$1.1404/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-03-06 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

#### 🏷️ Price Discrepancy & General Outliers (0 case studies)
_No anomalies logged in this category._

---

## 🛠️ Continuous Learning Mechanism Overview

```
 ┌─────────────────────────────────────────────────────────────┐
 │             1. DAILY PREDICTION & OUTCOME LOGGING           │
 │  Logs 5-day out-of-time forecasts -> backfills actual price │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │         2. EPISODIC MEMORY PASS (Retain-Recall-Reflect)     │
 │  Isolates forecast outliers -> generates root-cause post-   │
 │  mortems & stores in SQLite FTS5 / Vectorize Hindsight API  │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │             3. SAPIENT PRAXIST HYPOTHESIS HARNESS           │
 │  Autonomous grid sweep & t-tests on shock decay parameters   │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │          4. MLOps TELEMETRY & OBSERVABILITY DASHBOARD       │
 │  Updates MODEL_LEARNING.md, telemetry.html, and W&B charts  │
 └─────────────────────────────────────────────────────────────┘
```

_Automated Model Learning Journal maintained by `src/learning_tracker.py`._