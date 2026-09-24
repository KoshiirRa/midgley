"""
Ingest Midgley Forecasting Roadmap (Math Improvements and New Data Feeds)
into comprehensive GitHub Issues for milestone v0.8.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ISSUES = [
    {
        "id": "WS1",
        "title": "feat(modeling): Make asymmetric wholesale-to-retail pass-through ECM the core retail forecaster",
        "category": "Econometric Modeling & Core Forecasting",
        "milestone": "v0.8",
        "labels": ["enhancement", "modeling", "math", "econometrics"],
        "effort": "M (Medium)",
        "effort_days": "1-3 weeks",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["WS1", "Borenstein1997", "#402"],
        "body": """### Summary
Retail gasoline prices respond to wholesale price innovations with a lag of several weeks, and adjust faster to wholesale cost increases than to decreases ("rockets and feathers", Borenstein et al. 1997). Currently, regional metro models construct synthetic retail histories as `RBOB + current_margin`, which enforces artificial instant pass-through. Although `AsymmetricECM` exists in `src/asymmetric_ecm.py`, it is only imported by its unit test.

### Proposed Architecture & Formulation
1. **Long-Run Rack Margin Equilibrium**:
   $$r_t = c + \\beta\\, w_t + \\tau_t + z_t$$
   Where $r_t$ is metro retail price, $w_t$ is wholesale rack/hub benchmark, $\tau_t$ is per-gallon statutory tax, and $z_t$ is cointegrating margin disequilibrium.
2. **Direct $h$-Day Ahead Pass-Through Specification**:
   $$r_{t+h} - r_t = a_h + \\sum_{k=0}^{K}\\left(g^{+}_{h,k}\\,\\Delta w^{+}_{t-k} + g^{-}_{h,k}\\,\\Delta w^{-}_{t-k}\\right) + b_h\\, z_t + e_{t+h}$$
   Where $\\Delta w^+ = \\max(\\Delta w, 0)$ and $\\Delta w^- = \\min(\\Delta w, 0)$.
3. **Shared Forecasting Core**:
   Implement a shared estimator in `src/locations/` called across all regional metro pipelines (`newark`, `charlotte`, `greenville`, `port_st_lucie`, `tulsa`, `cincinnati`, `oakland`, `bayarea`), replacing duplicated custom forecast loops.
4. **Pilot Implementation**:
   Pilot on Newark, DE and Charlotte, NC first (clean hub price availability via FRED `DGASNYH` and `DGASUSGULF`, absence of Edgeworth price cycling).

### Acceptance Criteria
- [ ] `AsymmetricECM` integrated as the primary retail price estimator across regional metro modules.
- [ ] Multiplicative state sales tax scaling implemented for California (Oakland/Bay Area).
- [ ] Statistically outperforms naive persistence and legacy Ridge/XGBoost on 5-day MAE across walk-forward backtest origins ($\ge 6$ months, Diebold-Mariano HLN $p < 0.05$).
- [ ] Estimated coefficients satisfy economic plausibility ($\beta \\approx 1.0$, negative error correction $b_h < 0$, $g^+ > g^-$)."""
    },
    {
        "id": "WS2",
        "title": "fix(data-ingestion): Implement roll-adjusted RBOB futures returns and map metros to regional wholesale supply hubs",
        "category": "Data Ingestion & Commodity Feeds",
        "milestone": "v0.8",
        "labels": ["bug", "data-ingestion", "modeling", "math"],
        "effort": "S (Small)",
        "effort_days": "3-5 days",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["WS2", "CME191", "EIA-NYMEX", "#401", "#404"],
        "body": """### Summary
The continuous `RB=F` series from yfinance splices contracts across seasonal delivery months without roll adjustments. NYMEX RBOB specifications enforce maximum RVP of 13.5 psi in March, 7.4 psi from April to mid-September, and 13.5 psi in October (NYMEX Chapter 191). This causes severe artificial price jumps at late-February (+14.1%) and late-August (-10.2%) expiries, which distort model training. Furthermore, all metros are currently mapped to NY Harbor RBOB rather than their physical supply hubs.

