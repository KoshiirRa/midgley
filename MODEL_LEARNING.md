# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-10-05 18:33 UTC` | **Repository Architecture:** `v1.6 Ipatieff`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 74 | `$0.1399/gal` | `$0.1124/gal` | `-24.54%` | **`43.24%`** | `32.4%` | ⚠️ Calibration Active |
| **14-Day Window** | 99 | `$0.1426/gal` | `$0.1020/gal` | `-39.74%` | **`44.44%`** | `42.4%` | ⚠️ Calibration Active |
| **30-Day Window** | 139 | `$0.1454/gal` | `$0.1065/gal` | `-36.55%` | **`38.13%`** | `54.7%` | ⚠️ Calibration Active |
| **90-Day Window** | 355 | `$0.1673/gal` | `$0.1236/gal` | `-35.37%` | **`38.87%`** | `68.5%` | ⚠️ Calibration Active |
| **All-Time Window** | 1226 | `$0.1204/gal` | `$0.1024/gal` | `-17.49%` | **`47.96%`** | `54.0%` | ⚠️ Calibration Active |

---

## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger

- **Total Hypotheses Evaluated:** `11`
- **Accepted Hypotheses in Production:** `5`
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
| `2026-09-13` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-19` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-19` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-21` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-26` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-09-28` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-09-30` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-10-01` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-10-03` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |

---

## 🧠 Episodic Qualitative Failure Modes & Reflection Archive

Total indexed episodic memories in local store: **`7223`** | Total synthesized reflections: **`66`**

### 📂 Categorized Anomaly Case Studies

#### 🏷️ Seasonal Transition (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Refinery Outage (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Pipeline / Waterway Constraint (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Geopolitical & OPEC Shock (8 case studies)
- **Newark_DE Price Discrepancy ($+0.6802/gal)** (`Newark_DE` | `2026-10-03`)
  - **Root Cause:** Model underestimated price surge by -$0.6802/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-09-25 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **Newark_DE Price Discrepancy ($+0.7166/gal)** (`Newark_DE` | `2026-10-03`)
  - **Root Cause:** Model underestimated price surge by -$0.7166/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-09-23 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **Newark_DE Price Discrepancy ($+0.6802/gal)** (`Newark_DE` | `2026-10-02`)
  - **Root Cause:** Model underestimated price surge by -$0.6802/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-09-25 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

#### 🏷️ Price Discrepancy & General Outliers (4 case studies)
- **National Price Discrepancy ($+0.6620/gal)** (`National` | `2026-10-03`)
  - **Root Cause:** Model underestimated price surge by -$0.6620/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-03-06 (National)'.
  - **Historical Analogy:** Similar to historical National turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **National Price Discrepancy ($+0.6620/gal)** (`National` | `2026-10-02`)
  - **Root Cause:** Model underestimated price surge by -$0.6620/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-03-06 (National)'.
  - **Historical Analogy:** Similar to historical National turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **National Price Discrepancy ($+0.6620/gal)** (`National` | `2026-10-02`)
  - **Root Cause:** Model underestimated price surge by -$0.6620/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-03-06 (National)'.
  - **Historical Analogy:** Similar to historical National turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

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