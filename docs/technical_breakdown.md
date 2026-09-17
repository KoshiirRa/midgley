# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-17 16:32:37`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** Central Indiana gas prices jump as refinery outage adds to global supply pressure - LarryInFishers  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Central Indiana gas prices jump as refinery outage adds to global supply pressure - LarryInFishers
- **Active Ingested News Links:**
- [Central Indiana gas prices jump as refinery outage adds to global supply pressure - LarryInFishers](https://news.google.com/rss/articles/CBMiwgFBVV95cUxNbEYyRTVHV3hMV0x5YUc0ZEl6Mnp5WlVVMkxqUTg0V0xsTGhvcU5KTXY4WjExdTJpWHZjWmVwWkZ3c3pnR0xjVnFoNkYyYlJtcVVOclUyZ3hyZ1ZKeDFNOHdZYWhlTDVrUXRSeG9ReWxYdHI0NzJMYzlIbGI1ZlBCNWVKMW9jWUJfY25IRmowSFNpMkZNYTEyQ0MwSGpFVTNvWXd6VVBfUUxVTmlPQlBiVi1ZdjZCdWIySzkzYWJUNVNMZw?oc=5) (Google News Energy Feed)
- [Saudi Pipeline Outage Pushes Physical Crude and Diesel Into Scarcity Pricing, Saxo Bank Says - Oil & Gas Middle East](https://news.google.com/rss/articles/CBMizAFBVV95cUxOWnJ3VElEbHBxMi11MGlFMGI1a04zeHBraTBSazJlV2Ewb2JuTk5hOHZxdGszYjhoaGE0eE43ZmljX3JMc1gwZVZKY1VUdzNrb1JwNm8wX2d5MXZ5MlgtN0lJX01BY1U0X0hFR3VPeF9EUW1vdlRxU01LZ0tYSzFNUTVTN3NGRWk3V2hXQlhRUVpaR2NOQy1RQnc4c3NobGpiZlBZMHcxTUhCOHdqZW9Va0V1eG5razJmbEdWckZzSTZ6NEhpd3NwVDlmdk0?oc=5) (Google News Energy Feed)
- [Alberta drivers face another jump at the pump after Illinois refinery outage - Global News](https://news.google.com/rss/articles/CBMickFVX3lxTE1FeFFJZ0R1NDQzR2hwOVFYckUzeVpYRmZuUkVfQTNNOFM4NlFwU1VrX1IyMnJBY3hld3NUSzRVRVBXMEN6U2tkdkdBWjFNT1ZGZzFYblpqUEdOYzZXUUJxbVJ0TlRySkhiX1hpTkxKZUo1Zw?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.80`
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


Numeric Retention Schedule for This Run ($M_0 = 0.8000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.8000$
- **Day 1 Decayed Shock**: $M_1 = 0.8000 \times 0.87055 = 0.6964$
- **Day 2 Decayed Shock**: $M_2 = 0.8000 \times (0.87055)^2 = 0.6063$
- **Day 3 Decayed Shock**: $M_3 = 0.8000 \times (0.87055)^3 = 0.5278$
- **Day 4 Decayed Shock**: $M_4 = 0.8000 \times (0.87055)^4 = 0.4595$
- **Day 5 (Target Horizon)**: $M_5 = 0.8000 \times 0.50000 = 0.4000$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (-\$0.007) = \$3.299\text{/gal}$ (Delta: -\$0.007/gal, -0.21\%)
- **Tulsa, OK Retail**: $P = \$4.010 + (+\$0.418) = \$6.463\text{/gal}$ (Delta: +\$0.418/gal, +10.42\%)
- **Newark, DE Retail**: $P = \$4.361 + (-\$0.052) = \$4.174\text{/gal}$ (Delta: -\$0.052/gal, -1.19\%)
- **Cincinnati, OH/KY**: $P = \$4.500 + (-\$0.084) = \$4.317\text{/gal}$ (Delta: -\$0.084/gal, -1.86\%)
- **Greenville, NC Retail**: $P = \$4.159 + (-\$0.063) = \$3.971\text{/gal}$ (Delta: -\$0.063/gal, -1.51\%)
- **Charlotte, NC Retail**: $P = \$4.223 + (-\$0.093) = \$4.042\text{/gal}$ (Delta: -\$0.093/gal, -2.20\%)
- **Port St. Lucie, FL Retail**: $P = \$4.310 + (-\$0.137) = \$4.087\text{/gal}$ (Delta: -\$0.137/gal, -3.17\%)
- **Oakland, CA Retail**: $P = \$6.131 + (+\$0.403) = \$5.871\text{/gal}$ (Delta: +\$0.403/gal, +6.57\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.235 + (+\$0.402) = \$5.971\text{/gal}$ (Delta: +\$0.402/gal, +6.46\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-17 16:32:37]: Elevated upward price shock (+$0.90/gal) observed across wholesale futures. Event trigger 'Central Indiana gas prices jump as refinery outage adds to global supply pressure - LarryInFishers' drove supply disruption to S=0.80 and geopolitical risk to G=0.00. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.6964 and Day-5 horizon retention M₅=0.4000.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-17 16:32:37 (Mode: INTRADAY_REVISION), primary event trigger 'Central Indiana gas prices jump as refinery outage adds to global supply pressure - LarryInFishers' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.80, Price Pressure ΔP=+0.90, Geopolitical Risk G=0.00. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.8000
  - Day 1: M₁ = 0.6964
  - Day 5: M₅ = 0.4000 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.299/gal ($-0.007/gal, -0.21%)
  • Tulsa, OK Retail: $6.463/gal (+$0.418/gal, +10.42%)
  • Newark, DE Retail: $4.174/gal ($-0.052/gal, -1.19%)
  • Cincinnati, OH/KY: $4.317/gal ($-0.084/gal, -1.86%)
  • Greenville, NC Retail: $3.971/gal ($-0.063/gal, -1.51%)
  • Charlotte, NC Retail: $4.042/gal ($-0.093/gal, -2.20%)
  • Port St. Lucie, FL Retail: $4.087/gal ($-0.137/gal, -3.17%)
  • Oakland, CA Retail: $5.871/gal (+$0.403/gal, +6.57%)
  • SF Bay Area Region: $5.971/gal (+$0.402/gal, +6.46%)

Largest upward shift for this run: Tulsa, OK Retail at $6.463/gal (+0.418/gal). Largest downward shift for this run: Port St. Lucie, FL Retail at $4.087/gal (-0.137/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-17 16:32:37]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'Central Indiana gas prices jump as refinery outage adds to global supply pressure - LarryInFishers'. Overall price pressure vector sits at ΔP=+0.90/gal.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-17 16:32:37.*