### Proposed Implementation
1. **Contract-Specific Returns & Backward Ratio Adjustment**:
   $$\\text{ret}_t = \\frac{P^{(c)}_t}{P^{(c)}_{t-1}} - 1, \\qquad P^{\\text{adj}}_s = P^{\\text{old}}_s \\times \\frac{P^{\\text{new}}_{\\text{roll}}}{P^{\\text{old}}_{\\text{roll}}} \\quad \\forall s < t_{\\text{roll}}$$
   Roll on a fixed schedule (e.g. 5 trading days prior to expiry) using daily settlement prices for contracts 1 through 4 from EIA API / CME.
2. **Summer-Grade Seasonal Indicator**:
   Inject explicit summer RVP blend indicator ($I_{\\text{summer}}$) to distinguish seasonal grade transition spreads from exogenous economic shocks.
3. **Regional Wholesale Benchmark Mapping**:
   - Newark, DE $\\to$ NY Harbor Conventional Spot (`DGASNYH` via FRED)
   - Charlotte, Greenville, Port St. Lucie $\\to$ U.S. Gulf Coast Spot (`DGASUSGULF` via FRED)
   - Oakland & Bay Area $\\to$ Los Angeles CARBOB Spot (EIA API v2)
   - Tulsa $\\to$ Group 3 Mid-Continent (or fallback proxy)
   - Cincinnati $\\to$ Chicago CBOB / USGC blend

### Acceptance Criteria
- [ ] Continuous roll-adjusted RBOB series generated with zero artificial returns on contract expiry dates.
- [ ] Unit tests verifying synthetic multi-contract roll adjustment pass.
- [ ] Regional metros supply hubs configured to consume localized physical spot feeds."""
    },
    {
        "id": "WS3",
        "title": "feat(state-estimation): Build mixed-frequency Kalman filter metro 'true price' nowcast engine",
        "category": "State Estimation & Ground Truth",
        "milestone": "v0.8",
        "labels": ["enhancement", "modeling", "math", "data-ingestion"],
        "effort": "M (Medium)",
        "effort_days": "1-2 weeks",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["WS3", "DurbinKoopman2012", "#403", "#391", "#121"],
        "body": """### Summary
Evaluation accuracy is compromised by geographic and source mismatches between live forecast base prices (daily AAA metro readings) and recorded ground truth actuals (weekly state-level EIA survey releases or constant fallbacks), producing naive baseline errors of \$0.67–\$0.83/gal that mask true model performance.

### Proposed Architecture & Formulation
1. **State-Space Formulation**:
   Treat the true latent metro retail price as a hidden local-level state vector $x_t$:
   $$x_t = x_{t-1} + \\eta_t, \\qquad \\eta_t \\sim \\mathcal{N}(0, q)$$
   $$y^{(s)}_t = x_t + b_s + \\varepsilon^{(s)}_t, \\qquad \\varepsilon^{(s)}_t \\sim \\mathcal{N}(0, \\sigma^2_s), \\quad s \\in \\{\\text{AAA}, \\text{GasBuddy}, \\text{EIA}\\}$$
2. **Mixed-Frequency Maximum Likelihood Estimation**:
   Estimate observation noise variances $\\sigma^2_s$ and systematic source biases $b_s$ via Kalman filter on historical series, skipping update steps on non-reporting days.
3. **Bitemporal Nowcast & Ground Truth Separation**:
   - Point-in-time filtered state $\\hat{x}_{t|t}$ serves as the authoritative forecast baseline.
   - Fixed-interval smoothed state $\\hat{x}_{t|T}$ ($T > t+h$) serves as the matured evaluation ground truth.

