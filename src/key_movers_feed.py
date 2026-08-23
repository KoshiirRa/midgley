"""
Key Market Movers Intelligence Module (src/key_movers_feed.py)
Monitors high-impact global figures influencing unleaded gas and crude oil prices:
1. Saudi Energy Minister (Prince Abdulaziz bin Salman) - OPEC+ Quotas & Surprise Cuts
2. Federal Reserve Chair (Jerome Powell) - Interest Rates, USD DXY & Macro Demand
3. US Secretary of Energy & DOE - Strategic Petroleum Reserve (SPR) Releases/Buybacks
4. IEA Executive Director (Fatih Birol) - Global Oil Demand Growth & Emergency Stock Releases
5. Russian Deputy Prime Minister (Alexander Novak) - OPEC+ Production Compliance & Exports
6. EU Sanctions & Energy Commissioners - Russian Maritime Oil Price Cap Enforcement
7. EIA Lead Analysts - Weekly Petroleum Status Report (Stock Draws/Builds)
"""

import os
import json
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

KEY_MOVERS = {
    "Prince_Abdulaziz_bin_Salman": {
        "title": "Saudi Arabian Energy Minister",
        "institution": "Ministry of Energy / OPEC+",
        "primary_mechanism": "Surprise voluntary production cuts, OPEC+ quota enforcement, warnings to short-sellers.",
        "avg_historical_market_impact": "+2.5% to +4.8% RBOB price jump on surprise cut announcements."
    },
    "Jerome_Powell": {
        "title": "Federal Reserve Chair",
        "institution": "US Federal Reserve",
        "primary_mechanism": "FOMC interest rate policy, inflation guidance, US Dollar ($DXY$) strength impacting global oil demand.",
        "avg_historical_market_impact": "-1.2% to -2.1% demand destruction sell-off on aggressive rate hikes."
    },
    "US_Energy_Secretary_DOE": {
        "title": "US Secretary of Energy",
        "institution": "US Department of Energy (DOE)",
        "primary_mechanism": "Strategic Petroleum Reserve (SPR) emergency releases (ceiling) and SPR repurchase tender offers ($70-$79 floor).",
        "avg_historical_market_impact": "-2.5% RBOB drop on SPR release; +1.2% support on SPR refill buybacks."
    },
    "Fatih_Birol": {
        "title": "IEA Executive Director",
        "institution": "International Energy Agency (Paris)",
        "primary_mechanism": "Monthly IEA Oil Market Report (OMR) demand revisions and coordinated 31-member emergency stock drawdowns.",
        "avg_historical_market_impact": "-1.5% to +1.8% demand sentiment shift."
    },
    "Alexander_Novak": {
        "title": "Russian Deputy Prime Minister",
        "institution": "Russian Government / OPEC+ Joint Ministerial Committee",
        "primary_mechanism": "Russian crude export cut commitments, shadow fleet maritime logistics, and OPEC+ co-chair announcements.",
        "avg_historical_market_impact": "+1.8% to +3.2% crude/gasoline rally on export reduction announcements."
    },
    "EU_Sanctions_Commissioners": {
        "title": "EU Climate & Energy Commissioners",
        "institution": "European Commission (Brussels)",
        "primary_mechanism": "G7/EU $60/bbl Russian crude price cap enforcement, maritime insurance bans, and EU ETS carbon tariffs.",
        "avg_historical_market_impact": "+1.5% transatlantic refined product spread widening."
    }
}

def get_key_movers_event_feed() -> pd.DataFrame:
    """
    Returns historical dataset of high-impact statements and actions from top global energy figures.
    """
    events = [
        {
            "date": "2022-03-31",
            "entity": "US_Energy_Secretary_DOE",
            "person": "Jennifer Granholm / Biden Admin",
            "headline": "US announces historic 180 million barrel Strategic Petroleum Reserve (SPR) release over 6 months; gasoline futures drop.",
            "impact_category": "SPR_Release",
            "market_reaction_pct": -3.85
        },
        {
            "date": "2023-06-04",
            "entity": "Prince_Abdulaziz_bin_Salman",
            "person": "Prince Abdulaziz bin Salman (Saudi Arabia)",
            "headline": "Saudi Arabia announces solo 'Saudi Lollipop' voluntary oil production cut of 1.0 million barrels per day starting July; crude surges +4%.",
            "impact_category": "OPEC_Surprise_Cut",
            "market_reaction_pct": 4.12
        },
        {
            "date": "2023-07-26",
            "entity": "Jerome_Powell",
            "person": "Jerome Powell (Fed Chair)",
            "headline": "Fed raises interest rates to 22-year high of 5.50%; Powell emphasizes data-dependent stance, dampening energy demand outlook.",
            "impact_category": "Fed_Rate_Hike",
            "market_reaction_pct": -1.15
        },
        {
            "date": "2023-10-19",
            "entity": "US_Energy_Secretary_DOE",
            "person": "US Department of Energy",
            "headline": "US DOE solicits offers to buy back 6 million barrels of crude for Strategic Petroleum Reserve refill at $79/bbl target price.",
            "impact_category": "SPR_Refill_Floor",
            "market_reaction_pct": 1.45
        },
        {
            "date": "2024-02-15",
            "entity": "Fatih_Birol",
            "person": "Fatih Birol (IEA)",
            "headline": "IEA trims 2024 global oil demand growth forecast by 100,000 bpd citing slowing Chinese industrial activity.",
            "impact_category": "IEA_Demand_Downgrade",
            "market_reaction_pct": -1.38
        },
        {
            "date": "2024-06-03",
            "entity": "Alexander_Novak",
            "person": "Alexander Novak (Russia)",
            "headline": "Russia promises to compensate for overproduction in Q1 by deepening crude export cuts through Q3 2024.",
            "impact_category": "Russian_Export_Cut",
            "market_reaction_pct": 1.90
        }
    ]
    
    df = pd.DataFrame(events)
    df['date'] = pd.to_datetime(df['date'])
    return df

if __name__ == "__main__":
    df = get_key_movers_event_feed()
    print(f"Loaded {len(df)} Key Market Movers Events.")
    print(json.dumps(KEY_MOVERS, indent=2))
