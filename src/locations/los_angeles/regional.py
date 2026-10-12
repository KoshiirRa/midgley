"""
Los Angeles Basin & Southern California Regional Gas Price Forecasting Module (src/locations/los_angeles/regional.py)
Fuses Los Angeles Basin & South Coast Air Basin market data, modeling the Southern California refining complex
(Marathon Carson/Wilmington 363k bpd, Chevron El Segundo 269k bpd, PBF Energy Torrance 166k bpd,
Phillips 66 Wilmington 139k bpd, Valero Wilmington 85k bpd), Los Angeles CARBOB wholesale spot basis,
CARB Phase 3 CaRFG regulatory & tax burden breakdown ($0.953/gal state excise, Cap-and-Trade, LCFS, UST & sales taxes),
Kinder Morgan SFPP West/South/East pipeline logistics, USGS Newport-Inglewood & Palos Verdes Fault seismic risks,
Southern California Edison (SCE) PSPS & Santa Ana Red Flag wildfire wind alerts, San Pedro Bay marine terminal traffic,
and localized NOAA Weather Alerts for Los Angeles County (CAZ041 / KLAX).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
import logging

from src.noaa_weather import get_los_angeles_weather_dataset
from src.data_ingestion import get_historical_event_dataset
from src.live_fuel_feed import fetch_live_metro_retail_price
from src.carb_compliance import get_dynamic_carb_compliance_breakdown

logger = logging.getLogger(__name__)

# CARB (California Air Resources Board) & CA State Regulatory Tax Baseline Breakdown (USD per gallon)
_default_carb = get_dynamic_carb_compliance_breakdown()
CARB_EXCISE_TAX = _default_carb["carb_state_excise_tax"]         # CA State Excise Tax ($0.596/gal)
CAP_AND_TRADE_FEE = _default_carb["cap_and_trade_fee_per_gal"]   # Dynamic Cap-and-Trade Allowance Fee
LCFS_CREDIT_FEE = _default_carb["lcfs_credit_fee_per_gal"]       # Dynamic Low Carbon Fuel Standard (LCFS) Fee
LOCAL_TAX_UST_FEE = _default_carb["local_sales_ust_fee"]         # Local Sales Tax + UST Fee ($0.088/gal)
TOTAL_CARB_TAX_BURDEN = _default_carb["total_carb_tax_burden"]   # Dynamic Total Tax Burden (~$0.953–$1.02/gal)


def fetch_los_angeles_market_data(
    start_date: str = "2022-01-01",
    end_date: Optional[str] = None,
    live_pump_price: Optional[float] = None,
    live_current_price: Optional[float] = None
) -> pd.DataFrame:
    """
    Fetches market data tailored to the Los Angeles Basin & Southern California (PADD 5 Hub)
    and dynamically calibrates the retail series to match live pump prices:
      - California State & CARB Environmental Tax Burden: $0.953/gal ($1.407/gal total with federal & LA sales taxes)
      - Los Angeles CARBOB Reformulated Gasoline Spot Benchmark (EIA EER_EPMRU_PF4_RLA_DPG)
      - South Bay / Harbor Refining Complex (Carson, Wilmington, El Segundo, Torrance) crack and rack margins.
    """
    live_price = live_pump_price if live_pump_price is not None else live_current_price
    if live_price is None:
        try:
            live_price = fetch_live_metro_retail_price("Los_Angeles_CA")["price"]
        except Exception:
            live_price = 4.890

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Fetching market data for Los Angeles Basin region (Live Pump Price: ${live_price:.3f}/gal)...")

    from src.data_ingestion import fetch_market_data
    from src.eia_retail_feed import get_regional_retail_history
    base_df = fetch_market_data(start_date=start_date, end_date=end_date)
    if base_df is None or base_df.empty or 'gasoline_rbob' not in base_df.columns:
        return _generate_synthetic_los_angeles_data(start_date, end_date, live_price)

    market_df = base_df.copy()

    # Authentic regional retail series via EIA survey (Weekly Los Angeles All Formulations EMM_EPMR_PTE_Y05LA_DPG)
    market_df['los_angeles_ca_retail_gasoline'] = get_regional_retail_history("Los_Angeles_CA", market_df['date'], live_price)
    market_df['los_angeles_retail_gasoline'] = market_df['los_angeles_ca_retail_gasoline']

    # Los Angeles CARBOB wholesale spot benchmark column
    if 'spot_los_angeles' not in market_df.columns:
        market_df['spot_los_angeles'] = market_df['gasoline_rbob'] + 0.470

    market_df['brent_crude_per_gal'] = market_df['brent_crude'] / 42.0
    market_df['wti_crude_per_gal'] = market_df['wti_crude'] / 42.0
    market_df['socal_crack_spread'] = market_df['spot_los_angeles'] - market_df['brent_crude_per_gal']
    market_df['el_segundo_crack_spread'] = market_df['socal_crack_spread']
    market_df['los_angeles_rack_margin'] = market_df['los_angeles_retail_gasoline'] - market_df['spot_los_angeles']

    # Add CARB regulatory burden breakdown columns
    market_df['carb_excise_tax'] = CARB_EXCISE_TAX
    market_df['cap_and_trade_fee'] = CAP_AND_TRADE_FEE
    market_df['lcfs_credit_fee'] = LCFS_CREDIT_FEE
    market_df['local_tax_ust_fee'] = LOCAL_TAX_UST_FEE
    market_df['total_regulatory_tax_burden'] = TOTAL_CARB_TAX_BURDEN

    return market_df


def _generate_synthetic_los_angeles_data(
    start_date: str,
    end_date: str,
    live_pump_price: float = 4.890
) -> pd.DataFrame:
    """Generates synthetic historical business day series for Los Angeles Basin & Southern California."""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    n = len(dates)

    brent_crude = 80.0 + np.cumsum(np.random.normal(0, 1.15, n))
    wti_crude = brent_crude - 4.4 + np.random.normal(0, 0.38, n)
    rbob = (brent_crude / 42.0) * 1.34 + np.cumsum(np.random.normal(0, 0.024, n))
    spot_la = rbob + 0.470 + np.random.normal(0, 0.015, n)

    margin_la = live_pump_price - spot_la[-1]
    var_la = 0.16 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.022, n)
    var_la -= var_la[-1]

    la_retail = spot_la + margin_la + var_la

    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': np.maximum(rbob, 1.75),
        'spot_los_angeles': np.maximum(spot_la, 2.15),
        'wti_crude': np.maximum(wti_crude, 42.0),
        'brent_crude': np.maximum(brent_crude, 46.0),
        'los_angeles_ca_retail_gasoline': np.maximum(la_retail, 3.10),
        'los_angeles_retail_gasoline': np.maximum(la_retail, 3.10),
        'brent_crude_per_gal': brent_crude / 42.0,
        'wti_crude_per_gal': wti_crude / 42.0,
        'socal_crack_spread': spot_la - (brent_crude / 42.0),
        'el_segundo_crack_spread': spot_la - (brent_crude / 42.0),
        'los_angeles_rack_margin': la_retail - spot_la,
        'carb_excise_tax': CARB_EXCISE_TAX,
        'cap_and_trade_fee': CAP_AND_TRADE_FEE,
        'lcfs_credit_fee': LCFS_CREDIT_FEE,
        'local_tax_ust_fee': LOCAL_TAX_UST_FEE,
        'total_regulatory_tax_burden': TOTAL_CARB_TAX_BURDEN
    })


def get_los_angeles_regional_events() -> pd.DataFrame:
    """
    Merges macro LLM event logs with PADD 5 Southern California refining dynamics
    (Marathon Carson/Wilmington 363k bpd, Chevron El Segundo 269k bpd, PBF Torrance 166k bpd,
    Phillips 66 Wilmington 139k bpd), Kinder Morgan SFPP West/South/East pipeline operations,
    CARB Phase 3 CaRFG & SCAQMD summer RVP transitions, USGS Newport-Inglewood seismic events,
    and localized Los Angeles Basin NOAA Weather (Santa Ana Red Flag winds, atmospheric rivers, heatwaves).
    """
    # 1. Fetch Master Macro Event Dataset
    macro_events_df = get_historical_event_dataset()

    # 2. Los Angeles Basin & Southern California Regional Logistics, Refining & Hazard Dataset
    la_events = [
        {"date": "2022-03-10", "headline": "PBF Energy Torrance Refinery (166,000 bpd) reports unplanned fluid catalytic cracking unit (FCCU) flaring event; Los Angeles CARBOB spot basis surges +45¢/gal.", "category": "Torrance Refinery Outage"},
        {"date": "2022-04-01", "headline": "South Coast Air Quality Management District (SCAQMD) & CARB mandate early transition to summer-blend CaRFG (6.99 psi RVP cap) across Los Angeles, Orange, and Inland Empire racks.", "category": "CARB Summer CaRFG Transition"},
        {"date": "2022-09-29", "headline": "Chevron El Segundo Refinery (269,000 bpd) experiences unplanned flaring and alkylation unit upset during peak autumn turnaround window, spiking Southern California retail pump prices above $6.40/gal.", "category": "El Segundo Refinery Outage"},
        {"date": "2023-03-28", "headline": "California Energy Commission (CEC) advances SBX1-2 maximum gross gasoline refining margin penalty framework following historic PADD 5 Los Angeles CARBOB basis spikes.", "category": "CEC SBX1-2 Regulatory Action"},
        {"date": "2023-08-20", "headline": "Tropical Storm Hilary makes historic Southern California landfall, dumping record August rainfall across Los Angeles Basin and temporarily halting marine tanker discharges at Port of Long Beach.", "category": "Tropical Storm Hilary"},
        {"date": "2023-09-18", "headline": "Marathon Carson/Wilmington complex (363,000 bpd) enters scheduled hydrocracker maintenance while PBF Torrance experiences concurrent unit trip, driving LA CARBOB spot over +$1.10/gal above NYMEX RBOB.", "category": "Carson/Torrance Concurrent Outage"},
        {"date": "2024-04-15", "headline": "Kinder Morgan SFPP Watson Station in Carson executes pipeline manifold maintenance on East Line to Colton and Phoenix, tightening Inland Empire terminal allocations.", "category": "Kinder Morgan SFPP Maintenance"},
        {"date": "2024-10-16", "headline": "Phillips 66 announces plans to cease crude refining operations at its 139,000 bpd Los Angeles (Wilmington/Carson) refinery complex in Q4 2025, tightening structural PADD 5 CaRFG supply.", "category": "Wilmington Capacity Contraction"},
        {"date": "2025-01-08", "headline": "Extreme Santa Ana windstorm (85 mph gusts) triggers Southern California Edison (SCE) Public Safety Power Shutoffs (PSPS) and major Los Angeles County wildfires, disrupting regional fuel truck dispatch.", "category": "Santa Ana Wildfire / SCE PSPS"}
    ]

    regional_df = pd.DataFrame(la_events)
    regional_df['date'] = pd.to_datetime(regional_df['date'])

    # 3. Merge Localized NOAA Weather Alerts for Los Angeles Basin
    noaa_la_df = get_los_angeles_weather_dataset()
    noaa_formatted = noaa_la_df[['date', 'headline', 'weather_type']].rename(columns={'weather_type': 'category'})

    # 4. Ingest Live USGS Seismic Telemetry for Southern California (`socal` corridor)
    usgs_events = []
    try:
        from src.usgs_seismic import USGSSeismicConnector
        seismic_connector = USGSSeismicConnector()
        seismic_telemetry = seismic_connector.fetch_live_seismic_telemetry(corridor="socal")
        seismic_headline = seismic_connector.generate_seismic_event_headline(corridor="socal", telemetry=seismic_telemetry)
        if seismic_headline:
            usgs_events.append(seismic_headline)
    except Exception as e:
        logger.warning(f"Could not load live USGS seismic telemetry for Los Angeles/SoCal: {e}")

    # 5. Ingest Live AQI & Industrial Flaring Telemetry (South Bay / Carson / El Segundo / Torrance Corridor)
    try:
        from src.aqi_feed import AQIFeedConnector
        aqi_connector = AQIFeedConnector()
        aqi_telemetry = aqi_connector.fetch_live_aqi_telemetry(corridor="socal")
        aqi_headline = aqi_connector.generate_aqi_event_headline(corridor="socal", telemetry=aqi_telemetry)
        if aqi_headline:
            usgs_events.append(aqi_headline)
    except Exception as e:
        logger.warning(f"Could not load live AQI telemetry for Los Angeles/SoCal Corridor: {e}")

    frames = [macro_events_df, regional_df, noaa_formatted]
    if usgs_events:
        frames.append(pd.DataFrame(usgs_events))

    # Ingest Live Regional Intraday Anomalies (Issue #283)
    try:
        from src.data_ingestion import load_live_regional_intraday_events
        intraday_la_df = load_live_regional_intraday_events("Los_Angeles")
        if not intraday_la_df.empty:
            frames.append(intraday_la_df)
    except Exception as e:
        logger.debug(f"Could not load live regional intraday events for Los Angeles: {e}")

    # Combine Macro + Regional + Local NOAA Weather + USGS Seismic + AQI
    combined_events = pd.concat(frames, ignore_index=True)
    return combined_events.sort_values('date').reset_index(drop=True)
