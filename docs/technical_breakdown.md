# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-07 18:00:20`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** US Diesel Fuel Prices Reach Record Highs Amid Global Refinery Outages - SuaraGarut.ID  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** US Diesel Fuel Prices Reach Record Highs Amid Global Refinery Outages - SuaraGarut.ID
- **Active Ingested News Links:**
- [US Diesel Fuel Prices Reach Record Highs Amid Global Refinery Outages - SuaraGarut.ID](https://news.google.com/rss/articles/CBMiZEFVX3lxTFBPOE4zZDEyTE1YYXU4dFp0NDNXVnFjdVFkYTBUcGpxWjRtQ2h4TkJlRXpUU3A4RVVVVVdIVlJDYVl2dWFUek5PVzZiWFVSVjF2VFVyUXdacng5bm14VGQ2UUtFeFU?oc=5) (Google News Energy Feed)
- [Russia Vows to Keep Selling Oil to India Despite U.S. Tariff Threat - Crude Oil Prices Today | OilPrice.com](https://news.google.com/rss/articles/CBMivgFBVV95cUxNOUp3NTFDYTZxUS03aGVDY0ZfZzV4b3RCYnNTUE01cTI3cm1sUU5JVmYtQ1B1eml0aC0ySkFiQ1pZeE03RkNkVkZNSk8yQzBkQzlqWWlRZmlCWXlwb3hNaWw1VENhY1BmYXp6M2ZiRERHdnd5cTBkbjBPOWxIRHYzLVA0ZjZPN2Y5ZnVRalE1bHVNdkVHeUxJMWtHM2FseEFFNGpyMTBCSDFkZGlDdS1vUGVncFlPQkgyMVB2al9R0gHDAUFVX3lxTFB1QWstLVN0SEFMdER4My1nVTd2WTlEQ3NaQlQ1UkNqeFBPc2g0Mm1PTTIzZkZsVTNSTFRkYVA0REpzZy1UV29VR01ISUstZXZUd0lQbnZXZi1nR3ozM2hjSllHaHZiZm1aaUloVDVTRDBtRWlyeGZZWl95VG8wZ1lFSzRMaFVGa01EMFJkcjh1cVNTMmVPbTZBTFRHcm1qSHh3SE55Qnp0TWZnUEc4LURrUEFsa1hPSWJmejNXMmxuY1BkZw?oc=5) (Google News Energy Feed)
- [India buys oil for itself, not to help Moscow: Russian envoy amid US tariff threat - India Today](https://news.google.com/rss/articles/CBMihAJBVV95cUxPbzVTS2pHY3RxZXhPREJnQS1INzFDZ2Jlb2R3eU1uT3dnRml3UVcxWS1JZmJZZlJwLWRFYXZmc1g0VFNSMmFDQTEwOHQyNTAxN0NSYTBWT2lONHpTVFNpMHl2RGVURjJWX2NZdTR6NlRuR2hTbUhjRXNxV0FWeTdSUGVZMURNWGl5c3BWRU1zcjFSa3h6cTlpMnlpTkd4d2F2YnRwODEtOTFjSjFQSTZtd0xjUmxWSEhhRl80cnA3d2QwYXlpbTRUSzdrYS1kZGxFMjJJb3lBSnE4Q1AzMzJQQi1EekFlYlJBNWxDZmVqTFA1cHV2OXFmS2JWbUJvbHBIRDBZUdIBigJBVV95cUxPa19sSVNwVm11WjMxNVF5eklXVGxCZjZRRGgzZlBhYTVzYnJPV2c4WjVpS2dSalNyUDc1Qm5qRHFjbmk1QnpMU2hVdm01dUhhNnhJeDdVam53bzFRel9GYnQ0TTNKanUxc3N6T2hPZHRlcEMyVFFHNmFQVDNtbFRvOWM4YkdQV2RVUHVaQ2RpM2cwcjNzQ0ltNXNEMHlSWmoybGZUaDRsQ0p1Uy0wMVJ4VFNuWlJGR2NPRkJ5WjJhaGlPQ3Y3MnhmUXJua083M3hRMnRmREtEVC00b2VULXU4eGlSWkJsN1p1S25mMGRPcnhyUWYyODhXcFFHQUdBc0lpcm5ST2l5YjdpZw?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.50`
- **Price Pressure Shock ($\Delta P$):** `+0.26`
- **Geopolitical Risk Score ($G$):** `0.00`
- **Demand Sentiment Score ($D$):** `0.40`
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


Numeric Retention Schedule for This Run ($M_0 = 0.5000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.5000$
- **Day 1 Decayed Shock**: $M_1 = 0.5000 \times 0.87055 = 0.4353$
- **Day 2 Decayed Shock**: $M_2 = 0.5000 \times (0.87055)^2 = 0.3789$
- **Day 3 Decayed Shock**: $M_3 = 0.5000 \times (0.87055)^3 = 0.3299$
- **Day 4 Decayed Shock**: $M_4 = 0.5000 \times (0.87055)^4 = 0.2872$
- **Day 5 (Target Horizon)**: $M_5 = 0.5000 \times 0.50000 = 0.2500$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (-\$0.196) = \$3.217\text{/gal}$ (Delta: -\$0.196/gal, -6.17\%)
- **Tulsa, OK Retail**: $P = \$3.599 + (-\$0.278) = \$3.503\text{/gal}$ (Delta: -\$0.278/gal, -7.73\%)
- **Newark, DE Retail**: $P = \$3.381 + (-\$0.273) = \$3.299\text{/gal}$ (Delta: -\$0.273/gal, -8.07\%)
- **Cincinnati, OH/KY**: $P = \$3.883 + (-\$0.284) = \$3.799\text{/gal}$ (Delta: -\$0.284/gal, -7.31\%)
- **Greenville, NC Retail**: $P = \$3.705 + (-\$0.280) = \$3.621\text{/gal}$ (Delta: -\$0.280/gal, -7.56\%)
- **Charlotte, NC Retail**: $P = \$3.850 + (-\$0.284) = \$3.760\text{/gal}$ (Delta: -\$0.284/gal, -7.37\%)
- **Port St. Lucie, FL Retail**: $P = \$3.913 + (-\$0.285) = \$3.819\text{/gal}$ (Delta: -\$0.285/gal, -7.29\%)
- **Oakland, CA Retail**: $P = \$5.891 + (+\$0.289) = \$5.738\text{/gal}$ (Delta: +\$0.289/gal, +4.90\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.004 + (+\$0.299) = \$5.848\text{/gal}$ (Delta: +\$0.299/gal, +4.98\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-07 18:00:20]: Elevated upward price shock (+$0.26/gal) observed across wholesale futures. Event trigger 'US Diesel Fuel Prices Reach Record Highs Amid Global Refinery Outages - SuaraGarut.ID' drove supply disruption to S=0.50 and geopolitical risk to G=0.00. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.4353 and Day-5 horizon retention M₅=0.2500.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-07 18:00:20 (Mode: INTRADAY_REVISION), primary event trigger 'US Diesel Fuel Prices Reach Record Highs Amid Global Refinery Outages - SuaraGarut.ID' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.50, Price Pressure ΔP=+0.26, Geopolitical Risk G=0.00. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.5000
  - Day 1: M₁ = 0.4353
  - Day 5: M₅ = 0.2500 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.217/gal ($-0.196/gal, -6.17%)
  • Tulsa, OK Retail: $3.503/gal ($-0.278/gal, -7.73%)
  • Newark, DE Retail: $3.299/gal ($-0.273/gal, -8.07%)
  • Cincinnati, OH/KY: $3.799/gal ($-0.284/gal, -7.31%)
  • Greenville, NC Retail: $3.621/gal ($-0.280/gal, -7.56%)
  • Charlotte, NC Retail: $3.760/gal ($-0.284/gal, -7.37%)
  • Port St. Lucie, FL Retail: $3.819/gal ($-0.285/gal, -7.29%)
  • Oakland, CA Retail: $5.738/gal (+$0.289/gal, +4.90%)
  • SF Bay Area Region: $5.848/gal (+$0.299/gal, +4.98%)

Largest upward shift for this run: SF Bay Area Region at $5.848/gal (+0.299/gal). Largest downward shift for this run: Port St. Lucie, FL Retail at $3.819/gal (-0.285/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-07 18:00:20]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'US Diesel Fuel Prices Reach Record Highs Amid Global Refinery Outages - SuaraGarut.ID'. Overall price pressure vector sits at ΔP=+0.26/gal.
• Weather & Convective Risk: SPC convective outlook and NOAA zip-code alerts for Tulsa (74101), Newark (19711), Cincinnati (45202), Carolinas (27834/28202), and Oakland (94612) map zero active severe tornado trips for this forecast run.
• Maritime & Geopolitical Exposure: Geopolitical risk score G=0.00. Counterfactual Strait of Hormuz blockade would inject +$0.109/gal (+2.88%) to current baseline.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-07 18:00:20.*
