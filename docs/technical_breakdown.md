# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-15 19:35:35`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** Aramco Refinery Fires via Satellite: Saudi Export Lifeline Under Strain After a Month of Attacks - Energy News Beat  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Aramco Refinery Fires via Satellite: Saudi Export Lifeline Under Strain After a Month of Attacks - Energy News Beat
- **Active Ingested News Links:**
- [Aramco Refinery Fires via Satellite: Saudi Export Lifeline Under Strain After a Month of Attacks - Energy News Beat](https://news.google.com/rss/articles/CBMi1wFBVV95cUxNNlBWX3VvM0tnb1laVWx3aXlxQ0pqMU9DUlNzZ2NXMmN5RS0yRUhpME1ET2NNeUd4a2k3cERBRUFfMGpzWkZCVzFxb1JWVGc0T3hyUzVnOUNyR29uaS1feFBMNlR5T1UxYkdCM1hRLXR6Z29ETExpSG9VX013SVR2clhmU1EzTVVjd2Y3V1BGTGtZcFpQNGVuY3NiVDctaW94N29Oc2dKaElkMTlJLTRkT1hoVVlLOU9OTnowQ2hsajRwT3FGbFhxYW5GTXJhaVdiSm1IZW0xNA?oc=5) (Google News Energy Feed)
- [India still under 100% tariff threat: What’s happening as US house takes up Russia sanctions bill - The Economic Times](https://news.google.com/rss/articles/CBMi8wFBVV95cUxPSWJqMzFzOU9acEFZVjg4U0p2Q00zRERlbEZBeUFRS01jNE5YOURSWEVsWG1rVGZSN0JnUk9vcFJ6UDZ6VlQzcWJGS2o5MkdNcmhrcHFKWlFxT2R6aEt5OHAyakQ5V2p6NVVCbmhqZHN0bXUwLWV1OFFJVV8xalNvNmRZcEMwUFJGQWsyNmE2ZzFsQjhWZnlUb3pLRGZDVnJfekNaWVlpdzc4eHZsbVpSVFFvOU92bTNPRjZuYjNybDVSSVE0RGhlOWZsSzlMenNmRzdSMzhIdlJ3Z0N0WGlCN3FNUEtDSkNFTmFkZDFWcERPMm_SAfMBQVVfeXFMT0liajMxczlPWnBBWVY4OFNKdkNNM0REZWxGQXlBUUtNYzROWDlEUlhFbFhta1RmUjdCZ1JPb3BSelA2elZUM3FiRktqOTJHTXJoa3BxSlpRcU9kemhLeThwMmpEOVdqejVVQm5oamRzdG11MC1ldThRSVVfMWpTbzZkWXBDMFBSRkFrMjZhNmcxbEI4VmZ5VG96S0RmQ1ZyX3pDWllZaXc3OHh2bG1aUlRRbzlPdm0zT0Y2bmIzcmw1UklRNERoZTlmbEs5THpzZkc3UjM4SHZSd2dDdFhpQjdxTVBLQ0pDRU5hZGQxVnBETzJv?oc=5) (Google News Energy Feed)
- [Russia-Iran Sanctions Bill Could Reach Trump’s Desk Within Days, Says Congressman - Radio Free Europe/Radio Liberty](https://news.google.com/rss/articles/CBMif0FVX3lxTE5GVFVBY3JiLThMcDZsbUd0d2R2d1duNno5b1cwUngxdXplRE9QLWg2a21mWHVGcFhGRzdXdl94eW9JcnJZNUsybEpqQTNiT2xUM01jREtadnNiZm02N3owcUpBazdGaERvbkZxQWU1V0YzWXNBOEc2NE81emVIY2vSAYIBQVVfeXFMTXlpNDFsOXhSelEzNTg5anZSalYwemk2OTRyVlk2M3BlNFhsSDBldFNKc0NWeHJCcnpnNUktQ3pTdHE3R1Uxb2JkVFUySG44WWlabGhoYW0xZWtnUFpMNmpjRnVZNHRxc1lMQzVqdG1XZ1BNb0wtbDhKRy1mR21McWtUQQ?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.90`
- **Price Pressure Shock ($\Delta P$):** `+0.95`
- **Geopolitical Risk Score ($G$):** `1.00`
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

- **National Wholesale**: $P = \$3.184 + (-\$0.039) = \$3.305\text{/gal}$ (Delta: -\$0.039/gal, -1.24\%)
- **Tulsa, OK Retail**: $P = \$3.948 + (+\$0.103) = \$3.951\text{/gal}$ (Delta: +\$0.103/gal, +2.61\%)
- **Newark, DE Retail**: $P = \$4.359 + (+\$0.074) = \$4.349\text{/gal}$ (Delta: +\$0.074/gal, +1.69\%)
- **Cincinnati, OH/KY**: $P = \$4.071 + (+\$0.069) = \$4.062\text{/gal}$ (Delta: +\$0.069/gal, +1.69\%)
- **Greenville, NC Retail**: $P = \$3.949 + (+\$0.067) = \$3.922\text{/gal}$ (Delta: +\$0.067/gal, +1.70\%)
- **Charlotte, NC Retail**: $P = \$4.129 + (+\$0.065) = \$4.111\text{/gal}$ (Delta: +\$0.065/gal, +1.58\%)
- **Port St. Lucie, FL Retail**: $P = \$4.120 + (+\$0.058) = \$4.093\text{/gal}$ (Delta: +\$0.058/gal, +1.40\%)
- **Oakland, CA Retail**: $P = \$6.069 + (+\$0.823) = \$6.108\text{/gal}$ (Delta: +\$0.823/gal, +13.56\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.170 + (+\$0.825) = \$6.209\text{/gal}$ (Delta: +\$0.825/gal, +13.37\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-15 19:35:35]: Elevated upward price shock (+$0.95/gal) observed across wholesale futures. Event trigger 'Aramco Refinery Fires via Satellite: Saudi Export Lifeline Under Strain After a Month of Attacks - Energy News Beat' drove supply disruption to S=0.90 and geopolitical risk to G=1.00. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.7835 and Day-5 horizon retention M₅=0.4500.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-15 19:35:35 (Mode: INTRADAY_REVISION), primary event trigger 'Aramco Refinery Fires via Satellite: Saudi Export Lifeline Under Strain After a Month of Attacks - Energy News Beat' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.90, Price Pressure ΔP=+0.95, Geopolitical Risk G=1.00. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.9000
  - Day 1: M₁ = 0.7835
  - Day 5: M₅ = 0.4500 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.305/gal ($-0.039/gal, -1.24%)
  • Tulsa, OK Retail: $3.951/gal (+$0.103/gal, +2.61%)
  • Newark, DE Retail: $4.349/gal (+$0.074/gal, +1.69%)
  • Cincinnati, OH/KY: $4.062/gal (+$0.069/gal, +1.69%)
  • Greenville, NC Retail: $3.922/gal (+$0.067/gal, +1.70%)
  • Charlotte, NC Retail: $4.111/gal (+$0.065/gal, +1.58%)
  • Port St. Lucie, FL Retail: $4.093/gal (+$0.058/gal, +1.40%)
  • Oakland, CA Retail: $6.108/gal (+$0.823/gal, +13.56%)
  • SF Bay Area Region: $6.209/gal (+$0.825/gal, +13.37%)

Largest upward shift for this run: SF Bay Area Region at $6.209/gal (+0.825/gal). Largest downward shift for this run: National Wholesale at $3.305/gal (-0.039/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-15 19:35:35]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'Aramco Refinery Fires via Satellite: Saudi Export Lifeline Under Strain After a Month of Attacks - Energy News Beat'. Overall price pressure vector sits at ΔP=+0.95/gal.
• Weather & Convective Risk: SPC convective outlook and NOAA zip-code alerts for Tulsa (74101), Newark (19711), Cincinnati (45202), Carolinas (27834/28202), and Oakland (94612) map zero active severe tornado trips for this forecast run.
• Maritime & Geopolitical Exposure: Geopolitical risk score G=1.00. Counterfactual Strait of Hormuz blockade would inject +$0.109/gal (+2.88%) to current baseline.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-15 19:35:35.*
