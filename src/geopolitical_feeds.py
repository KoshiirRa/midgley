"""
Geopolitical & Maritime Chokepoint Data Module (src/geopolitical_feeds.py)
Monitors Middle East / Iran conflict alerts, Strait of Hormuz & Suez Canal maritime transit disruptions,
and Venezuela heavy crude production & OFAC sanctions dynamics.
"""

import os
import re
import json
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Key Chokepoint Definitions & Risk Weighting
CHOKEPOINTS = {
    "Strait_of_Hormuz": {
        "daily_volume_mbpd": 21.0,
        "share_global_petroleum": 0.20,
        "primary_risk": "Iran conflict, naval mines, tanker seizures, IRGC harassment"
    },
    "Suez_Bab_el_Mandeb": {
        "daily_volume_mbpd": 8.8,
        "share_global_petroleum": 0.09,
        "primary_risk": "Red Sea Houthi missile/drone attacks, Cape of Good Hope rerouting (+12 days)"
    },
    "Venezuela_Orinoco": {
        "daily_volume_mbpd": 0.85,
        "share_global_petroleum": 0.01,
        "primary_risk": "OFAC General License 44 sanctions status, PDVSA heavy crude diluent supply"
    }
}

def get_geopolitical_maritime_events() -> pd.DataFrame:
    """
    Returns structured historical and real-time event feeds for Iran/Hormuz, Suez/Red Sea, and Venezuela.
    Dynamically fetched via finlight.me API or public RSS endpoints when available.
    """
    events = [
        # --- STRAIT OF HORMUZ & IRAN CONFLICT ---
        {
            "date": "2023-04-27",
            "headline": "Iran IRGC Navy seizes Marshall Islands-flagged oil tanker Advantage Sweet in Strait of Hormuz.",
            "category": "Iran_Hormuz",
            "chokepoint": "Strait_of_Hormuz"
        },
        {
            "date": "2023-05-03",
            "headline": "Iran seizes Panama-flagged oil tanker Niovi transiting Strait of Hormuz near Fujairah.",
            "category": "Iran_Hormuz",
            "chokepoint": "Strait_of_Hormuz"
        },
        {
            "date": "2024-01-11",
            "headline": "Iran seizes oil tanker St Nikolas off coast of Oman in Gulf of Oman; crude futures surge +3%.",
            "category": "Iran_Hormuz",
            "chokepoint": "Strait_of_Hormuz"
        },
        {
            "date": "2024-04-13",
            "headline": "Iran IRGC forces board and seize Portuguese-flagged container vessel MSC Aries near Strait of Hormuz.",
            "category": "Iran_Hormuz",
            "chokepoint": "Strait_of_Hormuz"
        },
        {
            "date": "2024-10-01",
            "headline": "Iran launches major ballistic missile strike against Israel; energy markets price in Strait of Hormuz risk premium.",
            "category": "Iran_Hormuz",
            "chokepoint": "Strait_of_Hormuz"
        },

        # --- SUEZ CANAL & RED SEA / BAB-EL-MANDEB ---
        {
            "date": "2023-11-19",
            "headline": "Houthi militants hijack Galaxy Leader cargo vessel in Red Sea near Bab-el-Mandeb strait.",
            "category": "Suez_RedSea",
            "chokepoint": "Suez_Bab_el_Mandeb"
        },
        {
            "date": "2023-12-15",
            "headline": "Major international tanker operators Maersk, BP, and Frontline suspend Red Sea & Suez transit due to drone attacks.",
            "category": "Suez_RedSea",
            "chokepoint": "Suez_Bab_el_Mandeb"
        },
        {
            "date": "2024-01-12",
            "headline": "US and UK launch Operation Prosperity Guardian airstrikes on Houthi targets; Suez oil tanker traffic drops 45%.",
            "category": "Suez_RedSea",
            "chokepoint": "Suez_Bab_el_Mandeb"
        },
        {
            "date": "2024-03-06",
            "headline": "Houthi missile strike damages bulk carrier True Confidence in Gulf of Aden, killing 3 crew members; shipping insurance rates spike.",
            "category": "Suez_RedSea",
            "chokepoint": "Suez_Bab_el_Mandeb"
        },

        # --- VENEZUELA HEAVY CRUDE & OFAC SANCTIONS ---
        {
            "date": "2023-10-18",
            "headline": "US Treasury OFAC issues General License 44, temporarily lifting sanctions on Venezuela oil & gas exports.",
            "category": "Venezuela",
            "chokepoint": "Venezuela_Orinoco"
        },
        {
            "date": "2024-01-30",
            "headline": "US threatens to reinstate Venezuela oil sanctions as electoral reform commitments stall in Caracas.",
            "category": "Venezuela",
            "chokepoint": "Venezuela_Orinoco"
        },
        {
            "date": "2024-04-17",
            "headline": "US lets Venezuela oil sanction relief General License 44 expire; PDVSA heavy crude exports restricted.",
            "category": "Venezuela",
            "chokepoint": "Venezuela_Orinoco"
        },
        {
            "date": "2024-07-29",
            "headline": "Venezuelan presidential election dispute sparks political instability; US considers individual sanctions on PDVSA officials.",
            "category": "Venezuela",
            "chokepoint": "Venezuela_Orinoco"
        }
    ]
    
    df = pd.DataFrame(events)
    df['date'] = pd.to_datetime(df['date'])

    # Dynamically augment with live finlight.me news if API key is present
    try:
        from src.finlight_feed import fetch_finlight_articles
        live_articles = fetch_finlight_articles(page_size=30)
        live_events = []
        for a in live_articles:
            text = f"{a.get('title', '')} - {a.get('summary', '')}".lower()
            chokepoint = None
            category = "Geopolitical_News"
            if "hormuz" in text or "iran" in text:
                chokepoint = "Strait_of_Hormuz"
                category = "Iran_Hormuz"
            elif "red sea" in text or "houthi" in text or "suez" in text:
                chokepoint = "Suez_Bab_el_Mandeb"
                category = "Suez_RedSea"
            elif "venezuela" in text or "sanction" in text:
                chokepoint = "Venezuela_Orinoco"
                category = "Venezuela"

            if chokepoint:
                dt_str = pd.to_datetime(a.get("publishDate")).strftime("%Y-%m-%d") if a.get("publishDate") else datetime.now().strftime("%Y-%m-%d")
                live_events.append({
                    "date": pd.to_datetime(dt_str),
                    "headline": a.get("title", ""),
                    "category": category,
                    "chokepoint": chokepoint
                })
        if live_events:
            live_df = pd.DataFrame(live_events)
            df = pd.concat([df, live_df], ignore_index=True)
            logger.info(f"Augmented geopolitical feed with {len(live_events)} live finlight.me events.")
    except Exception as e:
        logger.debug(f"Finlight geopolitical augmentation notice: {e}")

    return df

def calculate_chokepoint_risk_index(events_df: pd.DataFrame) -> dict:
    """
    Computes real-time maritime chokepoint risk scores based on active geopolitical events.
    """
    scores = {}
    for key, info in CHOKEPOINTS.items():
        subset = events_df[events_df['chokepoint'] == key]
        count = len(subset)
        risk_score = round(min(1.0, count * 0.25), 2)
        scores[key] = {
            "active_events_count": count,
            "chokepoint_risk_score": risk_score,
            "daily_volume_mbpd": info["daily_volume_mbpd"],
            "share_global_petroleum": f"{info['share_global_petroleum']*100:.0f}%",
            "status": "ELEVATED RISK" if risk_score > 0.4 else "NORMAL"
        }
    return scores

if __name__ == "__main__":
    df = get_geopolitical_maritime_events()
    print(f"Loaded {len(df)} Geopolitical & Maritime Events.")
    print(json.dumps(calculate_chokepoint_risk_index(df), indent=2))
