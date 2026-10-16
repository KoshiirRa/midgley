"""
Houston Metro & USGC Refining Complex Regional Gas Price Forecasting Module (src/locations/houston/regional.py)
Fuses Houston & Gulf Coast market data, modeling the U.S. Gulf Coast refining complex
(ExxonMobil Baytown 560k bpd, Motiva Port Arthur 630k bpd, Marathon Galveston Bay 593k bpd, PEMEX Deer Park 312k bpd,
Valero Port Arthur 395k bpd, Chevron Pasadena 112k bpd), direct gate delivery and razor-thin retail rack margins,
Texas statutory fuel excise tax ($0.200/gal), Colonial Pipeline Lines 1 & 2 / Explorer Pipeline origin injection logistics,
Houston Ship Channel marine vessel traffic, and localized NOAA Weather Alerts for Harris County (TXZ213 / KHOU).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from src.noaa_weather import get_houston_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)


def fetch_houston_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Houston Metro & the U.S. Gulf Coast Refining Complex (PADD 3 Hub)
    and dynamically calibrates the retail series to match live pump prices:
      - Texas State Motor Fuel Tax: $0.200/gal (zero local municipal sales tax add-on)
      - Direct refinery gate proximity creating compressed wholesale-to-retail rack margins (~$0.65-$0.75/gal)
      - Spot Gulf Coast conventional gasoline wholesale pricing benchmark.
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("Houston_TX")["price"]
        except Exception:
            live_price = 2.850

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Houston & USGC region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_houston_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via EIA survey (Weekly Houston All Formulations EMM_EPMR_PTE_Y44HO_DPG)
    market_df['houston_tx_retail_gasoline'] = get_regional_retail_history("Houston_TX", market_df['date'], live_price)
    market_df['houston_retail_gasoline'] = market_df['houston_tx_retail_gasoline']

    # Spot Gulf Coast conventional gasoline benchmark column
    if 'spot_gulf_coast' not in market_df.columns:
        market_df['spot_gulf_coast'] = market_df['gasoline_rbob'] - 0.085

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['usgc_crack_spread'] = market_df['spot_gulf_coast'] - market_df['wti_crude_per_gal']
    market_df['houston_rack_margin'] = market_df['houston_retail_gasoline'] - market_df['spot_gulf_coast']

    return market_df


def _generate_synthetic_houston_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = 2.850
) -> pd.DataFrame:
    """Generates synthetic historical business day series for Houston & USGC Refining Complex."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 76.0 + np.cumsum(np.random.normal(0, 1.10, n))
    wti_crude = brent_crude - 4.2 + np.random.normal(0, 0.35, n)
    rbob = (wti_crude / 42.0) * 1.30 + np.cumsum(np.random.normal(0, 0.022, n))
    spot_gc = rbob - 0.085 + np.random.normal(0, 0.010, n)

    margin_houston = live_pump_price - spot_gc[-1]
    var_houston = 0.12 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.018, n)
    var_houston -= var_houston[-1]

    houston_retail = spot_gc + margin_houston + var_houston

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.45),
        'spot_gulf_coast': np.maximum(spot_gc, 1.38),
        'wti_crude': np.maximum(wti_crude, 38.0),
        'brent_crude': np.maximum(brent_crude, 42.0),
        'houston_tx_retail_gasoline': np.maximum(houston_retail, 1.85),
        'houston_retail_gasoline': np.maximum(houston_retail, 1.85),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'usgc_crack_spread': spot_gc - (wti_crude / 42.0),
        'houston_rack_margin': houston_retail - spot_gc
    })


