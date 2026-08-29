# Midgley LLM Energy Price Forecasting Engine — Technical Breakdown & Math Audit

**Log Timestamp:** `2026-08-28 19:03:38`  
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
- **Greenville, NC Retail**: $P = \$3.533 + (+\$0.112) = \$3.409/\text{gal}$ (Delta: $+\$0.112/\text{gal}$, $+3.17\%)
- **Charlotte, NC Retail**: $P = \$3.280 + (+\$0.121) = \$3.169/\text{gal}$ (Delta: $+\$0.121/\text{gal}$, $+3.68\%)
- **Oakland, CA Retail**: $P = \$5.647 + (+\$0.251) = \$5.451/\text{gal}$ (Delta: $+\$0.251/\text{gal}$, $+4.45\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*
- **SF Bay Area Region**: $P = \$5.647 + (+\$0.151) = \$5.451/\text{gal}$ (Delta: $+\$0.151/\text{gal}$, $+2.68\%) *(includes CA statutory CARB excise, Cap-and-Trade & LCFS fee overhead of $0.953/gal)*


---
*Report generated automatically by Midgley Dashboard Generator Engine at 2026-08-28 19:03:38.*
