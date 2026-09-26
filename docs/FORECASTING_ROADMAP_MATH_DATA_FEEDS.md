# Midgley Forecasting Roadmap: Math Improvements and New Data Feeds

**Handoff document** · Prepared for Marty Marks · 24 September 2026

Based on the `dev` branch snapshot of 24 September 2026. This document is a companion to the separate dev-branch code review and covers forecasting method and inputs only. Workstream IDs (WS1 to WS11) are meant to map one-to-one onto GitHub issues.

> Equations use GitHub-flavored LaTeX math (`$…$` inline, `$$…$$` for display). They render on GitHub and in most Markdown previewers.

## Contents

1. [Summary](#1-summary)
2. [Where the predictability is](#2-where-the-predictability-is)
3. [Before you start](#3-before-you-start)
4. [Workstreams](#4-workstreams)
5. [Data feeds](#5-data-feeds)
6. [Sequencing](#6-sequencing)
7. [Decisions needed](#7-decisions-needed)

Appendices: [A. Evidence from the dev branch](#appendix-a-evidence-from-the-dev-branch) · [B. References](#appendix-b-references) · [C. Rows for the research citations ledger](#appendix-c-rows-for-the-research-citations-ledger)

---

## 1. Summary

Modeling effort should go where predictability actually exists. Over five days, the front-month RBOB futures price behaves close to a random walk, so directional gains on wholesale will be small at best. Pump prices are different: they catch up to wholesale moves with a lag, retail margins drift back toward normal, some Midwestern markets run regular price cycles, and taxes and fuel-blend rules change on known dates. Midgley already has about 60 connector classes, yet its own forecast log shows the model not beating a "no change" forecast. More inputs will not fix that. Modeling how retail prices are actually formed can.

The four highest-value changes, in order:

1. **Make wholesale-to-retail pass-through the core retail model** ([WS1](#ws1-retail-pass-through-model)). An asymmetric error-correction model already exists in `src/asymmetric_ecm.py`, but only its unit test uses it.
2. **Fix the futures roll and map each metro to its own wholesale hub** ([WS2](#ws2-futures-roll-adjustment-and-hub-mapping)). The unadjusted `RB=F` series carries two artificial jumps a year of 10 to 14 percent.
3. **Build one reliable "true price" per metro** ([WS3](#ws3-metro-true-price-nowcast)) by combining AAA, GasBuddy and EIA data in a Kalman filter.
4. **Rework the news-event features** ([WS4](#ws4-news-event-features)) so a busy news day cannot saturate them, and measure event effects from data instead of assuming fixed decay rates.

On data, make the existing feeds real before adding new ones: several connectors train on formula-generated histories, and the EIA API key is documented but never used. The new feeds with the clearest payoff are rack (terminal) prices and regional wholesale benchmarks (paid), Kalshi's gas-price markets and NASA's FIRMS satellite fire detections (free), and EIA's Short-Term Energy Outlook as a benchmark. [Section 6](#6-sequencing) lays out a four-phase plan of about 16 weeks for one developer.

## 2. Where the predictability is

Retail gasoline prices are set along a chain. Crude oil and refining margins set wholesale prices at pipeline hubs, terminals add transport and a rack margin, and stations add taxes and their own margin. Each link adjusts at its own speed. Since Borenstein, Cameron and Gilbert (1997), research has shown that retail prices respond to wholesale changes over several weeks, and faster to increases than to decreases ("rockets and feathers"). That lag means part of next week's pump-price change is already determined by wholesale moves that have happened but not yet passed through.

Midgley's current design cannot use this. Each metro's historical retail series is built as the RBOB futures price plus today's margin (for example `src/locations/tulsa/regional.py:55-59`), and Oakland and the Bay Area fall back to fixed \$2.05 and \$2.15 offsets (`src/locations/oakland/main.py:172-173`). A series built that way moves one-for-one with RBOB on the same day, so any model trained on it can only learn instant pass-through, which is the one thing retail prices reliably do not do.

Wholesale is where the model spends most of its effort today, and it is the hardest place to win. The front-month contract prices news within minutes, so by the time a headline has been scored the move is usually already in the price. Treat wholesale as a distribution to forecast (how far it might move) rather than a direction to call ([WS6](#ws6-wholesale-distribution-forecasting)).

## 3. Before you start

These items come from the separate code review. Until they are in place, none of the improvements below can be measured honestly.

- Real ground truth. The prediction log's retail "actual" prices are fallback constants or test values: the 138 National retail actuals in the log sit between \$3.35 and \$3.53 in \$0.02 steps, while AAA's national average on 24 September 2026 was \$4.4825.
- Tests isolated from production data. Tests currently write into `data/` and `reports/`; point them at temporary paths.
- A real trading calendar. Target dates currently land on exchange holidays.
- One evaluation harness ([WS10](#ws10-evaluation-protocol-and-feature-admission-rule)) that every change below is scored with.

## 4. Workstreams

Eleven workstreams follow. The table sets the order of attack; each section then covers why it matters, what exists today, the proposed method and the acceptance test. Effort is an indicative sizing for one developer: S is under a week, M one to three weeks, L longer.

| ID | Workstream | Issue | Priority | Effort | Depends on |
|---|---|:---:|:---:|:---:|---|
| [WS1](#ws1-retail-pass-through-model) | Retail pass-through model (asymmetric error correction) | [#443](https://github.com/KoshiirRa/midgley/issues/443) | 1 | M | WS2, WS3 |
| [WS2](#ws2-futures-roll-adjustment-and-hub-mapping) | Futures roll adjustment and hub mapping | [#444](https://github.com/KoshiirRa/midgley/issues/444) | 1 | S | None |
| [WS3](#ws3-metro-true-price-nowcast) | Metro "true price" nowcast (Kalman filter) | [#445](https://github.com/KoshiirRa/midgley/issues/445) | 1 | M | Real retail data |
| [WS4](#ws4-news-event-features) | News-event features: deduplication, scaling, measured effects | [#446](https://github.com/KoshiirRa/midgley/issues/446) | 1 | M | WS10 |
| [WS5](#ws5-edgeworth-price-cycles-cincinnati-first) | Edgeworth price-cycle test and regime model | [#447](https://github.com/KoshiirRa/midgley/issues/447) | 2 | M | WS3 |
| [WS6](#ws6-wholesale-distribution-forecasting) | Wholesale distribution forecasting | [#448](https://github.com/KoshiirRa/midgley/issues/448) | 2 | M | WS2 |
| [WS7](#ws7-calibrated-uncertainty-and-proper-quantiles) | Calibrated uncertainty and proper quantiles | [#449](https://github.com/KoshiirRa/midgley/issues/449) | 2 | S | WS6 |
| [WS8](#ws8-pooling-and-reconciliation-across-metros) | Pooling and reconciliation across metros | [#450](https://github.com/KoshiirRa/midgley/issues/450) | 3 | L | WS1 |
| [WS9](#ws9-known-future-covariates) | Known-future covariates (taxes, blend switches, holidays) | [#451](https://github.com/KoshiirRa/midgley/issues/451) | 2 | S | WS1 |
| [WS10](#ws10-evaluation-protocol-and-feature-admission-rule) | Evaluation protocol and feature admission rule | [#452](https://github.com/KoshiirRa/midgley/issues/452) | 1 | S | None |
| [WS11](#ws11-supply-network-outage-exposure) | Supply-network outage exposure | [#453](https://github.com/KoshiirRa/midgley/issues/453) | 3 | M | WS1, FIRMS feed |

Notation used throughout: $r_t$ is the metro retail price on day $t$, $w_t$ the wholesale cost (rack price or hub spot), $\tau_t$ per-gallon taxes, $h$ the forecast horizon in trading days, and $\Delta$ a one-day change.

### WS1. Retail pass-through model

*Priority 1 · Effort M · Depends on WS2 and WS3*

**Why.** This is the most important single change for the retail metros, because it models the part of next week's price move that is already locked in.

**Today.** `AsymmetricECM` and `fit_regional_asymmetric_ecm` exist in `src/asymmetric_ecm.py` (Issue #402), but only `tests/test_asymmetric_ecm.py` imports them. The metro pipelines never call the model.

**Approach.** Wire the error-correction model (ECM) in as the core retail forecaster and let the existing machine-learning models compete against it. A long-run relation defines the "normal" retail price for a given wholesale cost and tax level, and the gap $z_t$ from that normal is the margin cushion or squeeze:

$$
r_t = c + \beta\, w_t + \tau_t + z_t
$$

The short-run equation passes recent wholesale rises and falls through with separate lag coefficients, and closes the gap at a speed that depends on its sign:

$$
\Delta r_t = \alpha + \sum_{k=0}^{K}\left(\gamma^{+}_{k}\,\Delta w^{+}_{t-k} + \gamma^{-}_{k}\,\Delta w^{-}_{t-k}\right) + \sum_{j=1}^{J}\phi_j\,\Delta r_{t-j} + \theta^{+} z^{+}_{t-1} + \theta^{-} z^{-}_{t-1} + \varepsilon_t
$$

Here $\Delta w^{+}_t = \max(\Delta w_t, 0)$ and $\Delta w^{-}_t = \min(\Delta w_t, 0)$, with $z^{+}$ and $z^{-}$ defined the same way. For the five-day product, estimate the direct form rather than iterating the daily equation; it matches the existing `shift(-h)` target setup:

$$
r_{t+h} - r_t = a_h + \sum_{k=0}^{K}\left(g^{+}_{h,k}\,\Delta w^{+}_{t-k} + g^{-}_{h,k}\,\Delta w^{-}_{t-k}\right) + b_h\, z_t + e_{t+h}
$$

Wholesale moves inside the horizon are unknown, so treat them as mean zero or take them from the futures curve. The forecastable part is the pass-through still owed from moves that have already happened, plus margin reversion. Inputs are the WS3 metro price, the hub or rack price (WS2 and the new feeds) and the per-gallon tax schedule already in the repo. Where a state levies a percentage sales tax on fuel (California does), apply it multiplicatively in the long-run relation. Put the model in one shared helper that every `src/locations/<metro>/` package calls, so the packages stop re-implementing their own forecast loops.

**Done when.** On real data, over walk-forward origins covering at least six months, the ECM beats both persistence and the current metro model on five-day MAE in most metros (Diebold–Mariano test with the Harvey–Leybourne–Newbold correction, p < 0.05). Its coefficients should also be sensible: $\beta$ near 1, both error-correction terms negative, and any asymmetry running the expected way, with rises passed through faster than falls.

### WS2. Futures roll adjustment and hub mapping

*Priority 1 · Effort S · No dependencies*

**Why.** The continuous `RB=F` series from yfinance splices futures contracts without adjustment, and RBOB contracts change grade by delivery month. The maximum Reid vapor pressure is 13.5 psi for the March contract, 7.4 psi from April through mid-September, and 13.5 psi again for October (CME Rulebook, NYMEX Chapter 191). Each contract stops trading on the last business day of the month before delivery, so the splice produces artificial jumps at the late-February and late-August expiries.

**Today.** In the prediction log's National base prices, the move from 27 February to 2 March 2026 is +\$0.2927 (+14.09%), and the move from 28 August to 1 September 2026 is −\$0.3548 (−10.17%). These are two of the four largest of 227 day-to-day moves; the September one is the largest. The fake returns enter training, and because metro histories are RBOB plus a margin, they also create pump-price jumps that never happened.

**Approach.** Build the continuous series from individual contracts. EIA publishes daily RBOB futures prices for contracts 1 through 4 at no cost, which is enough for roll-clean returns; CME settlement files are the licensed alternative. Compute each return within one contract, so the roll-day return uses the new front contract's own previous close, and ratio-adjust history at each roll when a level series is needed:

$$
\text{ret}_t = \frac{P^{(c)}_t}{P^{(c)}_{t-1}} - 1 \qquad \text{(the same contract } c \text{ on both days)}
$$

$$
P^{\text{adj}}_s = P^{\text{old}}_s \times \frac{P^{\text{new}}_{\text{roll}}}{P^{\text{old}}_{\text{roll}}} \qquad \text{for every day } s \text{ before the roll}
$$

Roll on a fixed rule, for example five trading days before expiry, rather than at expiry itself, and add a summer-grade indicator so the model learns the seasonal spread instead of mistaking it for news.

For retail forecasting, use the wholesale price that actually supplies each metro instead of New York Harbor RBOB everywhere:

| Metro | Wholesale benchmark | Status in the repo |
|---|---|---|
| Newark, DE | New York Harbor conventional | Fetched from FRED (`DGASNYH`) |
| Charlotte, Greenville, Port St. Lucie | U.S. Gulf Coast conventional (the Colonial Pipeline origin; waterborne cargoes for Florida) | Fetched from FRED (`DGASUSGULF`) |
| Oakland, Bay Area | Los Angeles CARBOB | Documented as a weekly retail proxy (`GASREGWCA`) and not fetched; daily spot is available from the EIA API |
| Tulsa | Group 3 (Mid-Continent) | Not available; paid (OPIS, Argus or Platts) |
| Cincinnati | Chicago CBOB, or the Gulf Coast, depending on which pipeline supplies the local terminals | Not available; Chicago is paid |
| National | RBOB futures, roll-adjusted | See the approach above |

The FRED fetch lives in `EIARegionalSpotConnector` (`src/data_ingestion.py:1083-1086`; the Los Angeles proxy is noted at line 1054).

**Done when.** The adjusted series shows no outsized return on expiry days, a unit test on synthetic two-contract data passes, and metro backtest histories no longer jump on roll dates.

### WS3. Metro "true price" nowcast

*Priority 1 · Effort M · Depends on real retail data*

**Why.** Every forecast needs a trustworthy base price and a trustworthy "actual" to be scored against.

**Today.** The two come from different sources and geographies: a live AAA metro price for the base, and a state-level EIA series or a fallback constant for the actual. That mismatch alone produces naive-forecast errors of \$0.67 to \$0.83 per gallon over five days in the Charlotte, Greenville, Oakland and Bay Area series, far larger than real five-day retail moves.

**Approach.** Treat the true metro average price as a hidden state and each source as a noisy, possibly biased reading of it. A Kalman filter handles mixed frequencies naturally: AAA and GasBuddy update daily, EIA weekly (a Monday survey), and missing days simply skip the update step. Estimate the noise variances and source biases by maximum likelihood on history:

$$
x_t = x_{t-1} + \eta_t, \qquad \eta_t \sim \mathcal{N}(0,\, q)
$$

$$
y^{(s)}_t = x_t + b_s + \varepsilon^{(s)}_t, \qquad \varepsilon^{(s)}_t \sim \mathcal{N}(0,\, \sigma^2_s), \qquad s \in \{\text{AAA},\ \text{GasBuddy},\ \text{EIA}\}
$$

Use the filtered estimate, which uses data up to day $t$ only, as the forecast base. Use the smoothed estimate as the "actual" when scoring, and only after the target date has passed. Where the EIA series is state- or city-level rather than metro-level, give it its own slowly varying basis instead of equating it with the metro price. No state-space library is in the dependencies today: `statsmodels` is the standard choice, and a short NumPy implementation is enough for a local-level model like this one. Confirm AAA's and GasBuddy's data-use terms before relying on them in production.

**Done when.** Every region has one nowcast series with a record of which sources fed each day, the backfill uses it only for matured targets, and on a hold-out period the nowcast and the EIA figure differ in release weeks by no more than their estimated combined noise.

### WS4. News-event features

*Priority 1 · Effort M · Depends on WS10*

**Why.** This layer produced the implausible Tulsa forecast in the README (\$3.99 to \$6.39 in five days).

**Today.** Of the 233 events in `data/intraday_events.json`, 152 are tagged only "National", all dated 4 September 2026 or later, and the regional loader treats "national" as a match for every metro (`src/data_ingestion.py:230-231`). Same-day scores are then summed and clipped to fixed bounds (`src/feature_engineering.py:657-663`), so a busy news day pins the features at their ceiling, a regime the model never saw in training. Decay half-lives are set by hand per category (2.5 to 14 days). The committed calibration output (`data/calibrated_event_decay_parameters.json`) is empty, and the code review found that the calibration fit cannot separate impact size from decay speed.

**Approach.** Make four changes, in this order:

1. Collapse syndicated copies of the same story into one event by clustering headlines within a time window on embedding similarity (`sentence-transformers` is already an optional dependency) or MinHash.
2. Scope events to regions explicitly. National stories reach metros through the wholesale price, which already reflects them, so they should not also enter every metro's event features.
3. Scale event intensity against a rolling baseline instead of summing and clipping.
4. Measure each category's effect at each horizon directly with local projections (Jordà 2005). This replaces the assumed exponential decay with an estimated response curve and removes the identification problem.

$$
I_{c,t} = \log\left(1 + N_{c,t}\right) \qquad \text{or} \qquad I_{c,t} = \frac{N_{c,t} - \bar{N}^{(90)}_{c,t}}{s^{(90)}_{c,t}}
$$

$$
y_{t+h} - y_t = a_h + b_{h,c}\, I_{c,t} + \Gamma_h^{\top} X_t + e_{t+h}, \qquad h = 1, \dots, 10
$$

Here $N_{c,t}$ is the deduplicated count of category-$c$ events on day $t$, $\bar{N}^{(90)}$ and $s^{(90)}$ are its 90-day rolling mean and standard deviation, $X_t$ holds controls such as lagged returns and volatility, and the sequence $b_{h,c}$ over $h$ is that category's impulse response. Use Newey–West standard errors with $h-1$ lags, because overlapping horizons make the errors autocorrelated. A Hawkes (self-exciting) process is an optional extension for forecasting near-term event intensity.

LLM scores must be point-in-time: a fixed prompt and model version, stored with a timestamp. Remove training headlines that state their own outcome, such as "Russia invades Ukraine; Cushing WTI crude surges above \$100/bbl, driving Tulsa gas prices higher." (`src/locations/tulsa/regional.py:93`).

**Done when.** No metro's event features saturate on the busiest news days in the history, every category has an estimated response curve with confidence bands, and a publication guard flags any forecast where the LLM-augmented model departs from the quantitative-only model by more than a set multiple of recent volatility.

### WS5. Edgeworth price cycles (Cincinnati first)

*Priority 2 · Effort M · Depends on WS3*

**Why.** Some retail markets run Edgeworth cycles: a sharp, market-wide price jump (a "restoration") followed by days of small undercuts, until margins are thin enough for the next jump. A single cycle is often one to two weeks long (Noel 2011), which is Midgley's forecast horizon, so in a cycling market the phase of the cycle can matter more than wholesale news. A Federal Trade Commission study of 355 U.S. cities (Zimmerman, Yun and Taylor 2010) found cycling concentrated in a small number of cities in contiguous upper-Midwestern states, with cities tending either to cycle every year or not at all.

**Today.** Nothing in the code tests for or models cycles. Cincinnati is the Midgley metro most likely to cycle, but that has to be checked before any modeling, and it needs daily metro data (WS3) because weekly averages hide cycles.

**Approach.** Start with cheap diagnostics on every metro: the share of daily changes that are decreases, the median daily change, the skewness of changes, and runs of consecutive decreases versus increases. Confirm with a two-regime Markov-switching model (restoration versus undercutting), the method used in this literature. For a metro that cycles, model the chance of a restoration within the horizon from the current margin $m_t$ and the days since the last restoration $d_t$, then combine it with the typical jump size $J$ and the daily undercutting drift $\delta$:

$$
P_{t,h} = \Pr\left(\text{restoration in } (t,\, t+h] \,\middle|\, m_t, d_t\right) = \operatorname{logit}^{-1}\left(a + b\, m_t + c\, d_t\right)
$$

$$
\mathbb{E}\left[r_{t+h} - r_t\right] \approx P_{t,h}\, J + \left(1 - P_{t,h}\right) \delta\, h
$$

**Done when.** A diagnostic report classifies each metro as cycling or not, and for any cycling metro the regime model beats the WS1 ECM on five-day MAE over walk-forward origins.

### WS6. Wholesale distribution forecasting

*Priority 2 · Effort M · Depends on WS2*

**Why.** For the National product, forecast how far the price might move, not which way.

**Today.** A volatility gate blends forecasts toward persistence with hand-set constants, `compute_volatility_gate_weight(volatility_14d, threshold=0.015, k=200.0)` in `src/models.py:1140`, while the Ridge and XGBoost models try to call direction.

**Approach.** Use persistence, or the drift implied by the futures curve, as the point forecast and put the modeling effort into volatility. A GARCH(1,1) model, its asymmetric GJR variant, or a HAR model on realized volatility gives a daily variance path. Sum it over the horizon and use a fat-tailed distribution such as Student-t for the return:

$$
\sigma^2_{t+1} = \omega + \alpha\, \varepsilon^2_t + \beta\, \sigma^2_t
$$

$$
RV_{t+1} = c + \beta_d\, RV_t + \beta_w\, RV^{(w)}_t + \beta_m\, RV^{(m)}_t
$$

$$
\sigma_{t,h} = \sqrt{\textstyle\sum_{i=1}^{h} \sigma^2_{t+i}}, \qquad R_{t \to t+h} \sim t_{\nu}\left(0,\, \sigma_{t,h}\right)
$$

Here $RV^{(w)}_t$ and $RV^{(m)}_t$ are the 5-day and 22-day averages of realized variance. If you keep the gate $\lambda_t = 1 / \left(1 + e^{-k(\sigma_{14,t} - s_0)}\right)$, estimate $k$ and $s_0$ by walk-forward cross-validation instead of fixing them, or replace it with a Markov-switching volatility regime. RBOB options-implied volatility would sharpen the distribution further ([Data feeds](#5-data-feeds)); the OVX index already in the repo measures crude-oil volatility, not gasoline. SciPy, already a dependency, is enough to fit GARCH by maximum likelihood; the `arch` package is more convenient but would be a new dependency.

**Done when.** Probability integral transform (PIT) histograms are close to uniform, interval coverage is within three percentage points of nominal on walk-forward data, and the continuous ranked probability score (CRPS) beats a constant-volatility baseline.

### WS7. Calibrated uncertainty and proper quantiles

*Priority 2 · Effort S · Depends on WS6*

**Why.** Headline Arena scores probabilistic forecasts, so miscalibrated quantiles cost directly, and published intervals should mean what they say.

**Today.** When a row has no interval of its own, the logger applies one residual standard deviation from the latest 30 days to every row in the batch (`src/prediction_logger.py:359, 382-383`). The Headline Arena submission sends the 95% interval bounds as the 10th and 90th percentiles (`run_all.py:116-120`). Split-conformal intervals (`src/models.py:1207`) and pinball-loss evaluation already exist to build on.

**Approach.** Produce explicit quantiles (at least the 10th, 50th and 90th, plus the 2.5th and 97.5th for the 95% band) from the WS6 distribution or from quantile regression. Keep them calibrated with adaptive conformal inference (Gibbs and Candès 2021), which adjusts the working miscoverage rate after each hit or miss so coverage holds as conditions drift. Calibrate only on matured forecasts at the same horizon, so no future data leaks in. For Headline Arena's directional questions, derive probabilities from the full predictive distribution:

$$
\alpha_{t+1} = \alpha_t + \gamma\left(\alpha^{*} - \text{miss}_t\right)
$$

$$
\Pr\left(\Delta P_{t \to t+h} > d\right) = 1 - F_{t,h}(d)
$$

Here $\alpha^{*}$ is the target miscoverage (0.05 for a 95% band), $\text{miss}_t$ is 1 when the outcome fell outside the interval and 0 otherwise, and $F_{t,h}$ is the predictive distribution of the $h$-day change.

**Done when.** Coverage is within three percentage points of nominal for every region and horizon over a rolling 90-day window, CRPS and pinball loss improve on the current method, and the Headline Arena submission uses true quantiles.

### WS8. Pooling and reconciliation across metros

*Priority 3 · Effort L · Depends on WS1*

**Why.** Each metro has limited real history, so WS1 coefficients estimated metro by metro will be noisy, and nothing currently keeps metro, state, PADD and national forecasts consistent with one another.

**Today.** Each of the seven metro packages under `src/locations/` trains and forecasts on its own, and the packages are largely copies of one another.

**Approach.** Partial pooling shrinks each metro's estimates toward a shared average in proportion to their uncertainty, so metros with little data borrow strength from the rest. A mixed-effects model, or simple empirical-Bayes (James–Stein) shrinkage of the per-metro estimates, is enough to start:

$$
\theta_r = \theta_0 + u_r, \qquad u_r \sim \mathcal{N}(0,\, \Omega)
$$

Then reconcile the forecasts so metro, state or PADD, and national figures are coherent. MinT reconciliation (Wickramasuriya, Athanasopoulos and Hyndman 2019) combines the independent base forecasts $\hat{y}$ using their error covariance $W$ and the aggregation matrix $S$:

$$
\tilde{y} = S \left(S^{\top} W^{-1} S\right)^{-1} S^{\top} W^{-1}\, \hat{y}
$$

Regional prices are averages rather than sums, so $S$ needs volume weights, for example from EIA or state motor-fuel sales data.

**Done when.** The pooled model matches or beats per-metro models out of sample for every metro and clearly beats them for the thinnest, and reconciled forecasts are coherent across levels. This is also the natural point to replace the seven metro packages with one configuration-driven pipeline that reads the existing `data/regional_metadata/` profiles.

### WS9. Known-future covariates

*Priority 2 · Effort S · Depends on WS1*

**Why.** Some price changes are known before they happen, and at a five-day horizon they are free accuracy around the dates they occur: scheduled state excise changes (California adjusts its rate every July 1), summer and winter blend switches, CARB blend transitions, major holidays, and the futures expiries from WS2. Fuel taxes typically pass through to pump prices quickly and close to one-for-one (Marion and Muehlegger 2011).

**Today.** Blend rules already live in `data/regulatory_rvp_rules.json` and `src/rvp_regulations.py`, and state tax rates are in the repo. The step this workstream adds is one dated calendar that gives each forecast the changes falling inside its horizon.

**Approach.** Keep a calendar table of dated events (effective date, region, type, amount), and at each forecast origin give the model the known changes that fall inside the horizon. Tax changes enter the WS1 long-run relation directly; blend switches enter as indicators on the margin.

**Done when.** Forecasts that span a tax or blend change capture the step, and errors on those dates fall relative to the current model.

### WS10. Evaluation protocol and feature admission rule

*Priority 1 · Effort S · No dependencies*

**Why.** Every other workstream is judged by this one, so build it first.

**Today.** The repo has purged and embargoed walk-forward splits and a Diebold–Mariano test with the Harvey–Leybourne–Newbold correction. It has no Pesaran–Timmermann test, no correction for comparing many model variants or many regions, and no rule for when a feature earns its place.

**Approach.** Use walk-forward origins with the existing purge and embargo logic, and align targets to a real trading calendar for futures and to each series' own observation calendar for retail. Always report the same baselines: persistence, the WS1 ECM once it exists, EIA's Short-Term Energy Outlook where the horizon allows, and Kalshi's market-implied forecast for the national average. Add four statistical checks:

- The Pesaran–Timmermann test, so directional accuracy is judged against chance.
- Newey–West standard errors ($h-1$ lags) for any regression on overlapping targets.
- The Model Confidence Set, or Hansen's test for superior predictive ability, whenever many variants are compared, as the PRAXIST experiments do.
- A Benjamini–Hochberg correction when the same test runs across many regions.

Finally, adopt a feature admission rule: a feature family enters the production model only if it improves walk-forward CRPS or MAE on real data and survives the Model Confidence Set at the 10% level. Apply it retroactively to the existing families.

**Done when.** One script produces a reproducible evaluation report from real data, runs on a schedule, and is the only source for any accuracy figure Midgley publishes.

### WS11. Supply-network outage exposure

*Priority 3 · Effort M · Depends on WS1 and the FIRMS feed*

**Why.** Distance is a weak proxy for dependence: a metro can sit near a refinery that does not supply it and far from one that does.

**Today.** Refinery and pipeline outages reach metro forecasts through a fixed 150-mile distance decay, `compute_spatial_distance_decay(distance_miles, half_decay_miles=150.0)` in `src/spatial_refinery.py:301`.

**Approach.** Use the knowledge graph (`src/knowledge_graph.py`, built on networkx) to hold supply shares: the fraction of each metro's gasoline that comes from each refinery, pipeline or terminal, taken from EIA refinery capacity data and pipeline topology. Then compute an exposure index:

$$
X_{r,t} = \sum_{k} s_{r,k}\, \frac{\text{offline}_{k,t}}{\text{capacity}_{k}}
$$

Here $s_{r,k}$ is metro $r$'s supply share from source $k$, and $\text{offline}_{k,t}$ is the capacity out of service on day $t$, taken from the existing Texas, Louisiana, Bay Area and National Response Center outage feeds plus the FIRMS feed proposed below. The index enters the WS1 margin equation.

**Done when.** The index spikes on known historical outages for the metros those outages actually affected, and it improves margin forecasts for those metros.

## 5. Data feeds

Midgley's inputs are already broad. The data work that pays off most is, first, making the existing feeds real and, second, adding the few inputs that sit closest to how pump prices are set.

### 5.1 Make existing feeds real first

| Feed | Current state | Change |
|---|---|---|
| EIA API (retail, stocks, spot, STEO) | `EIA_API_KEY` is documented, but no code reads it. National retail "actuals" in the log run \$3.35–\$3.53 against AAA's \$4.4825 national average on 24 September 2026. | Call EIA API v2 for weekly retail by city, state and PADD, PADD sub-region stocks, Los Angeles spot and STEO, and store each release as a vintage. |
| CFTC Commitments of Traders | The training history is a formula, `80000 + 16000·sin(2π(day of year − 60)/365.25)` (`src/feature_engineering.py:409`); the real report value is written only to the latest row. | Load the full history, which the CFTC publishes free, keyed by report date and release date. |
| EIA balances, USGS waterway risk, CEC stocks, USDA ethanol and D6 RIN features | Training histories are day-of-year sine or cosine curves (`src/feature_engineering.py:412-585`). | Pull each agency's archive, or drop the feature until its history is real. |
| Vintage files (`data/*_vintages.json`) | Present, but the features above still train on formula histories. | Backfill real history into the vintage files and use them for point-in-time joins in training. |

### 5.2 New feeds

| Feed | What it provides | Access | Used by |
|---|---|---|---|
| Rack (terminal) prices, from OPIS or DTN | The wholesale price stations actually pay at each terminal, the most direct cost input for retail. Start with terminals the repo already references, such as Paw Creek (Charlotte) and Selma (Greenville). | Paid | WS1, WS3 |
| Regional wholesale benchmarks | Group 3 (Tulsa) and Chicago CBOB (Cincinnati) from OPIS, Argus or Platts; Los Angeles CARBOB daily spot from the EIA API. | Group 3 and Chicago paid; Los Angeles free | WS1, WS2 |
| Kalshi gas-price markets | Market-implied probabilities for AAA's national average: next-day, weekly and monthly contracts, plus markets on California, Texas, New York and Florida prices. | Free API | WS10 benchmark, WS7 input |
| NASA FIRMS active-fire detections | Satellite hotspots (VIIRS, 375 m) with fire radiative power, queried by a bounding box around each refinery, in near-real time. | Free, with a MAP_KEY | WS11, WS4 |
| EIA Short-Term Energy Outlook | EIA's monthly professional forecast of retail gasoline prices. | Free (EIA API) | WS10 benchmark |
| RBOB futures contracts 1–4 | Per-contract daily prices for roll-clean returns. | Free from EIA; CME settlements licensed | WS2 |
| RBOB options-implied volatility | Gasoline-specific implied volatility for the wholesale distribution. | Licensed (CME options data) | WS6, WS7 |

Kalshi's national contracts settle on AAA's national average for regular gasoline. The monthly series settles on the last day of the month, and a price exactly equal to the strike resolves No. Store market odds point in time at each forecast origin (never backfill them), and check Kalshi's API terms on data use and redistribution before publishing anything derived from them.

FIRMS's area API returns up to five days per request. Global detections arrive within about three hours of a satellite pass, and much faster for much of the United States. Refineries flare routinely, so model each site's deviation from its own baseline fire radiative power rather than raw detections. Suomi NPP deliveries end on 1 November 2026, so use the NOAA-20 and NOAA-21 VIIRS sources. NASA asks for attribution when FIRMS data is shared.

Rack prices and the Group 3 and Chicago benchmarks are the only paid items with a clear, direct link to retail prices. A small subscription covering the terminals that serve Midgley's metros is likely to be worth more than several of the free feeds already in the repo (see [Decisions needed](#7-decisions-needed)).

### 5.3 Feeds to freeze

Earthquakes, air quality (outside its role in blend rules), rig counts, executive social media posts, the open-source AI model radar and research-literature feeds sit far from what moves pump prices in five days, and each adds a fallback path and a failure mode. Freeze new feeds of this kind until the WS10 admission rule has been applied to the existing families, then remove those that fail it.

## 6. Sequencing

| Phase | Workstreams | Outcome | Indicative timing |
|---|---|---|---|
| 0 | Code-review prerequisites; minimal WS10 harness | Real ground truth, isolated tests, a harness that can score anything | Weeks 1–2 |
| 1 | WS2, WS3, WS1 (pilot), WS10 in full | A retail model grounded in pass-through, scored honestly | Weeks 2–6 |
| 2 | WS4, WS5, WS9, WS7 | Events that cannot saturate, a cycle-aware Cincinnati, calendar effects, calibrated quantiles | Weeks 6–10 |
| 3 | WS6, WS8, WS11; paid-data decision | Wholesale distributions, pooled and reconciled metros, network outage exposure | Weeks 10–16 |

Timings assume one developer and should be revisited after Phase 1. Pilot WS1 on Newark and Charlotte first: both have free daily hub prices (New York Harbor and the Gulf Coast) and sit outside the region where U.S. studies find price cycling, so they give the cleanest read on whether pass-through modeling works before it is rolled out everywhere.

## 7. Decisions needed

1. Budget for paid data: rack prices for the terminals serving each metro, the Group 3 and Chicago benchmarks, and optionally RBOB options volatility.
2. Data-use terms for AAA, GasBuddy and Kalshi before their data feeds published outputs.
3. Whether the National wholesale product keeps a directional forecast at all, or becomes a price-range product (WS6).
4. New dependencies: `statsmodels` (state-space and mixed-effects models) and `arch` (GARCH), or NumPy and SciPy implementations.
5. Acceptance thresholds: confirm or change the bars used in this document (p < 0.05, coverage within three percentage points, at least six months of walk-forward origins, Model Confidence Set at 10%).
6. Pilot metros for WS1 (proposed: Newark and Charlotte).

## Appendix A. Evidence from the dev branch

| Finding | Evidence | Location |
|---|---|---|
| Pass-through model exists but is unused | `AsymmetricECM` and `fit_regional_asymmetric_ecm` are imported only by their unit test | `src/asymmetric_ecm.py`, `tests/test_asymmetric_ecm.py` |
| Metro histories assume instant pass-through | Retail history = RBOB + (today's live price − today's RBOB); Oakland and Bay Area fall back to +\$2.05 and +\$2.15 | `src/locations/tulsa/regional.py:55-59`, `src/locations/oakland/main.py:172-173` |
| Unadjusted futures roll | National base \$2.0779 (27 Feb 2026) to \$2.3706 (2 Mar 2026), +\$0.2927 (+14.09%); \$3.4899 (28 Aug 2026) to \$3.1351 (1 Sep 2026), −\$0.3548 (−10.17%); two of the four largest of 227 day-to-day moves | `data/prediction_history.csv` (National rows sourced from `yfinance:RB=F`) |
| Grade changes by contract month | Maximum RVP 13.5 psi (March), 7.4 psi (April to 15 September), 13.5 psi (October); trading ends on the last business day of the month before delivery | CME Rulebook, NYMEX Chapter 191 |
| Retail ground truth is not real | 138 National retail "actuals" between \$3.35 and \$3.53 in \$0.02 steps; AAA national average on 24 Sep 2026 was \$4.4825 | `data/prediction_history.csv`; AAA Gas Prices |
| Only two hub spot prices fetched | FRED `DGASUSGULF` and `DGASNYH`; Los Angeles documented as a weekly retail proxy | `src/data_ingestion.py:1054`, `src/data_ingestion.py:1083-1086` |
| Event features saturate | "national" events match every metro; same-day scores are summed, then clipped | `src/data_ingestion.py:230-231`, `src/feature_engineering.py:657-663` |
| National tagging since 4 September | 152 of 233 intraday events tagged only "National", all dated 4 Sep 2026 or later | `data/intraday_events.json` |
| Event calibration output empty | `{"calibrated_parameters": {}}` | `data/calibrated_event_decay_parameters.json` |
| Formula-generated training histories | COT, EIA balances, USGS waterway risk, CEC stocks, USDA ethanol and RIN series built from day-of-year sine or cosine curves; real values written only to the latest row | `src/feature_engineering.py:409-585` |
| One interval width for a whole batch | 1.96 × one 30-day residual standard deviation applied to every row lacking its own interval | `src/prediction_logger.py:359, 382-383` |
| Hand-set volatility gate | `threshold=0.015`, `k=200.0` | `src/models.py:1140` |
| Fixed distance decay | `half_decay_miles=150.0` | `src/spatial_refinery.py:301` |
| Quantile mismatch at Headline Arena | 95% interval bounds sent as P10 and P90 | `run_all.py:116-120` |
| Outcome-stating training headline | "…driving Tulsa gas prices higher." | `src/locations/tulsa/regional.py:93` |
| EIA API key unused | `EIA_API_KEY` appears in documentation only | `SELF_HOSTING.md`; no reads in `src/`, `scripts/`, `workers/` or `.github/` |

## Appendix B. References

Each entry lists the workstreams that draw on it and the existing GitHub issues it bears on. Linked issue numbers point to the project's tracker. Numbers without a link (#43, #188, #214, #361, #362 and #406) appear in the code and docs but are never linked anywhere in the repo, so confirm them in the tracker before publishing. Where no issue exists yet, open one for the workstream and swap its number in. Each paper's DOI was checked against publisher or bibliographic index records on 24 September 2026. [Appendix C](#appendix-c-rows-for-the-research-citations-ledger) has the same papers formatted as rows for `RESEARCH_CITATIONS.md`.

### Data sources and specifications

- AAA Gas Prices, national average for regular gasoline, 24 September 2026.
  - Used in [WS3](#ws3-metro-true-price-nowcast) and [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issue: [#403](https://github.com/KoshiirRa/midgley/issues/403) (EIA weekly retail prices by PADD and state as ground truth).
- CME Group, NYMEX Rulebook Chapter 191, RBOB Gasoline Futures: https://www.cmegroup.com/rulebook/NYMEX/1a/191.pdf
  - Used in [WS2](#ws2-futures-roll-adjustment-and-hub-mapping). Related issues: [#401](https://github.com/KoshiirRa/midgley/issues/401) and [#404](https://github.com/KoshiirRa/midgley/issues/404) (NYMEX forward curve, calendar spreads and 3-2-1 crack).
- U.S. Energy Information Administration, NYMEX futures prices, definitions and notes: https://www.eia.gov/dnav/pet/TblDefs/pet_pri_fut_tbldef2.asp
  - Used in [WS2](#ws2-futures-roll-adjustment-and-hub-mapping). Related issues: [#401](https://github.com/KoshiirRa/midgley/issues/401) and [#404](https://github.com/KoshiirRa/midgley/issues/404) (NYMEX forward curve, calendar spreads and 3-2-1 crack).
- Kalshi, gasoline markets: https://kalshi.com/category/commodities/gasoline
  - Used in [WS10](#ws10-evaluation-protocol-and-feature-admission-rule) and [WS7](#ws7-calibrated-uncertainty-and-proper-quantiles). Related issue: [#182](https://github.com/KoshiirRa/midgley/issues/182) (Headline Arena benchmark and calibration).
- NASA FIRMS, area API: https://firms.modaps.eosdis.nasa.gov/api/area/
  - Used in [WS11](#ws11-supply-network-outage-exposure). Related issue: #406 (Gulf Coast refinery outage telemetry from TCEQ, LDEQ and NRC).

### Literature

- Benjamini, Y., and Hochberg, Y. (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society, Series B*, 57(1). DOI: [10.1111/j.2517-6161.1995.tb02031.x](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x)
  - Used in [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issues: #362 (5-tier model evaluation hierarchy and promotion gate); #188 (PRAXIST autonomous research harness).
- Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics*, 31(3). DOI: [10.1016/0304-4076(86)90063-1](https://doi.org/10.1016/0304-4076%2886%2990063-1)
  - Used in [WS6](#ws6-wholesale-distribution-forecasting). Related issues: #214 (volatility-gated persistence blending and empirical residual intervals); [#44](https://github.com/KoshiirRa/midgley/issues/44) (P10/P50/P90 prediction interval bands scaling with horizon); [#119](https://github.com/KoshiirRa/midgley/issues/119) (fat-tail volatility engine for scenario simulation).
- Borenstein, S., Cameron, A. C., and Gilbert, R. (1997). Do gasoline prices respond asymmetrically to crude oil price changes? *Quarterly Journal of Economics*, 112(1). DOI: [10.1162/003355397555118](https://doi.org/10.1162/003355397555118)
  - Used in [WS1](#ws1-retail-pass-through-model). Related issue: [#402](https://github.com/KoshiirRa/midgley/issues/402) (asymmetric ECM for retail–wholesale pass-through). Already implemented in `src/asymmetric_ecm.py`, but not yet called by the metro pipelines.
- Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics*, 7(2). DOI: [10.1093/jjfinec/nbp001](https://doi.org/10.1093/jjfinec/nbp001)
  - Used in [WS6](#ws6-wholesale-distribution-forecasting). Related issues: #214 (volatility-gated persistence blending and empirical residual intervals); [#44](https://github.com/KoshiirRa/midgley/issues/44) (P10/P50/P90 prediction interval bands scaling with horizon).
- Diebold, F. X., and Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics*, 13(3). DOI: [10.1080/07350015.1995.10524599](https://doi.org/10.1080/07350015.1995.10524599)
  - Used in [WS1](#ws1-retail-pass-through-model) and [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issues: #362 (5-tier model evaluation hierarchy and promotion gate); #43 (naive persistence and NYMEX futures-implied benchmark comparisons). Already implemented in `src/model_evaluation.py`.
- Doyle, J., Muehlegger, E., and Samphantharak, K. (2010). Edgeworth cycles revisited. *Energy Economics*, 32(3). https://dspace.mit.edu/handle/1721.1/64740
  - Used in [WS5](#ws5-edgeworth-price-cycles-cincinnati-first). No existing issue; open one for WS5.
- Durbin, J., and Koopman, S. J. (2012). *Time Series Analysis by State Space Methods* (2nd ed.). Oxford University Press. DOI: [10.1093/acprof:oso/9780199641178.001.0001](https://doi.org/10.1093/acprof:oso/9780199641178.001.0001)
  - Used in [WS3](#ws3-metro-true-price-nowcast). Related issues: [#403](https://github.com/KoshiirRa/midgley/issues/403) (EIA weekly retail prices by PADD and state as ground truth); [#391](https://github.com/KoshiirRa/midgley/issues/391) (ground-truth integrity, plausibility guards and history sanitation); [#121](https://github.com/KoshiirRa/midgley/issues/121) (bitemporal vintage tracking for EIA data).
- Gibbs, I., and Candès, E. (2021). Adaptive conformal inference under distribution shift. *Advances in Neural Information Processing Systems*, 34. arXiv: [2106.00170](https://arxiv.org/abs/2106.00170); arXiv DOI: [10.48550/arXiv.2106.00170](https://doi.org/10.48550/arXiv.2106.00170)
  - Used in [WS7](#ws7-calibrated-uncertainty-and-proper-quantiles). Related issues: [#358](https://github.com/KoshiirRa/midgley/issues/358) (horizon-calibrated prediction intervals and split conformal inference); [#394](https://github.com/KoshiirRa/midgley/issues/394) (calibrated 95% interval coverage); #214 (volatility-gated persistence blending and empirical residual intervals).
- Gneiting, T., and Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. *Journal of the American Statistical Association*, 102(477). DOI: [10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437)
  - Used in [WS6](#ws6-wholesale-distribution-forecasting), [WS7](#ws7-calibrated-uncertainty-and-proper-quantiles) and [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issues: [#182](https://github.com/KoshiirRa/midgley/issues/182) (Headline Arena benchmark and calibration); [#408](https://github.com/KoshiirRa/midgley/issues/408) (Headline Arena EIA weekly retail gasoline challenge); [#358](https://github.com/KoshiirRa/midgley/issues/358) (horizon-calibrated prediction intervals and split conformal inference); [#44](https://github.com/KoshiirRa/midgley/issues/44) (P10/P50/P90 prediction interval bands scaling with horizon).
- Hansen, P. R. (2005). A test for superior predictive ability. *Journal of Business & Economic Statistics*, 23(4). DOI: [10.1198/073500105000000063](https://doi.org/10.1198/073500105000000063)
  - Used in [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issues: #188 (PRAXIST autonomous research harness); #362 (5-tier model evaluation hierarchy and promotion gate).
- Hansen, P. R., Lunde, A., and Nason, J. M. (2011). The model confidence set. *Econometrica*, 79(2). DOI: [10.3982/ECTA5771](https://doi.org/10.3982/ECTA5771)
  - Used in [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issues: #188 (PRAXIST autonomous research harness); #362 (5-tier model evaluation hierarchy and promotion gate).
- Harvey, D., Leybourne, S., and Newbold, P. (1997). Testing the equality of prediction mean squared errors. *International Journal of Forecasting*, 13(2). DOI: [10.1016/S0169-2070(96)00719-4](https://doi.org/10.1016/S0169-2070%2896%2900719-4)
  - Used in [WS1](#ws1-retail-pass-through-model) and [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issue: #362 (5-tier model evaluation hierarchy and promotion gate). Already implemented in `src/model_evaluation.py`.
- Hawkes, A. G. (1971). Spectra of some self-exciting and mutually exciting point processes. *Biometrika*, 58(1). DOI: [10.1093/biomet/58.1.83](https://doi.org/10.1093/biomet/58.1.83)
  - Used in [WS4](#ws4-news-event-features). Related issue: [#355](https://github.com/KoshiirRa/midgley/issues/355) (same-session event aggregation and calendar-time decay).
- Jordà, Ò. (2005). Estimation and inference of impulse responses by local projections. *American Economic Review*, 95(1). DOI: [10.1257/0002828053828518](https://doi.org/10.1257/0002828053828518)
  - Used in [WS4](#ws4-news-event-features). Related issues: #361 (empirical event calibration); [#355](https://github.com/KoshiirRa/midgley/issues/355) (same-session event aggregation and calendar-time decay).
- Marion, J., and Muehlegger, E. (2011). Fuel tax incidence and supply conditions. *Journal of Public Economics*, 95(9–10). DOI: [10.1016/j.jpubeco.2011.04.003](https://doi.org/10.1016/j.jpubeco.2011.04.003)
  - Used in [WS9](#ws9-known-future-covariates). Related issues: [#141](https://github.com/KoshiirRa/midgley/issues/141) (zero-cost energy feeds, including EIA v2 and state open-data tax rates); [#383](https://github.com/KoshiirRa/midgley/issues/383) (CARB LCFS and cap-and-trade compliance engine).
- Maskin, E., and Tirole, J. (1988). A theory of dynamic oligopoly, II: Price competition, kinked demand curves, and Edgeworth cycles. *Econometrica*, 56(3). DOI: [10.2307/1911701](https://doi.org/10.2307/1911701)
  - Used in [WS5](#ws5-edgeworth-price-cycles-cincinnati-first). No existing issue; open one for WS5.
- Newey, W. K., and West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3). DOI: [10.2307/1913610](https://doi.org/10.2307/1913610)
  - Used in [WS4](#ws4-news-event-features) and [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issues: [#117](https://github.com/KoshiirRa/midgley/issues/117) (purged and combinatorial cross-validation); [#396](https://github.com/KoshiirRa/midgley/issues/396) and [#397](https://github.com/KoshiirRa/midgley/issues/397) (return-target modeling and purged embargo cross-validation).
- Noel, M. D. (2011). Edgeworth price cycles. In *The New Palgrave Dictionary of Economics*. https://www.noeleconomics.com/articles/NOEL_palgrave.pdf
  - Used in [WS5](#ws5-edgeworth-price-cycles-cincinnati-first). No existing issue; open one for WS5.
- Pesaran, M. H., and Timmermann, A. (1992). A simple nonparametric test of predictive performance. *Journal of Business & Economic Statistics*, 10(4). DOI: [10.1080/07350015.1992.10509922](https://doi.org/10.1080/07350015.1992.10509922)
  - Used in [WS10](#ws10-evaluation-protocol-and-feature-admission-rule). Related issues: [#47](https://github.com/KoshiirRa/midgley/issues/47) (realized-vs-predicted rolling scoreboard); [#395](https://github.com/KoshiirRa/midgley/issues/395) (injectable evaluation architecture).
- Wickramasuriya, S. L., Athanasopoulos, G., and Hyndman, R. J. (2019). Optimal forecast reconciliation for hierarchical and grouped time series through trace minimization. *Journal of the American Statistical Association*, 114(526). DOI: [10.1080/01621459.2018.1448825](https://doi.org/10.1080/01621459.2018.1448825)
  - Used in [WS8](#ws8-pooling-and-reconciliation-across-metros). No existing issue; open one for WS8.
- Zimmerman, P. R., Yun, J. M., and Taylor, C. T. (2010). Edgeworth price cycles in gasoline: Evidence from the U.S. FTC Bureau of Economics Working Paper 303 (published in *Review of Industrial Organization*). https://www.ftc.gov/reports/edgeworth-price-cycles-gasoline-evidence-us
  - Used in [WS5](#ws5-edgeworth-price-cycles-cincinnati-first). No existing issue; open one for WS5.

## Appendix C. Rows for the research citations ledger

These rows follow the column layout of the "Implemented Research Papers Index" in `RESEARCH_CITATIONS.md`, including its plain "Issue #N" style. Rows 17 and 18 cover work that is already implemented; copy them (without the header row shown here) into the end of that table. The remaining papers are planned, so they are set out as a separate "Roadmap Research Papers" table with a "Target Module(s)" column; once the workstream issues exist, replace "roadmap WSn" with the issue number. Paper titles link to each paper's DOI, except Gibbs and Candès (arXiv, with the NeurIPS PDF) and the Noel, FTC and Doyle et al. papers (freely available versions). Module links are relative to the repo root, as in `RESEARCH_CITATIONS.md`.

### Append to the Implemented Research Papers Index

| # | Paper Title & arXiv Link | Authors | Date | Implemented Module(s) | Key Methodological Contribution & Implementation Details |
| :-: | :--- | :--- | :-: | :--- | :--- |
| **17** | [**Comparing Predictive Accuracy**](https://doi.org/10.1080/07350015.1995.10524599) & [**Testing the Equality of Prediction Mean Squared Errors**](https://doi.org/10.1016/S0169-2070%2896%2900719-4) | Francis X. Diebold, Roberto S. Mariano; David Harvey, Stephen Leybourne, Paul Newbold | 1995 / 1997 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`scripts/evaluate_model_hierarchy.py`](scripts/evaluate_model_hierarchy.py) | **Forecast-Accuracy Significance Testing (Diebold–Mariano with Harvey–Leybourne–Newbold Correction)**: Tests whether the loss differential between two competing forecasts has zero mean, with a small-sample and horizon correction for overlapping $h$-step errors. Used in the 5-tier nested evaluation hierarchy's promotion gate against naive persistence (Issue #362). |
| **18** | [**Do Gasoline Prices Respond Asymmetrically to Crude Oil Price Changes?**](https://doi.org/10.1162/003355397555118) | Severin Borenstein, A. Colin Cameron, Richard Gilbert | 1997 | [`src/asymmetric_ecm.py`](src/asymmetric_ecm.py) | **Asymmetric Retail Pass-Through ("Rockets and Feathers")**: Error-correction model in which retail prices respond faster to wholesale cost increases than to decreases, with separate adjustment speeds for positive and negative deviations from the long-run margin. Implemented as `AsymmetricECM` and `fit_regional_asymmetric_ecm` (Issue #402); not yet called by the metro pipelines. |

### New table: Roadmap Research Papers

| # | Paper Title & Link | Authors | Date | Target Module(s) | Planned Contribution & Related Issues |
| :-: | :--- | :--- | :-: | :--- | :--- |
| **R1** | [**Estimation and Inference of Impulse Responses by Local Projections**](https://doi.org/10.1257/0002828053828518) | Òscar Jordà | 2005 | [`src/event_calibration.py`](src/event_calibration.py)<br/>[`src/feature_engineering.py`](src/feature_engineering.py) | **Horizon-by-Horizon Event Impulse Responses**: Regresses $y_{t+h} - y_t$ on deduplicated event intensity and controls separately for each horizon, estimating each category's response curve directly instead of assuming exponential decay with hand-set half-lives, and separating impact size from decay speed (roadmap WS4; related Issues #361 & #355). |
| **R2** | [**Spectra of Some Self-Exciting and Mutually Exciting Point Processes**](https://doi.org/10.1093/biomet/58.1.83) | Alan G. Hawkes | 1971 | [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py)<br/>[`src/feature_engineering.py`](src/feature_engineering.py) | **Self-Exciting Event Intensity**: Models the clustering of news events, in which each event temporarily raises the rate of further events, to forecast near-term event intensity and normalize busy news days (roadmap WS4; related Issue #355). |
| **R3** | [**A Theory of Dynamic Oligopoly, II: Price Competition, Kinked Demand Curves, and Edgeworth Cycles**](https://doi.org/10.2307/1911701); [**Edgeworth Price Cycles**](https://www.noeleconomics.com/articles/NOEL_palgrave.pdf); [**Edgeworth Price Cycles in Gasoline: Evidence from the U.S.**](https://www.ftc.gov/reports/edgeworth-price-cycles-gasoline-evidence-us); [**Edgeworth Cycles Revisited**](https://dspace.mit.edu/handle/1721.1/64740) | Eric Maskin, Jean Tirole; Michael D. Noel; Paul R. Zimmerman, John M. Yun, Christopher T. Taylor; Joseph J. Doyle, Erich Muehlegger, Krislert Samphantharak | 1988 / 2011 / 2010 / 2010 | [`src/locations/cincinnati/`](src/locations/cincinnati/) | **Retail Price-Cycle Diagnostics & Restoration-Hazard Model**: Tests each metro for sawtooth cycles (sharp restorations followed by gradual undercutting) with asymmetry statistics and a two-regime Markov-switching model, then forecasts the chance of a restoration within the horizon from the current margin and the days since the last restoration, $P_{t,h} = \text{logit}^{-1}(a + b\,m_t + c\,d_t)$ (roadmap WS5, starting with Cincinnati; no existing issue). |
| **R4** | [**Time Series Analysis by State Space Methods**](https://doi.org/10.1093/acprof:oso/9780199641178.001.0001) (2nd ed.) | James Durbin, Siem Jan Koopman | 2012 | [`src/prediction_logger.py`](src/prediction_logger.py)<br/>[`src/eia_retail_feed.py`](src/eia_retail_feed.py)<br/>[`src/live_fuel_feed.py`](src/live_fuel_feed.py) | **Mixed-Frequency Kalman-Filter Price Nowcast**: Treats each metro's true average price as a latent local-level state read with source-specific bias and noise by AAA (daily), GasBuddy (daily) and EIA (weekly); the filtered estimate becomes the point-in-time forecast base and the smoothed estimate the matured ground truth (roadmap WS3; related Issues #403, #391 & #121). |
| **R5** | [**Generalized Autoregressive Conditional Heteroskedasticity**](https://doi.org/10.1016/0304-4076%2886%2990063-1) & [**A Simple Approximate Long-Memory Model of Realized Volatility**](https://doi.org/10.1093/jjfinec/nbp001) | Tim Bollerslev; Fulvio Corsi | 1986 / 2009 | [`src/models.py`](src/models.py) | **Wholesale Volatility Forecasting (GARCH & HAR-RV)**: Forecasts the RBOB variance path with GARCH(1,1), $\sigma^2_{t+1} = \omega + \alpha\,\varepsilon^2_t + \beta\,\sigma^2_t$, or HAR realized volatility, aggregates it over the horizon into Student-$t$ return distributions, and replaces the hand-set volatility gate constants (roadmap WS6; related Issues #214, #44 & #119). |
| **R6** | [**Adaptive Conformal Inference Under Distribution Shift**](https://arxiv.org/abs/2106.00170) <br/>([PDF](https://proceedings.neurips.cc/paper/2021/file/0d441de75945e5acbc865406fc9a2559-Paper.pdf)) | Isaac Gibbs, Emmanuel Candès | 2021 | [`src/models.py`](src/models.py)<br/>[`src/prediction_logger.py`](src/prediction_logger.py) | **Adaptive Conformal Calibration**: Updates the working miscoverage rate after each observed hit or miss, $\alpha_{t+1} = \alpha_t + \gamma(\alpha^{*} - \text{miss}_t)$, so interval coverage holds as conditions drift, calibrating only on matured forecasts at the same horizon (roadmap WS7; related Issues #358, #394 & #214). |
| **R7** | [**Strictly Proper Scoring Rules, Prediction, and Estimation**](https://doi.org/10.1198/016214506000001437) | Tilmann Gneiting, Adrian E. Raftery | 2007 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`src/headline_arena_connector.py`](src/headline_arena_connector.py) | **Proper Scoring Rules (CRPS & Pinball Loss)**: Scores full predictive distributions with CRPS and quantile forecasts with pinball loss, rewarding forecasts that are both calibrated and sharp; basis for true P10/P50/P90 submissions to Headline Arena (roadmap WS6, WS7 & WS10; related Issues #182, #408, #358 & #44). |
| **R8** | [**Optimal Forecast Reconciliation for Hierarchical and Grouped Time Series Through Trace Minimization**](https://doi.org/10.1080/01621459.2018.1448825) | Shanika L. Wickramasuriya, George Athanasopoulos, Rob J. Hyndman | 2019 | [`src/locations/`](src/locations/)<br/>[`src/regional_metadata.py`](src/regional_metadata.py) | **MinT Hierarchical Forecast Reconciliation**: Makes metro, state or PADD, and national forecasts coherent, $\tilde{y} = S(S^{\top}W^{-1}S)^{-1}S^{\top}W^{-1}\hat{y}$, using volume-weighted aggregation, alongside partial pooling of per-metro pass-through coefficients (roadmap WS8; no existing issue). |
| **R9** | [**Fuel Tax Incidence and Supply Conditions**](https://doi.org/10.1016/j.jpubeco.2011.04.003) | Justin Marion, Erich Muehlegger | 2011 | [`src/state_open_data.py`](src/state_open_data.py)<br/>[`src/carb_compliance.py`](src/carb_compliance.py)<br/>[`src/rvp_regulations.py`](src/rvp_regulations.py) | **Fuel Tax Pass-Through as a Known-Future Input**: Evidence that state gasoline and diesel taxes are on average fully passed through to consumers, with lower pass-through when supply is constrained (notably for diesel at high refinery utilization) and in states that use two gasoline blends, supports feeding scheduled excise changes and blend switches into forecasts as dated, known-in-advance inputs (roadmap WS9; related Issues #141 & #383). |
| **R10** | [**A Simple Nonparametric Test of Predictive Performance**](https://doi.org/10.1080/07350015.1992.10509922) & [**A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix**](https://doi.org/10.2307/1913610) | M. Hashem Pesaran, Allan Timmermann; Whitney K. Newey, Kenneth D. West | 1992 / 1987 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`src/prediction_logger.py`](src/prediction_logger.py) | **Directional-Accuracy Testing & HAC Inference for Overlapping Targets**: Tests whether directional hit rates beat chance given the base rates of up and down moves, and uses heteroskedasticity- and autocorrelation-consistent standard errors with $h-1$ lags for regressions on overlapping 5-day targets (roadmap WS10 & WS4; related Issues #47, #395, #117, #396 & #397). |
| **R11** | [**A Test for Superior Predictive Ability**](https://doi.org/10.1198/073500105000000063); [**The Model Confidence Set**](https://doi.org/10.3982/ECTA5771); [**Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing**](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x) | Peter R. Hansen; Peter R. Hansen, Asger Lunde, James M. Nason; Yoav Benjamini, Yosef Hochberg | 2005 / 2011 / 1995 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`src/praxist_engine.py`](src/praxist_engine.py) | **Data-Snooping Controls for Many Model Comparisons**: Superior Predictive Ability test and Model Confidence Set for comparing many forecast variants against a benchmark, plus false-discovery-rate control across regions; basis for a feature admission rule (roadmap WS10; related Issues #188 & #362). |

---

*Prepared with Microsoft Copilot from a static review of the dev-branch snapshot. Figures drawn from the prediction log reflect the committed data as of 24 September 2026.*
