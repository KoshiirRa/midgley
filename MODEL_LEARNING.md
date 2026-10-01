# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-10-01 17:33 UTC` | **Repository Architecture:** `v1.6 Ipatieff`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 83 | `$0.1579/gal` | `$0.1146/gal` | `-37.78%` | **`45.78%`** | `49.4%` | ⚠️ Calibration Active |
| **14-Day Window** | 158 | `$0.1793/gal` | `$0.0955/gal` | `-87.69%` | **`34.81%`** | `64.6%` | ⚠️ Calibration Active |
| **30-Day Window** | 313 | `$0.1595/gal` | `$0.1187/gal` | `-34.39%` | **`41.53%`** | `65.8%` | ⚠️ Calibration Active |
| **90-Day Window** | 918 | `$0.1604/gal` | `$0.1336/gal` | `-20.01%` | **`49.46%`** | `68.4%` | ⚠️ Calibration Active |
| **All-Time Window** | 3518 | `$0.1250/gal` | `$0.1154/gal` | `-8.32%` | **`51.79%`** | `50.5%` | ⚠️ Calibration Active |

---

## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger

- **Total Hypotheses Evaluated:** `9`
- **Accepted Hypotheses in Production:** `3`
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

---

## 🧠 Episodic Qualitative Failure Modes & Reflection Archive

Total indexed episodic memories in local store: **`1968`** | Total synthesized reflections: **`7`**

### 📂 Categorized Anomaly Case Studies

#### 🏷️ Seasonal Transition (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Refinery Outage (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Pipeline / Waterway Constraint (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Geopolitical & OPEC Shock (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Price Discrepancy & General Outliers (7 case studies)
- **Oakland_CA Price Discrepancy ($+2.7083/gal)** (`Oakland_CA` | `2026-09-28`)
  - **Root Cause:** Model overestimated 5-day price by +$2.7083/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-05-01 (Oakland_CA)'.
  - **Historical Analogy:** Similar to historical Oakland_CA turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **BayArea_CA Price Discrepancy ($+2.7791/gal)** (`BayArea_CA` | `2026-09-28`)
  - **Root Cause:** Model overestimated 5-day price by +$2.7791/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-03-06 (BayArea_CA)'.
  - **Historical Analogy:** Similar to historical BayArea_CA turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **Oakland_CA Price Discrepancy ($+2.7791/gal)** (`Oakland_CA` | `2026-09-28`)
  - **Root Cause:** Model overestimated 5-day price by +$2.7791/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-03-06 (Oakland_CA)'.
  - **Historical Analogy:** Similar to historical Oakland_CA turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

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