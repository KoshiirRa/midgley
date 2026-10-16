"""
Greater Chicago Metro, IL & Northwest Indiana Regional Gas Price Forecasting Module (src/locations/chicago/regional.py)
Fuses Chicagoland market data across state lines, modeling the dual-state fuel tax differential
(Illinois state motor fuel tax 47.0¢/gal + Cook County 6.0¢ + Chicago 8.0¢ + local sales tax vs Indiana state motor fuel tax 35.0¢/gal),
BP Whiting Refinery (435,000 bpd capacity), CITGO Lemont Refinery (177,000 bpd), ExxonMobil Joliet Refinery (251,000 bpd),
Midwest clean products pipelines (Explorer, Wolverine, West Shore, Badger), Des Plaines River / Illinois Waterway marine barge logistics,
and localized NOAA Weather Alerts for Cook County IL (ILZ104 / KLOT) & Lake County IN (INZ001).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from src.noaa_weather import get_chicago_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price

logger = logging.getLogger(__name__)


def fetch_chicago_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_il_price: Optional[float] = None,
    live_in_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to Greater Chicago Metro, IL & Northwest Indiana (Tri-State Great Lakes Hub)
    and dynamically calibrates the dual-state retail series to match live pump prices:
      - Illinois Side (Cook County / City of Chicago): State MFT 47.0¢ + Cook County 6.0¢ + Chicago 8.0¢ + Sales Tax
      - Indiana Side (Lake / Porter County): State Fuel Tax 35.0¢ / low municipal tax
      - Cross-Border Tax & Retail Spread: ~$0.40/gal.
    """
    if live_il_price is None:
        live_il_price = live_current_price if live_current_price is not None else fetch_live_metro_retail_price("Chicago_IL")["price"]
    if live_in_price is None:
        live_in_price = live_current_price - 0.400 if live_current_price is not None else live_il_price - 0.400

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Greater Chicago region (Live IL: ${live_il_price:.3f}/gal, Live IN: ${live_in_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_chicago_data(start_date, end_date, live_il_price, live_in_price)

    market_df = base_df.copy()

    # Authentic regional retail series via EIA survey (Issues #607, #608)
    market_df['chicago_il_retail_gasoline'] = get_regional_retail_history("Chicago_IL", market_df['date'], live_il_price)
    market_df['chicago_retail_gasoline'] = market_df['chicago_il_retail_gasoline']

    # Northwest Indiana retail series modeled from regional PADD 2 benchmark
    market_df['chicago_in_retail_gasoline'] = get_regional_retail_history("Tulsa_OK", market_df['date'], live_in_price)
    market_df['chicago_metro_avg_retail'] = (market_df['chicago_il_retail_gasoline'] * 0.80) + (market_df['chicago_in_retail_gasoline'] * 0.20)

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['il_in_tax_spread'] = market_df['chicago_il_retail_gasoline'] - market_df['chicago_in_retail_gasoline']
    market_df['whiting_crack_spread'] = market_df['chicago_il_retail_gasoline'] - market_df['brent_crude_per_gal']

    return market_df


def _generate_synthetic_chicago_data(
    start_date: str,
    end_date: str,
    live_il_price: float = 3.850,
    live_in_price: float = 3.450
) -> pd.DataFrame:
    """Generates synthetic historical business day series for Greater Chicago Metro."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 78.0 + np.cumsum(np.random.normal(0, 1.15, n))
    wti_crude = brent_crude - 3.8 + np.random.normal(0, 0.4, n)
    rbob = (brent_crude / 42.0) * 1.32 + np.cumsum(np.random.normal(0, 0.024, n))

    margin_il = live_il_price - rbob[-1]
    margin_in = live_in_price - rbob[-1]

    var_il = 0.16 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.02, n)
    var_in = 0.13 * np.cos(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.02, n)
    var_il -= var_il[-1]
    var_in -= var_in[-1]

    il_retail = rbob + margin_il + var_il
    in_retail = rbob + margin_in + var_in
    metro_avg = (il_retail * 0.80) + (in_retail * 0.20)

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.50),
        'wti_crude': np.maximum(wti_crude, 40.0),
        'brent_crude': np.maximum(brent_crude, 45.0),
        'chicago_il_retail_gasoline': np.maximum(il_retail, 2.20),
        'chicago_retail_gasoline': np.maximum(il_retail, 2.20),
        'chicago_in_retail_gasoline': np.maximum(in_retail, 1.95),
        'chicago_metro_avg_retail': np.maximum(metro_avg, 2.15),
        'brent_crude_per_gal': brent_crude / 42.0,
        'il_in_tax_spread': il_retail - in_retail,
        'whiting_crack_spread': il_retail - (brent_crude / 42.0)
    })


def get_chicago_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 2 Great Lakes refining dynamics (BP Whiting 435k bpd, CITGO Lemont 177k bpd,
    ExxonMobil Joliet 251k bpd), Des Plaines River barge logistics, Explorer/Wolverine/Badger Pipeline shipments,
    state/county gas tax updates (IL MFT 47.0¢ vs IN 35.0¢), and localized Chicagoland NOAA Weather.
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. Greater Chicago & Great Lakes Regional Logistics, Refining & Tax Disruption Dataset
    chicago_events = [
        {"date": "2022-03-15", "headline": "BP Whiting Refinery (435,000 bpd) initiates emergency shutdown of fluid catalytic cracking complex following cooling water pump trip; Chicago CBOB cash differentials surge +18¢/gal.", "category": "Whiting Refinery Outage"},
        {"date": "2022-07-01", "headline": "Illinois General Assembly adjusts state motor fuel tax to $0.470/gal; combined with Cook County and Chicago municipal taxes, local tax burden exceeds $1.00/gal.", "category": "Policy/Gas Tax"},
        {"date": "2022-08-25", "headline": "Electrical fire at BP Whiting refinery shuts crude distillation and coking units; governor declares regional fuel transportation emergency across Illinois and Indiana.", "category": "Whiting Refinery Outage"},
        {"date": "2023-01-18", "headline": "USACE schedules maintenance on Lockport Lock and Dam along Des Plaines River, throttling barge shipments of heavy crude and clean product to Lemont terminals.", "category": "Illinois Waterway Lock Maintenance"},
        {"date": "2023-06-01", "headline": "EPA Reid Vapor Pressure (RVP) summer-blend 7.4 psi RFG compliance deadline takes effect across Cook, DuPage, and Lake counties, adding +$0.18/gal seasonal refinery blending premium.", "category": "RVP Summer Transition"},
        {"date": "2023-11-10", "headline": "Explorer Pipeline reports scheduled line segment pigging between Tulsa and Hammond IN terminal hub, restricting Gulf Coast product delivery to Chicagoland racks.", "category": "Regional Pipeline"},
        {"date": "2024-02-01", "headline": "Catastrophic plant-wide power failure forces full operational shutdown of BP Whiting refinery (435,000 bpd); Midwest wholesale prompt rack prices spike +35¢/gal within 24 hours.", "category": "Whiting Refinery Outage"},
        {"date": "2024-06-20", "headline": "CITGO Lemont refinery (177,000 bpd) reports minor hydrotreater flaring incident; local Will County rack supplies tighten moderately.", "category": "Lemont Refinery Outage"},
        {"date": "2025-01-15", "headline": "Deep polar vortex Arctic freeze hits Chicagoland (-14°F); freezing spray locks Calumet River marine barge terminals, shifting wholesale distribution to rail at +12.5¢/gal.", "category": "Great Lakes Freeze Lockout"}
    ]

    regional_df = pd.DataFrame(chicago_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    # 3. Merge Localized NOAA Weather Alerts for Chicago Metro & Northwest Indiana
    noaa_chi_df = get_chicago_weather_dataset()
    noaa_formatted = noaa_chi_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    # 4. Ingest Live USGS Water Data Telemetry (Illinois Waterway / Inland Barge)
    usgs_events = []
    try:
        from src.usgs_water_feed import USGSWaterFeedConnector
        water_connector = USGSWaterFeedConnector()
        water_telemetry = water_connector.fetch_live_water_telemetry(cluster="inland_barge")
        indices = water_telemetry.get("indices", {})
        if indices.get("is_barge_draft_restricted", False):
            bottleneck_idx = indices.get("hydrological_barge_bottleneck_index", 0.0)
            usgs_events.append({
                "date": pd.to_datetime(datetime.now().strftime("%Y-%m-%d")),
                "headline": f"USGS waterway telemetry confirms Midwest river draft restrictions (Bottleneck Index: {bottleneck_idx:.2f}); Illinois Waterway barge payload throttled, widening Chicago rack margins.",
                "category": "Illinois Waterway Low-Water"
            })
    except Exception as e:
        logger.warning(f"Could not load live USGS water telemetry for Chicago: {e}")

    # 5. Ingest Live AQI & Industrial Flaring Telemetry (Whiting & Lemont Corridor)
    try:
        from src.aqi_feed import AQIFeedConnector
        aqi_connector = AQIFeedConnector()
        aqi_telemetry = aqi_connector.fetch_live_aqi_telemetry(corridor="chicago")
        aqi_headline = aqi_connector.generate_aqi_event_headline(corridor="chicago", telemetry=aqi_telemetry)
        if aqi_headline:
            usgs_events.append(aqi_headline)
    except Exception as e:
        logger.warning(f"Could not load live AQI telemetry for Whiting/Lemont Corridor: {e}")

    frames = [macro_events_df, regional_df, noaa_formatted]
    if usgs_events:
        frames.append(pd.DataFrame(usgs_events))

    # Ingest Live Regional Intraday Anomalies (Issue #283)
    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_chicago_df = load_live_regional_intraday_events("Chicago")
        if not intraday_chicago_df.empty:
            frames.append(intraday_chicago_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for Chicago: {e}")

    # Combine Macro + Regional + Local NOAA Weather + USGS Hydrology + AQI
    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)


def compute_chicago_edgeworth_forecast(
    market_df: pd.DataFrame,
    live_il_price: Optional[float] = None,
    live_in_price: Optional[float] = None,
    horizon_days: int = 5
) -> Dict[str, Any]:
    """
    Computes Edgeworth price cycle diagnostics and restoration hazard forecast for Greater Chicago Metro (Issue #447).
    """
    from src.edgeworth_cycle import EdgeworthCycleAnalyzer, RestorationHazardModel

    analyzer = EdgeworthCycleAnalyzer(jump_threshold_cpg=0.08)
    hazard_model = RestorationHazardModel()

    # Diagnostics on Illinois retail series
    il_series = market_df.get('chicago_il_retail_gasoline', pd.Series(dtype=float))
    rbob_series = market_df.get('gasoline_rbob', pd.Series(dtype=float))

    diag = analyzer.compute_cycle_diagnostics(il_series)

    if not il_series.empty and not rbob_series.empty:
        hazard_model.fit(il_series, rbob_series)

    current_il = live_il_price if live_il_price is not None else (float(il_series.iloc[-1]) if not il_series.empty else 3.850)
    current_rbob = float(rbob_series.iloc[-1]) if not rbob_series.empty else 2.325

    # Estimate elapsed days since last sharp restoration
    elapsed = 5
    if len(il_series) >= 10:
        d_il = il_series.diff()
        jumps_idx = np.where(d_il >= 0.08)[0]
        if len(jumps_idx) > 0:
            elapsed = int(len(il_series) - 1 - jumps_idx[-1])

    forecast_il = hazard_model.forecast_expected_horizon_change(
        current_retail=current_il,
        current_wholesale=current_rbob,
        elapsed_days=elapsed,
        horizon_days=horizon_days
    )

    return {
        "region": "Chicago_IL",
        "cycle_diagnostics": diag,
        "hazard_model_forecast": forecast_il
    }
