## Feature Request: Cincinnati, OH / Northern KY Metro Area Expansion & Dual-State Cross-River Display

### Summary
Expand Midgley's regional forecasting capabilities by adding **Cincinnati, OH & Northern Kentucky (Tri-State Metro Area, PADD 2 Midwest)** as a dedicated regional model and public dashboard locale.

### Regional Infrastructure & Dual-State Market Dynamics
1. **Dual-State State Fuel Tax Differential**: Ohio state motor fuel tax ($0.385/gal) vs Kentucky state motor fuel tax ($0.260/gal) creates a persistent **~$0.125/gal cross-river retail price gap** ($3.450/gal OH base vs $3.325/gal KY base).
2. **PADD 2 Refining Hub**: Marathon Petroleum Catlettsburg KY Refinery (291,000 bpd capacity) serves as the primary regional refining benchmark for the Ohio Valley.
3. **Mississippi & Lower Ohio River Downriver Logistics**: Refined fuel barges moving north from Gulf Coast refining hubs enter the Ohio River at the **Cairo, IL confluence** (Mile 981 on Lower Mississippi / Mile 0 on Ohio River). Autumn low-water drought crises (e.g., Memphis/Cairo gage drops) enforce -40% barge payload draft limits, surging spot freight rates +300% and expanding Cincinnati rack margins (+14.5¢/gal).
4. **Ohio River Lock Logistics**: Winter ice jams and lock maintenance near Cincinnati (Markland Locks & Dam) choke barge throughput and force reliance on higher-cost rail transport.
5. **Cross-River Consumer Arbitrage**: Commuters frequently cross the Ohio River bridges into Northern Kentucky to save ~$0.125/gal on retail fuel.

### Implementation Summary
- [x] `src/cincinnati_regional.py`: Cincinnati dual-state market data ingestion, Catlettsburg crack spread calculation, river logistics events, and Tri-State NOAA weather dataset.
- [x] `cincinnati_main.py`: Standalone 6-step regional forecasting pipeline with real-time shock scenario simulations.
- [x] `build_cincinnati_notebook.py` & `notebooks/cincinnati_gas_price_llm_forecasting.ipynb`.
- [x] `src/prediction_logger.py`: Add `Cincinnati_OH` and `Cincinnati_KY` out-of-time forecast tracking & backfill support.
- [x] `src/dashboard_generator.py`: Generate `docs/cincinnati.html` and `docs/cincinnati/index.html` with Cross-River Dual-State Fuel Display, update navbar dropdown & multi-locale overview cards on `docs/index.html`.
- [x] `run_all.py`: Updated master orchestrator to include Cincinnati model execution.
- [x] Documentation updates (`README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/math.html`).
