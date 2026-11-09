# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-11-09 02:07 UTC` | **Repository Architecture:** `v1.6 Ipatieff`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 708 | `$0.2705/gal` | `$0.2760/gal` | **`+2.00%`** | **`40.11%`** | `13.4%` | 🟢 Optimal |
| **14-Day Window** | 1653 | `$0.2563/gal` | `$0.2594/gal` | **`+1.22%`** | **`39.93%`** | `14.2%` | 🟢 Optimal |
| **30-Day Window** | 2903 | `$0.2314/gal` | `$0.2315/gal` | **`+0.04%`** | **`40.54%`** | `16.2%` | 🟢 Optimal |
| **90-Day Window** | 6069 | `$0.2370/gal` | `$0.2300/gal` | `-3.06%` | **`45.30%`** | `30.9%` | ⚠️ Calibration Active |
| **All-Time Window** | 17822 | `$0.2864/gal` | `$0.2919/gal` | **`+1.88%`** | **`47.33%`** | `32.5%` | 🟢 Optimal |

---

## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger

- **Total Hypotheses Evaluated:** `16`
- **Accepted Hypotheses in Production:** `10`
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
| `2026-10-10` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-10-17` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-10-24` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-10-31` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-11-07` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |

---

## 🧠 Episodic Qualitative Failure Modes & Reflection Archive

Total indexed episodic memories in local store: **`2056`** | Total synthesized reflections: **`18`**

### 📂 Categorized Anomaly Case Studies

#### 🏷️ Seasonal Transition (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Refinery Outage (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Pipeline / Waterway Constraint (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Geopolitical & OPEC Shock (4 case studies)
- **Newark_DE Price Discrepancy ($+0.6802/gal)** (`Newark_DE` | `2026-10-03`)
  - **Root Cause:** Model underestimated price surge by -$0.6802/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-09-25 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **Newark_DE Price Discrepancy ($+0.7166/gal)** (`Newark_DE` | `2026-10-03`)
  - **Root Cause:** Model underestimated price surge by -$0.7166/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-09-23 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

- **Newark_DE Price Discrepancy ($+0.6802/gal)** (`Newark_DE` | `2026-10-01`)
  - **Root Cause:** Model underestimated price surge by -$0.6802/gal. Physical supply constraints or rack margin spikes expanded faster than captured by baseline futures curves. Associated context: 'Historical shock record on 2026-09-25 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts.`

#### 🏷️ Price Discrepancy & General Outliers (8 case studies)
- **Anomaly Post-Mortem** (`None` | `2026-11-07`)
  - **Root Cause:** 
  - **Historical Analogy:** 
  - **Calibration Suggestion:** ``

- **Anomaly Post-Mortem** (`None` | `2026-10-31`)
  - **Root Cause:** 
  - **Historical Analogy:** 
  - **Calibration Suggestion:** ``

- **Anomaly Post-Mortem** (`None` | `2026-10-24`)
  - **Root Cause:** 
  - **Historical Analogy:** 
  - **Calibration Suggestion:** ``

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