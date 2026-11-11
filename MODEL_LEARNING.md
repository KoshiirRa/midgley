# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-11-11 13:47 UTC` | **Repository Architecture:** `v1.6 Ipatieff`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 748 | `$0.2704/gal` | `$0.2741/gal` | **`+1.36%`** | **`45.59%`** | `17.6%` | 🟢 Optimal |
| **14-Day Window** | 1588 | `$0.2610/gal` | `$0.2652/gal` | **`+1.60%`** | **`41.88%`** | `16.1%` | 🟢 Optimal |
| **30-Day Window** | 3216 | `$0.2360/gal` | `$0.2364/gal` | **`+0.18%`** | **`41.54%`** | `16.8%` | 🟢 Optimal |
| **90-Day Window** | 6252 | `$0.2381/gal` | `$0.2316/gal` | `-2.81%` | **`45.84%`** | `29.9%` | ⚠️ Calibration Active |
| **All-Time Window** | 18135 | `$0.2863/gal` | `$0.2917/gal` | **`+1.87%`** | **`47.39%`** | `32.3%` | 🟢 Optimal |

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

Total indexed episodic memories in local store: **`0`** | Total synthesized reflections: **`0`**

### 📂 Categorized Anomaly Case Studies

#### 🏷️ Seasonal Transition (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Refinery Outage (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Pipeline / Waterway Constraint (0 case studies)
_No anomalies logged in this category._

#### 🏷️ Geopolitical & OPEC Shock (0 case studies)
_No anomalies logged in this category._

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