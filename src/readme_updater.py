"""
README Live Forecast Updater (src/readme_updater.py)
Reads the latest predictions from prediction_history.csv / model outputs
and automatically updates the Live Forecast Summary Table near the top of README.md.
"""

import os
import re
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

README_PATH = "README.md"
HISTORY_CSV_PATH = os.path.join("data", "prediction_history.csv")

START_TAG = "<!-- START_LIVE_FORECAST -->"
END_TAG = "<!-- END_LIVE_FORECAST -->"

def update_readme_forecasts():
    """Reads latest forecast records and injects formatted table into README.md."""
    if not os.path.exists(README_PATH):
        logger.warning("README.md not found.")
        return
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    # Defaults in case CSV is absent
    nat_price = 3.077
    nat_dir = "DOWN 📉"
    tulsa_price = 3.780
    tulsa_dir = "DOWN 📉"
    cin_oh_price = 3.350
    cin_oh_dir = "DOWN 📉"
    cin_ky_price = 3.225
    cin_ky_dir = "DOWN 📉"
    greenville_price = 3.150
    greenville_dir = "DOWN 📉"
    oakland_price = 5.440
    oakland_dir = "DOWN 📉"
    # Base price defaults
    base_nat = 3.184
    base_tulsa = 3.890
    base_newark = 3.350
    base_cin_oh = 3.450
    base_cin_ky = 3.325
    base_greenville = 3.250
    base_oakland = 5.550
    base_bayarea = 5.650
    target_nat = "Next 5 Business Days"
    target_tulsa = "Next 5 Business Days"
    target_newark = "Next 5 Business Days"
    target_cin_oh = "Next 5 Business Days"
    target_cin_ky = "Next 5 Business Days"
    target_greenville = "Next 5 Business Days"
    target_oakland = "Next 5 Business Days"
    target_bayarea = "Next 5 Business Days"
    
    if os.path.exists(HISTORY_CSV_PATH):
        try:
            df = pd.read_csv(HISTORY_CSV_PATH)
            if not df.empty:
                nat_df = df[df['region'] == 'National']
                tulsa_df = df[df['region'] == 'Tulsa_OK']
                newark_df = df[df['region'] == 'Newark_DE']
                cin_oh_df = df[df['region'] == 'Cincinnati_OH']
                cin_ky_df = df[df['region'] == 'Cincinnati_KY']
                greenville_df = df[df['region'] == 'Greenville_NC']
                charlotte_df = df[df['region'] == 'Charlotte_NC']
                psl_df = df[df['region'] == 'Port_St_Lucie_FL']
                oakland_df = df[df['region'] == 'Oakland_CA']
                bayarea_df = df[df['region'] == 'BayArea_CA']
                
                if not nat_df.empty:
                    latest_nat = nat_df.iloc[-1]
                    nat_price = latest_nat['predicted_5d_price']
                    base_nat = latest_nat['current_base_price']
                    nat_dir = "UP 📈" if nat_price >= base_nat else "DOWN 📉"
                    target_nat = latest_nat['forecast_target_date']
                    
                if not tulsa_df.empty:
                    latest_tulsa = tulsa_df.iloc[-1]
                    tulsa_price = latest_tulsa['predicted_5d_price']
                    base_tulsa = latest_tulsa['current_base_price']
                    tulsa_dir = "UP 📈" if tulsa_price >= base_tulsa else "DOWN 📉"
                    target_tulsa = latest_tulsa['forecast_target_date']

                if not newark_df.empty:
                    latest_newark = newark_df.iloc[-1]
                    newark_price = latest_newark['predicted_5d_price']
                    base_newark = latest_newark['current_base_price']
                    newark_dir = "UP 📈" if newark_price >= base_newark else "DOWN 📉"
                    target_newark = latest_newark['forecast_target_date']

                if not cin_oh_df.empty:
                    latest_cin_oh = cin_oh_df.iloc[-1]
                    cin_oh_price = latest_cin_oh['predicted_5d_price']
                    base_cin_oh = latest_cin_oh['current_base_price']
                    cin_oh_dir = "UP 📈" if cin_oh_price >= base_cin_oh else "DOWN 📉"
                    target_cin_oh = latest_cin_oh['forecast_target_date']

                if not cin_ky_df.empty:
                    latest_cin_ky = cin_ky_df.iloc[-1]
                    cin_ky_price = latest_cin_ky['predicted_5d_price']
                    base_cin_ky = latest_cin_ky['current_base_price']
                    cin_ky_dir = "UP 📈" if cin_ky_price >= base_cin_ky else "DOWN 📉"
                    target_cin_ky = latest_cin_ky['forecast_target_date']

                if not greenville_df.empty:
                    latest_greenville = greenville_df.iloc[-1]
                    greenville_price = latest_greenville['predicted_5d_price']
                    base_greenville = latest_greenville['current_base_price']
                    greenville_dir = "UP 📈" if greenville_price >= base_greenville else "DOWN 📉"
                    target_greenville = latest_greenville['forecast_target_date']

                if not oakland_df.empty:
                    latest_oakland = oakland_df.iloc[-1]
                    oakland_price = latest_oakland['predicted_5d_price']
                    base_oakland = latest_oakland['current_base_price']
                    oakland_dir = "UP 📈" if oakland_price >= base_oakland else "DOWN 📉"
                    target_oakland = latest_oakland['forecast_target_date']

                if not bayarea_df.empty:
                    latest_bayarea = bayarea_df.iloc[-1]
                    bayarea_price = latest_bayarea['predicted_5d_price']
                    base_bayarea = latest_bayarea['current_base_price']
                    bayarea_dir = "UP 📈" if bayarea_price >= base_bayarea else "DOWN 📉"
                    target_bayarea = latest_bayarea['forecast_target_date']
        except Exception as e:
            logger.warning(f"Could not read prediction history: {e}")
            
    live_table_markdown = f"""{START_TAG}
### 📢 Live 5-Day Price Forecasts (Updated: {now_str})

| Region / Market | Current Price | 5-Day Forecast | Projected Direction | Target Date | Model Version |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **National Wholesale (RBOB)** | `${base_nat:.3f}`/gal | **`${nat_price:.3f}`/gal** | **{nat_dir}** | `{target_nat}` | `v1.4-Finlight-Ridge` |
| **Tulsa, OK Metro Retail** | `${base_tulsa:.3f}`/gal | **`${tulsa_price:.3f}`/gal** | **{tulsa_dir}** | `{target_tulsa}` | `v1.4-Finlight-Ridge` |
| **Newark, DE Metro Retail** | `${base_newark:.3f}`/gal | **`${newark_price:.3f}`/gal** | **{newark_dir}** | `{target_newark}` | `v1.4-Finlight-Ridge` |
| **Cincinnati, OH Retail** | `${base_cin_oh:.3f}`/gal | **`${cin_oh_price:.3f}`/gal** | **{cin_oh_dir}** | `{target_cin_oh}` | `v1.4-Finlight-Ridge` |
| **Northern Kentucky Retail** | `${base_cin_ky:.3f}`/gal | **`${cin_ky_price:.3f}`/gal** | **{cin_ky_dir}** | `{target_cin_ky}` | `v1.4-Finlight-Ridge` |
| **Greenville, NC Metro Retail** | `${base_greenville:.3f}`/gal | **`${greenville_price:.3f}`/gal** | **{greenville_dir}** | `{target_greenville}` | `v1.4-Finlight-Ridge` |
| **Oakland, CA Metro Retail** | `${base_oakland:.3f}`/gal | **`${oakland_price:.3f}`/gal** | **{oakland_dir}** | `{target_oakland}` | `v1.4-Finlight-Ridge` |
| **SF Bay Area 9-County Avg** | `${base_bayarea:.3f}`/gal | **`${bayarea_price:.3f}`/gal** | **{bayarea_dir}** | `{target_bayarea}` | `v1.4-Finlight-Ridge` |

*🌐 View Interactive Web Dashboard & Public Visual Analytics at [koshiirra.github.io/midgley](https://koshiirra.github.io/midgley/)*
{END_TAG}"""


    with open(README_PATH, "r", encoding="utf-8") as f:
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
            
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    logger.info("Successfully updated README.md live forecast table!")

if __name__ == "__main__":
    update_readme_forecasts()
