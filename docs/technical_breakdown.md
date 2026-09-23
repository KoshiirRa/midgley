# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-23 22:50:17`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** Copper Erases Tariff Selloff as Shanghai Stockpiles Hit Three-Year Low - Crude Oil Prices Today | OilPrice.com  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Copper Erases Tariff Selloff as Shanghai Stockpiles Hit Three-Year Low - Crude Oil Prices Today | OilPrice.com
- **Active Ingested News Links:**
- [Copper Erases Tariff Selloff as Shanghai Stockpiles Hit Three-Year Low - Crude Oil Prices Today | OilPrice.com](https://news.google.com/rss/articles/CBMitgFBVV95cUxQUFhCVG9mR09LTHBySG5zUk9Nc2hZQ1BKQndvRnN3aEstbE9BREhSWi16Uy1oRHJwMEhuM2NLTXRST25PbnJ0OGpYanVPeUF4ZmZmcHJ5UC1pSUNNZXZ1VEFyTjhOTjU5bHFWZmJ4cWJzMDVNeDVBblF5UTVOaW9NT09yLWFEMzhjX2ZFdWZtZW42S3Mwb2RDdmZ1RVgwd21wRVh6UnB2YWZIaFQ0NFJrOGNYM2UxQdIBuwFBVV95cUxNZnR3V194VnFNdW1EX0FxMzVQOU9fdUplMmJ5Q0oyZnBRQVU4cy1SaFpqVTFQNjNNa0RVaEhjTzkzbFhKbXMzOVZWSGVwdF9vR3lxWXVhdElpUWprV2NMWjB0ZWg5S0djc0s0RDdhaVNXMHd2TDc2R1FWVEU4UllBU1MtM2ROOFlMUUowVUxPWE9YUS1lSFRiWDd0SkJabXdnS3lKcUk4N1FwODY4ZGtZUm5SdWJ6cDhPdkFz?oc=5) (Google News Energy Feed)
- [Discount on Western Canada Select Widens with Joliet Refinery Outage - EnergyNow](https://news.google.com/rss/articles/CBMinwFBVV95cUxOTS00VjJiZWtoNHlMSEhTQU03RDZvdjdUd00xZFIwLUZteE1DQVhPbTJRdEpaSDFLZUo3TlpZaE9ZOWVoWG8tMkFQcnltOWFBWFE0SWVidkxvcGdYR01INXhHS2hnc3NGc3JyN1ZOVlZtZXg3aXJtR2x3bDMxRTBuYm1KLWJ5bDdOMnFROVplTFpjUXNhM3lodUpwRy1oVXM?oc=5) (Google News Energy Feed)
- [Trump’s 100% tariff threat: Why India must stand firm on Russian crude and trade security - government.economictimes.indiatimes.com](https://news.google.com/rss/articles/CBMi4wFBVV95cUxOeF9IeU9BSjZTb252dDNvTk1mX3czQjhvNWRpTV9BTGNBbUxlakliczV4cnI3S1NEOHhwcHM1V1JjdGcwUEQ2alB5dnNESkoySnRaUUhXZzJwY1JaMlZOSmcxTlp3X3hoVzZiNjVXaVNMTDFoNkNtWFJDcEU5TEV1cFRCOWc5WnMzVkcySlU3ODBrWnJ4THYyX1E3dHBaWDVaT1Jtd3RLU05FOWhkQ2pRNUtfcWtzdG45RnVhZWdISmpQUElSYkMwVVQ5b2RhR1pNNHBzODlYZjBpLXJZSmxrV0xSQdIB6AFBVV95cUxOcVNQa040dy1TWmQ2X3UycGJ1N2RlVFR4c0xoS2lmX1BlTTg5RVRrWHZhMmNsUGx0VGl2UW50R25mZGZfNTJ5ZzFUYmdTbldfVFFVaEZYSTkxUGswQzVSajhMMEN0Ri0zSjg3ZUN0aGFQRnUyLUZVeGNNX3FvTG1NTXhKU3UxdkxhQ200YkZDbmo4ZkN2MjlIcWpmSmExYmVOMnpoSlRUZnNOM1BtNWN1clBPaThrekpfMERJbmRkRWxIS1FLZnB0ZEhsc2pNRElFRHRiSzk0SllMNE9CUTBzYnBXMlQweXg4?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.00`
- **Price Pressure Shock ($\Delta P$):** `+0.75`
- **Geopolitical Risk Score ($G$):** `0.00`
- **Demand Sentiment Score ($D$):** `0.85`
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


Numeric Retention Schedule for This Run ($M_0 = 0.0000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.0000$
- **Day 1 Decayed Shock**: $M_1 = 0.0000 \times 0.87055 = 0.0000$
- **Day 2 Decayed Shock**: $M_2 = 0.0000 \times (0.87055)^2 = 0.0000$
- **Day 3 Decayed Shock**: $M_3 = 0.0000 \times (0.87055)^3 = 0.0000$
- **Day 4 Decayed Shock**: $M_4 = 0.0000 \times (0.87055)^4 = 0.0000$
- **Day 5 (Target Horizon)**: $M_5 = 0.0000 \times 0.50000 = 0.0000$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (-\$0.200) = \$3.280\text{/gal}$ (Delta: -\$0.200/gal, -6.28\%)
- **Tulsa, OK Retail**: $P = \$3.994 + (+\$0.502) = \$7.685\text{/gal}$ (Delta: +\$0.502/gal, +12.57\%)
- **Newark, DE Retail**: $P = \$4.343 + (-\$0.052) = \$4.322\text{/gal}$ (Delta: -\$0.052/gal, -1.19\%)
- **Cincinnati, OH/KY**: $P = \$4.419 + (-\$0.071) = \$4.382\text{/gal}$ (Delta: -\$0.071/gal, -1.62\%)
- **Greenville, NC Retail**: $P = \$4.115 + (-\$0.064) = \$4.083\text{/gal}$ (Delta: -\$0.064/gal, -1.55\%)
- **Charlotte, NC Retail**: $P = \$4.170 + (-\$0.059) = \$4.156\text{/gal}$ (Delta: -\$0.059/gal, -1.41\%)
- **Port St. Lucie, FL Retail**: $P = \$4.309 + (-\$0.073) = \$4.266\text{/gal}$ (Delta: -\$0.073/gal, -1.70\%)
- **Oakland, CA Retail**: $P = \$6.244 + (+\$0.663) = \$6.227\text{/gal}$ (Delta: +\$0.663/gal, +10.63\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.357 + (+\$0.676) = \$6.340\text{/gal}$ (Delta: +\$0.676/gal, +10.64\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-23 22:50:17]: Elevated upward price shock (+$0.75/gal) observed across wholesale futures. Event trigger 'Copper Erases Tariff Selloff as Shanghai Stockpiles Hit Three-Year Low - Crude Oil Prices Today | OilPrice.com' drove supply disruption to S=0.00 and geopolitical risk to G=0.00. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.0000 and Day-5 horizon retention M₅=0.0000.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-23 22:50:17 (Mode: INTRADAY_REVISION), primary event trigger 'Copper Erases Tariff Selloff as Shanghai Stockpiles Hit Three-Year Low - Crude Oil Prices Today | OilPrice.com' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.00, Price Pressure ΔP=+0.75, Geopolitical Risk G=0.00. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.0000
  - Day 1: M₁ = 0.0000
  - Day 5: M₅ = 0.0000 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.280/gal ($-0.200/gal, -6.28%)
  • Tulsa, OK Retail: $7.685/gal (+$0.502/gal, +12.57%)
  • Newark, DE Retail: $4.322/gal ($-0.052/gal, -1.19%)
  • Cincinnati, OH/KY: $4.382/gal ($-0.071/gal, -1.62%)
  • Greenville, NC Retail: $4.083/gal ($-0.064/gal, -1.55%)
  • Charlotte, NC Retail: $4.156/gal ($-0.059/gal, -1.41%)
  • Port St. Lucie, FL Retail: $4.266/gal ($-0.073/gal, -1.70%)
  • Oakland, CA Retail: $6.227/gal (+$0.663/gal, +10.63%)
  • SF Bay Area Region: $6.340/gal (+$0.676/gal, +10.64%)

Largest upward shift for this run: SF Bay Area Region at $6.340/gal (+0.676/gal). Largest downward shift for this run: National Wholesale at $3.280/gal (-0.200/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-23 22:50:17]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'Copper Erases Tariff Selloff as Shanghai Stockpiles Hit Three-Year Low - Crude Oil Prices Today | OilPrice.com'. Overall price pressure vector sits at ΔP=+0.75/gal.
• Weather & Convective Risk: SPC convective outlook and NOAA zip-code alerts for Tulsa (74101), Newark (19711), Cincinnati (45202), Carolinas (27834/28202), and Oakland (94612) map zero active severe tornado trips for this forecast run.
• Maritime & Geopolitical Exposure: Geopolitical risk score G=0.00. Counterfactual Strait of Hormuz blockade would inject +$0.109/gal (+2.88%) to current baseline.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-23 22:50:17.*