### Acceptance Criteria
- [ ] Pure NumPy/SciPy (or statsmodels) local-level Kalman filter nowcast implementation in `src/metro_nowcast.py`.
- [ ] Each regional metro produces unified daily filtered nowcasts with source attribution logging.
- [ ] Holdout validation confirms nowcast residuals stay within estimated noise bounds against EIA weekly releases."""
    },
    {
        "id": "WS4",
        "title": "feat(nlp): Rework news-event features with semantic deduplication, rolling scaling, and local projections",
        "category": "NLP & Qualitative Shock Engineering",
        "milestone": "v0.8",
        "labels": ["enhancement", "nlp", "modeling", "econometrics"],
        "effort": "M (Medium)",
        "effort_days": "1-2 weeks",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["WS4", "Jorda2005", "Hawkes1971", "#361", "#355"],
        "body": """### Summary
National news events currently match all regional metros indiscriminately, same-day shock scores are summed and clipped to fixed arbitrary bounds (causing saturation during high news velocity), and exponential decay rates are hand-configured rather than estimated from empirical data.

### Proposed Implementation
1. **Semantic Headline Deduplication**:
   Cluster syndicated and duplicate news wire stories within rolling 24-48h windows using cosine similarity on sentence embeddings (`sentence-transformers` / MinHash).
2. **Explicit Regional Event Scoping**:
   National macroeconomic events affect retail prices via the wholesale price channel; reserve regional event features strictly for locale-specific refinery, pipeline, or weather disruptions.
3. **Rolling Baseline Shock Normalization**:
   $$I_{c,t} = \\log(1 + N_{c,t}) \\qquad \\text{or} \\qquad I_{c,t} = \\frac{N_{c,t} - \\bar{N}^{(90)}_{c,t}}{s^{(90)}_{c,t}}$$
4. **Local Projections Impulse Response Estimation (Jordà 2005)**:
   $$y_{t+h} - y_t = a_h + b_{h,c}\\, I_{c,t} + \\Gamma_h^\\top X_t + e_{t+h}, \\qquad h = 1, \\dots, 10$$
   Estimate non-parametric multi-horizon response curves with Newey-West HAC standard errors ($h-1$ lags) to identify empirical shock persistence without assuming exponential decay.

### Acceptance Criteria
- [ ] Event features maintain numerical headroom without clipping/saturation on historical high-volume news days.
- [ ] Local projection response functions estimated per event category with confidence bands.
- [ ] Outcome-stating prompts scrubbed from training datasets."""
    },
    {
        "id": "WS5",
        "title": "feat(microstructure): Implement Edgeworth price cycle diagnostics and restoration-hazard model (Cincinnati first)",
        "category": "Microstructure & Price Cycle Modeling",
        "milestone": "v0.8",
        "labels": ["enhancement", "modeling", "math", "econometrics"],
        "effort": "M (Medium)",
        "effort_days": "1-2 weeks",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["WS5", "MaskinTirole1988", "Noel2011", "FTC2010", "Doyle2010"],
        "body": """### Summary
Certain Midwestern retail gasoline markets (including Ohio/Cincinnati) exhibit Edgeworth price cycles characterized by rapid, coordinated price spikes ("restorations") followed by prolonged daily price undercutting. In cycling markets, cycle phase and margin compression dominate wholesale spot changes over 5-day horizons.

### Proposed Implementation
1. **Cycle Detection & Asymmetry Diagnostics**:
   Compute daily price change distribution metrics across all metros (fraction of negative daily changes, median daily decrease, change skewness, run lengths of consecutive declines).
2. **Two-Regime Markov-Switching Classification**:
   Fit Markov-switching regime models to classify metros into cycling vs non-cycling regimes.
3. **Restoration Hazard & Expected Horizon Change Model**:
   $$P_{t,h} = \\Pr(\\text{restoration in } (t, t+h] \\mid m_t, d_t) = \\operatorname{logit}^{-1}(a + b\\, m_t + c\\, d_t)$$
   $$\\mathbb{E}[r_{t+h} - r_t] \\approx P_{t,h}\\, J + (1 - P_{t,h})\\, \\delta\\, h$$
   Where $m_t$ is current retail-wholesale margin, $d_t$ is elapsed days since last restoration, $J$ is mean restoration jump size, and $\\delta$ is daily undercutting drift.

