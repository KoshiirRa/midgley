# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-20 22:17:30`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** U.S., Russia, India In Oil Tariff Triangle—Who Wins? - Forbes  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** U.S., Russia, India In Oil Tariff Triangle—Who Wins? - Forbes
- **Active Ingested News Links:**
- [U.S., Russia, India In Oil Tariff Triangle—Who Wins? - Forbes](https://news.google.com/rss/articles/CBMinwFBVV95cUxQejVTV3VJMTRHRWNBV1pxblh5Z25YN3lKa0lGcERsaGVEc2k3SUNPNF9iN3FjTmJNQUsxV3VmY01LYVp4SU1RU3FrRHhaUnp5YnNXUi13cE9DZWN1bjVYOEl2U01nTm9RcUVQSUlSeG0zY3lSQmtGa1VOcEFzeElXVEk4WmY3cjlKQ1NKNnJFay1jRFBjZ1IzUzduNEtMY1U?oc=5) (Google News Energy Feed)
- [US' 100% tariff threat: India may find it difficult to cut Russian oil buys - Business Standard](https://news.google.com/rss/articles/CBMi1gFBVV95cUxNM3NKMERUcWZpMzdtMTlyQm1YU0t5U1FCVTdybUQ0RXFmTkdEYnFLVjhDOXpCWDlCQXdpVnFHSERnRF9Fd2YxelN2SElYMUhGMWNmMHhzYXhYY19mZmY1RXdTRGlBRzZVaTB2dHhXbkxySmU5LVZSemhmSFVRZDkwYmI5aFhtbkgtcVl6RFFoS0lBdi1Xc2JCSUFzYlFYeVJaS2REdlpMNVQ5TmJMRHBHdkRuQVMwX0xuSzNnNHNOb0d0M2Y5ZnVOanJNN0M5UmFDSG9fZXJR0gHbAUFVX3lxTE14NnRadGRKMkRuZ3hoejZ2YzlFVFdtM0IzbktRajRzQWJiRW5vS0J4cEtxLXk1WGZIVktxUnBZU0RmSkI0UVhRcDRSaVlPdnNzbWpUR0lZTVhhOXk0YTc1SlJBOHREYnAweDAzdTdZVHZ3TjJhZHltcGQ1cXZ2a05CV1hocE5JZDRJWHNYTUkyd0tGcDNvR1FhYUxRNm1SdGhnZDhrT0kxbUFpblI0SGVHeG5FbndlMDNRaHRDMDlVQkRGY1lXS0lDaWl5WE4wQWRfZktEcHJmTkY3dw?oc=5) (Google News Energy Feed)
- [Illinois refinery outage drives up Iowa gas costs - weareiowa.com](https://news.google.com/rss/articles/CBMi2AFBVV95cUxPaGVqOU50RVdLM2c5bTJxbnBDbU1Ea0VEa190bWJWTVdOLTd5S2hCNTAwVlJTZ19qUFRnYkpXd040ZC02a1pCWExXZ09XcHRFdTFxNFBNbkJSYk1rVmtqMV90OGN4WGJVa1lDTDBTazlla2Y1NE1zWklqaTNaRmcyYlB6S0c4eFRNNmlQbTN6RlJ6ZXpRZkxWcnRqQ29xSWFWTUV1cmE2NW9OWkExdXB2dUk1c1ZXazg1dEdxbWVZaFI5N2tOdmVGLTNBNXlvRkZxbGlQRnVYckE?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.50`
- **Price Pressure Shock ($\Delta P$):** `+0.70`
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


Numeric Retention Schedule for This Run ($M_0 = 0.5000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.5000$
- **Day 1 Decayed Shock**: $M_1 = 0.5000 \times 0.87055 = 0.4353$
- **Day 2 Decayed Shock**: $M_2 = 0.5000 \times (0.87055)^2 = 0.3789$
- **Day 3 Decayed Shock**: $M_3 = 0.5000 \times (0.87055)^3 = 0.3299$
- **Day 4 Decayed Shock**: $M_4 = 0.5000 \times (0.87055)^4 = 0.2872$
- **Day 5 (Target Horizon)**: $M_5 = 0.5000 \times 0.50000 = 0.2500$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (+\$0.033) = \$3.273\text{/gal}$ (Delta: +\$0.033/gal, +1.05\%)
- **Tulsa, OK Retail**: $P = \$4.004 + (+\$0.740) = \$5.895\text{/gal}$ (Delta: +\$0.740/gal, +18.49\%)
- **Newark, DE Retail**: $P = \$4.357 + (-\$0.002) = \$4.355\text{/gal}$ (Delta: -\$0.002/gal, -0.05\%)
- **Cincinnati, OH/KY**: $P = \$4.487 + (-\$0.005) = \$4.487\text{/gal}$ (Delta: -\$0.005/gal, -0.10\%)
- **Greenville, NC Retail**: $P = \$4.146 + (+\$0.002) = \$4.146\text{/gal}$ (Delta: +\$0.002/gal, +0.06\%)
- **Charlotte, NC Retail**: $P = \$4.204 + (+\$0.010) = \$4.214\text{/gal}$ (Delta: +\$0.010/gal, +0.25\%)
- **Port St. Lucie, FL Retail**: $P = \$4.335 + (+\$0.001) = \$4.343\text{/gal}$ (Delta: +\$0.001/gal, +0.01\%)
- **Oakland, CA Retail**: $P = \$6.206 + (+\$0.008) = \$6.236\text{/gal}$ (Delta: +\$0.008/gal, +0.14\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.329 + (+\$0.009) = \$6.359\text{/gal}$ (Delta: +\$0.009/gal, +0.14\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-20 22:17:30]: Elevated upward price shock (+$0.70/gal) observed across wholesale futures. Event trigger 'U.S., Russia, India In Oil Tariff Triangle—Who Wins? - Forbes' drove supply disruption to S=0.50 and geopolitical risk to G=0.80. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.4353 and Day-5 horizon retention M₅=0.2500.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-20 22:17:30 (Mode: INTRADAY_REVISION), primary event trigger 'U.S., Russia, India In Oil Tariff Triangle—Who Wins? - Forbes' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.50, Price Pressure ΔP=+0.70, Geopolitical Risk G=0.80. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.5000
  - Day 1: M₁ = 0.4353
  - Day 5: M₅ = 0.2500 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.273/gal (+$0.033/gal, +1.05%)
  • Tulsa, OK Retail: $5.895/gal (+$0.740/gal, +18.49%)
  • Newark, DE Retail: $4.355/gal ($-0.002/gal, -0.05%)
  • Cincinnati, OH/KY: $4.487/gal ($-0.005/gal, -0.10%)
  • Greenville, NC Retail: $4.146/gal (+$0.002/gal, +0.06%)
  • Charlotte, NC Retail: $4.214/gal (+$0.010/gal, +0.25%)
  • Port St. Lucie, FL Retail: $4.343/gal (+$0.001/gal, +0.01%)
  • Oakland, CA Retail: $6.236/gal (+$0.008/gal, +0.14%)
  • SF Bay Area Region: $6.359/gal (+$0.009/gal, +0.14%)

Largest upward shift for this run: Tulsa, OK Retail at $5.895/gal (+0.740/gal). Largest downward shift for this run: Cincinnati, OH/KY at $4.487/gal (-0.005/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-20 22:17:30]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'U.S., Russia, India In Oil Tariff Triangle—Who Wins? - Forbes'. Overall price pressure vector sits at ΔP=+0.70/gal.
• Weather & Convective Risk: SPC convective outlook and NOAA zip-code alerts for Tulsa (74101), Newark (19711), Cincinnati (45202), Carolinas (27834/28202), and Oakland (94612) map zero active severe tornado trips for this forecast run.
• Maritime & Geopolitical Exposure: Geopolitical risk score G=0.80. Counterfactual Strait of Hormuz blockade would inject +$0.109/gal (+2.88%) to current baseline.
• Executive Social Media Gap Analysis: If weekend executive social media posts emerge while commodity exchanges are closed, Monday morning open price gap volatility is projected at 1.42x normal intraday range.
• Climatological Plausibility Horizon: [SEASONALLY_PLAUSIBLE] Category 3 Atlantic Hurricane Landfall & Tar River Flooding; [SEASONALLY_PLAUSIBLE] Category 3 Atlantic Hurricane & Port Everglades Marine Shutdown; [SEASONALLY_PLAUSIBLE] PG&E PSPS Red Flag Wildfire Power Shutoff & Refinery Blackout; [SEASONALLY_PLAUSIBLE] Lower Mississippi & Ohio River Low-Water Barge Bottleneck

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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-20 22:17:30.*
