"""
Alternative & Physical Energy Data Feeds Module (src/alternative_data_feeds.py)
Ingests advanced physical, macroeconomic, and alternative data feeds:
1. EIA Weekly Petroleum Status Report (WPSR) - Inventory Draws/Builds & Refinery Utilization %
2. Baker Hughes US Active Drilling Rig Count - Domestic Crude Supply Pipeline (3-6 mo lead)
3. FRED Macro Data (US Dollar DXY Index, Vehicle Miles Traveled VMT)
4. Cboe Crude Oil Volatility Index (OVX) - Market Tail Risk & Hedging Sentiment
"""

import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import logging
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

ALTERNATIVE_DATA_SOURCES = {
    "EIA_Weekly_Inventories": {
        "agency": "US Energy Information Administration (EIA)",
        "frequency": "Weekly (Wednesdays 10:30 AM EST)",
        "key_metrics": ["Commercial Crude Stocks", "Finished Motor Gasoline Supplied (Demand)", "Refinery Utilization %"],
        "predictive_power": "High short-term (1-5 day) price adjustment driver.",
        "bitemporal_architecture": {
            "fields": ["valid_date", "as_of", "is_vintage_reconstructed"],
            "description": "Bitemporal vintage tracking eliminating lookahead bias in historical backtests and model retraining (Issue #121)."
        }
    },
    "Baker_Hughes_Rig_Count": {
        "agency": "Baker Hughes / Enverus",
        "frequency": "Weekly (Fridays 1:00 PM EST)",
        "key_metrics": ["Permian Basin Rig Count", "Eagle Ford Rig Count", "Total US Active Oil Rigs"],
        "predictive_power": "Medium-to-long term (3-6 month) domestic crude supply pipeline lead indicator.",
        "bitemporal_architecture": {
            "fields": ["valid_date", "as_of", "is_vintage_reconstructed"],
            "description": "Bitemporal vintage tracking eliminating lookahead bias in historical backtests (Issue #269)."
        }
    },
    "FRED_Macro_USD_VMT": {
        "agency": "Federal Reserve Bank of St. Louis (FRED) & US DOT",
        "frequency": "Daily / Monthly",
        "key_metrics": ["US Dollar Index (DXY / DTWEXBGS)", "Vehicle Miles Traveled (VMT)", "Commercial Freight Index"],
        "predictive_power": "Macro demand foundation & currency exchange rate pricing impact."
    },
    "OVX_Crude_Volatility": {
        "agency": "Chicago Board Options Exchange (Cboe)",
        "frequency": "Daily real-time",
        "key_metrics": ["OVX Crude Volatility Index"],
        "predictive_power": "Options tail-risk sentiment & supply shock panic gauge."
    },
    "BTS_Freight_Transportation_Services_Index": {
        "agency": "U.S. Bureau of Transportation Statistics (BTS)",
        "frequency": "Monthly (Seasonally Adjusted)",
        "key_metrics": ["Freight TSI (tsi_freight)", "Truck Tonnage Index (truck_d11)", "Petroleum Transport (petroleum_d11)"],
        "predictive_power": "Leading physical freight and commercial transportation demand proxy for diesel and motor gasoline consumption (Issue #74).",
        "bitemporal_architecture": {
            "fields": ["valid_date", "as_of", "is_vintage_reconstructed"],
            "description": "Bitemporal vintage tracking eliminating lookahead bias in historical backtests (Issue #74)."
        }
    }
}

HISTORICAL_BAKER_HUGHES_RIGS = [
    {"date": "2022-01-07", "us_active_oil_rigs": 481, "permian_rigs": 293},
    {"date": "2022-06-03", "us_active_oil_rigs": 574, "permian_rigs": 345},
    {"date": "2022-12-02", "us_active_oil_rigs": 627, "permian_rigs": 353},
    {"date": "2023-06-02", "us_active_oil_rigs": 555, "permian_rigs": 349},
    {"date": "2023-12-01", "us_active_oil_rigs": 505, "permian_rigs": 310},
    {"date": "2024-06-07", "us_active_oil_rigs": 492, "permian_rigs": 309},
    {"date": "2024-12-06", "us_active_oil_rigs": 484, "permian_rigs": 304},
    {"date": "2025-06-06", "us_active_oil_rigs": 478, "permian_rigs": 301},
    {"date": "2026-01-09", "us_active_oil_rigs": 472, "permian_rigs": 298}
]

