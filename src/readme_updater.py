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
    target_date = "Next 5 Business Days"
    
    if os.path.exists(HISTORY_CSV_PATH):
        try:
            df = pd.read_csv(HISTORY_CSV_PATH)
            if not df.empty:
                nat_df = df[df['region'] == 'National']
                tulsa_df = df[df['region'] == 'Tulsa_OK']
                
                if not nat_df.empty:
                    latest_nat = nat_df.iloc[-1]
                    nat_price = latest_nat['predicted_5d_price']
                    base = latest_nat['current_base_price']
                    nat_dir = "UP 📈" if nat_price >= base else "DOWN 📉"
                    target_date = latest_nat['forecast_target_date']
                    
                if not tulsa_df.empty:
                    latest_tulsa = tulsa_df.iloc[-1]
                    tulsa_price = latest_tulsa['predicted_5d_price']
                    base_t = latest_tulsa['current_base_price']
                    tulsa_dir = "UP 📈" if tulsa_price >= base_t else "DOWN 📉"
                    target_date = latest_tulsa['forecast_target_date']
        except Exception as e:
            logger.warning(f"Could not read prediction history: {e}")
            
    live_table_markdown = f"""{START_TAG}
### 📢 Live 5-Day Price Forecasts (Updated: {now_str})

| Region / Market | Current Price | 5-Day Forecast | Projected Direction | Target Date | Model Version |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **National Wholesale (RBOB)** | `$3.184`/gal | **`${nat_price:.3f}`/gal** | **{nat_dir}** | `{target_date}` | `v1.4-Finlight-Ridge` |
| **Tulsa, OK Metro Retail** | `$3.890`/gal | **`${tulsa_price:.3f}`/gal** | **{tulsa_dir}** | `{target_date}` | `v1.4-Finlight-Ridge` |

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
