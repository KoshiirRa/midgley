## Summary
Resolves #27.

Restructures the Midgley public web dashboard (`docs/`) to improve navigation, route hierarchy, and multi-locale scaling:

### Key Highlights & Changes
1. **General Overview Landing Page (`/` / `docs/index.html`)**:
   - Central Midgley overview landing page featuring active forecast summary cards for **National Wholesale RBOB** ($3.184 → $3.077/gal) and **Tulsa Metro Retail Gas** ($3.890 → $3.780/gal).
   - Includes historical model accuracy improvement charts (MAE & Directional Hit Rate) and model iteration timeline (v1.0 to v1.4 Finlight-LLM).
   - Core multi-agent system architecture pillars breakdown.

2. **National Wholesale RBOB Page (`/national` / `docs/national.html` & `docs/national/index.html`)**:
   - Dedicated commodity futures page featuring spot NYMEX RBOB predictions, out-of-time error metrics (MAE $0.1069/gal, RMSE $0.1490/gal, MAPE 4.76%, Hit Rate 60.79%), global maritime shock scenarios (Strait of Hormuz 21M bpd blockade & Red Sea / Suez rerouting), and quantitative model feature driver breakdowns.
   - Accessible via **`National Wholesale`** in the top navigation header.

3. **Tulsa Metro Retail Gas Page (`/tulsa` / `docs/tulsa.html` & `docs/tulsa/index.html`)**:
   - Dedicated localized retail pump page calibrated to live pump prices ($3.890/gal), Cushing WTI delivery hub proximity (50 miles), West Tulsa HF Sinclair refinery (125k bpd), regional EF-3 tornado/freeze shock scenarios, and dynamic rack margins ($0.706/gal).
   - Accessible via a future-proof **`Metro Areas`** dropdown menu in the top navigation bar.

4. **Educational Math Guide (`/math` / `docs/math.html`)**:
   - Preserved as a separate educational reference detailing equations and vector spaces across all 9 feature layers rendered via KaTeX.

5. **Updated Documentation & Workflows**:
   - Updated `AGENTS.md` (Agent Specification #7: Dashboard Generator Agent).
   - Updated `README.md`, `docs/API.md`, `docs/ARCHITECTURE.md`.
   - Updated `.github/workflows/gas_price_forecast.yml` & `weekly_model_review.yml` `file_pattern` to `"README.md docs/ data/prediction_history.csv"`.