### Acceptance Criteria
- [ ] Metro cycle diagnostic report generated identifying cycling vs non-cycling markets.
- [ ] For Cincinnati, OH, restoration hazard model outperforms standard ECM on 5-day walk-forward MAE."""
    },
    {
        "id": "WS6",
        "title": "feat(volatility): Wholesale RBOB volatility distribution forecasting via GARCH and HAR-RV",
        "category": "Volatility & Quantitative Distribution Forecasting",
        "milestone": "v0.8",
        "labels": ["enhancement", "modeling", "math", "volatility"],
        "effort": "M (Medium)",
        "effort_days": "1-2 weeks",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["WS6", "Bollerslev1986", "Corsi2009", "#214", "#44", "#119"],
        "body": """### Summary
Front-month wholesale RBOB futures prices behave approximately as a random walk over 5-day horizons. Rather than attempting low-signal directional prediction, wholesale forecasting should model the predictive return distribution, volatility path, and tail risk.

### Proposed Formulation & Approach
1. **GARCH(1,1) / GJR-GARCH & HAR-RV Realized Volatility**:
   $$\\sigma^2_{t+1} = \\omega + \\alpha\\, \\varepsilon^2_t + \\beta\\, \\sigma^2_t$$
   $$RV_{t+1} = c + \\beta_d\\, RV_t + \\beta_w\\, RV^{(w)}_t + \\beta_m\\, RV^{(m)}_t$$
2. **Multi-Step Volatility Path & Fat-Tailed Predictive Distribution**:
   $$\\sigma_{t,h} = \\sqrt{\\sum_{i=1}^h \\sigma^2_{t+i}}, \\qquad R_{t \\to t+h} \\sim t_\\nu(0, \\sigma_{t,h})$$
3. **Data-Driven Volatility Regimes**:
   Replace heuristic volatility gate constants (`k=200`, `threshold=0.015`) with cross-validated parameter estimation or Markov-switching variance regimes.

### Acceptance Criteria
- [ ] GARCH(1,1) / HAR-RV volatility forecasting module integrated in `src/volatility_engine.py`.
- [ ] Probability Integral Transform (PIT) histograms demonstrate uniform calibration.
- [ ] Continuous Ranked Probability Score (CRPS) improves significantly over constant-volatility baseline."""
    },
    {
        "id": "WS7",
        "title": "feat(uncertainty): Calibrated prediction intervals and proper quantile generation via Adaptive Conformal Inference",
        "category": "Probabilistic Forecasting & Conformal Inference",
        "milestone": "v0.8",
        "labels": ["enhancement", "modeling", "math", "statistics"],
        "effort": "S (Small)",
        "effort_days": "3-5 days",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["WS7", "GibbsCandes2021", "GneitingRaftery2007", "#358", "#394", "#182"],
        "body": """### Summary
Prediction intervals currently rely on single 30-day pooled residual standard deviations across entire forecast batches, and Headline Arena submissions map 95% confidence intervals incorrectly as P10/P90 quantiles.

### Proposed Implementation
1. **Exact Horizon Quantile Generation**:
   Generate explicit $P_{10}, P_{50}, P_{90}$ (and $P_{2.5}, P_{97.5}$) quantiles from the parametric Student-$t$ predictive distribution or quantile regression.
2. **Adaptive Conformal Inference (Gibbs & Candès 2021)**:
   Dynamically adjust nonconformity thresholds based on recent realization coverage under distribution shift:
   $$\\alpha_{t+1} = \\alpha_t + \\gamma(\\alpha^* - \\text{miss}_t)$$
   Calibrated strictly on matured forecast horizons ($t \\le \\text{today} - h$).