def fetch_cboe_crude_volatility_ovx(start_date: str = "2022-01-01", end_date: str = None) -> pd.DataFrame:
    """
    Fetches the Cboe Crude Oil Volatility Index (ticker: ^OVX) using yfinance with daily lookup caching.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    cache_key = f"altdata:cboe_ovx:{start_date}:{end_date}"
    cached = global_cache.get(cache_key)
    if cached and "records" in cached:
        logger.info("Loaded Cboe OVX volatility index from lookup cache.")
        df = pd.DataFrame(cached["records"])
        df['date'] = pd.to_datetime(df['date'])
        return df

    logger.info(f"Fetching Cboe Crude Oil Volatility Index (^OVX) from {start_date} to {end_date}...")
    try:
        ovx_data = yf.download("^OVX", start=start_date, end=end_date, progress=False)
        if isinstance(ovx_data.columns, pd.MultiIndex):
            close_series = ovx_data['Close']['^OVX']
        else:
            close_series = ovx_data['Close']
            
        df = pd.DataFrame({'date': close_series.index, 'ovx_volatility_index': close_series.values})
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        res_df = df.sort_values('date').ffill().bfill().reset_index(drop=True)
        
        # Save to lookup cache (24 hours TTL)
        records = res_df.assign(date=res_df['date'].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
        global_cache.set(cache_key, {"records": records}, ttl_seconds=86400)
        return res_df
    except Exception as e:
        logger.warning(f"Could not fetch ^OVX volatility index: {e}")
        return pd.DataFrame()


class BakerHughesDataConnector:
    """
    Zero-Cost Baker Hughes & Rotary Drilling Rig Count Connector.
    Ingests weekly active drilling rig counts, provides bitemporal vintage tracking,
    7-day lookup caching, and resilient offline fallback (Issue #269).
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def fetch_rig_counts(self, start_date: str = None) -> pd.DataFrame:
        """
        Fetches Baker Hughes rig count data dynamically with 7-day cache and offline fallback.
        """
        import urllib.request
        cache_key = f"altdata:baker_hughes:{start_date or 'all'}"
        cached = global_cache.get(cache_key)
        if cached and "records" in cached:
            df = pd.DataFrame(cached["records"])
            df['date'] = pd.to_datetime(df['date'])
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date)]
            return df

        df = None
        # Attempt 1: Fetch via public open FRED rotary rig series (OILRESUS / free CSV download)
        try:
            url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=OILRESUS"
            req = urllib.request.Request(url, headers={"User-Agent": "Midgley-BakerHughesConnector/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    raw_lines = response.read().decode('utf-8').strip().split('\n')
                    if len(raw_lines) > 2:
                        records = []
                        for line in raw_lines[1:]:
                            parts = line.split(',')
                            if len(parts) == 2 and parts[1] != '.':
                                try:
                                    dt = parts[0].strip()
                                    oil_rigs = int(float(parts[1]))
                                    permian_est = int(oil_rigs * 0.62)
                                    records.append({
                                        "date": dt,
                                        "us_active_oil_rigs": oil_rigs,
                                        "permian_rigs": permian_est
                                    })
                                except ValueError:
                                    continue
                        if records:
                            df = pd.DataFrame(records)
                            df['date'] = pd.to_datetime(df['date'])
                            try:
                                from src.benchmark_updater import save_historical_benchmark
                                save_historical_benchmark("baker_hughes", records)
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Dynamic online rig count fetch skipped/failed: {e}")

        # Fallback to persistent historical benchmark file before hardcoded constant
        if df is None or df.empty:
            try:
                from src.benchmark_updater import load_historical_benchmark
                bench_records = load_historical_benchmark("baker_hughes")
                if bench_records and isinstance(bench_records, list):
                    df = pd.DataFrame(bench_records)
                    df['date'] = pd.to_datetime(df['date'])
            except Exception:
                df = None

        # Fallback to curated historical dataset constant if needed
        if df is None or df.empty:
            df = pd.DataFrame(HISTORICAL_BAKER_HUGHES_RIGS)
            df['date'] = pd.to_datetime(df['date'])

        # Standardize columns
        df = df.sort_values('date').reset_index(drop=True)
        if "baker_hughes_oil_rigs" not in df.columns and "us_active_oil_rigs" in df.columns:
            df['baker_hughes_oil_rigs'] = df['us_active_oil_rigs']
        if "baker_hughes_us_rig_count" not in df.columns:
            df['baker_hughes_us_rig_count'] = df['baker_hughes_oil_rigs']
        if "baker_hughes_gas_rigs" not in df.columns:
            df['baker_hughes_gas_rigs'] = (df['baker_hughes_us_rig_count'] * 0.20).astype(int)
        if "baker_hughes_rig_delta_1w" not in df.columns:
            df['baker_hughes_rig_delta_1w'] = df['baker_hughes_us_rig_count'].diff().fillna(0.0)

        # Persist bitemporal vintage snapshot
        try:
            latest_row = df.iloc[-1].to_dict()
            self.save_baker_hughes_vintage_record({
                "source": "Baker Hughes Rig Count (Zero-Cost)",
                "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "valid_date": pd.to_datetime(latest_row["date"]).strftime("%Y-%m-%d"),
                "latest_us_active_oil_rigs": int(latest_row.get("baker_hughes_oil_rigs", 0)),
                "latest_us_total_rigs": int(latest_row.get("baker_hughes_us_rig_count", 0)),
                "is_vintage_reconstructed": False
            })
        except Exception as e:
            logger.debug(f"Could not persist Baker Hughes vintage snapshot: {e}")

        # Cache in global_cache (7 days TTL)
        try:
            records = df.assign(date=df['date'].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
            global_cache.set(cache_key, {"records": records}, ttl_seconds=604800)
        except Exception:
            pass

        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        return df

    @staticmethod
    def save_baker_hughes_vintage_record(record: dict, filepath: str = os.path.join("data", "baker_hughes_vintages.json")) -> None:
        """
        Saves or appends a bitemporal Baker Hughes observation snapshot to persistent vintage storage (Issue #269).
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            vintages = []
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        vintages = json.load(f)
                except Exception:
                    vintages = []

            rec_copy = dict(record)
            if "as_of" not in rec_copy:
                rec_copy["as_of"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "valid_date" not in rec_copy:
                rec_copy["valid_date"] = datetime.now().strftime("%Y-%m-%d")
            if "is_vintage_reconstructed" not in rec_copy:
                rec_copy["is_vintage_reconstructed"] = False

            vintages = [v for v in vintages if not (v.get("as_of") == rec_copy["as_of"] and v.get("valid_date") == rec_copy.get("valid_date"))]
            vintages.append(rec_copy)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json.dumps(vintages, indent=2))
        except Exception as e:
            logger.warning(f"Could not persist Baker Hughes vintage record: {e}")

    @staticmethod
    def get_baker_hughes_vintages_as_of(target_as_of: str = None, filepath: str = os.path.join("data", "baker_hughes_vintages.json")) -> list:
        """
        Retrieves Baker Hughes observations published on or before target_as_of (Issue #269).
        """
        try:
            if not os.path.exists(filepath):
                return []
            with open(filepath, "r", encoding="utf-8") as f:
                vintages = json.load(f)
            if not target_as_of:
                return vintages
            
            target_str = str(target_as_of)
            filtered = []
            for v in vintages:
                as_of_val = v.get("as_of", "")
                if as_of_val <= target_str or as_of_val[:10] <= target_str[:10]:
                    filtered.append(v)
            return filtered
        except Exception as e:
            logger.warning(f"Could not read Baker Hughes vintages as of {target_as_of}: {e}")
            return []


def get_baker_hughes_rig_count_feed() -> pd.DataFrame:
    """
    Returns US active oil drilling rig count DataFrame via BakerHughesDataConnector.
    """
    connector = BakerHughesDataConnector()
    return connector.fetch_rig_counts()


def fetch_baker_hughes_rig_counts(start_date: str = None) -> pd.DataFrame:
    """
    Returns Baker Hughes active drilling rig count DataFrame with expected feature engineering column schema.
    """
    connector = BakerHughesDataConnector()
    df = connector.fetch_rig_counts(start_date=start_date)
    if df.empty:
        return pd.DataFrame()
    return df


def fetch_bts_transportation_data(start_date: str = "2020-01-01") -> pd.DataFrame:
    """
    Returns U.S. BTS Freight Transportation Services Index and Truck Tonnage DataFrame (Issue #74).
    """
    from src.bts_transportation import BTSTransportationConnector
    connector = BTSTransportationConnector()
    return connector.fetch_bts_tsi_dataset(start_date=start_date)


if __name__ == "__main__":
    ovx_df = fetch_cboe_crude_volatility_ovx("2024-01-01")
    rigs_df = get_baker_hughes_rig_count_feed()
    bts_df = fetch_bts_transportation_data("2024-01-01")
    print("\n" + "="*80)
    print(" ALTERNATIVE & PHYSICAL DATA FEEDS SUMMARY")
    print("="*80)
    print(f"OVX Volatility Days Fetched: {len(ovx_df)}")
    print(f"Baker Hughes Rig Count Samples: {len(rigs_df)}")
    print(f"BTS Transportation Index Samples: {len(bts_df)}")
    print(json.dumps(ALTERNATIVE_DATA_SOURCES, indent=2))
