"""
Official U.S. EIA API v2 Connector (src/eia_api_client.py)
Provides authenticated and resilient access to EIA API v2 endpoints:
- Petroleum Marketing & Retail Gasoline Prices (petroleum/pri/gnd)
- Weekly Petroleum Status Report (WPSR) Physical Fundamentals (petroleum/stoc/wstk, petroleum/pnp/wiup, etc.)

Features:
- Lookahead-safe point-in-time extraction with published_at timestamps.
- Zero-cost resilient HTTP pooling via src.http_client.
- Automatic integration with VintageStore and bitemporal cache.
- Clear data provenance tiers (City, State, PADD, Country).
"""

import os
import json
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple, Union

from src.http_client import get_session
from src.vintage_store import VintageStore, QUALITY_LIVE, QUALITY_CACHED, QUALITY_BENCHMARK

logger = logging.getLogger("midgley.eia_api_client")

EIA_V2_BASE_URL = "https://api.eia.gov/v2"

# Provenance tier classifications for official EIA series
EIA_SERIES_PROVENANCE: Dict[str, Dict[str, str]] = {
    # Retail Unleaded Gasoline Series
    "EMM_EPMR_PTE_NUS_DPG": {
        "tier": "EIA_COUNTRY_US",
        "name": "U.S. Regular Gasoline Retail Benchmark",
        "geo": "US"
    },
    "EMM_EPMR_PTE_Y05SF_DPG": {
        "tier": "EIA_CITY_SanFrancisco",
        "name": "San Francisco Regular All Formulations (Oakland / SF Bay Area)",
        "geo": "City_SF"
    },
    "EMM_EPMR_PTE_SOH_DPG": {
        "tier": "EIA_STATE_OH",
        "name": "Ohio Regular Conventional Retail Price",
        "geo": "State_OH"
    },
    "EMM_EPMR_PTE_SFL_DPG": {
        "tier": "EIA_STATE_FL",
        "name": "Florida Regular Conventional Retail Price",
        "geo": "State_FL"
    },
    "EMM_EPMR_PTE_SCA_DPG": {
        "tier": "EIA_STATE_CA",
        "name": "California Regular Reformulated Retail Price",
        "geo": "State_CA"
    },
    "EMM_EPMR_PTE_R1Y_DPG": {
        "tier": "EIA_PADD_1B",
        "name": "PADD 1B Central Atlantic Regular Retail Price",
        "geo": "PADD_1B"
    },
    "EMM_EPMR_PTE_R1Z_DPG": {
        "tier": "EIA_PADD_1C",
        "name": "PADD 1C Lower Atlantic Regular Retail Price",
        "geo": "PADD_1C"
    },
    "EMM_EPMR_PTE_R20_DPG": {
        "tier": "EIA_PADD_2",
        "name": "PADD 2 Midwest Regular Retail Price",
        "geo": "PADD_2"
    },
    # Weekly Petroleum Status Report (WPSR) Fundamental Series
    "WGTSTUS1": {
        "tier": "EIA_WPSR_STOCKS_US",
        "name": "U.S. Total Gasoline Stocks (Thousand Barrels)",
        "geo": "US"
    },
    "WGTSTP11": {
        "tier": "EIA_WPSR_STOCKS_PADD1",
        "name": "PADD 1 Total Gasoline Stocks (Thousand Barrels)",
        "geo": "PADD_1"
    },
    "WGTST1B1": {
        "tier": "EIA_WPSR_STOCKS_PADD1B",
        "name": "PADD 1B Total Gasoline Stocks (Thousand Barrels)",
        "geo": "PADD_1B"
    },
    "WGTST1C1": {
        "tier": "EIA_WPSR_STOCKS_PADD1C",
        "name": "PADD 1C Total Gasoline Stocks (Thousand Barrels)",
        "geo": "PADD_1C"
    },
    "WGTSTP21": {
        "tier": "EIA_WPSR_STOCKS_PADD2",
        "name": "PADD 2 Total Gasoline Stocks (Thousand Barrels)",
        "geo": "PADD_2"
    },
    "WPULEUS3": {
        "tier": "EIA_WPSR_UTIL_US",
        "name": "U.S. Refinery Utilization Percent",
        "geo": "US"
    },
    "W_NA_YUP_R20_PER": {
        "tier": "EIA_WPSR_UTIL_PADD2",
        "name": "PADD 2 Refinery Utilization Percent",
        "geo": "PADD_2"
    },
    "W_NA_YUP_R30_PER": {
        "tier": "EIA_WPSR_UTIL_PADD3",
        "name": "PADD 3 Refinery Utilization Percent",
        "geo": "PADD_3"
    },
    "WGFRPP12": {
        "tier": "EIA_WPSR_PROD_PADD1",
        "name": "PADD 1 Refiner & Blender Net Production of Finished Gasoline",
        "geo": "PADD_1"
    },
    "WGFRPP32": {
        "tier": "EIA_WPSR_PROD_PADD3",
        "name": "PADD 3 Refiner & Blender Net Production of Finished Gasoline",
        "geo": "PADD_3"
    },
    "W_EPC0_SAX_YCUOK_MBBL": {
        "tier": "EIA_WPSR_CUSHING_CRUDE",
        "name": "Cushing, OK Ending Stocks of Crude Oil (Excl. SPR)",
        "geo": "Cushing_OK"
    },
    "WGFUPUS2": {
        "tier": "EIA_WPSR_DEMAND_US",
        "name": "U.S. Product Supplied of Finished Motor Gasoline",
        "geo": "US"
    },
    "W_EPOOXE_YOP_NUS_MBBLD": {
        "tier": "EIA_WPSR_ETHANOL_PROD",
        "name": "U.S. Fuel Ethanol Production (Thousand Barrels/Day)",
        "geo": "US"
    },
    "W_EPOOXE_SAE_NUS_MBBL": {
        "tier": "EIA_WPSR_ETHANOL_STOCKS",
        "name": "U.S. Fuel Ethanol Stocks (Thousand Barrels)",
        "geo": "US"
    }
}


