# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-08-28 19:14:21`  
**Run Mode:** `DAILY_BATCH`  
**Primary Event Trigger:** Scheduled Daily Batch Refresh (02:00 AM Central)  

---

## 1. Execution Audit & Trigger Headline Context

- **Headline Trigger:** Scheduled Daily Batch Refresh (02:00 AM Central)
- **Active Ingested News Links:**
- [NYMEX RBOB Futures & WTI Crude Spot Energy Commodity Benchmark Refresh](https://www.cmegroup.com/markets/energy/refined-products/rbob-gasoline.html) (CME_Group / NYMEX)
- [NOAA National Weather Service Multi-Basin Severe Weather & Freeze Warning Ingestion](https://api.weather.gov) (NOAA_NWS_API)
- [Executive Social Media Feed & OPEC Weekend Price Gap Analysis](https://finlight.me) (Finlight_v2_API)


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

- **National Wholesale**: $P = \$3.384 + (\$0.000) = \$3.153/\text{gal}$ (Delta: $\$0.000/\text{gal}$, $0.00\%)
- **Tulsa, OK Retail**: $P = \$3.890 + (+\$0.098) = \$3.747/\text{gal}$ (Delta: $+\$0.098/\text{gal}$, $+2.53\%)
- **Newark, DE Retail**: $P = \$3.943 + (+\$0.099) = \$3.814/\text{gal}$ (Delta: $+\$0.099/\text{gal}$, $+2.51\%)
- **Cincinnati, OH/KY**: $P = \$3.903 + (+\$0.101) = \$3.778/\text{gal}$ (Delta: $+\$0.101/\text{gal}$, $+2.58\%)
- **Greenville, NC Retail**: $P = \$3.250 + (+\$0.122) = \$3.136/\text{gal}$ (Delta: $+\$0.122/\text{gal}$, $+3.75\%)
- **Charlotte, NC Retail**: $P = \$3.280 + (+\$0.121) = \$3.169/\text{gal}$ (Delta: $+\$0.121/\text{gal}$, $+3.68\%)
- **Oakland, CA Retail**: $P = \$4.950 + (\$-0.421) = \$4.778/\text{gal}$ (Delta: $\$-0.421/\text{gal}$, $-8.52\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$5.050 + (\$-0.425) = \$4.874/\text{gal}$ (Delta: $\$-0.425/\text{gal}$, $-8.42\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*


---

## 5. NOAA SPC-Style Technical Discussion & Narrative Synopsis

### Executive Forecast Summary
SUMMARY: Baseline market conditions prevail across national wholesale RBOB futures and regional retail pump prices. Minimal exogenous supply shocks (S=0.10) and moderate geopolitical risk (G=0.15) yield a neutral price pressure vector (ΔP=+0.02). Standard macroeconomic futures momentum and localized rack margins remain the primary drivers over the 5-day evaluation horizon.

### Technical Discussion & Market Dynamics
TECHNICAL DISCUSSION & MARKET DYNAMICS:

1. Wholesale Baseline & Memory Decay Integration:
Standardized Ridge regression (α=10.0) integrates macro futures momentum with fused qualitative event memory vectors. Initial shock score M₀=0.10 decays exponentially via decay constant λ = ln(2)/5.0 = 0.13863 day⁻¹, yielding a daily retention factor γ ≈ 0.87055. By Day 5, exactly 50.0% of the initial event pressure (0.0500) remains active in the estimator state space.

2. Regional Metro Calibration Breakdown:
• Tulsa Metro (Cushing WTI Hub): Calibrated to WTI delivery logistics and West Tulsa refinery rack margins.
• Newark Metro (PADD 1B Central Atlantic): Calibrated to PBF Delaware City refinery (180k bpd) and C&D Canal detour alerts.
• Cincinnati Tri-State (OH/KY): Models Ohio/Kentucky dual-state fuel tax differential ($0.125/gal gap) and Catlettsburg KY refinery logistics.
• Carolinas (Greenville & Charlotte, PADD 1C): Models Colonial Line 1/2 breakout hubs at Selma NC and Paw Creek terminal infrastructure.
• Oakland & SF Bay Area (PADD 5 West Coast): Incorporates statutory California CARB excise tax, Cap-and-Trade carbon fees, and LCFS compliance overhead ($0.953/gal statutory total).

### Forecast Uncertainty & Counterfactual Catalysts
FORECAST UNCERTAINTY & CATALYST SCENARIOS:

Key downside/upside tail risks evaluated for this forecast window include:
• NOAA Convective & Severe Weather Alerts: Regional refinery or terminal convective outages (Tornado/High Wind risk mapped via SPC/NWS).
• Maritime Chokepoint Disruption: Escalations in Strait of Hormuz (21M bpd flow) or Suez Canal detours (+2.88% to +5.32% counterfactual shock).
• Executive Social Feed & Weekend Gaps: Off-market social posts published while commodity exchanges are closed produce 1.42x open gap volatility.

---
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-08-28 19:14:21.*