3. **Headline Arena Quantile Mapping**:
   Emit true predictive distribution quantiles and directional probabilities $\\Pr(\\Delta P_{t \\to t+h} > d) = 1 - F_{t,h}(d)$.

### Acceptance Criteria
- [ ] Empirical coverage of 90% and 95% prediction intervals within $\\pm 3\\%$ of nominal across 90-day rolling windows.
- [ ] Headline Arena connector updated to submit verified P10/P50/P90 quantiles.
- [ ] Evaluated against Pinball loss and CRPS metrics."""
    },
    {
        "id": "WS8",
        "title": "feat(hierarchical): Partial pooling and MinT hierarchical reconciliation across metro, state, and national forecasts",
        "category": "Hierarchical Forecasting & Multi-Metro Calibration",
        "milestone": "v0.8",
        "labels": ["enhancement", "modeling", "math", "architecture"],
        "effort": "L (High)",
        "effort_days": "2-3 weeks",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["WS8", "Wickramasuriya2019", "JamesStein"],
        "body": """### Summary
Individual metro models are currently trained in isolation across largely duplicated directory packages (`src/locations/<metro>/`), leading to noisy parameter estimates in thin data regimes and aggregate incoherence between metro, state/PADD, and national levels.

### Proposed Architecture & Formulation
1. **Empirical Bayes / Mixed-Effects Partial Pooling**:
   Shrink per-metro pass-through coefficients toward national/regional cluster priors:
   $$\\theta_r = \\theta_0 + u_r, \\qquad u_r \\sim \\mathcal{N}(0, \\Omega)$$
2. **Minimum Trace (MinT) Optimal Reconciliation (Wickramasuriya et al. 2019)**:
   Reconcile base forecasts $\\hat{y}$ across geographic aggregation matrix $S$ (using volume weights) and error covariance $W$:
   $$\\tilde{y} = S\\left(S^\\top W^{-1} S\\right)^{-1} S^\\top W^{-1}\\, \\hat{y}$$
3. **Configuration-Driven Modular Pipeline**:
   Refactor 7 distinct metro packages into a single unified driver parameterized by `data/regional_metadata/` JSON profiles.

### Acceptance Criteria
- [ ] Reconciled forecasts satisfy exact hierarchical consistency across metro, state, and national levels.
- [ ] Pooled model matches or beats unpooled individual metro models on out-of-sample MAE.
- [ ] Unified regional driver operational across all existing metro targets."""
    },
    {
        "id": "WS9",
        "title": "feat(calendar): Integrate known-future regulatory and tax covariates into pass-through forecasts",
        "category": "Regulatory Compliance & Forward Calendar",
        "milestone": "v0.8",
        "labels": ["enhancement", "data-ingestion", "modeling", "regulations"],
        "effort": "S (Small)",
        "effort_days": "3-5 days",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["WS9", "MarionMuehlegger2011", "#141", "#383", "#366"],
        "body": """### Summary
Scheduled state fuel excise tax adjustments (e.g. California annual July 1 rate reset), EPA/CARB seasonal RVP blend transitions (May 1 terminal / June 1 retail / Sept 16 winter transition), and exchange settlement holidays are deterministic, known-in-advance inputs that provide high-certainty predictive signals over 5-day horizons.

### Proposed Implementation
1. **Forward Regulatory & Tax Event Registry**:
   Construct a structured forward calendar table (`data/known_future_events.json`) storing effective dates, affected metro regions, event type (excise tax change, RVP blend switch, holiday roll), and expected rate delta $\\Delta \\tau$.
2. **Direct Inclusion in Pass-Through ECM**:
   Inject known tax innovations $\\Delta \\tau_{t \\to t+h}$ directly into the long-run equilibrium relation:
   $$r_{t+h} = c + \\beta\\, w_{t+h} + \\tau_{t+h} + z_{t+h}$$
   And seasonal RVP transition indicators into short-run margin dynamics.

