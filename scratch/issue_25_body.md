## 🐛 Bug Description

In the **Live 5-Day Price Forecasts** table and public dashboard, the **Tulsa, OK Metro Retail** 5-day forecast displays a drastic, unanchored drop from **$3.890/gal** (current live pump price) down to **$3.156/gal** (**DOWN 📉**).

While the National Wholesale (RBOB) forecast properly shifts from $3.184/gal to $3.144/gal (-$0.040/gal), the Tulsa regional retail forecast plummets by **-$0.734/gal** in 5 business days because raw wholesale RBOB predictions are being logged directly as the retail forecast.

---

## 📸 Observed Behavior in Live Dashboard Table

| Region / Market | Current Price | 5-Day Forecast | Projected Direction |
| :--- | :--- | :--- | :--- |
| **National Wholesale (RBOB)** | `$3.184 /gal` | `$3.144 /gal` | **DOWN 📉** |
| **Tulsa, OK Metro Retail** | `$3.890 /gal` | `$3.156 /gal` | **DOWN 📉** |

*Notice that $3.156/gal is actually the wholesale RBOB prediction (+ $0.012 rack difference), completely ignoring the current $3.890/gal Tulsa retail pump price baseline.*

---

## 🔍 Root Cause Analysis

1. **Target Construction in Feature Matrix ([`src/feature_engineering.py`](file:///C:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py#L113)):**
   ```python
   df[f'target_price_{forecast_horizon}d'] = df['gasoline_rbob'].shift(-forecast_horizon)
   ```
   The forecast target $y$ is hardcoded to wholesale RBOB futures (`gasoline_rbob`), even when running the localized Tulsa dataset containing `tulsa_retail_gasoline`.

2. **Unadjusted Prediction Logging ([`tulsa_main.py`](file:///C:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tulsa_main.py#L140-L148)):**
   When logging forecasts in Step 6 of `tulsa_main.py`:
   ```python
   test_current_prices = splits['test_df']['tulsa_retail_gasoline'] if 'tulsa_retail_gasoline' in splits['test_df'].columns else splits['test_df']['gasoline_rbob']
   preds_hybrid = results['predictions_hybrid'] # Raw RBOB wholesale predictions (~$3.156)
   
   pred_log_df = pd.DataFrame({
       'date': test_dates.values,
       'current_price': test_current_prices.values, # $3.890
       'predicted_5d_price': preds_hybrid          # $3.156! (Wholesale forecast, not retail)
   })
   ```

3. **Downstream MLOps & Dashboard Distortion:**
   - [`src/readme_updater.py`](file:///C:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/readme_updater.py) and [`src/dashboard_generator.py`](file:///C:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py) pull `predicted_5d_price` directly from `data/prediction_history.csv`, displaying `$3.156/gal` to end users.
   - [`src/prediction_logger.py`](file:///C:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/prediction_logger.py) calculates `error_dollars = |3.890 - 3.156| = 0.734`, artificially inflating the Tulsa MAE metric to **0.5611** (vs National MAE of 0.1069).

---

## 🛠️ Proposed Solution

1. **Re-anchor Retail Predictions in `tulsa_main.py`:**
   Apply dynamic rack margin re-anchoring or return percentage to `live_pump_price` before logging predictions:
   ```python
   # Option A: Baseline return scaling
   baseline_return = (preds_hybrid - splits['test_df']['gasoline_rbob']) / splits['test_df']['gasoline_rbob']
   tulsa_preds = test_current_prices * (1.0 + baseline_return)
   
   # Option B: Target construction on tulsa_retail_gasoline
   target_col = 'tulsa_retail_gasoline' if 'tulsa_retail_gasoline' in df.columns else 'gasoline_rbob'
   df[f'target_price_{forecast_horizon}d'] = df[target_col].shift(-forecast_horizon)
   ```
2. **Backfill & Clean Up History:**
   Re-evaluate and backfill historical records in `data/prediction_history.csv` so that Tulsa retail predictions align with live pump baseline prices.
