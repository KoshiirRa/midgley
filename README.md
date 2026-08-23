# LLM-Augmented Unleaded Gas Price Prediction Model (`midgley`)

[![Daily Gas Price LLM Forecasting & Public Dashboard](https://github.com/KoshiirRa/midgley/actions/workflows/gas_price_forecast.yml/badge.svg)](https://github.com/KoshiirRa/midgley/actions/workflows/gas_price_forecast.yml)
[![Public Dashboard](https://img.shields.io/badge/Public_Dashboard-koshiirra.github.io%2Fmidgley-blue.svg)](https://koshiirra.github.io/midgley/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](requirements.txt)

An **LLM Multi-Agent Time-Series Forecasting Framework** that integrates qualitative real-world news feeds, **NOAA Weather Models**, **Global Maritime Chokepoints (Hormuz/Suez/Venezuela)**, **Executive Social Media (Trump Posts & Weekend Gap Analysis)**, and **Tulsa Regional Refining Dynamics** with quantitative commodity futures ($RB=F$, $CL=F$, $BZ=F$) to predict wholesale and retail unleaded gasoline prices.

<!-- START_LIVE_FORECAST -->
### 📢 Live 5-Day Price Forecasts (Updated: 2026-08-23 13:27 UTC)

| Region / Market | Current Price | 5-Day Forecast | Projected Direction | Target Date | Model Version |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **National Wholesale (RBOB)** | `$3.184`/gal | **`$3.144`/gal** | **DOWN 📉** | `2026-08-19` | `v1.2-NOAA-Ridge` |
| **Tulsa, OK Metro Retail** | `$3.890`/gal | **`$3.131`/gal** | **DOWN 📉** | `2026-08-19` | `v1.2-NOAA-Ridge` |

*🌐 View Interactive Web Dashboard & Public Visual Analytics at [koshiirra.github.io/midgley](https://koshiirra.github.io/midgley/)*
<!-- END_LIVE_FORECAST -->

---

## 📜 Etymology & Historical Namesake

This project is named **`midgley`** in ironic homage to **Thomas Midgley Jr.** (1889–1944), the American chemical engineer who invented **tetraethyllead (TEL)** as a gasoline anti-knock additive in 1921 (and later chlorofluorocarbons/CFCs). Environmental historian J. R. McNeill famously remarked that Midgley *"had more adverse impact on the atmosphere than any other single organism in Earth's history."*

In stark contrast to Midgley's legacy of unintended consequences on atmospheric chemistry and public health, this project harnesses modern **LLM intelligence and NOAA atmospheric weather models** to forecast unleaded gasoline markets and mitigate supply disruption risks.

---

## 🌐 Public Interactive Web Dashboard

A live public web dashboard (both Executive Consumer View & Technical MLOps Analytics) is automatically updated and deployed on every workflow run via GitHub Pages:

👉 **[https://koshiirra.github.io/midgley/](https://koshiirra.github.io/midgley/)**

---

## 🏗️ Architecture Overview

```
               ┌─────────────────────────────────────────────────────────────┐
               │    UNSTRUCTURED NEWS, NOAA WEATHER & SOCIAL MEDIA FEEDS     │
               │  • Global Geopolitical Bulletins & OPEC Press Releases       │
               │  • NOAA NWS API (api.weather.gov) - Oklahoma & Basin Alerts │
               │  • Maritime Chokepoints (Hormuz 21M bpd, Suez, Venezuela)   │
               │  • Executive Social Feed (Trump Twitter / Truth Social)     │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │               EVENT & WEATHER EXTRACTION AGENT              │
               │        (Google Gemini 2.5 Flash / Domain NLP Lexicon)       │
               │ • Geopolitical Risk  • Supply Disruption  • OPEC Action     │
               │ • NOAA Tornado Risk  • NOAA Polar Vortex  • Hurricane Track │
               │ • Weekend Gap Multiplier (1.42x Monday Open Volatility)     │
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
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │         PUBLIC GITHUB PAGES WEB DASHBOARD DEPLOYER          │
               │   (src/dashboard_generator.py -> koshiirra.github.io/midgley)│
               └─────────────────────────────────────────────────────────────┘
```

---

## 📱 Executive Social Media & Weekend Market Gap Engine (`src/executive_social_feed.py`)

Our empirical econometric analysis of executive social media posts (Twitter/X and Truth Social energy commentary from 2018–2026) reveals statistically significant price return and volatility correlations ($p < 0.01$):

1. **Dovish OPEC Pressure Posts:** Statements urging OPEC to increase production or ease price hikes cause immediate average **$-1.85\%$ single-day wholesale RBOB drops**.
2. **Hawkish Tariff Shocks:** Announcements threatening energy import tariffs (e.g., 25% foreign crude tariffs) produce immediate average **$+2.10\%$ price return surges**.
3. **Weekend Market Gap Multiplier ($1.42\times$):** Because commodity futures markets are closed from Friday 17:00 EST to Sunday 18:00 EST, Saturday/Sunday executive social media posts cannot be immediately priced in by spot trading algorithms. On Sunday evening 18:00 EST market reopen, weekend posts generate **$42\%$ higher Monday morning open price gap volatility** than baseline weekends.

---

## ⚡ Key Features

1. **Auto-Updating Live README Forecast Table (`src/readme_updater.py`):** Automatically injects the latest 5-day national & Tulsa forecasts into `README.md`.
2. **Public Web Dashboard Generator (`src/dashboard_generator.py`):** Builds a responsive HTML/Tailwind/Chart.js web app (`docs/index.html`) deployed automatically to GitHub Pages ([koshiirra.github.io/midgley](https://koshiirra.github.io/midgley/)).
3. **Regional Tulsa, OK Retail Model (`tulsa_main.py`):** Dedicated regional forecasting module calibrated directly to live local pump prices (**$\$3.89/\text{gal}$**), factoring in Cushing WTI crude proximity ($50\text{ miles}$ from Tulsa) and HF Sinclair West Tulsa Refinery ($125,000\text{ bpd}$) shocks.
4. **Two-Tiered NOAA Weather Integration (`src/noaa_weather.py`):**
   - **Tier 1 (National Basins):** NOAA NHC Hurricane advisories in Gulf Coast refining hubs & Permian/Bakken winter freeze warnings.
   - **Tier 2 (Localized Tulsa & Cushing):** NOAA NWS Tornado Warnings for **Tulsa County (`OKZ060`)** and sub-zero freeze warnings for **Cushing/Payne County (`OKZ066`)**.
5. **Global Maritime Chokepoint Feeds (`src/geopolitical_feeds.py`):** Tracks Iran conflict alerts in the **Strait of Hormuz** ($21.0\text{M bpd}$ / $20\%$ of global oil), Red Sea / Suez Canal tanker rerouting events, and Venezuela Orinoco heavy crude sanctions.
6. **Executive Social Media & Weekend Gap Engine (`src/executive_social_feed.py`):** Quantifies Trump Twitter/Truth Social energy posts and models Monday morning futures open price gaps ($1.42\times$ volatility multiplier).
7. **Ultra-Fast Single-Batch Gemini 2.5 Flash LLM Scoring (`src/event_analyzer.py`):** Scores all energy headlines in a single 2-second API call.
8. **MLOps Prediction Logging Engine (`src/prediction_logger.py`):** Automatically logs all 5-day out-of-time forecasts to `data/prediction_history.csv` and backfills actual prices as time progresses.
9. **Automated GitHub Actions CI/CD & Deploy (`.github/workflows/gas_price_forecast.yml`):** Automatically executes daily forecasts at 02:00 AM Central, commits prediction logs, and deploys the public dashboard to GitHub Pages.

---

## 📊 Model Performance Summary

| Region / Target | Model Algorithm | MAE ($/gal) | RMSE ($/gal) | MAPE (%) | Directional Hit Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **National Wholesale (RBOB)** | Ridge ($\alpha=10.0$) + Gemini 2.5 Flash | **$0.1151** | **$0.1568** | **4.76%** | **60.79%** (+4.40% boost) |
| **Tulsa, OK Metro Retail** | Ridge ($\alpha=10.0$) + Localized NOAA | **$0.1331** | **$0.1880** | **4.83%** | **58.15%** |
