# System Architecture & Technical Specifications

Technical design document for the **LLM-Augmented Unleaded Gas Price Prediction Engine**.

---

## 1. Mathematical Formulations & Feature Fusion

### A. Crack Spread Proxy Formulations
Gasoline crack spreads represent refiner acquisition and processing margins:
- **National Crack Spread Proxy:**
  \[
  \text{CrackSpread}_{\text{National}} = P_{\text{RBOB Wholesale (\$ / gal)}} - \frac{P_{\text{WTI Crude (\$ / bbl)}}}{42.0}
  \]
- **Tulsa Regional Crack Spread:**
  \[
  \text{CrackSpread}_{\text{Tulsa}} = P_{\text{Tulsa Retail (\$ / gal)}} - \frac{P_{\text{Cushing WTI (\$ / bbl)}}}{42.0}
  \]

### B. Exponential Memory Decay Equation
Real-world event news persistence is modeled via exponential memory decay ($t_{1/2} = 4.0\text{ to }5.0\text{ days}$):
\[
\lambda = \frac{\ln(2)}{t_{1/2}}
\]
\[
\text{Memory}_t = \text{Memory}_{t-1} \times e^{-\lambda} + \text{Shock}_t
\]

---

## 2. Two-Tiered NOAA Weather Integration Architecture

```
               ┌─────────────────────────────────────────────────────────────┐
               │                     NOAA WEATHER SERVICE API                │
               │                        (api.weather.gov)                    │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                   ┌──────────────────────────┴──────────────────────────┐
                   ▼                                                     ▼
   ┌───────────────────────────────┐                     ┌───────────────────────────────┐
   │ TIER 1: NATIONAL BASINS       │                     │ TIER 2: LOCALIZED TULSA       │
   │ • Gulf Coast Hurricanes (NHC) │                     │ • Tulsa County (OKZ060)       │
   │ • Permian Basin Freeze Alerts │                     │   Tornado Warnings (NWS/SPC)  │
   │ • Bakken Shale Polar Vortexes │                     │ • Cushing/Payne (OKZ066)      │
   │                               │                     │   Tank Farm Freeze Warnings   │
   └───────────────┬───────────────┘                     └───────────────┬───────────────┘
                   │                                                     │
                   ▼                                                     ▼
   ┌───────────────────────────────┐                     ┌───────────────────────────────┐
   │ NATIONAL MODEL (main.py)      │                     │ TULSA MODEL (tulsa_main.py)   │
   │ • Directional Acc: 60.79%     │                     │ • Directional Acc: 58.15%     │
   └───────────────────────────────┘                     └───────────────────────────────┘
```

---

## 3. Live Pump Price Anchoring & Return Modeling

Instead of predicting raw non-stationary price levels directly, the model learns **5-day percentage price returns** ($\Delta \%$):
\[
\Delta \%_t = \frac{P_{t+5} - P_t}{P_t}
\]
The forecasted price calibrated to live pump prices ($P_{\text{Live}} = \$3.89/\text{gal}$) is calculated as:
\[
\hat{P}_{t+5} = P_{\text{Live}} \times (1 + \hat{\Delta}_{\%})
\]

---

## 4. MLOps Prediction Logging & Backfilling Engine (`src/prediction_logger.py`)

All 5-day out-of-time forecasts are persisted directly to `data/prediction_history.csv` during daily execution runs. As forecast target dates mature, `src/prediction_logger.py` queries ground-truth historical market prices from `yfinance` and populates actual price records.

---

## 5. Weekly Model Performance Review & Continuous Feedback Loop (`.github/workflows/weekly_model_review.yml`)

The weekly model performance review runs automatically on Saturday mornings (08:00 AM Central / 13:00 UTC). Its primary purpose is to calculate rolling error metrics and operate an automated feedback loop back into the forecasting pipeline to continuously enhance model performance over time:

