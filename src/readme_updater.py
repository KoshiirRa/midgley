"""
README Live Forecast Updater (src/readme_updater.py)
Reads the latest predictions from prediction_history.csv / model outputs
and automatically updates the Live Forecast Summary Table near the top of README.md.
"""

import os
import re
from typing import Optional, Any
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

README_PATH = "README.md"
HISTORY_CSV_PATH = os.path.join("data", "prediction_history.csv")

START_TAG = "<!-- START_LIVE_FORECAST -->"
END_TAG = "<!-- END_LIVE_FORECAST -->"

def update_readme_forecasts(
    readme_path: str = README_PATH,
    history_csv_path: str = HISTORY_CSV_PATH
):
    """Reads latest forecast records and injects formatted table into README.md."""
    if not os.path.exists(readme_path):
        logger.warning(f"{readme_path} not found.")
        return
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    # Defaults in case CSV is absent
    nat_price = 3.077
    nat_dir = "DOWN 📉"
    tulsa_price = 3.780
    tulsa_dir = "DOWN 📉"
    newark_price = 3.280
    newark_dir = "DOWN 📉"
    cin_oh_price = 3.350
    cin_oh_dir = "DOWN 📉"
    cin_ky_price = 3.225
    cin_ky_dir = "DOWN 📉"
    greenville_price = 3.150
    greenville_dir = "DOWN 📉"
    charlotte_price = 3.210
    charlotte_dir = "DOWN 📉"
    psl_price = 3.320
    psl_dir = "DOWN 📉"
    oakland_price = 5.440
    oakland_dir = "DOWN 📉"
    bayarea_price = 5.540
    bayarea_dir = "DOWN 📉"

    # Base price defaults
    base_nat = 3.184
    base_tulsa = 3.890
    base_newark = 3.350
    base_cin_oh = 3.450
    base_cin_ky = 3.325
    base_greenville = 3.250
    base_charlotte = 3.310
    base_psl = 3.420
    base_oakland = 5.550
    base_bayarea = 5.650

    target_nat = "Next 5 Business Days"
    target_tulsa = "Next 5 Business Days"
    target_newark = "Next 5 Business Days"
    target_cin_oh = "Next 5 Business Days"
    target_cin_ky = "Next 5 Business Days"
    target_greenville = "Next 5 Business Days"
    target_charlotte = "Next 5 Business Days"
    target_psl = "Next 5 Business Days"
    target_oakland = "Next 5 Business Days"
    target_bayarea = "Next 5 Business Days"
    
    def get_latest_valid_region_forecast(df: pd.DataFrame, region: str) -> Optional[pd.Series]:
        if df.empty or 'region' not in df.columns:
            return None
        reg_df = df[df['region'] == region]
        if reg_df.empty:
            return None
        
        # Prioritize prospective live runs and 5-day horizon (Issue #428)
        if 'run_type' in reg_df.columns:
            live_df = reg_df[
                (~reg_df['run_type'].astype(str).str.contains("RETROSPECTIVE", case=False)) &
                (~reg_df['run_type'].astype(str).str.contains("TEST", case=False))
            ]
        else:
            live_df = reg_df
        if not live_df.empty and 'forecast_horizon_days' in live_df.columns:
            h5_df = live_df[live_df['forecast_horizon_days'].fillna(5).astype(float) == 5.0]
            if not h5_df.empty:
                live_df = h5_df
                
        chosen_df = live_df if not live_df.empty else reg_df
        return chosen_df.iloc[-1]

    if os.path.exists(history_csv_path):
        try:
            df = pd.read_csv(history_csv_path)
            if not df.empty:
                latest_nat = get_latest_valid_region_forecast(df, 'National')
                latest_tulsa = get_latest_valid_region_forecast(df, 'Tulsa_OK')
                latest_newark = get_latest_valid_region_forecast(df, 'Newark_DE')
                latest_cin_oh = get_latest_valid_region_forecast(df, 'Cincinnati_OH')
                latest_cin_ky = get_latest_valid_region_forecast(df, 'Cincinnati_KY')
                latest_greenville = get_latest_valid_region_forecast(df, 'Greenville_NC')
                latest_charlotte = get_latest_valid_region_forecast(df, 'Charlotte_NC')
                latest_psl = get_latest_valid_region_forecast(df, 'Port_St_Lucie_FL')
                latest_oakland = get_latest_valid_region_forecast(df, 'Oakland_CA')
                latest_bayarea = get_latest_valid_region_forecast(df, 'BayArea_CA')
                
                if latest_nat is not None:
                    nat_price = float(latest_nat['predicted_5d_price'])
                    base_nat = float(latest_nat['current_base_price'])
                    nat_dir = "UP 📈" if nat_price >= base_nat else "DOWN 📉"
                    target_nat = str(latest_nat['forecast_target_date'])
                    
                if latest_tulsa is not None:
                    tulsa_price = float(latest_tulsa['predicted_5d_price'])
                    base_tulsa = float(latest_tulsa['current_base_price'])
                    tulsa_dir = "UP 📈" if tulsa_price >= base_tulsa else "DOWN 📉"
                    target_tulsa = str(latest_tulsa['forecast_target_date'])

                if latest_newark is not None:
                    newark_price = float(latest_newark['predicted_5d_price'])
                    base_newark = float(latest_newark['current_base_price'])
                    newark_dir = "UP 📈" if newark_price >= base_newark else "DOWN 📉"
                    target_newark = str(latest_newark['forecast_target_date'])

                if latest_cin_oh is not None:
                    cin_oh_price = float(latest_cin_oh['predicted_5d_price'])
                    base_cin_oh = float(latest_cin_oh['current_base_price'])
                    cin_oh_dir = "UP 📈" if cin_oh_price >= base_cin_oh else "DOWN 📉"
                    target_cin_oh = str(latest_cin_oh['forecast_target_date'])

                if latest_cin_ky is not None:
                    cin_ky_price = float(latest_cin_ky['predicted_5d_price'])
                    base_cin_ky = float(latest_cin_ky['current_base_price'])
                    cin_ky_dir = "UP 📈" if cin_ky_price >= base_cin_ky else "DOWN 📉"
                    target_cin_ky = str(latest_cin_ky['forecast_target_date'])

                if latest_greenville is not None:
                    greenville_price = float(latest_greenville['predicted_5d_price'])
                    base_greenville = float(latest_greenville['current_base_price'])
                    greenville_dir = "UP 📈" if greenville_price >= base_greenville else "DOWN 📉"
                    target_greenville = str(latest_greenville['forecast_target_date'])

                if latest_charlotte is not None:
                    charlotte_price = float(latest_charlotte['predicted_5d_price'])
                    base_charlotte = float(latest_charlotte['current_base_price'])
                    charlotte_dir = "UP 📈" if charlotte_price >= base_charlotte else "DOWN 📉"
                    target_charlotte = str(latest_charlotte['forecast_target_date'])

                if latest_psl is not None:
                    psl_price = float(latest_psl['predicted_5d_price'])
                    base_psl = float(latest_psl['current_base_price'])
                    psl_dir = "UP 📈" if psl_price >= base_psl else "DOWN 📉"
                    target_psl = str(latest_psl['forecast_target_date'])

                if latest_oakland is not None:
                    oakland_price = float(latest_oakland['predicted_5d_price'])
                    base_oakland = float(latest_oakland['current_base_price'])
                    oakland_dir = "UP 📈" if oakland_price >= base_oakland else "DOWN 📉"
                    target_oakland = str(latest_oakland['forecast_target_date'])

                if latest_bayarea is not None:
                    bayarea_price = float(latest_bayarea['predicted_5d_price'])
                    base_bayarea = float(latest_bayarea['current_base_price'])
                    bayarea_dir = "UP 📈" if bayarea_price >= base_bayarea else "DOWN 📉"
                    target_bayarea = str(latest_bayarea['forecast_target_date'])
        except Exception as e:
            logger.warning(f"Could not read prediction history: {e}")
            
    from src.prediction_logger import resolve_model_tag
    v_nat = resolve_model_tag("National", "Ridge")
    v_tulsa = resolve_model_tag("Tulsa", "Ridge")
    v_newark = resolve_model_tag("Newark", "Ridge")
    v_cin_oh = resolve_model_tag("Cincinnati_OH", "Ridge")
    v_cin_ky = resolve_model_tag("Cincinnati_KY", "Ridge")
    v_greenville = resolve_model_tag("Greenville", "Ridge")
    v_charlotte = resolve_model_tag("Charlotte", "Ridge")
    v_psl = resolve_model_tag("Port_St_Lucie", "Ridge")
    v_oakland = resolve_model_tag("Oakland", "Ridge")
    v_bayarea = resolve_model_tag("BayArea", "Ridge")

    live_table_markdown = f"""{START_TAG}
### 📢 Live 5-Day Price Forecasts (Updated: {now_str})

| Region / Market | Current Price | 5-Day Forecast | Projected Direction | Target Date | Model Version |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **National Wholesale (RBOB)** | `${base_nat:.3f}`/gal | **`${nat_price:.3f}`/gal** | **{nat_dir}** | `{target_nat}` | `{v_nat}` |
| **Tulsa, OK Metro Retail** | `${base_tulsa:.3f}`/gal | **`${tulsa_price:.3f}`/gal** | **{tulsa_dir}** | `{target_tulsa}` | `{v_tulsa}` |
| **Newark, DE Metro Retail** | `${base_newark:.3f}`/gal | **`${newark_price:.3f}`/gal** | **{newark_dir}** | `{target_newark}` | `{v_newark}` |
| **Cincinnati, OH Retail** | `${base_cin_oh:.3f}`/gal | **`${cin_oh_price:.3f}`/gal** | **{cin_oh_dir}** | `{target_cin_oh}` | `{v_cin_oh}` |
| **Northern Kentucky Retail** | `${base_cin_ky:.3f}`/gal | **`${cin_ky_price:.3f}`/gal** | **{cin_ky_dir}** | `{target_cin_ky}` | `{v_cin_ky}` |
| **Greenville, NC Metro Retail** | `${base_greenville:.3f}`/gal | **`${greenville_price:.3f}`/gal** | **{greenville_dir}** | `{target_greenville}` | `{v_greenville}` |
| **Charlotte, NC Metro Retail** | `${base_charlotte:.3f}`/gal | **`${charlotte_price:.3f}`/gal** | **{charlotte_dir}** | `{target_charlotte}` | `{v_charlotte}` |
| **Port St. Lucie, FL Waterborne** | `${base_psl:.3f}`/gal | **`${psl_price:.3f}`/gal** | **{psl_dir}** | `{target_psl}` | `{v_psl}` |
| **Oakland, CA Metro Retail** | `${base_oakland:.3f}`/gal | **`${oakland_price:.3f}`/gal** | **{oakland_dir}** | `{target_oakland}` | `{v_oakland}` |
| **SF Bay Area 9-County Avg** | `${base_bayarea:.3f}`/gal | **`${bayarea_price:.3f}`/gal** | **{bayarea_dir}** | `{target_bayarea}` | `{v_bayarea}` |

*🌐 View Interactive Web Dashboard & Public Visual Analytics at [koshiirra.github.io/midgley](https://koshiirra.github.io/midgley/)*
{END_TAG}"""


    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if START_TAG in content and END_TAG in content:
        pattern = re.compile(f"{re.escape(START_TAG)}.*?{re.escape(END_TAG)}", re.DOTALL)
        updated_content = pattern.sub(live_table_markdown, content)
    else:
        # Insert right after main header
        header_end = content.find("---")
        if header_end != -1:
            updated_content = content[:header_end] + live_table_markdown + "\n\n---\n" + content[header_end + 3:]
        else:
            updated_content = live_table_markdown + "\n\n" + content
            
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    logger.info("Successfully updated README.md live forecast table!")

if __name__ == "__main__":
    update_readme_forecasts()
