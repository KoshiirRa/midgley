# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-10 16:15:15`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** Russia Vows to Keep Selling Oil to India Despite U.S. Tariff Threat - Crude Oil Prices Today | OilPrice.com  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Russia Vows to Keep Selling Oil to India Despite U.S. Tariff Threat - Crude Oil Prices Today | OilPrice.com
- **Active Ingested News Links:**
- [Russia Vows to Keep Selling Oil to India Despite U.S. Tariff Threat - Crude Oil Prices Today | OilPrice.com](https://news.google.com/rss/articles/CBMivgFBVV95cUxNOUp3NTFDYTZxUS03aGVDY0ZfZzV4b3RCYnNTUE01cTI3cm1sUU5JVmYtQ1B1eml0aC0ySkFiQ1pZeE03RkNkVkZNSk8yQzBkQzlqWWlRZmlCWXlwb3hNaWw1VENhY1BmYXp6M2ZiRERHdnd5cTBkbjBPOWxIRHYzLVA0ZjZPN2Y5ZnVRalE1bHVNdkVHeUxJMWtHM2FseEFFNGpyMTBCSDFkZGlDdS1vUGVncFlPQkgyMVB2al9R0gHDAUFVX3lxTFB1QWstLVN0SEFMdER4My1nVTd2WTlEQ3NaQlQ1UkNqeFBPc2g0Mm1PTTIzZkZsVTNSTFRkYVA0REpzZy1UV29VR01ISUstZXZUd0lQbnZXZi1nR3ozM2hjSllHaHZiZm1aaUloVDVTRDBtRWlyeGZZWl95VG8wZ1lFSzRMaFVGa01EMFJkcjh1cVNTMmVPbTZBTFRHcm1qSHh3SE55Qnp0TWZnUEc4LURrUEFsa1hPSWJmejNXMmxuY1BkZw?oc=5) (Google News Energy Feed)
- [Tariffs, Oil Prices, and AI: A Triple Assault That Rate Hikes May Struggle to Tame as Structural Inflation Persists - finance.biggo.com](https://news.google.com/rss/articles/CBMidkFVX3lxTFBndWoxX1JuSk41ZmtQb3dFeG5iX0ZrM09yWlF3akdZLWxGWFpZWU1FcE9FMW1OT2hKcHM0ekRsNHBIUjV1ckVXYmpUaUE1NndMcE5jTUFxMkZtMTJFRjU0UWx0alM0MnBvS1JIaGZSbXlOU2xKR3c?oc=5) (Google News Energy Feed)
- [US-Canada tariffs are now in effect: Why autos and oil might be the bigger inflation risks - Chase Bank](https://news.google.com/rss/articles/CBMiygFBVV95cUxOVlZNdVJGTE9Vd3hHc3F5RnlSSVRneDRicnE4TnBONFo0SlhzNmVVQnZuMHZXREZOdzNLTXFBZ2VtT2NZOWtjTERhLXVoeGdqaWpST0w5MTE1cXl3ZlA4YmNhT2lFYjdmZXJIMGRVR3BRQkEza2xWZ0RpR3pKdXlOaFB0S1NlR29PLUdtak53UkZUdUc2NHpwVHh0c1NMVDJISkY3bVVUMEN0Z1pYOEptd0pBMVdWZXhWUGF3LUFxekVESmRObnhTNC1n?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.80`
- **Price Pressure Shock ($\Delta P$):** `+0.52`
- **Geopolitical Risk Score ($G$):** `0.80`
- **Demand Sentiment Score ($D$):** `0.00`
- **OPEC Action Score ($O$):** `0.00`
- **Decay Half-Life ($t_{1/2}$):** `5.0 days`

---

## 3. Step-by-Step Exponential Memory Decay Math for This Run

Exponential Memory Decay Model Equation:
$$M_t = M_{t-1} \cdot e^{-\frac{\ln(2)}{t_{1/2}}} + S_t$$
![Exponential Decay Formula](https://latex.codecogs.com/svg.latex?M_t%20%3D%20M_%7Bt-1%7D%20%5Ccdot%20e%5E%7B-%5Cfrac%7B%5Cln%282%29%7D%7Bt_%7B1/2%7D%7D%7D%20%2B%20S_t)

Decay Parameter Substitutions:
- Decay constant: $\lambda = \frac{\ln(2)}{5.0} = 0.13863 \text{ day}^{-1}$
- Daily retention multiplier: $\gamma = e^{-0.13863} \approx 0.87055$


Numeric Retention Schedule for This Run ($M_0 = 0.8000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.8000$
- **Day 1 Decayed Shock**: $M_1 = 0.8000 \times 0.87055 = 0.6964$
- **Day 2 Decayed Shock**: $M_2 = 0.8000 \times (0.87055)^2 = 0.6063$
- **Day 3 Decayed Shock**: $M_3 = 0.8000 \times (0.87055)^3 = 0.5278$
- **Day 4 Decayed Shock**: $M_4 = 0.8000 \times (0.87055)^4 = 0.4595$
- **Day 5 (Target Horizon)**: $M_5 = 0.8000 \times 0.50000 = 0.4000$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (+\$0.111) = \$3.250\text{/gal}$ (Delta: +\$0.111/gal, +3.48\%)
- **Tulsa, OK Retail**: $P = \$3.599 + (-\$0.278) = \$3.503\text{/gal}$ (Delta: -\$0.278/gal, -7.73\%)
- **Newark, DE Retail**: $P = \$3.220 + (-\$0.269) = \$3.142\text{/gal}$ (Delta: -\$0.269/gal, -8.35\%)
- **Cincinnati, OH/KY**: $P = \$3.883 + (-\$0.284) = \$3.799\text{/gal}$ (Delta: -\$0.284/gal, -7.31\%)
- **Greenville, NC Retail**: $P = \$3.250 + (+\$0.074) = \$3.204\text{/gal}$ (Delta: +\$0.074/gal, +2.27\%)
- **Charlotte, NC Retail**: $P = \$3.280 + (+\$0.074) = \$3.236\text{/gal}$ (Delta: +\$0.074/gal, +2.24\%)
- **Port St. Lucie, FL Retail**: $P = \$3.913 + (-\$0.285) = \$3.819\text{/gal}$ (Delta: -\$0.285/gal, -7.29\%)
- **Oakland, CA Retail**: $P = \$4.950 + (-\$0.260) = \$4.882\text{/gal}$ (Delta: -\$0.260/gal, -5.25\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$5.050 + (-\$0.261) = \$4.981\text{/gal}$ (Delta: -\$0.261/gal, -5.18\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-10 16:15:15]: Elevated upward price shock (+$0.52/gal) observed across wholesale futures. Event trigger 'Russia Vows to Keep Selling Oil to India Despite U.S. Tariff Threat - Crude Oil Prices Today | OilPrice.com' drove supply disruption to S=0.80 and geopolitical risk to G=0.80. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.6964 and Day-5 horizon retention M₅=0.4000.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-10 16:15:15 (Mode: INTRADAY_REVISION), primary event trigger 'Russia Vows to Keep Selling Oil to India Despite U.S. Tariff Threat - Crude Oil Prices Today | OilPrice.com' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.80, Price Pressure ΔP=+0.52, Geopolitical Risk G=0.80. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.8000
  - Day 1: M₁ = 0.6964
  - Day 5: M₅ = 0.4000 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.250/gal (+$0.111/gal, +3.48%)
  • Tulsa, OK Retail: $3.503/gal ($-0.278/gal, -7.73%)
  • Newark, DE Retail: $3.142/gal ($-0.269/gal, -8.35%)
  • Cincinnati, OH/KY: $3.799/gal ($-0.284/gal, -7.31%)
  • Greenville, NC Retail: $3.204/gal (+$0.074/gal, +2.27%)
  • Charlotte, NC Retail: $3.236/gal (+$0.074/gal, +2.24%)
  • Port St. Lucie, FL Retail: $3.819/gal ($-0.285/gal, -7.29%)
  • Oakland, CA Retail: $4.882/gal ($-0.260/gal, -5.25%)
  • SF Bay Area Region: $4.981/gal ($-0.261/gal, -5.18%)

Largest upward shift for this run: National Wholesale at $3.250/gal (+0.111/gal). Largest downward shift for this run: Port St. Lucie, FL Retail at $3.819/gal (-0.285/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-10 16:15:15]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'Russia Vows to Keep Selling Oil to India Despite U.S. Tariff Threat - Crude Oil Prices Today | OilPrice.com'. Overall price pressure vector sits at ΔP=+0.52/gal.
• Weather & Convective Risk: SPC convective outlook and NOAA zip-code alerts for Tulsa (74101), Newark (19711), Cincinnati (45202), Carolinas (27834/28202), and Oakland (94612) map zero active severe tornado trips for this forecast run.
• Maritime & Geopolitical Exposure: Geopolitical risk score G=0.80. Counterfactual Strait of Hormuz blockade would inject +$0.109/gal (+2.88%) to current baseline.
• Executive Social Media Gap Analysis: If weekend executive social media posts emerge while commodity exchanges are closed, Monday morning open price gap volatility is projected at 1.42x normal intraday range.

---

## 6. Advanced Quantitative Feature & Physical Data Formulas

### 3-2-1 Refining Crack Spread Formula (Issue #169)
$$\text{Crack}_{321} (\$/\text{bbl}) = \frac{2 \times (P_{\text{RBOB}} \times 42) + 1 \times (P_{\text{HO}} \times 42) - 3 \times P_{\text{WTI}}}{3}$$

### Stacking Ensemble Quantile Prediction Bounds (Issue #170)
$$P_{10} = P_{50} - 1.2815\sigma, \quad P_{90} = P_{50} + 1.2815\sigma$$

### Dynamic Volatility-Gated Persistence Blending (DV-GPB) (Issue #214)
$$\lambda_{\text{vol}} = \frac{1}{1 + e^{-200.0 \cdot (\sigma_{14\text{d}} - 0.015)}}, \quad \hat{y}_{t+5} = \lambda_{\text{vol}} \hat{y}_{\text{model}} + (1 - \lambda_{\text{vol}}) y_t$$

### Empirical Residual 95% Confidence Intervals (Issue #214)
$$\text{CI}_{95\%} = \hat{y}_{t+5} \pm 1.96 \cdot \sigma_{\text{residual, 30d}}(r)$$

### USGS 3D Hypocentral Attenuation & Ground Shaking Intensity (Issue #55)
$$R = \sqrt{d^2 + h^2}, \quad w(R) = \frac{1}{1 + (R/35)^2}, \quad I = 10^{M - M_{\text{base}}} \times w(R)$$

### USGS Hydrological Streamflow & Barge Bottleneck Index (Issue #56)
$$\text{Index}_{\text{barge}} = \max\left(0, \min\left(1, \frac{\text{Gage}_{\text{threshold}} - \text{Gage}_t}{\text{Gage}_{\text{threshold}} - \text{Gage}_{\text{min}}}\right)\right)$$

### Multi-Feed AQI Standardized Flaring Outage Detection Z-Score (Issue #54)
$$Z_{\text{PM2.5}} = \frac{\text{PM2.5}_t - \mu_{30\text{d}}}{\sigma_{30\text{d}}}, \quad Z_{\text{SO2}} = \frac{\text{SO2}_t - \mu_{30\text{d}}}{\sigma_{30\text{d}}}$$

### EPA Ozone & Statutory Seasonal RVP Compliance Surcharge (Issue #73)
$$\text{Surcharge}_{\text{RVP}} = \Delta \text{Spread}_{\text{Summer Blend}} + 0.040 \cdot \mathbf{1}_{\text{AQI}_{\text{O3}} \ge 101}$$

### U.S. Census Commuter Inelastic Demand Score (Issue #75)
$$\text{Score}_{\text{inelastic}} = \frac{\text{DriveAlone} + \text{Carpool}}{\text{TotalCommuters}} \times (1 - \text{TransitIndex})$$

### Treasury 10Y-2Y Term Spread & Momentum Delta (Issue #66)
$$\text{Spread}_{10\text{Y}-2\text{Y}} = Y_{10\text{Y}} - Y_{2\text{Y}}, \quad \Delta \text{Spread}_{5\text{d}} = \text{Spread}_t - \text{Spread}_{t-5}$$

### Qlib Symbolic Alpha Factor Information Coefficient (Issue #127)
$$IC_t = \text{Corr}(f_t, r_{t+h}), \quad IC_{IR} = \frac{\mu(IC)}{\sigma(IC)}$$

### Multi-Horizon Forecast Scoreboard Accuracy (Issue #209)
$$\text{MAE}_H = \frac{1}{N_H} \sum_{i=1}^{N_H} |\hat{y}_{i, H} - y_{i, H}|, \quad H \in [1\text{d}, 2\text{d}, 3\text{d}, 4\text{d}, 5\text{d}]$$



---
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-10 16:15:15.*