def get_houston_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 3 Gulf Coast refining dynamics (ExxonMobil Baytown 560k bpd,
    Motiva Port Arthur 630k bpd, Marathon Galveston Bay 593k bpd, PEMEX Deer Park 312k bpd),
    Colonial Pipeline Lines 1 & 2 origin injections, Explorer Pipeline operations,
    Texas statutory fuel tax stability ($0.200/gal), and localized Houston NOAA Weather (hurricanes, tropical storms, freezes).
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. Houston & USGC Regional Logistics, Refining & Weather Disruption Dataset
    houston_events = [
        {"date": "2021-02-16", "headline": "Winter Storm Uri deep freeze knocks out ERCOT industrial grid; ExxonMobil Baytown (560k bpd) and Motiva Port Arthur (630k bpd) declare force majeure as uninsulated lines freeze.", "category": "Refinery Freeze-Off"},
        {"date": "2021-05-08", "headline": "Colonial Pipeline halts all 5,500 miles of refined product shipments from Houston/Pasadena origin hub due to ransomware attack, trapping wholesale inventory in USGC storage.", "category": "Colonial Pipeline Origin Outage"},
        {"date": "2022-06-15", "headline": "BSEE Gulf of Mexico tropical disturbance triggers precautionary offshore production shut-ins; USGC waterborne barge crude deliveries into Houston Ship Channel briefly delayed.", "category": "Gulf Weather / Tropical Disturbance"},
        {"date": "2022-09-20", "headline": "PEMEX Deer Park refinery (312,000 bpd) flaring event prompts temporary shelter-in-place along State Highway 225 corridor; local rack supplies remain resilient.", "category": "Deer Park Flaring Incident"},
        {"date": "2023-05-01", "headline": "EPA Reid Vapor Pressure (RVP) summer transition to 7.8 psi takes effect across Harris, Galveston, and Brazoria counties, introducing modest seasonal refining blending premium.", "category": "RVP Summer Transition"},
        {"date": "2023-08-28", "headline": "Extreme summer heatwave across Texas forces voluntary industrial power curtailments at Pasadena and Texas City refining terminals to prevent grid overload.", "category": "Grid Heatwave Curtailment"},
        {"date": "2024-01-16", "headline": "Arctic blast brings sub-freezing temperatures to Upper Texas Coast; minor instrument air line freezing reported across Port Arthur refining complex with zero major outages.", "category": "Gulf Coast Hard Freeze"},
        {"date": "2024-07-08", "headline": "Hurricane Beryl makes landfall near Matagorda Bay as Category 1 hurricane, cutting CenterPoint power to 2.2 million Houston customers and idling retail pump dispensers across Harris County.", "category": "Hurricane Landfall / Power Grid Outage"},
        {"date": "2024-10-10", "headline": "Motiva Port Arthur completes major scheduled turnaround on fluid catalytic cracker (FCCU), restoring full 630,000 bpd throughput capacity to USGC wholesale racks.", "category": "Refinery Turnaround Completion"}
    ]

    regional_df = pd.DataFrame(houston_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    # 3. Merge Localized NOAA Weather Alerts for Houston Metro & Harris County
    noaa_hou_df = get_houston_weather_dataset()
    noaa_formatted = noaa_hou_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    # 4. Ingest Live USGS Water Data Telemetry (Houston Ship Channel / San Jacinto River)
    usgs_events = []
    try:
        from src.usgs_water_feed import USGSWaterFeedConnector
        water_connector = USGSWaterFeedConnector()
        water_telemetry = water_connector.fetch_live_water_telemetry(cluster="gulf_coast")
        indices = water_telemetry.get("indices", {})
        if indices.get("is_flood_surge_warning", False) or indices.get("is_barge_draft_restricted", False):
            storm_idx = indices.get("hydrological_storm_surge_index", 0.0)
            usgs_events.append({
                "date": pd.to_datetime(datetime.now().strftime("%Y-%m-%d")),
                "headline": f"USGS hydrologic telemetry confirms elevated storm surge / water levels along Houston Ship Channel (Surge Index: {storm_idx:.2f}); vessel drafts restricted.",
                "category": "Houston Ship Channel Storm Surge"
            })
    except Exception as e:
        logger.warning(f"Could not load live USGS water telemetry for Houston: {e}")

    # 5. Ingest Live AQI & Industrial Flaring Telemetry (Houston / Pasadena / Baytown Corridor)
    try:
        from src.aqi_feed import AQIFeedConnector
        aqi_connector = AQIFeedConnector()
        aqi_telemetry = aqi_connector.fetch_live_aqi_telemetry(corridor="houston")
        aqi_headline = aqi_connector.generate_aqi_event_headline(corridor="houston", telemetry=aqi_telemetry)
        if aqi_headline:
            usgs_events.append(aqi_headline)
    except Exception as e:
        logger.warning(f"Could not load live AQI telemetry for Houston/Pasadena Corridor: {e}")

    frames = [macro_events_df, regional_df, noaa_formatted]
    if usgs_events:
        frames.append(pd.DataFrame(usgs_events))

    # Ingest Live Regional Intraday Anomalies (Issue #283)
    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_houston_df = load_live_regional_intraday_events("Houston")
        if not intraday_houston_df.empty:
            frames.append(intraday_houston_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for Houston: {e}")

    # Combine Macro + Regional + Local NOAA Weather + USGS Hydrology + AQI
    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
