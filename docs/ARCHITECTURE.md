# Technical Architecture & Modeling Methodology

## 1. Executive Summary

Forecasting wholesale unleaded gasoline prices ($RB=F$) presents a unique challenge: price movements are driven by a combination of continuous financial variables (crude oil futures, crack spreads, seasonal demand) and discrete, non-linear qualitative shocks (geopolitical conflict, hurricane refinery outages, OPEC quota shifts).

This architecture implements a **Hybrid LLM + Regularized Quantitative Forecasting System** that merges both quantitative price dynamics and LLM-extracted qualitative event signals.

---

## 2. Quantitative Feature Formulations

The quantitative module computes financial signals derived from daily trading data:

1. **Crack Spread Proxy:**
   \[
   \text{CrackSpread}_t = \text{Gasoline Price ($/gal)}_t - \frac{\text{WTI Crude ($/bbl)}_t}{42.0}
   \]
   *Represents the refining margin per gallon.*

2. **Price Returns & Momentum:**
   \[
   R_t^{(1)} = \frac{P_t - P_{t-1}}{P_{t-1}}, \quad R_t^{(5)} = \frac{P_t - P_{t-5}}{P_{t-5}}
   \]

3. **Simple Moving Averages (SMA):**
   \[
   \text{SMA}_k(t) = \frac{1}{k}\sum_{i=0}^{k-1} P_{t-i}, \quad k \in \{7, 14, 30\}
   \]

4. **Rolling Volatility:**
   \[
   \sigma_{14}(t) = \text{std}\left(R_{t-13}^{(1)}, \dots, R_t^{(1)}\right)
   \]

5. **Cyclical Seasonality:**
   \[
   \sin\left(\frac{2\pi \cdot \text{DayOfYear}}{365.25}\right), \quad \cos\left(\frac{2\pi \cdot \text{DayOfYear}}{365.25}\right)
   \]

---

## 3. Qualitative LLM Feature Fusion & Memory Decay

### News Factor Scoring
Raw text headlines are converted into scalar factors in \([-1.0, +1.0]\) via LLM JSON extraction:
- $S_{\text{geo}}$: Geopolitical Risk
- $S_{\text{supply}}$: Supply Disruption
- $S_{\text{demand}}$: Demand Sentiment
- $S_{\text{opec}}$: OPEC Policy Impact

### Half-Life Memory Decay Formula
To prevent single-day event signals from disappearing immediately, continuous feature series are generated using an exponential decay filter with half-life $t_{1/2} = 5.0$ business days:

\[
\lambda = \frac{\ln(2)}{5.0} \approx 0.1386
\]
\[
F_{\text{event}}(t) = F_{\text{event}}(t-1) \cdot e^{-\lambda} + S_{\text{headline}}(t)
\]

---

## 4. Chronological Validation & Model Fitting

To prevent lookahead bias (temporal data leakage):
1. The dataset is ordered chronologically by date.
2. The initial $80\%$ of trading days form `Train`, and the final $20\%$ form the out-of-time `Test` set.
3. Features are standard-scaled using parameters fit **exclusively** on the training set:
   \[
   z = \frac{x - \mu_{\text{train}}}{\sigma_{\text{train}}}
   \]
4. **Ridge Regularization:**
   Linear regularized estimation minimizes the objective:
   \[
   \min_{w} \| y - Xw \|_2^2 + \alpha \|w\|_2^2, \quad \alpha = 10.0
   \]

---

## 5. Evaluation Metrics

Model performance is measured on the out-of-time test set using:
- **Mean Absolute Error (MAE):** $\frac{1}{n}\sum |y_i - \hat{y}_i|$
- **Root Mean Squared Error (RMSE):** $\sqrt{\frac{1}{n}\sum (y_i - \hat{y}_i)^2}$
- **Mean Absolute Percentage Error (MAPE):** $\frac{100\%}{n}\sum \left|\frac{y_i - \hat{y}_i}{y_i}\right|$
- **Directional Hit Rate:** $\frac{1}{n}\sum \mathbb{I}\left(\text{sign}(y_i - y_{\text{curr}}) == \text{sign}(\hat{y}_i - y_{\text{curr}})\right)$
