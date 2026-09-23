# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-09-23 20:46 UTC` | **Repository Architecture:** `v1.6 Ipatieff`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 136 | `$0.9233/gal` | `$0.7098/gal` | `-30.08%` | **`22.06%`** | `21.3%` | ⚠️ Calibration Active |
| **14-Day Window** | 424 | `$0.6008/gal` | `$0.4572/gal` | `-31.42%` | **`40.09%`** | `34.2%` | ⚠️ Calibration Active |
| **30-Day Window** | 942 | `$0.4881/gal` | `$0.3906/gal` | `-24.97%` | **`49.89%`** | `44.6%` | ⚠️ Calibration Active |
| **90-Day Window** | 2635 | `$0.4019/gal` | `$0.3485/gal` | `-15.33%` | **`50.25%`** | `46.4%` | ⚠️ Calibration Active |
| **All-Time Window** | 9305 | `$0.5308/gal` | `$0.5087/gal` | `-4.34%` | **`57.53%`** | `38.1%` | ⚠️ Calibration Active |

---

## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger

- **Total Hypotheses Evaluated:** `6`
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
| `2026-09-13` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-19` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-19` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |
| `2026-09-21` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.0331` | `$0.0332` | `+0.0001` | $t=-1.19$ ($p=0.2371$) | ⚪ `REJECTED` |

---

## 🧠 Episodic Qualitative Failure Modes & Reflection Archive

Total indexed episodic memories in local store: **`1830`** | Total synthesized reflections: **`113`**

### 📂 Categorized Anomaly Case Studies

#### 🏷️ Seasonal Transition (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Refinery Outage (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Pipeline / Waterway Constraint (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Geopolitical & OPEC Shock (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Price Discrepancy & General Outliers (12 case studies)
- **Tulsa_OK Price Discrepancy ($+3.4722/gal)** (`Tulsa_OK` | `2026-09-23`)
  - **Root Cause:** Model overestimated 5-day price by +$3.4722/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-09-23 (Tulsa_OK)'.
  - **Historical Analogy:** Similar to historical Tulsa_OK turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **Tulsa_OK Price Discrepancy ($+3.5213/gal)** (`Tulsa_OK` | `2026-09-23`)
  - **Root Cause:** Model overestimated 5-day price by +$3.5213/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-09-28 (Tulsa_OK)'.
  - **Historical Analogy:** Similar to historical Tulsa_OK turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **Tulsa_OK Price Discrepancy ($+3.8952/gal)** (`Tulsa_OK` | `2026-09-23`)
  - **Root Cause:** Model overestimated 5-day price by +$3.8952/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-09-24 (Tulsa_OK)'.
  - **Historical Analogy:** Similar to historical Tulsa_OK turnaround shocks where market pricing normalized post-event.
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