* **Mean Absolute Error (MAE):**
  \[
  \text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |P_{\text{actual}, i} - \hat{P}_{\text{pred}, i}|
  \]
* **Root Mean Squared Error (RMSE):**
  \[
  \text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (P_{\text{actual}, i} - \hat{P}_{\text{pred}, i})^2}
  \]
* **Directional Accuracy (%):**
  \[
  \text{Hit Rate} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}\left(\text{sign}(\Delta P_{\text{actual}, i}) == \text{sign}(\Delta \hat{P}_{\text{pred}, i})\right) \times 100\%
  \]

### Continuous Feedback Loop Mechanics:
1. **Diagnostic Validation & Error Tracking:** Calculates rolling metrics across 30-day, 60-day, and 90-day evaluation windows to detect model drift or unmodeled shock divergence.
2. **Estimator Hyperparameter Re-Calibration:** Feeds validation loss signals back into quantitative estimation, optimizing regularized Ridge regression alpha penalties ($\alpha = 10.0$) and re-fitting pipeline scalers.
3. **Feature Decay & Weight Optimization:** Adjusts exponential memory half-lives ($t_{1/2} = 4.0\text{ to }5.0\text{ days}$) and fine-tunes LLM prompt impact scoring weights based on empirical directional success rates.

---

## 6. Multi-Page Web Architecture & Routing (`src/dashboard_generator.py`)

The public presentation layer is compiled by `src/dashboard_generator.py` into static HTML artifacts in `docs/`:

```
                               ┌───────────────────────────────┐
                               │     docs/index.html (/)       │
                               │  Midgley Overview Landing     │
                               │  Summary Forecast Cards Grid  │
                               └──────────────┬────────────────┘
                                              │
           ┌──────────────────────────────────┼──────────────────────────────────┐
           ▼                                  ▼                                  ▼
┌─────────────────────┐            ┌─────────────────────┐            ┌─────────────────────┐
│  docs/national.html │            │   docs/tulsa.html   │            │   docs/math.html    │
│    (/national)      │            │      (/tulsa)       │            │       (/math)       │
│ National Wholesale  │            │ Tulsa Retail Gas    │            │ KaTeX Math & Vector │
│ Futures Analytics   │            │ Metro Dropdown Menu │            │ Layer Architecture  │
└─────────────────────┘            └─────────────────────┘            └─────────────────────┘
```

Static web compatibility is preserved across both direct file routes (`/national.html`, `/tulsa.html`) and clean directory routes (`/national`, `/tulsa`) by outputting matching `index.html` files in subdirectory paths (`docs/national/index.html` and `docs/tulsa/index.html`).

---

## 7. Local Dev Environment & Permanent Web Server (`dev-vm` Port 8080)

To support rapid iteration and local testing, a dedicated Linux dev environment is configured on `dev-vm` (`10.42.42.54`):

* **Permanent `dev` Branch:** A permanent development branch (`origin/dev`) is maintained and checked out at `/home/marty/projects/midgley`.
* **Systemd User Service (`midgley-dev.service`):** Runs `python3 -m http.server 8080 --directory /home/marty/projects/midgley/docs --bind 0.0.0.0` as a background user service under systemd.
* **Service Persistence & Linger:** User linger is enabled (`loginctl enable-linger marty`), allowing the dev web server to start automatically at system boot and persist without an open SSH session. Automatic restart (`Restart=always`) ensures high availability against process crashes.

---

## 8. Automated Nightly Dev Release Pipeline (`.github/workflows/nightly_dev_release.yml`)

The project operates an automated release pipeline targeting the `dev` branch:

* **Trigger Schedule:** Scheduled at `0 8 * * *` (03:00 AM Central Time / 08:00 UTC) every night.
* **Pre-Release Tagging:** Publishes pre-release tags in format `dev-YYYY-MM-DD`.
* **Automated Release Notes:** Dynamically computes commit history and pull request contributions between consecutive nightly tags, attaching formatted Markdown release notes to the GitHub Release.



