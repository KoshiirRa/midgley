"""
Feast Feature Store Module for Point-in-Time Backtesting & Unified Feature Serving
Defines Feast entities, feature views, file sources, and point-in-time join engine
for EIA, FRED, NOAA weather, and LLM event shock decay vectors (Issue #94).
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Mandatory Feast & PyArrow Import Handling
try:
    import feast
    from feast import (
        Entity,
        FeatureView,
        Field,
        FileSource,
        FeatureStore,
        ValueType,
    )
    from feast.types import Float32, Float64, Int64, String, Bool
    HAS_FEAST = True
except ImportError:
    HAS_FEAST = False
    logger.warning("Feast library not installed. Falling back to offline point-in-time simulation engine.")


class MidgleyFeastStore:
    """
    Feast Feature Store manager providing point-in-time (AS OF) historical joins
    and online feature materialization across EIA, FRED, NOAA, and LLM Event Shocks.
    """

    def __init__(self, repo_path: str = "data"):
        self.repo_path = os.path.abspath(repo_path)
        self.config_path = os.path.join(self.repo_path, "feature_store.yaml")
        self.parquet_dir = os.path.join(self.repo_path, "feast_parquet")
        os.makedirs(self.parquet_dir, exist_ok=True)

        self._store = None
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Ensures data/feature_store.yaml exists."""
        if not os.path.exists(self.config_path):
            reg_path = os.path.join(self.repo_path, 'registry.pb').replace('\\', '/')
            db_path = os.path.join(self.repo_path, 'online_store.db').replace('\\', '/')
            config_content = f"""project: midgley_feature_store
registry: {reg_path}
provider: local
offline_store:
  type: file
online_store:
  type: sqlite
  path: {db_path}
flags:
  alpha_features: false
"""
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(config_content)
            logger.info(f"Generated Feast feature_store.yaml at {self.config_path}")

    def initialize_store(self):
        """Initializes and returns the Feast FeatureStore instance."""
        if not HAS_FEAST:
            logger.warning("Feast not installed. Cannot instantiate FeatureStore.")
            return None

        if self._store is None:
            try:
                self._store = FeatureStore(repo_path=self.repo_path)
                logger.info("Successfully initialized Feast FeatureStore.")
            except Exception as e:
                logger.error(f"Error initializing Feast FeatureStore: {e}")
                self._store = None
        return self._store

    def prepare_parquet_sources(self, market_df: pd.DataFrame, events_df: pd.DataFrame = None, region: str = "Tulsa_OK"):
        """
        Exports feature feeds into timestamped Parquet files for Feast offline point-in-time joins.
        """
        if market_df.empty:
            logger.warning("Cannot prepare Feast Parquet sources: market_df is empty.")
            return {}

        df = market_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # Add required Feast timestamp columns
        df['event_timestamp'] = df['date'].dt.tz_localize(None)
        df['created_timestamp'] = pd.Timestamp.now()
        df['location_id'] = region
        df['market_id'] = "RBOB_FUTURES"

        # 1. EIA & Market Physical Features Parquet Source
        eia_cols = ['event_timestamp', 'created_timestamp', 'location_id', 'gasoline_rbob']
        if 'wti_crude' in df.columns:
            df['crude_per_gal'] = df['wti_crude'] / 42.0
            df['crack_spread'] = df['gasoline_rbob'] - df['crude_per_gal']
            eia_cols.extend(['wti_crude', 'crack_spread'])
        else:
            df['wti_crude'] = 70.0
            df['crack_spread'] = 0.50
            eia_cols.extend(['wti_crude', 'crack_spread'])

        if 'heating_oil' in df.columns:
            rbob_bbl = df['gasoline_rbob'] * 42.0
            ho_bbl = df['heating_oil'] * 42.0
            df['crack_spread_321'] = (2.0 * rbob_bbl + 1.0 * ho_bbl - 3.0 * df['wti_crude']) / 3.0
            eia_cols.append('crack_spread_321')
        else:
            df['crack_spread_321'] = df['crack_spread'] * 42.0
            eia_cols.append('crack_spread_321')

        eia_parquet_path = os.path.join(self.parquet_dir, "eia_weekly.parquet")
        df[eia_cols].to_parquet(eia_parquet_path, index=False)

        # 2. FRED Economic Features Parquet Source
        fred_cols = ['event_timestamp', 'created_timestamp', 'market_id', 'gasoline_rbob']
        df['gas_return_1d'] = df['gasoline_rbob'].pct_change(1).fillna(0.0)
        df['gas_return_5d'] = df['gasoline_rbob'].pct_change(5).fillna(0.0)
        fred_cols.extend(['gas_return_1d', 'gas_return_5d'])
        fred_parquet_path = os.path.join(self.parquet_dir, "fred_macro.parquet")
        df[fred_cols].to_parquet(fred_parquet_path, index=False)

        # 3. NOAA Weather Features Parquet Source
        noaa_cols = ['event_timestamp', 'created_timestamp', 'location_id']
        df['hdd_daily'] = df.get('hdd_daily', 0.0)
        df['cdd_daily'] = df.get('cdd_daily', 0.0)
        df['freeze_warning_flag'] = df.get('freeze_warning_flag', 0.0)
        df['spc_tornado_risk'] = df.get('spc_tornado_risk', 0.0)
        noaa_cols.extend(['hdd_daily', 'cdd_daily', 'freeze_warning_flag', 'spc_tornado_risk'])
        noaa_parquet_path = os.path.join(self.parquet_dir, "noaa_weather.parquet")
        df[noaa_cols].to_parquet(noaa_parquet_path, index=False)

        # 4. LLM Event Shock Decay Parquet Source
        llm_cols = ['event_timestamp', 'created_timestamp', 'location_id']
        decay_cols = ['geopolitical_risk', 'supply_disruption', 'demand_sentiment', 'opec_action', 'overall_price_pressure']
        if events_df is not None and not events_df.empty:
            ev = events_df.copy()
            ev['date'] = pd.to_datetime(ev['date'])
            ev['event_timestamp'] = ev['date'].dt.tz_localize(None)
            ev['created_timestamp'] = pd.Timestamp.now()
            ev['location_id'] = region
            for col in decay_cols:
                if col not in ev.columns:
                    ev[col] = 0.0
            llm_df = ev[['event_timestamp', 'created_timestamp', 'location_id'] + decay_cols]
        else:
            llm_df = df[['event_timestamp', 'created_timestamp', 'location_id']].copy()
            for col in decay_cols:
                llm_df[col] = 0.0

        llm_parquet_path = os.path.join(self.parquet_dir, "llm_event_decay.parquet")
        llm_df.to_parquet(llm_parquet_path, index=False)

        paths = {
            "eia": eia_parquet_path,
            "fred": fred_parquet_path,
            "noaa": noaa_parquet_path,
            "llm_decay": llm_parquet_path,
        }
        logger.info(f"Exported Feast Parquet feature sources to {self.parquet_dir}")
        return paths

    def get_historical_point_in_time_features(
        self,
        entity_df: pd.DataFrame,
        feature_refs: list = None,
        market_df: pd.DataFrame = None,
        events_df: pd.DataFrame = None,
        region: str = "Tulsa_OK"
    ) -> pd.DataFrame:
        """
        Executes point-in-time (AS OF) joins to retrieve features on or before entity timestamps.
        Prevents future data leakage in backtesting.
        """
        if market_df is not None:
            self.prepare_parquet_sources(market_df, events_df, region)

        entity = entity_df.copy()
        if 'event_timestamp' not in entity.columns:
            if 'date' in entity.columns:
                entity['event_timestamp'] = pd.to_datetime(entity['date']).dt.tz_localize(None)
            else:
                raise ValueError("entity_df must contain 'date' or 'event_timestamp' column.")

        if 'location_id' not in entity.columns:
            entity['location_id'] = region
        if 'market_id' not in entity.columns:
            entity['market_id'] = "RBOB_FUTURES"

        if HAS_FEAST:
            store = self.initialize_store()
            if store is not None and feature_refs:
                try:
                    historical_df = store.get_historical_features(
                        entity_df=entity,
                        features=feature_refs
                    ).to_df()
                    return historical_df
                except Exception as e:
                    logger.warning(f"Feast get_historical_features failed: {e}. Executing point-in-time fallback join.")

        # Offline Point-in-Time AS OF Join Simulation Engine
        return self._simulate_point_in_time_join(entity, region)

    def _simulate_point_in_time_join(self, entity_df: pd.DataFrame, region: str) -> pd.DataFrame:
        """
        Simulates Feast point-in-time AS OF join using pandas merge_asof
        to guarantee strict temporal non-leakage when Feast is offline/initializing.
        """
        res = entity_df.copy().sort_values('event_timestamp')

        eia_path = os.path.join(self.parquet_dir, "eia_weekly.parquet")
        if os.path.exists(eia_path):
            eia_df = pd.read_parquet(eia_path).sort_values('event_timestamp')
            cols_to_merge = [c for c in eia_df.columns if c not in ['created_timestamp', 'location_id'] or c == 'event_timestamp']
            res = pd.merge_asof(res, eia_df[cols_to_merge], on='event_timestamp', direction='backward')

        llm_path = os.path.join(self.parquet_dir, "llm_event_decay.parquet")
        if os.path.exists(llm_path):
            llm_df = pd.read_parquet(llm_path).sort_values('event_timestamp')
            cols_to_merge = [c for c in llm_df.columns if c not in ['created_timestamp', 'location_id'] or c == 'event_timestamp']
            res = pd.merge_asof(res, llm_df[cols_to_merge], on='event_timestamp', direction='backward', suffixes=('', '_llm'))

        return res.reset_index(drop=True)


