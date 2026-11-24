# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal

> **Last Evaluated & Synced:** `2026-11-24 04:43 UTC` | **Repository Architecture:** `v1.6 Ipatieff`

This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.

---

## 📈 Longitudinal Performance Evolution (Multi-Window)

| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **7-Day Window** | 1000 | `$0.2763/gal` | `$0.2802/gal` | **`+1.39%`** | **`60.70%`** | `28.1%` | 🟢 Optimal |
| **14-Day Window** | 1777 | `$0.2722/gal` | `$0.2758/gal` | **`+1.30%`** | **`57.29%`** | `25.0%` | 🟢 Optimal |
| **30-Day Window** | 3310 | `$0.2650/gal` | `$0.2686/gal` | **`+1.33%`** | **`49.03%`** | `19.9%` | 🟢 Optimal |
| **90-Day Window** | 7076 | `$0.2412/gal` | `$0.2359/gal` | `-2.24%` | **`47.87%`** | `27.6%` | ⚠️ Calibration Active |
| **All-Time Window** | 19479 | `$0.2853/gal` | `$0.2907/gal` | **`+1.84%`** | **`48.25%`** | `31.9%` | 🟢 Optimal |

---

## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger

- **Total Hypotheses Evaluated:** `18`
- **Accepted Hypotheses in Production:** `12`
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
| `2026-11-14` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |
| `2026-11-21` | **`Weekly_Exogenous_Decay_Validation`** | $t_{1/2}=4.8\text{d}, W_{wknd}=1.45\times$ | `$0.1390` | `$0.1379` | `-0.0011` | $t=2.84$ ($p=0.0217$) | 🟢 **ACCEPTED** |

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