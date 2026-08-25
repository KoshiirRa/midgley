## Feature Request: Oakland, CA Metro Area Expansion (PADD 5 West Coast) & CARB Regulatory Cost Display

### Summary
Expand Midgley's regional forecasting capabilities by adding **Oakland, CA & the San Francisco Bay Area (PADD 5 West Coast)** as a dedicated regional model and public dashboard locale. With a baseline pump price anchor of **~$4.950/gal** (compared to $3.890 in Tulsa, $3.350 in Newark, and $3.450 in Cincinnati), Oakland represents the highest-cost, most highly-regulated regional market in the nation, providing a stark baseline comparison ("scare factor") for users across all other metropolitan areas.

### Regional Infrastructure, PADD 5 Isolation & Regulatory Cost Drivers
1. **Unprecedented Tax & Environmental Regulatory Burden**:
   - **California Excise Tax**: 63.4¢/gal (adjusted July 1, 2026).
   - **Cap-and-Trade (Cap-and-Invest) Program**: ~25.0¢/gal carbon allowance cost.
   - **Low Carbon Fuel Standard (LCFS)**: ~18.5¢/gal compliance credit deficit cost.
   - **State/Local Sales Taxes & Underground Storage Tank Fee**: ~15.0¢/gal.
   - **Federal Excise Tax**: 18.4¢/gal.
   - **Total Regulatory & Tax Burden**: **~95.3¢/gal** embedded into every gallon at Oakland pumps (vs $0.190 in OK or $0.385 in OH).
2. **PADD 5 "Refining Island" Geographic Isolation**:
   - Zero interstate refined product pipelines cross the Rocky Mountains or Sierra Nevada into California.
   - San Francisco Bay Area refined product deficits cannot be backfilled from Gulf Coast (PADD 3) or Midwest (PADD 2) pipeline infrastructure; shortfalls must be imported via ocean oil tankers from Asia/Middle East (3+ week transit) or Alaska North Slope (ANS) crude maritime routes.
3. **SF Bay Area Refining Hub & Local Infrastructure**:
   - **Chevron Richmond Refinery** (Contra Costa County, 245,000 bpd capacity): Directly adjacent to Oakland; primary regional producer of CARB Reformulated Gasoline (CaRFG).
   - **PBF Energy Martinez Refinery** (156,000 bpd capacity) & **Valero Benicia Refinery** (145,000 bpd capacity).
   - **Marathon Martinez Facility**: Converted to renewable diesel, contracting total regional crude refining capacity.
4. **Distribution Logistics**:
   - **Kinder Morgan SFPP (Santa Fe Pacific Pipeline) System**: Originates at Richmond/Concord terminals, distributing fuel across Northern California and Nevada (Reno/Sparks).
5. **CARB Reformulated Gasoline (CaRFG) Transition**:
   - Seasonal transition to CaRFG summer blend (effective April 1) adds +15¢–25¢/gal refining premium and surges volatility during spring refinery maintenance turnarounds.
6. **Localized Weather & Infrastructure Shocks**:
   - Atmospheric river winter storms & refinery grid disruptions (PG&E PSPS power outages).
   - NOAA Alerts for Alameda County (CAZ508) and Contra Costa County (CAZ511).

### Implementation Plan
- [ ] `src/oakland_regional.py`: Oakland market data ingestion ($4.950/gal anchor), Richmond refinery crack spread calculation, CARB regulatory cost layer, SF Bay regional events, and NOAA CAZ508 weather dataset.
- [ ] `oakland_main.py`: Standalone 6-step regional forecasting pipeline with Oakland shock scenario simulations (Chevron Richmond flaring outage, CaRFG summer blend switch, atmospheric river grid failure).
- [ ] `build_oakland_notebook.py` & `notebooks/oakland_gas_price_llm_forecasting.ipynb`: Programmatic notebook generator and interactive Jupyter notebook.
- [ ] `src/prediction_logger.py`: Add `Oakland_CA` out-of-time forecast tracking & backfill support.
- [ ] `src/dashboard_generator.py`: Generate `docs/oakland.html` and `docs/oakland/index.html` with CARB Regulatory Breakdown card, update navbar dropdown & multi-locale overview cards on `docs/index.html`.
- [ ] `run_all.py`: Update master orchestrator to execute Oakland model.
- [ ] `tests/test_oakland_regional.py`: Comprehensive test suite for Oakland module and execution pipeline.
- [ ] Documentation updates (`README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/math.html`).
