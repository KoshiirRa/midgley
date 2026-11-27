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
    "WGTSTP41": {
        "tier": "EIA_WPSR_STOCKS_PADD4",
        "name": "PADD 4 Rocky Mountain Total Gasoline Stocks (Thousand Barrels)",
        "geo": "PADD_4"
    },
    "WGTSTP51": {
        "tier": "EIA_WPSR_STOCKS_PADD5",
        "name": "PADD 5 West Coast Total Gasoline Stocks (Thousand Barrels)",
        "geo": "PADD_5"
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
    "W_NA_YUP_R40_PER": {
        "tier": "EIA_WPSR_UTIL_PADD4",
        "name": "PADD 4 Rocky Mountain Refinery Utilization Percent",
        "geo": "PADD_4"
    },
    "W_NA_YUP_R50_PER": {
        "tier": "EIA_WPSR_UTIL_PADD5",
        "name": "PADD 5 West Coast Refinery Utilization Percent",
        "geo": "PADD_5"
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
    },
    # Daily Regional Spot Gasoline Series (petroleum/pri/spt/)
    "EER_EPMRU_PF4_RGC_DPG": {
        "tier": "EIA_SPOT_GULF_COAST",
        "name": "U.S. Gulf Coast Conventional Regular Spot Price ($/gal)",
        "geo": "PADD_3"
    },
    "EER_EPMRU_PF4_YNY_DPG": {
        "tier": "EIA_SPOT_NY_HARBOR",
        "name": "New York Harbor Conventional Regular Spot Price ($/gal)",
        "geo": "PADD_1B"
    },
    "EER_EPMRU_PF4_RLA_DPG": {
        "tier": "EIA_SPOT_LOS_ANGELES",
        "name": "Los Angeles Reformulated RBOB Regular Spot Price ($/gal)",
        "geo": "PADD_5"
    },
    "EER_EPMRU_PF4_RGP_DPG": {
        "tier": "EIA_SPOT_GROUP3_TULSA",
        "name": "Group 3 (Tulsa/Midcontinent) Regular Gasoline Spot Price ($/gal)",
        "geo": "PADD_2_Group3"
    },
    "EER_EPMRU_PF4_RCH_DPG": {
        "tier": "EIA_SPOT_CHICAGO",
        "name": "Chicago Regular Gasoline Spot Price ($/gal)",
        "geo": "PADD_2_Chicago"
    },
    # Phase 2: Inter-PADD Logistics, Pipeline Movements & Import/Export Flows (Issue #649)
    "M_EPM0_MPL_R30-R10_MBBL": {
        "tier": "EIA_MOVE_PIPE_PADD3_TO_PADD1",
        "name": "PADD 3 to PADD 1 Pipeline Shipments of Motor Gasoline (Thousand Barrels/Month)",
        "geo": "PADD3_to_PADD1"
    },
    "WIRPUS1": {
        "tier": "EIA_MOVE_IMPORTS_PADD1_TOTAL",
        "name": "Weekly PADD 1 Motor Gasoline Imports (Thousand Barrels/Day)",
        "geo": "PADD_1"
    },
    "W_EPM0_IM0_R10-Z00_MBBLD": {
        "tier": "EIA_MOVE_IMPORTS_PADD1_BLEND",
        "name": "Weekly PADD 1 Gasoline & Blendstock Imports (Thousand Barrels/Day)",
        "geo": "PADD_1"
    },
    "W_EPM0_EEX_R30-Z00_MBBLD": {
        "tier": "EIA_MOVE_EXPORTS_PADD3",
        "name": "Weekly PADD 3 Gulf Coast Motor Gasoline Exports (Thousand Barrels/Day)",
        "geo": "PADD_3"
    },
    # Phase 3: Physical 3:2:1 Cash Crack Spreads (ULSD Spot) & Finished vs. Blendstock Stocks (Issue #649)
    "EER_EPD2DXL0_PF4_RGC_DPG": {
        "tier": "EIA_SPOT_ULSD_GULF_COAST",
        "name": "U.S. Gulf Coast Ultra-Low Sulfur No. 2 Diesel Spot Price ($/gal)",
        "geo": "PADD_3"
    },
    "EER_EPD2DXL0_PF4_YNY_DPG": {
        "tier": "EIA_SPOT_ULSD_NY_HARBOR",
        "name": "New York Harbor Ultra-Low Sulfur No. 2 Diesel Spot Price ($/gal)",
        "geo": "PADD_1B"
    },
    "EER_EPD2DXL0_PF4_RLA_DPG": {
        "tier": "EIA_SPOT_ULSD_LOS_ANGELES",
        "name": "Los Angeles Ultra-Low Sulfur CARB Diesel Spot Price ($/gal)",
        "geo": "PADD_5"
    },
    "WGFSTUS1": {
        "tier": "EIA_WPSR_STOCKS_FINISHED_US",
        "name": "U.S. Ending Stocks of Finished Motor Gasoline (Thousand Barrels)",
        "geo": "US"
    },
    "WGIOREST1": {
        "tier": "EIA_WPSR_STOCKS_BLENDSTOCK_US",
        "name": "U.S. Ending Stocks of Motor Gasoline Blending Components (Thousand Barrels)",
        "geo": "US"
    },
    # Phase 4: Short-Term Energy Outlook (STEO) Macro Priors (Issue #649)
    "MGRARUS": {
        "tier": "EIA_STEO_RETAIL_GAS_US",
        "name": "STEO U.S. Regular Gasoline Retail Price Projection ($/gal)",
        "geo": "US"
    },
    "MGWHUUS": {
        "tier": "EIA_STEO_WHOLESALE_GAS_US",
        "name": "STEO U.S. Regular Gasoline Wholesale Price Projection ($/gal)",
        "geo": "US"
    },
    "WTIPUUS": {
        "tier": "EIA_STEO_WTI_CRUDE",
        "name": "STEO WTI Crude Oil Price Projection ($/bbl)",
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
        if self._is_network_suppressed():
            return {}

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

    def _is_network_suppressed(self) -> bool:
        """Suppresses real network calls under TESTING=1 unless session.get is explicitly mocked."""
        if os.getenv("TESTING") == "1":
            return not hasattr(self.session.get, "assert_called")
        return False

    @staticmethod
    def _spot_publication_timestamp(obs_date_str: str) -> str:
        """
        Computes strict T+1 business-day publication timestamp (15:00 UTC)
        for daily EIA petroleum spot prices.
        """
        try:
            dt = datetime.strptime(obs_date_str, "%Y-%m-%d")
            # Friday -> Monday (+3), Saturday -> Monday (+2), else +1 day
            if dt.weekday() == 4:
                pub_date = dt + timedelta(days=3)
            elif dt.weekday() == 5:
                pub_date = dt + timedelta(days=2)
            else:
                pub_date = dt + timedelta(days=1)
            return pub_date.strftime("%Y-%m-%dT15:00:00Z")
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    def fetch_spot_price_series(
        self,
        series_id: str,
        start_period: str = "2024-01-01",
        record_vintages: bool = True
    ) -> Dict[str, float]:
        """
        Fetches daily physical spot gasoline prices via EIA API v2 `petroleum/pri/spt/data/`.
        Enforces T+1 business-day publication lag for point-in-time safety.
        Returns dict mapping 'YYYY-MM-DD' -> price ($/gal).
        """
        if self._is_network_suppressed():
            return {}

        key = self.get_api_key()
        if not key:
            logger.debug(f"EIA_API_KEY not configured. Skipping live EIA v2 spot call for {series_id}.")
            return {}

        url = f"{EIA_V2_BASE_URL}/petroleum/pri/spt/data/"
        params: Dict[str, Any] = {
            "api_key": key,
            "frequency": "daily",
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
        prov = EIA_SERIES_PROVENANCE.get(series_id, {"tier": "EIA_SPOT", "geo": "US"})
        tier = prov.get("tier", "EIA_SPOT")

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
                                pub_at = self._spot_publication_timestamp(period)
                                self.vintage_store.record_observation(
                                    feed="eia_spot",
                                    entity=series_id,
                                    obs_date=period,
                                    values={"price": val, "series_id": series_id, "tier": tier},
                                    published_at=pub_at,
                                    quality=QUALITY_LIVE
                                )
                        except (ValueError, TypeError):
                            continue
                logger.info(f"Successfully fetched {len(history)} daily EIA v2 spot rows for {series_id} ({tier})")
            else:
                logger.warning(f"EIA API v2 spot returned status {resp.status_code} for {series_id}: {resp.text[:200]}")
        except Exception as e:
            logger.debug(f"Failed to query EIA API v2 spot series {series_id}: {e}")

        return history

    def fetch_movement_series(
        self,
        series_id: str,
        frequency: str = "weekly",
        start_period: str = "2023-01-01",
        record_vintages: bool = True
    ) -> Dict[str, float]:
        """
        Fetches inter-PADD pipeline movements (`petroleum/move/pipe/data/`) or
        weekly waterborne import/export flows (`petroleum/move/wkly/data/`).
        Enforces strict publication lags:
          - weekly WPSR flows: Wednesday 15:30 UTC (+5 days from Friday period end)
          - monthly PSM pipeline flows: +60 days from month start (15:00 UTC)
        """
        if self._is_network_suppressed():
            return {}

        key = self.get_api_key()
        if not key:
            logger.debug(f"EIA_API_KEY not configured. Skipping live EIA v2 movement call for {series_id}.")
            return {}

        is_monthly = (frequency == "monthly")
        route = "petroleum/move/pipe/data/" if is_monthly else "petroleum/move/wkly/data/"
        url = f"{EIA_V2_BASE_URL}/{route}"
        params: Dict[str, Any] = {
            "api_key": key,
            "frequency": "monthly" if is_monthly else "weekly",
            "data[0]": "value",
            "facets[series][]": series_id,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if start_period:
            params["start"] = start_period[:7] if is_monthly else start_period

        history: Dict[str, float] = {}
        prov = EIA_SERIES_PROVENANCE.get(series_id, {"tier": "EIA_MOVE", "geo": "US"})
        tier = prov.get("tier", "EIA_MOVE")
        feed_name = "eia_move_pipe" if is_monthly else "eia_move_wkly"

        try:
            resp = self.session.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("response", {}).get("data", [])
                for row in rows:
                    raw_period = str(row.get("period", ""))
                    period = raw_period[:7] if is_monthly else raw_period[:10]
                    raw_val = row.get("value")
                    if period and raw_val is not None:
                        try:
                            val = float(raw_val)
                            history[period] = val
                            if record_vintages:
                                try:
                                    if is_monthly:
                                        dt = datetime.strptime(period + "-01", "%Y-%m-%d")
                                        pub_at = (dt + timedelta(days=60)).strftime("%Y-%m-%dT15:00:00Z")
                                    else:
                                        dt = datetime.strptime(period, "%Y-%m-%d")
                                        pub_at = (dt + timedelta(days=5)).strftime("%Y-%m-%dT15:30:00Z")
                                except Exception:
                                    pub_at = datetime.now(timezone.utc).isoformat()

                                self.vintage_store.record_observation(
                                    feed=feed_name,
                                    entity=series_id,
                                    obs_date=period,
                                    values={"value": val, "series_id": series_id, "tier": tier},
                                    published_at=pub_at,
                                    quality=QUALITY_LIVE
                                )
                        except (ValueError, TypeError):
                            continue
                logger.info(f"Successfully fetched {len(history)} EIA v2 movement rows for {series_id} ({tier})")
            else:
                logger.warning(f"EIA API v2 movement returned status {resp.status_code} for {series_id}: {resp.text[:200]}")
        except Exception as e:
            logger.debug(f"Failed to query EIA API v2 movement series {series_id}: {e}")

        return history

    def fetch_steo_series(
        self,
        series_id: str,
        start_period: str = "2024-01",
        record_vintages: bool = True
    ) -> Dict[str, float]:
        """
        Fetches monthly Short-Term Energy Outlook (STEO) consensus projections
        via EIA API v2 `/steo/data/` (Phase 4, Issue #649).
        """
        if self._is_network_suppressed():
            return {}

        key = self.get_api_key()
        if not key:
            logger.debug(f"EIA_API_KEY not configured. Skipping live EIA v2 STEO call for {series_id}.")
            return {}

        url = f"{EIA_V2_BASE_URL}/steo/data/"
        params: Dict[str, Any] = {
            "api_key": key,
            "frequency": "monthly",
            "data[0]": "value",
            "facets[seriesId][]": series_id,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if start_period:
            params["start"] = start_period

        history: Dict[str, float] = {}
        prov = EIA_SERIES_PROVENANCE.get(series_id, {"tier": "EIA_STEO", "geo": "US"})
        tier = prov.get("tier", "EIA_STEO")

        try:
            resp = self.session.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("response", {}).get("data", [])
                pub_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT16:00:00Z")
                for row in rows:
                    period = str(row.get("period", ""))[:7]
                    raw_val = row.get("value")
                    if period and raw_val is not None:
                        try:
                            val = round(float(raw_val), 3)
                            history[period] = val
                            if record_vintages:
                                self.vintage_store.record_observation(
                                    feed="eia_steo",
                                    entity=series_id,
                                    obs_date=period,
                                    values={"value": val, "series_id": series_id, "tier": tier},
                                    published_at=pub_at,
                                    quality=QUALITY_LIVE
                                )
                        except (ValueError, TypeError):
                            continue
                logger.info(f"Successfully fetched {len(history)} EIA v2 STEO rows for {series_id} ({tier})")
            else:
                logger.warning(f"EIA API v2 STEO returned status {resp.status_code} for {series_id}: {resp.text[:200]}")
        except Exception as e:
            logger.debug(f"Failed to query EIA API v2 STEO series {series_id}: {e}")

        return history

    def fetch_gallon_cost_breakdown(self) -> Dict[str, Any]:
        """
        Returns the EIA 'What We Pay for in a Gallon of Gasoline' structural cost breakdown
        (crude oil, refining, distribution & marketing, taxes) for ECM cointegration priors (Phase 4, Issue #649).
        """
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # EIA published historical baseline shares (sum = 100.0%)
        breakdown = {
            "crude_oil_pct": 54.0,
            "refining_pct": 18.0,
            "distribution_marketing_pct": 12.0,
            "taxes_pct": 16.0,
            "provenance_type": "BENCHMARK_BASELINE",
            "source": "U.S. EIA Gasoline and Diesel Fuel Update (Structural Baseline)",
            "as_of": now_iso,
        }

        wti_hist = self.fetch_steo_series("WTIPUUS", record_vintages=False)
        whs_hist = self.fetch_steo_series("MGWHUUS", record_vintages=False)
        ret_hist = self.fetch_steo_series("MGRARUS", record_vintages=False)

        if wti_hist and whs_hist and ret_hist:
            common = sorted(set(wti_hist.keys()) & set(whs_hist.keys()) & set(ret_hist.keys()))
            if common:
                latest = common[-1]
                ret = max(ret_hist[latest], 0.50)
                crude_gal = wti_hist[latest] / 42.0
                whs = whs_hist[latest]
                tax_gal = 0.52  # Combined federal + avg state excise tax benchmark ($/gal)
                crude_pct = round(max(0.0, min(85.0, (crude_gal / ret) * 100.0)), 1)
                ref_pct = round(max(0.0, min(50.0, ((whs - crude_gal) / ret) * 100.0)), 1)
                tax_pct = round(max(0.0, min(40.0, (tax_gal / ret) * 100.0)), 1)
                dist_pct = round(max(0.0, 100.0 - crude_pct - ref_pct - tax_pct), 1)
                breakdown.update({
                    "crude_oil_pct": crude_pct,
                    "refining_pct": ref_pct,
                    "distribution_marketing_pct": dist_pct,
                    "taxes_pct": tax_pct,
                    "period": latest,
                    "provenance_type": "OBSERVED",
                    "source": "U.S. EIA API v2 STEO Structural Breakdown",
                })

        return breakdown


_GLOBAL_EIA_CLIENT: Optional[EIAClientV2] = None


def get_eia_client() -> EIAClientV2:
    """Returns singleton EIAClientV2 instance."""
    global _GLOBAL_EIA_CLIENT
    if _GLOBAL_EIA_CLIENT is None:
        _GLOBAL_EIA_CLIENT = EIAClientV2()
    return _GLOBAL_EIA_CLIENT
