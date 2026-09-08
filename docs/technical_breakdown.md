# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-09-08 10:30:09`  
**Run Mode:** `INTRADAY_REVISION`  
**Primary Event Trigger:** Oil Price Seen At US$95-US$110 On Sustained Hormuz Impairment, Refinery Outage And Inventory Draws - BernamaBiz  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Oil Price Seen At US$95-US$110 On Sustained Hormuz Impairment, Refinery Outage And Inventory Draws - BernamaBiz
- **Active Ingested News Links:**
- [Oil Price Seen At US$95-US$110 On Sustained Hormuz Impairment, Refinery Outage And Inventory Draws - BernamaBiz](https://news.google.com/rss/articles/CBMiWkFVX3lxTE5OallDX1JqMFZJaUdzTmhxdUtKQWR5cHFEQXBFSUFxSWowNXVNYUFWMDVEVjJmTjdxdXItQy1RaUlMWEtUV3R4cFdUZVBDbHhiaTBEUWgzbDk1UQ?oc=5) (Google News Energy Feed)
- [Oil surges above $97; Canada to double tariffs on US goods from today - DhanamOnline](https://news.google.com/rss/articles/CBMitwFBVV95cUxQY2VoaTJEWi11RUdsSFVfUmJVMGJ2Rnc5bnhQQ2t1SjEtUWp0YWtrVW1QT2dHTDF1Mjc4Ynh1blJHaFdpWnp4d1B2YTZwVEdjM0dWWWpydF9KX1hkVlJ4bV9DMndJLVRHLWp5TnFGQWVibVZHRDZlaUJ6THpvdnZVQUFwUlhEWEowajBrRU9wcVRKTE5ROGg1bzZjV0RpdlZoSDRfcGdyUHRJUkNmZkJmd3dyZlQ1UHPSAcQBQVVfeXFMUFA5dXc3MlhzMUFjdVc2SkVlOEtDN3JzTFF2MjFoWHpJYVNkUHluVmhJQTRQR041T1pSWFdyN1dWcG0xamlXNUhsb0JST1lnOVhWZ0RFUUJfQ0R0aHhXNzVlRWZxeEl5bzdsa3gwdkxyLTJza2tabU9RNE9uQWMydXNsNFNzZ0VOblJfVHdoekJHbUg0UTNoeEFpRkpEVG9wTE1nV3dnSUFOMXJKSm96UGl0bnVkWXNHNkRVUXlaaHozRTJmdg?oc=5) (Google News Energy Feed)
- [Russia ready to supply ‘as much oil as India needs’, envoy slams 'pressure tactics' amid US' 100% tariff threats | India News - Hindustan Times](https://news.google.com/rss/articles/CBMi_AFBVV95cUxOWml5Z25XNGRpcEtJWnQwRVlWRXduNkpkMVRVYTl6YkJWeG9sWWd2X29RTlFzVWk1dk5ZWmRIR25DSmNfMDhfMDlKQzYxZTE5T1lMcUphcHd5bllVNE1RaFlIdU1ZWU1uRTdnMzRFU1BKdmo0b193TXZPM3RRSDBaWE1VOVQ4QVh6YWlQeGVxUTZpZWt5QXp1YkZ4TGhpWl9SNlkwTzYwa3VFTmxlUGh5akpDS1JzSkg2TEhvbVFKQ09zYjJiWjNkei1qd3hYQlc5MVhVcV9EUlpTSThkZDNMNTR5WjI4TDdlTi0wWFJOV3RGVWNBRGF6WmItSy3SAYICQVVfeXFMT013YXF6b1V4c1NpRDlHQWJiRXN2VEQxZm9QZ2laTl8zbFl1OVBKMzh4TGI0X00tOVcwcTJlcndwNmRVSWtmRWh6bHAtZDJXcTZBQ2h6cmJZQmdoWC1jZUdvTTBLZkdiMzFQMXdRNkk5dGdraEg2MmNWTHYxUE44UjJmeGU4Rk8zeWwwVHdwUzZjeW1UQUVrVkpBNkctcGF4T0E4UEdDTHgwYi1DU2JKZFYyTmQ0RlJxYmJzUVY1X0NiUUtHLWZjNnpWemZtSUVpeHc5aEJvMk0tOFdCNUUtb3VDdFRwOTFVbWprSDVCQTgyd2FGY3YtVi1DLWRtUEtXRUpR?oc=5) (Google News Energy Feed)


---

## 2. Ingested Factor Score Vector (Exact Run Values)

- **Supply Disruption Score ($S$):** `0.50`
- **Price Pressure Shock ($\Delta P$):** `+0.18`
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


Numeric Retention Schedule for This Run ($M_0 = 0.5000$):
- **Day 0 (Initial Shock Target)**: $M_0 = 0.5000$
- **Day 1 Decayed Shock**: $M_1 = 0.5000 \times 0.87055 = 0.4353$
- **Day 2 Decayed Shock**: $M_2 = 0.5000 \times (0.87055)^2 = 0.3789$
- **Day 3 Decayed Shock**: $M_3 = 0.5000 \times (0.87055)^3 = 0.3299$
- **Day 4 Decayed Shock**: $M_4 = 0.5000 \times (0.87055)^4 = 0.2872$
- **Day 5 (Target Horizon)**: $M_5 = 0.5000 \times 0.50000 = 0.2500$ (50.0% residual event memory)

---

## 4. Regional Metro Calibration Equations (Substituted Run Values)

- **National Wholesale**: $P = \$3.184 + (-\$0.207) = \$3.207\text{/gal}$ (Delta: -\$0.207/gal, -6.49\%)
- **Tulsa, OK Retail**: $P = \$3.599 + (-\$0.278) = \$3.503\text{/gal}$ (Delta: -\$0.278/gal, -7.73\%)
- **Newark, DE Retail**: $P = \$3.220 + (-\$0.269) = \$3.142\text{/gal}$ (Delta: -\$0.269/gal, -8.35\%)
- **Cincinnati, OH/KY**: $P = \$3.883 + (-\$0.284) = \$3.799\text{/gal}$ (Delta: -\$0.284/gal, -7.31\%)
- **Greenville, NC Retail**: $P = \$3.544 + (-\$0.277) = \$3.463\text{/gal}$ (Delta: -\$0.277/gal, -7.80\%)
- **Charlotte, NC Retail**: $P = \$3.850 + (-\$0.284) = \$3.760\text{/gal}$ (Delta: -\$0.284/gal, -7.37\%)
- **Port St. Lucie, FL Retail**: $P = \$3.913 + (-\$0.285) = \$3.819\text{/gal}$ (Delta: -\$0.285/gal, -7.29\%)
- **Oakland, CA Retail**: $P = \$5.891 + (+\$0.289) = \$5.738\text{/gal}$ (Delta: +\$0.289/gal, +4.90\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$6.004 + (+\$0.299) = \$5.848\text{/gal}$ (Delta: +\$0.299/gal, +4.98\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **ULSD Distillate Crack Engine (WIP)**: $P_{\text{ULSD}} = \$2.850\text{/gal}$, Distillate Crack Spread = $\$0.742\text{/gal}$, 3-2-1 Crack Margin = $\$0.685\text{/gal}$ *(Experimental Work-In-Progress undergoing multi-week feedback loop empirical evaluation)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY FOR RUN [2026-09-08 10:30:09]: Elevated upward price shock (+$0.18/gal) observed across wholesale futures. Event trigger 'Oil Price Seen At US$95-US$110 On Sustained Hormuz Impairment, Refinery Outage And Inventory Draws - BernamaBiz' drove supply disruption to S=0.50 and geopolitical risk to G=0.00. Exponential decay (t½=5.0d) models Day-1 retained shock M₁=0.4353 and Day-5 horizon retention M₅=0.2500.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS FOR THIS RUN:

1. Qualitative Shock Integration & Decay Dynamics:
During execution 2026-09-08 10:30:09 (Mode: INTRADAY_REVISION), primary event trigger 'Oil Price Seen At US$95-US$110 On Sustained Hormuz Impairment, Refinery Outage And Inventory Draws - BernamaBiz' was processed by the extraction engine. Inspiration stream ingested 3 headline bulletins from sources (Google News Energy Feed). Ingested factor vector: Supply Disruption S=0.50, Price Pressure ΔP=+0.18, Geopolitical Risk G=0.00. Exponential decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹ dictates daily retention factor γ ≈ 0.87055. Initial shock retention schedule for this specific execution:
  - Day 0: M₀ = 0.5000
  - Day 1: M₁ = 0.4353
  - Day 5: M₅ = 0.2500 (50.0% residual memory acting on Day-5 target horizon).

2. Substituted Regional Metro Price Calibrations:
The base commodity forecast was calibrated across all 8 modeled metro locales for this run:
  • National Wholesale: $3.207/gal ($-0.207/gal, -6.49%)
  • Tulsa, OK Retail: $3.503/gal ($-0.278/gal, -7.73%)
  • Newark, DE Retail: $3.142/gal ($-0.269/gal, -8.35%)
  • Cincinnati, OH/KY: $3.799/gal ($-0.284/gal, -7.31%)
  • Greenville, NC Retail: $3.463/gal ($-0.277/gal, -7.80%)
  • Charlotte, NC Retail: $3.760/gal ($-0.284/gal, -7.37%)
  • Port St. Lucie, FL Retail: $3.819/gal ($-0.285/gal, -7.29%)
  • Oakland, CA Retail: $5.738/gal (+$0.289/gal, +4.90%)
  • SF Bay Area Region: $5.848/gal (+$0.299/gal, +4.98%)

Largest upward shift for this run: SF Bay Area Region at $5.848/gal (+0.299/gal). Largest downward shift for this run: Port St. Lucie, FL Retail at $3.819/gal (-0.285/gal). California locations (Oakland & SF Bay Area) incorporate statutory $0.953/gal CARB excise, Cap-and-Trade, and LCFS fee overhead on top of the base commodity calibration.

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS FOR THIS RUN:

Evaluated tail-risk catalysts specific to execution [2026-09-08 10:30:09]:
• Execution Context: Run type 'INTRADAY_REVISION' triggered by 'Oil Price Seen At US$95-US$110 On Sustained Hormuz Impairment, Refinery Outage And Inventory Draws - BernamaBiz'. Overall price pressure vector sits at ΔP=+0.18/gal.
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
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-09-08 10:30:09.*