### Acceptance Criteria
- [ ] Forward calendar table integrated into feature pipeline for $t \\in [t, t+h]$.
- [ ] Forecast error step-reductions verified on historical tax rate resets and blend transition dates."""
    },
    {
        "id": "WS10",
        "title": "feat(evaluation): Build unified statistical evaluation harness, Model Confidence Set & feature admission gate",
        "category": "Evaluation Protocol & Validation Rigor",
        "milestone": "v0.8",
        "labels": ["enhancement", "testing", "statistics", "mlops"],
        "effort": "S (Small)",
        "effort_days": "3-5 days",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["WS10", "DieboldMariano1995", "PesaranTimmermann1992", "Hansen2005", "BenjaminiHochberg1995", "#362", "#188"],
        "body": """### Summary
Model evaluation lacks rigorous statistical hypothesis testing for directional hit rates (Pesaran-Timmermann), data-snooping controls for comparing many model variants (Model Confidence Set), false discovery rate corrections across multiple metro regions (Benjamini-Hochberg), and formal admission criteria for new feature families.

### Proposed Implementation
1. **Unified Evaluation Harness**:
   - Out-of-sample walk-forward evaluation using purged & embargoed cross-validation.
   - Standardized baselines: Naive persistence, Asymmetric ECM, EIA STEO benchmark, Kalshi market odds.
2. **Statistical Test Suite**:
   - **Pesaran-Timmermann Directional Test**: Assess directional hit rate against chance.
   - **Newey-West HAC Standard Errors**: Correction for overlapping $h$-day horizon forecast errors.
   - **Hansen's Model Confidence Set (MCS)**: Filter superior predictive models at $\\alpha = 0.10$.
   - **Benjamini-Hochberg FDR Control**: Correct for multi-region simultaneous testing.
3. **Formal Feature Admission Gate**:
   A candidate feature family is admitted to production only if it produces statistically significant CRPS/MAE gains surviving the Model Confidence Set.

### Acceptance Criteria
- [ ] Automated evaluation script `scripts/evaluate_forecast_rigor.py` executing all 4 statistical tests.
- [ ] Standardized evaluation scorecard exported as markdown and JSON reports."""
    },
    {
        "id": "WS11",
        "title": "feat(topology): Model supply network outage exposure via Knowledge Graph and NASA FIRMS active fire telemetry",
        "category": "Spatial Economics & Network Outage Topology",
        "milestone": "v0.8",
        "labels": ["enhancement", "data-ingestion", "modeling", "spatial"],
        "effort": "M (Medium)",
        "effort_days": "1-2 weeks",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["WS11", "FIRMS-VIIRS", "NetworkX", "#406", "#386"],
        "body": """### Summary
Refinery and pipeline outages currently propagate to metro forecasts through isotropic Euclidean distance decay (150-mile radius), which fails to account for actual pipeline connectivity, terminal origins, and physical supply chain dependencies.

### Proposed Implementation
1. **Supply Share Exposure Index**:
   Leverage the NetworkX knowledge graph (`src/knowledge_graph.py`) to map metro supply shares $s_{r,k}$ from specific refineries, pipeline mainlines, and waterborne marine terminals:
   $$X_{r,t} = \\sum_k s_{r,k}\\, \\frac{\\text{offline}_{k,t}}{\\text{capacity}_k}$$
2. **NASA FIRMS Active Fire Satellite Telemetry**:
   Ingest near-real-time VIIRS (375m) Fire Radiative Power (FRP) data from NOAA-20 and NOAA-21 within refinery bounding boxes to detect major flaring upsets and unscheduled unit shutdowns.
3. **Integration with Outage Registry**:
   Fuse FIRMS thermal anomaly scores with TCEQ EEERD, LDEQ EDMS, and USCG NRC incident feeds.

