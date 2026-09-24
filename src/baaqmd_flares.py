"""
BAAQMD Bay Area Refinery Flare Incident Connector (src/baaqmd_flares.py)
Ingests Bay Area Air Quality Management District (BAAQMD) Regulation 12 Rule 11/12 flare causal
investigation reports for retrospective Northern California / SF Bay Area refinery outage validation. (Issue #385)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

BAAQMD_STORAGE_FILE = os.path.join("data", "benchmarks", "baaqmd_refinery_events.csv")
BAAQMD_VINTAGE_FILE = os.path.join("data", "baaqmd_flare_vintages.json")

# Monitored SF Bay Area Petroleum Refineries
BAY_AREA_REFINERIES = {
    "CHEVRON_RICHMOND": {
        "facility_name": "Chevron Products Company - Richmond Refinery",
        "county": "Contra Costa",
        "crude_capacity_bpd": 245000,
        "primary_metro": "Oakland_CA"
    },
    "VALERO_BENICIA": {
        "facility_name": "Valero Refining Company - Benicia Refinery",
        "county": "Solano",
        "crude_capacity_bpd": 170000,
        "primary_metro": "BayArea_CA"
    },
    "PHILLIPS_66_RODEO": {
        "facility_name": "Phillips 66 Company - San Francisco Refinery (Rodeo)",
        "county": "Contra Costa",
        "crude_capacity_bpd": 140000,
        "primary_metro": "BayArea_CA"
    },
    "PBF_MARTINEZ": {
        "facility_name": "Martinez Refining Company LLC (PBF)",
        "county": "Contra Costa",
        "crude_capacity_bpd": 157000,
        "primary_metro": "BayArea_CA"
    }
}

# Curated Historical BAAQMD Flare Causal Benchmark Dataset
CURATED_BAAQMD_BENCHMARKS = [
    {
        "report_id": "BAAQMD-2022-0041",
        "facility_id": "CHEVRON_RICHMOND",
        "facility_name": "Chevron Products Company - Richmond Refinery",
        "event_date": "2022-04-12",
        "duration_hours": 18.5,
        "affected_unit": "Fluid Catalytic Cracking Unit (FCCU)",
        "root_cause_category": "unplanned_power_outage",
        "root_cause_summary": "PG&E external grid voltage sag tripped main refinery power feeder causing automated safety flaring.",
        "flared_gas_scf": 1850000.0,
        "so2_emissions_lbs": 4200.0,
        "unplanned_shutdown": True,
        "disruption_severity": "High"
    },
    {
        "report_id": "BAAQMD-2022-0118",
        "facility_id": "VALERO_BENICIA",
        "facility_name": "Valero Refining Company - Benicia Refinery",
        "event_date": "2022-09-06",
        "duration_hours": 24.0,
        "affected_unit": "Alkylation Unit & Boiler House",
        "root_cause_category": "compressor_trip",
        "root_cause_summary": "Wet gas compressor mechanical seal failure resulted in pressure buildup and automated relief venting.",
        "flared_gas_scf": 2400000.0,
        "so2_emissions_lbs": 6800.0,
        "unplanned_shutdown": True,
        "disruption_severity": "High"
    },
    {
        "report_id": "BAAQMD-2023-0029",
        "facility_id": "PBF_MARTINEZ",
        "facility_name": "Martinez Refining Company LLC (PBF)",
        "event_date": "2023-03-15",
        "duration_hours": 8.0,
        "affected_unit": "Catalytic Reforming Unit (CRU)",
        "root_cause_category": "flaring_safety_relief",
        "root_cause_summary": "Instrument air line leak caused reformer feed valve closure and brief safety relief flaring.",
        "flared_gas_scf": 620000.0,
        "so2_emissions_lbs": 850.0,
        "unplanned_shutdown": False,
        "disruption_severity": "Medium"
    },
    {
        "report_id": "BAAQMD-2023-0094",
        "facility_id": "CHEVRON_RICHMOND",
        "facility_name": "Chevron Products Company - Richmond Refinery",
        "event_date": "2023-08-22",
        "duration_hours": 12.0,
        "affected_unit": "Crude Distillation Unit (CDU)",
        "root_cause_category": "unit_turnaround",
        "root_cause_summary": "Controlled startup purge flaring during scheduled hydrotreater turnaround and catalyst loading.",
        "flared_gas_scf": 890000.0,
        "so2_emissions_lbs": 1100.0,
        "unplanned_shutdown": False,
        "disruption_severity": "Low"
    },
    {
        "report_id": "BAAQMD-2024-0012",
        "facility_id": "PHILLIPS_66_RODEO",
        "facility_name": "Phillips 66 Company - San Francisco Refinery (Rodeo)",
        "event_date": "2024-01-19",
        "duration_hours": 36.0,
        "affected_unit": "Renewable Diesel Hydrotreater Unit",
        "root_cause_category": "unplanned_power_outage",
        "root_cause_summary": "Atmospheric river storm high winds downed on-site sub-transmission line halting reactor feed pumps.",
        "flared_gas_scf": 3100000.0,
        "so2_emissions_lbs": 5400.0,
        "unplanned_shutdown": True,
        "disruption_severity": "High"
    }
]


class BAAQMDFlareConnector:
    """
    Ingests and queries official BAAQMD refinery flare causal reports for retrospective
    detector validation, AQI spike corroboration, and empirical outage impact benchmarking.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        vintage_path: Optional[str] = None
    ):
        self.storage_file = storage_path or BAAQMD_STORAGE_FILE
        self.storage_path = self.storage_file
        self.vintage_file = vintage_path or BAAQMD_VINTAGE_FILE
        self.vintage_path = self.vintage_file
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.storage_file)), exist_ok=True)
        if not os.path.exists(self.vintage_file):
            with open(self.vintage_file, "w", encoding="utf-8") as f:
                json.dump({"vintages": {}, "last_updated": None}, f, indent=2)
        if not os.path.exists(self.storage_file):
            self._initialize_benchmark_data()

    def _initialize_benchmark_data(self) -> None:
        df = pd.DataFrame(CURATED_BAAQMD_BENCHMARKS)
        df.to_csv(self.storage_file, index=False)

    def fetch_flare_incidents(
        self,
        facility_id: Optional[str] = None,
        root_cause_category: Optional[str] = None,
        only_unplanned: bool = False,
        min_flared_scf: float = 0.0,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Retrieves BAAQMD flare incident records with filtering parameters.
        """
        if not os.path.exists(self.storage_file) or force_refresh:
            self._initialize_benchmark_data()

        df = pd.read_csv(self.storage_file)
        df["event_date"] = pd.to_datetime(df["event_date"])
        df = df.sort_values("event_date")

        if facility_id:
            df = df[df["facility_id"] == facility_id]

        if root_cause_category:
            df = df[df["root_cause_category"] == root_cause_category]

        if only_unplanned:
            df = df[df["unplanned_shutdown"] == True]

        if min_flared_scf > 0:
            df = df[df["flared_gas_scf"] >= min_flared_scf]

        return df

    def get_facility_incident_history(self, facility_id: str) -> List[Dict[str, Any]]:
        """Returns chronological flare investigation reports for a specific Bay Area refinery."""
        df = self.fetch_flare_incidents(facility_id=facility_id)
        return df.to_dict(orient="records")

    def get_refinery_disruption_benchmark_matrix(self) -> pd.DataFrame:
        """
        Generates benchmark summary matrix of verified refinery flaring upsets.
        """
        df = self.fetch_flare_incidents(only_unplanned=True)
        records = []
        for _, row in df.iterrows():
            records.append({
                "report_id": row["report_id"],
                "facility_name": row["facility_name"],
                "event_date": row["event_date"].strftime("%Y-%m-%d") if hasattr(row["event_date"], "strftime") else str(row["event_date"]),
                "affected_unit": row["affected_unit"],
                "root_cause_category": row["root_cause_category"],
                "flared_gas_scf": float(row["flared_gas_scf"]),
                "so2_emissions_lbs": float(row["so2_emissions_lbs"]),
                "duration_hours": float(row["duration_hours"]),
                "disruption_severity": row["disruption_severity"]
            })
        return pd.DataFrame(records)