class EIAClientV2:
    """
    Direct Client for U.S. EIA API v2.
    Queries official weekly retail prices and WPSR fundamentals.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EIA_API_KEY", "")
        self.session = get_session(timeout=(3.05, 15.0), retries=2)
        self.vintage_store = VintageStore()

    def get_api_key(self) -> str:
        return self.api_key or os.getenv("EIA_API_KEY", "")

    def fetch_retail_gasoline_series(
        self,
        series_id: str,
        start_period: str = "2022-01-01",
        record_vintages: bool = True
    ) -> Dict[str, float]:
        """
        Fetches historical weekly retail prices for a specific EIA v2 series ID
        via `petroleum/pri/gnd/data`.
        Returns dict mapping 'YYYY-MM-DD' -> price ($/gal).
        """
        key = self.get_api_key()
        if not key:
            logger.debug(f"EIA_API_KEY not configured. Skipping live EIA v2 call for {series_id}.")
            return {}

        url = f"{EIA_V2_BASE_URL}/petroleum/pri/gnd/data/"
        params: Dict[str, Any] = {
            "api_key": key,
            "frequency": "weekly",
            "data[0]": "value",
            "facets[series][]": series_id,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if start_period:
            params["start"] = start_period

        history: Dict[str, float] = {}
        prov = EIA_SERIES_PROVENANCE.get(series_id, {"tier": "EIA_UNKNOWN", "geo": "US"})
        tier = prov.get("tier", "EIA_UNKNOWN")

        try:
            resp = self.session.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("response", {}).get("data", [])
                for row in rows:
                    period = str(row.get("period", ""))[:10]
                    raw_val = row.get("value")
                    if period and raw_val is not None:
                        try:
                            val = round(float(raw_val), 3)
                            history[period] = val
                            if record_vintages:
                                # EIA Retail survey is conducted Monday morning, released Tuesday ~10:00 AM ET (14:00/15:00 UTC)
                                try:
                                    dt = datetime.strptime(period, "%Y-%m-%d")
                                    # Tuesday after survey Monday
                                    pub_date = dt + timedelta(days=1)
                                    pub_at = pub_date.strftime("%Y-%m-%dT15:00:00Z")
                                except Exception:
                                    pub_at = datetime.now(timezone.utc).isoformat()

                                self.vintage_store.record_observation(
                                    feed="eia_retail",
                                    entity=series_id,
                                    obs_date=period,
                                    values={"price": val, "series_id": series_id, "tier": tier},
                                    published_at=pub_at,
                                    quality=QUALITY_LIVE
                                )
                        except (ValueError, TypeError):
                            continue
                logger.info(f"Successfully fetched {len(history)} weekly EIA v2 rows for {series_id} ({tier})")
            else:
                logger.warning(f"EIA API v2 returned status {resp.status_code} for {series_id}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Failed to query EIA API v2 for series {series_id}: {e}")

        return history

    def fetch_wpsr_supply_series(
        self,
        series_id: str,
        start_period: str = "2022-01-01",
        record_vintages: bool = True
    ) -> Dict[str, float]:
        """
        Fetches historical weekly WPSR supply/stocks/utilization series for an EIA series ID.
        Returns dict mapping 'YYYY-MM-DD' -> value.
        """
        key = self.get_api_key()
        if not key:
            return {}

        # Query series ID backward-compatible v2 route or facets
        url = f"{EIA_V2_BASE_URL}/seriesid/PET.{series_id}.W"
        params: Dict[str, Any] = {
            "api_key": key
        }

        history: Dict[str, float] = {}
        prov = EIA_SERIES_PROVENANCE.get(series_id, {"tier": "EIA_WPSR", "geo": "US"})
        tier = prov.get("tier", "EIA_WPSR")

        try:
            resp = self.session.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("response", {}).get("data", [])
                for row in rows:
                    period = str(row.get("period", ""))[:10]
                    raw_val = row.get("value")
                    if period and raw_val is not None:
                        try:
                            val = float(raw_val)
                            history[period] = val
                            if record_vintages:
                                # WPSR released Wednesday 10:30 AM ET (14:30/15:30 UTC)
                                try:
                                    dt = datetime.strptime(period, "%Y-%m-%d")
                                    # Period ends Friday, report released following Wednesday (+5 days)
                                    pub_date = dt + timedelta(days=5)
                                    pub_at = pub_date.strftime("%Y-%m-%dT15:30:00Z")
                                except Exception:
                                    pub_at = datetime.now(timezone.utc).isoformat()

                                self.vintage_store.record_observation(
                                    feed="eia_wpsr",
                                    entity=series_id,
                                    obs_date=period,
                                    values={"value": val, "series_id": series_id, "tier": tier},
                                    published_at=pub_at,
                                    quality=QUALITY_LIVE
                                )
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            logger.debug(f"Failed to query WPSR series {series_id}: {e}")

        return history


_GLOBAL_EIA_CLIENT: Optional[EIAClientV2] = None


def get_eia_client() -> EIAClientV2:
    """Returns singleton EIAClientV2 instance."""
    global _GLOBAL_EIA_CLIENT
    if _GLOBAL_EIA_CLIENT is None:
        _GLOBAL_EIA_CLIENT = EIAClientV2()
    return _GLOBAL_EIA_CLIENT