### Acceptance Criteria
- [ ] NASA FIRMS satellite connector implemented in `src/firms_satellite_feed.py`.
- [ ] Supply network outage exposure index $X_{r,t}$ computed per metro.
- [ ] Historical flaring events (e.g. Baytown, Galveston Bay) demonstrate elevated exposure scores for dependent metros."""
    }
]


def update_local_roadmap_json():
    summary_path = Path("master_roadmap_summary.json")
    evaluated_path = Path("evaluated_master_roadmap.json")

    summary_data = []
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

    evaluated_data = []
    if evaluated_path.exists():
        with open(evaluated_path, "r", encoding="utf-8") as f:
            evaluated_data = json.load(f)

    existing_titles = {item["title"] for item in summary_data}

    start_num = 460
    for idx, iss in enumerate(ISSUES):
        if iss["title"] in existing_titles:
            continue

        item_num = start_num + idx
        summary_entry = {
            "number": item_num,
            "title": iss["title"],
            "status": "Ready",
            "milestone": iss["milestone"],
            "labels": iss["labels"],
            "body_preview": iss["body"][:250] + "..."
        }
        summary_data.append(summary_entry)

        eval_entry = {
            "number": item_num,
            "title": iss["title"],
            "category": iss["category"],
            "status": "Ready",
            "milestone": iss["milestone"],
            "labels": iss["labels"],
            "effort": iss["effort"],
            "effort_days": iss["effort_days"],
            "risk": iss["risk"],
            "risk_color": iss["risk_color"],
            "body_snippet": iss["body"][:250] + "..."
        }
        evaluated_data.append(eval_entry)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    with open(evaluated_path, "w", encoding="utf-8") as f:
        json.dump(evaluated_data, f, indent=2)

    print(f"Updated {summary_path} and {evaluated_path} with {len(ISSUES)} v0.8 roadmap issues.")


def get_github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        try:
            res = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode == 0 and res.stdout.strip():
                token = res.stdout.strip()
        except Exception:
            pass
    return token


def get_repo_milestone_number(token, milestone_title="v0.8"):
    url = "https://api.github.com/repos/KoshiirRa/midgley/milestones"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Midgley-Issue-Creator"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for ms in data:
                if ms["title"].lower() == milestone_title.lower():
                    return ms["number"]
    except Exception as e:
        print(f"Failed to query milestones: {e}")

    # If not found, create it
    try:
        create_req = urllib.request.Request(
            url,
            data=json.dumps({"title": milestone_title, "state": "open", "description": "v0.8 Math Improvements and New Data Feeds"}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Midgley-Issue-Creator",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(create_req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["number"]
    except Exception as e:
        print(f"Failed to create milestone {milestone_title}: {e}")
        return None


def create_github_issue(token, issue_data, milestone_num=None):
    url = "https://api.github.com/repos/KoshiirRa/midgley/issues"
    payload = {
        "title": issue_data["title"],
        "body": issue_data["body"],
        "labels": issue_data["labels"]
    }
    if milestone_num:
        payload["milestone"] = milestone_num

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Midgley-Issue-Creator",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return {"error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    print(f"Ingesting {len(ISSUES)} roadmap workstreams into v0.8 milestone...")
    update_local_roadmap_json()

    token = get_github_token()
    if not token:
        print("GitHub token not found or unauthenticated. Local roadmap JSON files updated successfully.")
        return

    milestone_num = get_repo_milestone_number(token, "v0.8")
    print(f"Target milestone 'v0.8' resolved to GitHub milestone number: {milestone_num}")

    created_issues = []
    for iss in ISSUES:
        print(f"Creating: {iss['title']}...")
        res = create_github_issue(token, iss, milestone_num)
        if "number" in res:
            print(f"  -> Created issue #{res['number']}: {res['html_url']}")
            created_issues.append({"id": iss["id"], "number": res["number"], "url": res["html_url"], "title": iss["title"]})
        else:
            print(f"  -> Result: {res}")
        time.sleep(0.5)

    print(f"\nDone! Processed {len(created_issues)} of {len(ISSUES)} issues on GitHub.")


if __name__ == "__main__":
    main()
