# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-09-18 21:32 UTC` | **Repository Architecture:** `v1.6 Ipatieff`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 104 | `$0.4078/gal` | `$0.2742/gal` | `-48.71%` | **`53.85%`** | `43.3%` | ⚠️ Calibration Active |
| **14-Day Window** | 180 | `$0.4025/gal` | `$0.3055/gal` | `-31.75%` | **`56.67%`** | `50.6%` | ⚠️ Calibration Active |
| **30-Day Window** | 408 | `$0.4126/gal` | `$0.3416/gal` | `-20.78%` | **`61.27%`** | `56.4%` | ⚠️ Calibration Active |
| **90-Day Window** | 1045 | `$0.4467/gal` | `$0.3822/gal` | `-16.89%` | **`57.03%`** | `52.7%` | ⚠️ Calibration Active |
| **All-Time Window** | 2890 | `$0.3626/gal` | `$0.3079/gal` | `-17.78%` | **`47.13%`** | `40.9%` | ⚠️ Calibration Active |

---

## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger

- **Total Hypotheses Evaluated:** `3`
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

---

## 🧠 Episodic Qualitative Failure Modes & Reflection Archive

Total indexed episodic memories in local store: **`60`** | Total synthesized reflections: **`12`**

### 📂 Categorized Anomaly Case Studies

#### 🏷️ Seasonal Transition (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Refinery Outage (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Pipeline / Waterway Constraint (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Geopolitical & OPEC Shock (9 case studies)
- **Newark_DE Price Discrepancy ($+0.9720/gal)** (`Newark_DE` | `2026-09-17`)
  - **Root Cause:** Model overestimated 5-day price by +$0.9720/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-08-04 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **Newark_DE Price Discrepancy ($+1.0470/gal)** (`Newark_DE` | `2026-09-17`)
  - **Root Cause:** Model overestimated 5-day price by +$1.0470/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-08-05 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **Newark_DE Price Discrepancy ($+0.9720/gal)** (`Newark_DE` | `2026-09-17`)
  - **Root Cause:** Model overestimated 5-day price by +$0.9720/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-08-04 (Newark_DE)'.
  - **Historical Analogy:** Similar to historical Newark_DE turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

#### 🏷️ Price Discrepancy & General Outliers (3 case studies)
- **Cincinnati_KY Price Discrepancy ($+0.9815/gal)** (`Cincinnati_KY` | `2026-09-17`)
  - **Root Cause:** Model overestimated 5-day price by +$0.9815/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-08-05 (Cincinnati_KY)'.
  - **Historical Analogy:** Similar to historical Cincinnati_KY turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **Cincinnati_KY Price Discrepancy ($+0.9815/gal)** (`Cincinnati_KY` | `2026-09-17`)
  - **Root Cause:** Model overestimated 5-day price by +$0.9815/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-08-05 (Cincinnati_KY)'.
  - **Historical Analogy:** Similar to historical Cincinnati_KY turnaround shocks where market pricing normalized post-event.
  - **Calibration Suggestion:** `Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages.`

- **Cincinnati_KY Price Discrepancy ($+0.9815/gal)** (`Cincinnati_KY` | `2026-09-17`)
  - **Root Cause:** Model overestimated 5-day price by +$0.9815/gal. Qualitative news shock or supply disruption premium decayed slower than physical market clearing capacity. Associated context: 'Historical shock record on 2026-08-05 (Cincinnati_KY)'.
  - **Historical Analogy:** Similar to historical Cincinnati_KY turnaround shocks where market pricing normalized post-event.
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