# Feast Definitions (Exposed at Module Level when Feast is Installed)
if HAS_FEAST:
    location_entity = Entity(
        name="location_id",
        value_type=ValueType.STRING,
        description="Metropolitan area or regional location key"
    )
    market_entity = Entity(
        name="market_id",
        value_type=ValueType.STRING,
        description="Commodity market ticker identifier"
    )

    eia_source = FileSource(
        name="eia_weekly_source",
        path="data/feast_parquet/eia_weekly.parquet",
        timestamp_field="event_timestamp",
        created_timestamp_column="created_timestamp"
    )
    fred_source = FileSource(
        name="fred_macro_source",
        path="data/feast_parquet/fred_macro.parquet",
        timestamp_field="event_timestamp",
        created_timestamp_column="created_timestamp"
    )
    noaa_source = FileSource(
        name="noaa_weather_source",
        path="data/feast_parquet/noaa_weather.parquet",
        timestamp_field="event_timestamp",
        created_timestamp_column="created_timestamp"
    )
    llm_decay_source = FileSource(
        name="llm_event_decay_source",
        path="data/feast_parquet/llm_event_decay.parquet",
        timestamp_field="event_timestamp",
        created_timestamp_column="created_timestamp"
    )

    eia_feature_view = FeatureView(
        name="eia_weekly_fv",
        entities=[location_entity],
        schema=[
            Field(name="gasoline_rbob", dtype=Float64),
            Field(name="wti_crude", dtype=Float64),
            Field(name="crack_spread", dtype=Float64),
            Field(name="crack_spread_321", dtype=Float64),
        ],
        online=True,
        source=eia_source,
        ttl=timedelta(days=1825),
    )

    fred_feature_view = FeatureView(
        name="fred_macro_fv",
        entities=[market_entity],
        schema=[
            Field(name="gasoline_rbob", dtype=Float64),
            Field(name="gas_return_1d", dtype=Float64),
            Field(name="gas_return_5d", dtype=Float64),
        ],
        online=True,
        source=fred_source,
        ttl=timedelta(days=1825),
    )

    noaa_feature_view = FeatureView(
        name="noaa_weather_fv",
        entities=[location_entity],
        schema=[
            Field(name="hdd_daily", dtype=Float64),
            Field(name="cdd_daily", dtype=Float64),
            Field(name="freeze_warning_flag", dtype=Float64),
            Field(name="spc_tornado_risk", dtype=Float64),
        ],
        online=True,
        source=noaa_source,
        ttl=timedelta(days=1825),
    )

    llm_event_decay_feature_view = FeatureView(
        name="llm_event_decay_fv",
        entities=[location_entity],
        schema=[
            Field(name="geopolitical_risk", dtype=Float64),
            Field(name="supply_disruption", dtype=Float64),
            Field(name="demand_sentiment", dtype=Float64),
            Field(name="opec_action", dtype=Float64),
            Field(name="overall_price_pressure", dtype=Float64),
        ],
        online=True,
        source=llm_decay_source,
        ttl=timedelta(days=1825),
    )
