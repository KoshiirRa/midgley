# LLM-Augmented Unleaded Gas Price Prediction Model (`midgley`)

[![Daily Gas Price LLM Forecasting](https://github.com/KoshiirRa/midgley/actions/workflows/gas_price_forecast.yml/badge.svg)](https://github.com/KoshiirRa/midgley/actions/workflows/gas_price_forecast.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](requirements.txt)

An **LLM Multi-Agent Time-Series Forecasting Framework** that integrates qualitative real-world news feeds, **NOAA Weather Models**, and **Tulsa Regional Refining Dynamics** with quantitative commodity futures ($RB=F$, $CL=F$, $BZ=F$) to predict wholesale and retail unleaded gasoline prices.

---

## 📜 Etymology & Historical Namesake

This project is named **`midgley`** in ironic homage to **Thomas Midgley Jr.** (1889–1944), the American chemical engineer who invented **tetraethyllead (TEL)** as a gasoline anti-knock additive in 1921 (and later chlorofluorocarbons/CFCs). Environmental historian J. R. McNeill famously remarked that Midgley *"had more adverse impact on the atmosphere than any other single organism in Earth's history."*

In stark contrast to Midgley's legacy of unintended consequences on atmospheric chemistry and public health, this project harnesses modern **LLM intelligence and NOAA atmospheric weather models** to forecast unleaded gasoline markets and mitigate supply disruption risks.

---

## 🏗️ Architecture Overview

```
               ┌─────────────────────────────────────────────────────────────┐
               │              UNSTRUCTURED NEWS & NOAA WEATHER FEEDS         │
               │  • Global Geopolitical Bulletins & OPEC Press Releases       │
               │  • NOAA NWS API (api.weather.gov) - Oklahoma & Basin Alerts │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │               EVENT & WEATHER EXTRACTION AGENT              │
               │        (Google Gemini 2.5 Flash / Domain NLP Lexicon)       │
               │ • Geopolitical Risk  • Supply Disruption  • OPEC Action     │
               │ • NOAA Tornado Risk  • NOAA Polar Vortex  • Hurricane Track │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Bounded Factor Vectors
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │              EXPONENTIAL MEMORY FUSION AGENT                │
               │       (Decays Shocks with Half-Life t1/2 = 4 to 5 Days)     │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Unified Feature Matrix
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │              QUANTITATIVE FORECASTING AGENT                 │
               │          (Standardized Ridge / XGBoost Estimator)           │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Base Forecasts
                                              ▼
                        ┌─────────────────────┴─────────────────────┐
                        ▼                                           ▼
        ┌───────────────────────────────┐           ┌───────────────────────────────┐
        │  NATIONAL MODEL (main.py)     │           │ TULSA REGIONAL (tulsa_main.py)│
        │ • Wholesale RBOB Futures      │           │ • Live Pump Base: $3.89/gal   │
        │ • Directional Acc: 60.79%     │           │ • Cushing WTI Proximity       │
        │ • Gulf Hurricane: +$0.141/gal │           │ • West Tulsa Refinery Tornado │
        └───────────────┬───────────────┘           └───────────────┬───────────────┘
                        │                                           │
                        └─────────────────────┬─────────────────────┘
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             MLOps PREDICTION TRACKER & LOGGING              │
               │        (src/prediction_logger.py -> prediction_history.csv)│
               │  Backfills Actual Market Prices & Tracks Iteration Metrics  │
               └─────────────────────────────────────────────────────────────┘
```

---

## ⚡ Key Features

1. **Regional Tulsa, OK Retail Model (`tulsa_main.py`):** Dedicated regional forecasting module calibrated directly to live local pump prices (**$\$3.89/\text{gal}$**), factoring in Cushing WTI crude proximity ($50\text{ miles}$ from Tulsa) and HF Sinclair West Tulsa Refinery ($125,000\text{ bpd}$) shocks.
2. **Two-Tiered NOAA Weather Integration (`src/noaa_weather.py`):**
   - **Tier 1 (National Basins):** NOAA NHC Hurricane advisories in Gulf Coast refining hubs & Permian/Bakken winter freeze warnings.
   - **Tier 2 (Localized Tulsa & Cushing):** NOAA NWS Tornado Warnings for **Tulsa County (`OKZ060`)** and sub-zero freeze warnings for **Cushing/Payne County (`OKZ066`)**.
3. **Google Gemini 2.5 Flash LLM Scoring (`src/event_analyzer.py`):** Real-time qualitative sentiment scoring using `google-genai` SDK with deterministic NLP fallback.
4. **MLOps Prediction Logging Engine (`src/prediction_logger.py`):** Automatically logs all 5-day out-of-time forecasts to `data/prediction_history.csv` and backfills actual prices as time progresses to evaluate model iteration drift.
5. **Live Fuel Price Feeds (`src/live_fuel_feed.py`):** Supports station-level queries via GasBuddy GraphQL and Google Places API (`fuelOptions`).
6. **Automated GitHub Actions CI/CD Workflow (`.github/workflows/gas_price_forecast.yml`):** Automatically executes daily forecasts at 02:00 AM Central and commits updated prediction logs back to GitHub.

---

## 📊 Model Performance Summary

| Region | Model Version | Evaluated Days | MAE ($/gal) | RMSE ($/gal) | Directional Accuracy (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **National Wholesale** | `v1.2-NOAA-National-Ridge` | 133 | **$0.1151** | **$0.1568** | **60.79%** (+4.40% over baseline) |
| **Tulsa, OK Retail** | `v1.2-NOAA-Tulsa-Ridge` | 133 | **$0.1331** | **$0.1880** | **58.15%** |

---

## 🚀 Quickstart & Execution

### 1. Environment Setup
```powershell
# Create & activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional for Live Gemini & Google Maps)
```powershell
# Gemini 2.5 Flash API Key (Free Tier at aistudio.google.com)
$env:GEMINI_API_KEY="AIzaSyYourGeminiKey"

# Google Maps / Places API Key
$env:GOOGLE_MAPS_API_KEY="AIzaSyYourGoogleMapsKey"
```

### 3. Execution Commands

* **Run Master Combined Script (National + Tulsa + Prediction Tracker):**
  ```powershell
  .venv\Scripts\python.exe run_all.py --use-llm-api
  ```
* **Run Tulsa Regional Model Only (Live Base $3.89/gal):**
  ```powershell
  .venv\Scripts\python.exe tulsa_main.py --use-llm-api
  ```
* **Run National Wholesale Model Only:**
  ```powershell
  .venv\Scripts\python.exe main.py --use-llm-api
  ```

---

## 📓 Interactive Notebooks

* **Tulsa Regional Notebook:** [`notebooks/tulsa_gas_price_llm_forecasting.ipynb`](notebooks/tulsa_gas_price_llm_forecasting.ipynb)
* **National Wholesale Notebook:** [`notebooks/gas_price_llm_forecasting.ipynb`](notebooks/gas_price_llm_forecasting.ipynb)

---

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
