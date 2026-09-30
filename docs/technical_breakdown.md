# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-30 12:09:46`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** Indian refiners may trim Russian oil imports, assess US tariff risks - Moneycontrol.com  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Indian refiners may trim Russian oil imports, assess US tariff risks - Moneycontrol.com
- **Active Ingested News Links:**
- [Indian refiners may trim Russian oil imports, assess US tariff risks - Moneycontrol.com](https://news.google.com/rss/articles/CBMizAFBVV95cUxNbUc1VHlySFR0NmFpNmJYcnpPRzRqS1Z5TnNLc1NfRFBHZHdOMVFHUldtdnZETlN6ZElZbEo0RTN4ZHV5NlF1N0ZJY0NrOXVqVDRaSHhic18zOUxmUXR1VW5iem4zSmpwMVRPbVM5UFRpVzBEaFUySEMyZHMwV1Bmb2I0dGE5Y0dqUlFXaDUxSG9HX0xtd3JwS0taOVJ3Vkh2X3dGNmVpcUxGRlE0azV0YjBOZ3RZdGhuUW9wTUs0OXgtS0ZhYldBRXlvR0PSAdIBQVVfeXFMTXRxSjJQUGYzNHNLTERHRXZVQ3NSX1VxR0RZVFdsNUZtV21rVUtMNVExd0N6TklkZl9TeGRhVTNzWEVsU3BVMm01MFZibnNqWEd4TjEwRUlzVHd4SkJ0UmlxdDFrenc2WGlLNGNjc3JVNzR5UmJ2OVlzNzQyYVB2YURqbFVzQmJwZDVrSF9aOVRQbG14bkNsM0E0ZThId3BJNkprRHdPTXFuXzhNN09KQkRPRDJ1UUstVEFBd1lfNXFQSjM5czB2eTZFNGxSLTgtbUVR?oc=5) (Google News Energy Feed)
- [PHILLIPS 66 TEAMSTERS OVERWHELMINGLY AUTHORIZE STRIKE - finance.yahoo.com](https://news.google.com/rss/articles/CBMipgFBVV95cUxNRDZ2OU93V0lhOGZzQnJoV05SczFLOTd3Ylowb1YydjVWaFNHQmZ6NWFJRWZKUzFVVjBMSVg3QWtxWEM4VXhrQjh4M3hVbmdZUjVKdktNYlZ6aXNUSVJsbTVzU2JDYjlmWklTLTlHdFhrU0xZWGpKOHBGUDBHUzRCTmhxeDhlUS1NVzlySGpnOGQ1LU9sUzhDc2tYNDVXdjZMUVVueE1n?oc=5) (Google News Energy Feed)
- [Lindsey O. Graham sanctioning Russia and Iran Act 2026: restrictive U.S. tariff measures targeting all imports from major buyers of Russian energy - stephensonharwood.com](https://news.google.com/rss/articles/CBMilAJBVV95cUxQWXg1WExONkNocmh0WUx2aldNdy1pU2FYYzh0RFI4VVcwbk82WnNfUVB3UUFZMEk0MGVuTE1CUExidFRNbWNPZThzeHlPRHlqRHJDclEzNVlLMTUxMWtmYnNxWG1UZGNPSjl4MlNKRXlqVVZpd0xaeHZvVDlJNTdhVThSYXM0cFBSN3lweWdsRUxrWEJmUXRQSVYwWkgyczlzbkt1bUwybl9Lc18yQmlaQjNPZkNaWHZGQThrX21ncWtjVXBMVHJfME50V0lLcW9ocnd1ZG9iLTh0TzNNZjVBR2hzQU9pM1hEdzRmWHhmMWJVVkFhN0c5Sm5qQTFsRnRmcnRFWWhBMnBOWHdhckV5ZndvY0w?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.30`
- **Price Pressure Shock ($\Delta P$):** `+0.40`
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


Numeric Retention Schedule for This Run ($M_0 = 0.3000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.3000$
- **Day 1 Decayed Shock**: $M_1 = 0.3000 \times 0.87055 = 0.2612$
- **Day 2 Decayed Shock**: $M_2 = 0.3000 \times (0.87055)^2 = 0.2274$
- **Day 3 Decayed Shock**: $M_3 = 0.3000 \times (0.87055)^3 = 0.1979$
- **Day 4 Decayed Shock**: $M_4 = 0.3000 \times (0.87055)^4 = 0.1723$
- **Day 5 (Target Horizon)**: $M_5 = 0.3000 \times 0.50000 = 0.1500$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (+\$0.020) = \$3.235\text{/gal}$ (Delta: +\$0.020/gal, +0.61\%)
- **Tulsa, OK Retail**: $P = \$4.150 + (-\$0.229) = \$4.089\text{/gal}$ (Delta: -\$0.229/gal, -5.52\%)
- **Newark, DE Retail**: $P = \$4.316 + (-\$0.398) = \$4.417\text{/gal}$ (Delta: -\$0.398/gal, -9.21\%)
- **Cincinnati, OH/KY**: $P = \$4.247 + (-\$0.412) = \$4.308\text{/gal}$ (Delta: -\$0.412/gal, -9.69\%)
- **Greenville, NC Retail**: $P = \$4.120 + (-\$0.376) = \$4.221\text{/gal}$ (Delta: -\$0.376/gal, -9.12\%)
- **Charlotte, NC Retail**: $P = \$4.160 + (-\$0.244) = \$4.350\text{/gal}$ (Delta: -\$0.244/gal, -5.87\%)
- **Port St. Lucie, FL Retail**: $P = \$4.301 + (-\$0.354) = \$4.364\text{/gal}$ (Delta: -\$0.354/gal, -8.23\%)
- **Oakland, CA Retail**: $P = \$6.434 + (-\$0.435) = \$6.514\text{/gal}$ (Delta: -\$0.435/gal, -6.76\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.566 + (-\$0.302) = \$6.648\text{/gal}$ (Delta: -\$0.302/gal, -4.59\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-30 12:09:46]: Elevated upward price shock (+$0.40/gal) observed across wholesale futures. Event trigger 'Indian refiners may trim Russian oil imports, assess US tariff risks - Moneycontrol.com' drove supply disruption to S=0.30 and geopolitical risk to G=0.80. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.2612 and Day-5 horizon retention M₅=0.1500.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-30 12:09:46 (Mode: INTRADAY_REVISION), primary event trigger 'Indian refiners may trim Russian oil imports, assess US tariff risks - Moneycontrol.com' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.30, Price Pressure ΔP=+0.40, Geopolitical Risk G=0.80. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.3000
  - Day 1: M₁ = 0.2612
  - Day 5: M₅ = 0.1500 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.235/gal (+$0.020/gal, +0.61%)
  • Tulsa, OK Retail: $4.089/gal ($-0.229/gal, -5.52%)
  • Newark, DE Retail: $4.417/gal ($-0.398/gal, -9.21%)
  • Cincinnati, OH/KY: $4.308/gal ($-0.412/gal, -9.69%)
  • Greenville, NC Retail: $4.221/gal ($-0.376/gal, -9.12%)
  • Charlotte, NC Retail: $4.350/gal ($-0.244/gal, -5.87%)
  • Port St. Lucie, FL Retail: $4.364/gal ($-0.354/gal, -8.23%)
  • Oakland, CA Retail: $6.514/gal ($-0.435/gal, -6.76%)
  • SF Bay Area Region: $6.648/gal ($-0.302/gal, -4.59%)

Largest upward shift for this run: National Wholesale at $3.235/gal (+0.020/gal). Largest downward shift for this run: Oakland, CA Retail at $6.514/gal (-0.435/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-30 12:09:46]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'Indian refiners may trim Russian oil imports, assess US tariff risks - Moneycontrol.com'. Overall price pressure vector sits at ΔP=+0.40/gal.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-30 12:09:46.*
