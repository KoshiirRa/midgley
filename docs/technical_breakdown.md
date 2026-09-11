# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-11 22:55:55`  
**Run Mode:** `DAILY_BATCH`  
**Primary Event Trigger:** Daily Forecast Batch Execution (2026-09-11 22:55:55)  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Daily Forecast Batch Execution (2026-09-11 22:55:55)
- **Active Ingested News Links:**
- [NYMEX RBOB Futures & WTI Crude Spot Energy Commodity Benchmark Refresh](https://www.cmegroup.com/markets/energy/refined-products/rbob-gasoline.html) (CME Group / NYMEX)
- [NOAA National Weather Service Multi-Basin Severe Weather & Freeze Warning Ingestion](https://www.weather.gov) (NOAA NWS Storm Alert)
- [Executive Policy Feed & OPEC Weekend Open Price Gap Intelligence](https://www.bloomberg.com/energy) (Bloomberg Market Wire)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.10`
- **Price Pressure Shock ($\Delta P$):** `+0.02`
- **Geopolitical Risk Score ($G$):** `0.15`
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


Numeric Retention Schedule for This Run ($M_0 = 0.1000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.1000$
- **Day 1 Decayed Shock**: $M_1 = 0.1000 \times 0.87055 = 0.0871$
- **Day 2 Decayed Shock**: $M_2 = 0.1000 \times (0.87055)^2 = 0.0758$
- **Day 3 Decayed Shock**: $M_3 = 0.1000 \times (0.87055)^3 = 0.0660$
- **Day 4 Decayed Shock**: $M_4 = 0.1000 \times (0.87055)^4 = 0.0574$
- **Day 5 (Target Horizon)**: $M_5 = 0.1000 \times 0.50000 = 0.0500$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.393 + (+\$0.000) = \$3.109\text{/gal}$ (Delta: +\$0.000/gal, 0.00\%)
- **Tulsa, OK Retail**: $P = \$3.817 + (+\$0.278) = \$3.754\text{/gal}$ (Delta: +\$0.278/gal, +7.27\%)
- **Newark, DE Retail**: $P = \$3.293 + (+\$0.287) = \$3.246\text{/gal}$ (Delta: +\$0.287/gal, +8.71\%)
- **Cincinnati, OH/KY**: $P = \$4.149 + (+\$0.276) = \$4.096\text{/gal}$ (Delta: +\$0.276/gal, +6.65\%)
- **Greenville, NC Retail**: $P = \$3.617 + (+\$0.282) = \$3.562\text{/gal}$ (Delta: +\$0.282/gal, +7.79\%)
- **Charlotte, NC Retail**: $P = \$3.963 + (+\$0.278) = \$3.908\text{/gal}$ (Delta: +\$0.278/gal, +7.00\%)
- **Port St. Lucie, FL Retail**: $P = \$3.747 + (+\$0.280) = \$3.694\text{/gal}$ (Delta: +\$0.280/gal, +7.48\%)
- **Oakland, CA Retail**: $P = \$5.974 + (+\$0.780) = \$5.891\text{/gal}$ (Delta: +\$0.780/gal, +13.06\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.060 + (+\$0.765) = \$5.976\text{/gal}$ (Delta: +\$0.765/gal, +12.63\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-11 22:55:55]: Baseline daily batch market conditions prevail with minimal exogenous shocks. Ingested supply disruption S=0.10 and geopolitical risk G=0.15 yield a price pressure vector of ΔP=+0.02/gal. Primary trigger: 'Daily Forecast Batch Execution (2026-09-11 22:55:55)'. The standardized Ridge model calculates stable wholesale futures re-anchoring, with Day-5 residual event memory decaying from M₀=0.1000 down to M₅=0.0500.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-11 22:55:55 (Mode: DAILY_BATCH), primary event trigger 'Daily Forecast Batch Execution (2026-09-11 22:55:55)' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Bloomberg Market Wire, NOAA NWS Storm Alert, CME Group / NYMEX). Ingested factor vector: Supply Disruption S=0.10, Price Pressure ΔP=+0.02, Geopolitical Risk G=0.15. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.1000
  - Day 1: M₁ = 0.0871
  - Day 5: M₅ = 0.0500 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.109/gal ($0.000/gal, 0.00%)
  • Tulsa, OK Retail: $3.754/gal (+$0.278/gal, +7.27%)
  • Newark, DE Retail: $3.246/gal (+$0.287/gal, +8.71%)
  • Cincinnati, OH/KY: $4.096/gal (+$0.276/gal, +6.65%)
  • Greenville, NC Retail: $3.562/gal (+$0.282/gal, +7.79%)
  • Charlotte, NC Retail: $3.908/gal (+$0.278/gal, +7.00%)
  • Port St. Lucie, FL Retail: $3.694/gal (+$0.280/gal, +7.48%)
  • Oakland, CA Retail: $5.891/gal (+$0.780/gal, +13.06%)
  • SF Bay Area Region: $5.976/gal (+$0.765/gal, +12.63%)

Largest upward shift for this run: Oakland, CA Retail at $5.891/gal (+0.780/gal). Largest downward shift for this run: National Wholesale at $3.109/gal (+0.000/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-11 22:55:55]:
• Execution Context: Run type 'DAILY_BATCH' triggered by 'Daily Forecast Batch Execution (2026-09-11 22:55:55)'. Overall price pressure vector sits at ΔP=+0.02/gal.
• Weather & Convective Risk: SPC convective outlook and NOAA zip-code alerts for Tulsa (74101), Newark (19711), Cincinnati (45202), Carolinas (27834/28202), and Oakland (94612) map zero active severe tornado trips for this forecast run.
• Maritime & Geopolitical Exposure: Geopolitical risk score G=0.15. Counterfactual Strait of Hormuz blockade would inject +$0.109/gal (+2.88%) to current baseline.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-11 22:55:55.*
