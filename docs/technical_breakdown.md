# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-17 11:16:02`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** Saudi Pipeline Outage Pushes Physical Crude and Diesel Into Scarcity Pricing, Saxo Bank Says - Oil & Gas Middle East  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Saudi Pipeline Outage Pushes Physical Crude and Diesel Into Scarcity Pricing, Saxo Bank Says - Oil & Gas Middle East
- **Active Ingested News Links:**
- [Saudi Pipeline Outage Pushes Physical Crude and Diesel Into Scarcity Pricing, Saxo Bank Says - Oil & Gas Middle East](https://news.google.com/rss/articles/CBMizAFBVV95cUxOWnJ3VElEbHBxMi11MGlFMGI1a04zeHBraTBSazJlV2Ewb2JuTk5hOHZxdGszYjhoaGE0eE43ZmljX3JMc1gwZVZKY1VUdzNrb1JwNm8wX2d5MXZ5MlgtN0lJX01BY1U0X0hFR3VPeF9EUW1vdlRxU01LZ0tYSzFNUTVTN3NGRWk3V2hXQlhRUVpaR2NOQy1RQnc4c3NobGpiZlBZMHcxTUhCOHdqZW9Va0V1eG5razJmbEdWckZzSTZ6NEhpd3NwVDlmdk0?oc=5) (Google News Energy Feed)
- [Alberta drivers face another jump at the pump after Illinois refinery outage - Global News](https://news.google.com/rss/articles/CBMickFVX3lxTE1FeFFJZ0R1NDQzR2hwOVFYckUzeVpYRmZuUkVfQTNNOFM4NlFwU1VrX1IyMnJBY3hld3NUSzRVRVBXMEN6U2tkdkdBWjFNT1ZGZzFYblpqUEdOYzZXUUJxbVJ0TlRySkhiX1hpTkxKZUo1Zw?oc=5) (Google News Energy Feed)
- [100% tariff on India? Russia sanctions bill clears key hurdle, final House vote next - timesofindia.indiatimes.com](https://news.google.com/rss/articles/CBMihgJBVV95cUxQaEdkZjFaYU9PYXRrRUxKa2pNU2szZjA4WXdNdTZyODBXN2JpeU5QOHhZOTZQYnE2aUEtODFoVkloUFZOUDFMYWh1b1g5RG1oeUJRdVdsUDhTTFFGY0hmR0lVU1J4SVJscnFiOUFVV3dTZUV6QVdpNzgxVEJtcUNZN2RuUlJGUldHNUhjR1cycVNTWjdYT0ZIdmUxZm1kbGtneWEzYWJWZmVPMFAyb0liS2lpc0JLV0d2RS1zMm1CS3VCaWowVlR1alFuM0JpMTVoSjJTUzFockV3dVZqZG1lMngzanEzOTNUOVRPQ1Jpak5IUzJyT3dZWFY0UDRvZzRNVlNEYnJ30gGLAkFVX3lxTE9qN0lsTWVKTEllczNBdkpGR2VhemZ5akZNdTRlYUo4YW1MQnlfMEtURkI3Q2JRbWQzeXZVU3dVOE1xbVlUYjM0bjlwS3Y3S2VWNG1Uczk3b2lQckpkUVM3elFfQThCY0RGV3Z6cGVPTjBKT2FmWVNBRzVtVElqTndDbVRhSnJ0NXNMUnBZaFJLZ1h1UDM1b1N2bl96LWxlNlZiNk9xaW9VdXBxeHBmR1ktdGQ3S1FmWTdHazF2NWtvbVhnM1B5dHZBN2l5OS15M2FuZE51RGtFay1kNC1iZkYyaGtTWkc4MVFBdkt4Y290RU4zaG92SXRha2VlZGl3Q0NlaE80VTB1d1A2QQ?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.90`
- **Price Pressure Shock ($\Delta P$):** `+0.90`
- **Geopolitical Risk Score ($G$):** `0.00`
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


Numeric Retention Schedule for This Run ($M_0 = 0.9000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.9000$
- **Day 1 Decayed Shock**: $M_1 = 0.9000 \times 0.87055 = 0.7835$
- **Day 2 Decayed Shock**: $M_2 = 0.9000 \times (0.87055)^2 = 0.6821$
- **Day 3 Decayed Shock**: $M_3 = 0.9000 \times (0.87055)^3 = 0.5938$
- **Day 4 Decayed Shock**: $M_4 = 0.9000 \times (0.87055)^4 = 0.5169$
- **Day 5 (Target Horizon)**: $M_5 = 0.9000 \times 0.50000 = 0.4500$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (+\$0.064) = \$3.299\text{/gal}$ (Delta: +\$0.064/gal, +2.00\%)
- **Tulsa, OK Retail**: $P = \$4.000 + (+\$0.483) = \$5.961\text{/gal}$ (Delta: +\$0.483/gal, +12.07\%)
- **Newark, DE Retail**: $P = \$4.361 + (-\$0.076) = \$3.959\text{/gal}$ (Delta: -\$0.076/gal, -1.75\%)
- **Cincinnati, OH/KY**: $P = \$4.322 + (-\$0.079) = \$3.962\text{/gal}$ (Delta: -\$0.079/gal, -1.83\%)
- **Greenville, NC Retail**: $P = \$4.117 + (-\$0.091) = \$3.733\text{/gal}$ (Delta: -\$0.091/gal, -2.21\%)
- **Charlotte, NC Retail**: $P = \$4.194 + (-\$0.011) = \$3.816\text{/gal}$ (Delta: -\$0.011/gal, -0.26\%)
- **Port St. Lucie, FL Retail**: $P = \$4.178 + (+\$0.018) = \$3.808\text{/gal}$ (Delta: +\$0.018/gal, +0.44\%)
- **Oakland, CA Retail**: $P = \$6.088 + (+\$0.357) = \$5.509\text{/gal}$ (Delta: +\$0.357/gal, +5.87\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.188 + (+\$0.348) = \$5.599\text{/gal}$ (Delta: +\$0.348/gal, +5.62\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-17 11:16:02]: Elevated upward price shock (+$0.90/gal) observed across wholesale futures. Event trigger 'Saudi Pipeline Outage Pushes Physical Crude and Diesel Into Scarcity Pricing, Saxo Bank Says - Oil & Gas Middle East' drove supply disruption to S=0.90 and geopolitical risk to G=0.00. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.7835 and Day-5 horizon retention M₅=0.4500.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-17 11:16:02 (Mode: INTRADAY_REVISION), primary event trigger 'Saudi Pipeline Outage Pushes Physical Crude and Diesel Into Scarcity Pricing, Saxo Bank Says - Oil & Gas Middle East' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.90, Price Pressure ΔP=+0.90, Geopolitical Risk G=0.00. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.9000
  - Day 1: M₁ = 0.7835
  - Day 5: M₅ = 0.4500 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.299/gal (+$0.064/gal, +2.00%)
  • Tulsa, OK Retail: $5.961/gal (+$0.483/gal, +12.07%)
  • Newark, DE Retail: $3.959/gal ($-0.076/gal, -1.75%)
  • Cincinnati, OH/KY: $3.962/gal ($-0.079/gal, -1.83%)
  • Greenville, NC Retail: $3.733/gal ($-0.091/gal, -2.21%)
  • Charlotte, NC Retail: $3.816/gal ($-0.011/gal, -0.26%)
  • Port St. Lucie, FL Retail: $3.808/gal (+$0.018/gal, +0.44%)
  • Oakland, CA Retail: $5.509/gal (+$0.357/gal, +5.87%)
  • SF Bay Area Region: $5.599/gal (+$0.348/gal, +5.62%)

Largest upward shift for this run: Tulsa, OK Retail at $5.961/gal (+0.483/gal). Largest downward shift for this run: Greenville, NC Retail at $3.733/gal (-0.091/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-17 11:16:02]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'Saudi Pipeline Outage Pushes Physical Crude and Diesel Into Scarcity Pricing, Saxo Bank Says - Oil & Gas Middle East'. Overall price pressure vector sits at ΔP=+0.90/gal.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-17 11:16:02.*
