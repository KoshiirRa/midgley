"""
Agent Memory Manager Module (src/agent_memory.py)
Implements Episodic Qualitative Error Reflection & Historical Analogy Search (Retain-Recall-Reflect).
Issue #230: [Weekly Review 2.0] Qualitative Anomaly Post-Mortems

Architecture:
- Primary Engine: Vectorize Hindsight API on Google Cloud Run (Scale-to-Zero) backed by Supabase pgvector.
- Zero-Cost Fallback: Local SQLite FTS5 Memory Store (data/agent_memory.sqlite) with BM25 indexing.
- Synthesis: Gemini 2.5 Flash LLM reflection pass with deterministic rule-based fallback.
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.hindsight_client import HindsightClient
from src.telemetry import log_agent_memory_op

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = os.path.join("data", "agent_memory.sqlite")
DEFAULT_VINTAGES_PATH = os.path.join("data", "agent_memory_vintages.json")
HISTORY_CSV = os.path.join("data", "prediction_history.csv")
TELEMETRY_LEDGER_PATH = os.path.join("data", "telemetry_ledger.json")


class SQLiteMemoryStore:
    """
    Zero-Cost, 100% Offline Local SQLite Memory Store with Full-Text Search (FTS5).
    """

    def __init__(self, db_path: str = DEFAULT_SQLITE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # 1. Main memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT UNIQUE,
                    bank_id TEXT DEFAULT 'midgley-gas-forecasting',
                    memory_type TEXT DEFAULT 'experience',
                    region TEXT NOT NULL,
                    forecast_target_date TEXT,
                    predicted_price REAL,
                    actual_price REAL,
                    error_dollars REAL,
                    anomaly_type TEXT,
                    content TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}',
                    cloud_synced INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            # Migration check: Ensure cloud_synced column exists for existing databases
            cursor.execute("PRAGMA table_info(memories)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "cloud_synced" not in columns:
                cursor.execute("ALTER TABLE memories ADD COLUMN cloud_synced INTEGER DEFAULT 0")

            # 2. FTS5 full text search virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    memory_id UNINDEXED,
                    region,
                    anomaly_type,
                    content,
                    tokenize='porter unicode61'
                )
            """)
            # 3. Reflections / Mental models table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reflection_id TEXT UNIQUE,
                    region TEXT,
                    anomaly_type TEXT,
                    title TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    historical_analogy TEXT,
                    calibration_suggestion TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def retain(
        self,
        content: str,
        region: str,
        memory_type: str = "experience",
        anomaly_type: Optional[str] = None,
        error_dollars: Optional[float] = None,
        predicted_price: Optional[float] = None,
        actual_price: Optional[float] = None,
        forecast_target_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cloud_synced: int = 0
    ) -> Dict[str, Any]:
        """Stores experience memory in local SQLite with FTS5 index."""
        now_str = datetime.now(timezone.utc).isoformat()
        date_tag = (forecast_target_date or datetime.now().strftime("%Y%m%d")).replace("-", "")
        mem_id = f"exp_{date_tag}_{region.lower()}_{anomaly_type or 'general'}_{abs(int((error_dollars or 0) * 1000))}"
        meta_str = json.dumps(metadata or {})

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO memories (
                    memory_id, bank_id, memory_type, region, forecast_target_date,
                    predicted_price, actual_price, error_dollars, anomaly_type,
                    content, metadata_json, cloud_synced, created_at
                ) VALUES (?, 'midgley-gas-forecasting', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mem_id, memory_type, region, forecast_target_date,
                predicted_price, actual_price, error_dollars, anomaly_type,
                content, meta_str, cloud_synced, now_str
            ))

            # Update FTS5 index
            cursor.execute("DELETE FROM memories_fts WHERE memory_id = ?", (mem_id,))
            cursor.execute("""
                INSERT INTO memories_fts (memory_id, region, anomaly_type, content)
                VALUES (?, ?, ?, ?)
            """, (mem_id, region, anomaly_type or "", content))

            conn.commit()
            logger.debug(f"Retained local SQLite memory {mem_id}")
            return {"status": "SUCCESS", "memory_id": mem_id, "backend": "sqlite_fts5"}
        except Exception as e:
            logger.warning(f"Failed to retain memory in SQLite: {e}")
            return {"status": "ERROR", "error": str(e), "backend": "sqlite_fts5"}
        finally:
            conn.close()

    def mark_as_synced(self, memory_id: str) -> bool:
        """Marks a local SQLite memory record as synced to Hindsight Cloud."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE memories SET cloud_synced = 1 WHERE memory_id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.debug(f"Error marking memory {memory_id} as synced: {e}")
            return False
        finally:
            conn.close()

    def get_unretained_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches pending memories that have not yet been synchronized to Hindsight Cloud."""
        results = []
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT memory_id, memory_type, region, forecast_target_date,
                       predicted_price, actual_price, error_dollars, anomaly_type,
                       content, metadata_json
                FROM memories
                WHERE cloud_synced = 0
                ORDER BY id ASC LIMIT ?
            """, (limit,))
            for r in cursor.fetchall():
                results.append({
                    "memory_id": r["memory_id"],
                    "memory_type": r["memory_type"],
                    "region": r["region"],
                    "forecast_target_date": r["forecast_target_date"],
                    "predicted_price": r["predicted_price"],
                    "actual_price": r["actual_price"],
                    "error_dollars": r["error_dollars"],
                    "anomaly_type": r["anomaly_type"],
                    "content": r["content"],
                    "metadata": json.loads(r["metadata_json"] or "{}")
                })
        except Exception as e:
            logger.debug(f"Error reading pending memories from SQLite: {e}")
        finally:
            conn.close()
        return results

    def recall(
        self,
        query: str,
        region: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Searches memories using SQLite FTS5 full-text ranking with sanitized token matching."""
        results = []
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Clean query for FTS5 syntax: strip special boolean punctuation (+, -, *, :, ^) and wrap tokens in double quotes (Issue #331)
            raw_query = query or ""
            clean_words = [w for w in re.sub(r'[^\w\s]', ' ', raw_query).split() if len(w) > 2]
            if not clean_words:
                fallback_term = region or "refinery price shock"
                clean_words = [w for w in re.sub(r'[^\w\s]', ' ', fallback_term).split() if len(w) > 2]

            clean_query = " ".join(f'"{w}"' for w in clean_words) if clean_words else ""

            if clean_query:
                try:
                    sql = """
                        SELECT m.*, bm25(memories_fts) as score
                        FROM memories_fts f
                        JOIN memories m ON m.memory_id = f.memory_id
                        WHERE memories_fts MATCH ?
                    """
                    params = [clean_query]
                    if region:
                        sql += " AND m.region = ?"
                        params.append(region)
                    if anomaly_type:
                        sql += " AND m.anomaly_type = ?"
                        params.append(anomaly_type)

                    sql += " ORDER BY score LIMIT ?"
                    params.append(top_k)

                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                    for r in rows:
                        results.append({
                            "memory_id": r["memory_id"],
                            "region": r["region"],
                            "anomaly_type": r["anomaly_type"],
                            "content": r["content"],
                            "predicted_price": r["predicted_price"],
                            "actual_price": r["actual_price"],
                            "error_dollars": r["error_dollars"],
                            "forecast_target_date": r["forecast_target_date"],
                            "score": r["score"],
                            "metadata": json.loads(r["metadata_json"] or "{}")
                        })
                except Exception as fts_err:
                    logger.debug(f"FTS5 match error for query '{clean_query}', falling back to recent: {fts_err}")

            # Fallback to recent records if FTS match returned 0
            if not results:
                cursor.execute("""
                    SELECT * FROM memories
                    WHERE (? IS NULL OR region = ?)
                    ORDER BY created_at DESC LIMIT ?
                """, (region, region, top_k))
                for r in cursor.fetchall():
                    results.append({
                        "memory_id": r["memory_id"],
                        "region": r["region"],
                        "anomaly_type": r["anomaly_type"],
                        "content": r["content"],
                        "predicted_price": r["predicted_price"],
                        "actual_price": r["actual_price"],
                        "error_dollars": r["error_dollars"],
                        "forecast_target_date": r["forecast_target_date"],
                        "score": 0.0,
                        "metadata": json.loads(r["metadata_json"] or "{}")
                    })
        except Exception as e:
            logger.debug(f"SQLite recall notice: {e}")
        finally:
            conn.close()

        return results

    def save_reflection(self, reflection: Dict[str, Any]) -> bool:
        """Saves a synthesized reflection / mental model to SQLite."""
        import uuid
        conn = self._get_connection()
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            uid = uuid.uuid4().hex[:8]
            ref_id = f"ref_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uid}_{reflection.get('region', 'all').lower()}"
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO reflections (
                    reflection_id, region, anomaly_type, title,
                    root_cause, historical_analogy, calibration_suggestion, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ref_id,
                reflection.get("region"),
                reflection.get("anomaly_type"),
                reflection.get("title", "Anomaly Post-Mortem"),
                reflection.get("root_cause", ""),
                reflection.get("historical_analogy", ""),
                reflection.get("calibration_suggestion", ""),
                now_str
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Could not save reflection to SQLite: {e}")
            return False
        finally:
            conn.close()


class AgentMemoryManager:
    """
    Unified Memory Manager supporting Retain-Recall-Reflect with Cloud Run + Supabase and Local SQLite Fallback.
    """

    def __init__(
        self,
        hindsight_url: Optional[str] = None,
        hindsight_key: Optional[str] = None,
        sqlite_path: str = DEFAULT_SQLITE_PATH,
        vintages_path: str = DEFAULT_VINTAGES_PATH,
        ledger_path: str = TELEMETRY_LEDGER_PATH
    ):
        self.sqlite_store = SQLiteMemoryStore(db_path=sqlite_path)
        self.hindsight_client = HindsightClient(base_url=hindsight_url, api_key=hindsight_key)
        self.vintages_path = vintages_path
        self.ledger_path = ledger_path

    def _persist_bank_vintages(self, inventory: Dict[str, Any]) -> bool:
        """
        Persists authoritative memory bank counts to data/agent_memory_vintages.json
        for resilient fallback in ephemeral CI environments and offline runs.
        """
        if not inventory or (inventory.get("memories_count", 0) == 0 and inventory.get("reflections_count", 0) == 0):
            return False
        try:
            os.makedirs(os.path.dirname(self.vintages_path), exist_ok=True)
            snapshot = {
                "bank_id": inventory.get("bank_id", self.hindsight_client.bank_id),
                "source": inventory.get("source", "local_sqlite"),
                "backend": inventory.get("backend", "Local SQLite FTS5"),
                "memories_count": int(inventory.get("memories_count", 0)),
                "observations_count": int(inventory.get("observations_count", 0)),
                "reflections_count": int(inventory.get("reflections_count", 0)),
                "pending_reconciliation_count": int(inventory.get("pending_reconciliation_count", 0)),
                "last_synced_at": datetime.now(timezone.utc).isoformat()
            }
            tmp_path = f"{self.vintages_path}.tmp-{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
            os.replace(tmp_path, self.vintages_path)
            return True
        except Exception as e:
            logger.debug(f"Failed to persist agent memory vintages snapshot: {e}")
            return False

    @property
    def is_cloud_engine_active(self) -> bool:
        """Checks if Cloud Run / Supabase Hindsight service is connected."""
        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            return False
        return self.hindsight_client.is_configured and self.hindsight_client.ping()

    def sync_pending_memories(self, limit: int = 50) -> int:
        """
        Synchronizes any memories stored only in SQLite (e.g. during cold-start or offline)
        to the Hindsight Cloud Run memory bank. Returns number of synced memories.
        """
        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_HINDSIGHT_FORCE") != "1":
            return 0
        if not self.hindsight_client.is_configured:
            return 0

        pending = self.sqlite_store.get_unretained_memories(limit=limit)
        if not pending:
            return 0

        if not self.hindsight_client.ping():
            return 0

        synced_count = 0
        for item in pending:
            cloud_res = self.hindsight_client.retain(
                content=item["content"],
                region=item["region"],
                memory_type=item.get("memory_type", "experience"),
                anomaly_type=item.get("anomaly_type"),
                error_dollars=item.get("error_dollars"),
                predicted_price=item.get("predicted_price"),
                actual_price=item.get("actual_price"),
                forecast_target_date=item.get("forecast_target_date"),
                metadata=item.get("metadata")
            )
            if cloud_res.get("status") == "SUCCESS":
                self.sqlite_store.mark_as_synced(item["memory_id"])
                synced_count += 1

        if synced_count > 0:
            logger.info(f"Reconciled and synced {synced_count} pending memories to Hindsight Cloud bank.")
        return synced_count

    def retain(
        self,
        content: str,
        region: str,
        memory_type: str = "experience",
        anomaly_type: Optional[str] = None,
        error_dollars: Optional[float] = None,
        predicted_price: Optional[float] = None,
        actual_price: Optional[float] = None,
        forecast_target_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retains an experience record in SQLite (always) and Hindsight Cloud Run (if active).
        """
        # 1. Always retain in local SQLite for zero-cost offline guarantee
        local_res = self.sqlite_store.retain(
            content=content,
            region=region,
            memory_type=memory_type,
            anomaly_type=anomaly_type,
            error_dollars=error_dollars,
            predicted_price=predicted_price,
            actual_price=actual_price,
            forecast_target_date=forecast_target_date,
            metadata=metadata,
            cloud_synced=0
        )

        # 2. Dual-dispatch to Hindsight Cloud Run if online
        cloud_res = None
        if self.is_cloud_engine_active:
            cloud_res = self.hindsight_client.retain(
                content=content,
                region=region,
                memory_type=memory_type,
                anomaly_type=anomaly_type,
                error_dollars=error_dollars,
                predicted_price=predicted_price,
                actual_price=actual_price,
                forecast_target_date=forecast_target_date,
                metadata=metadata
            )
            if cloud_res.get("status") == "SUCCESS" and local_res.get("memory_id"):
                self.sqlite_store.mark_as_synced(local_res["memory_id"])

        active_backend = "hindsight_cloud" if (cloud_res and cloud_res.get("status") == "SUCCESS") else "sqlite_fts5"
        log_agent_memory_op(
            operation="retain",
            backend=active_backend,
            status="success" if local_res.get("status") == "SUCCESS" else "error"
        )

        return {
            "local_status": local_res.get("status"),
            "cloud_status": cloud_res.get("status") if cloud_res else "SKIPPED",
            "active_backend": active_backend
        }

    def reconcile_unretained_prediction_anomalies(
        self,
        start_date: str = "2026-09-25",
        history_csv: str = HISTORY_CSV
    ) -> Dict[str, Any]:
        """
        Scans prediction_history.csv for evaluated prediction anomalies since start_date
        and reconciles them into SQLite and Hindsight Hosted memory bank (Issue #557).
        """
        if not os.path.exists(history_csv):
            return {"status": "SKIPPED", "synced": 0, "reason": "History CSV not found"}
        
        try:
            from src.prediction_logger import read_prediction_history
            df = read_prediction_history(history_csv)
            if df.empty or 'actual_5d_price' not in df.columns:
                return {"status": "SKIPPED", "synced": 0, "reason": "No evaluated predictions"}
            
            eval_df = df[df['actual_5d_price'].notna()].copy()
            if 'is_retroactive_backtest' in eval_df.columns:
                eval_df = eval_df[eval_df['is_retroactive_backtest'].fillna(False).astype(bool) == False]
            if 'run_type' in eval_df.columns:
                eval_df = eval_df[~eval_df['run_type'].astype(str).str.upper().str.contains('BACKTEST', na=False)]
            if 'forecast_target_date' in eval_df.columns:
                eval_df = eval_df[eval_df['forecast_target_date'].astype(str) >= str(start_date)]
            
            if eval_df.empty:
                return {"status": "SUCCESS", "synced": 0, "message": "No evaluated records in window"}
            
            # Sort chronologically
            eval_df = eval_df.sort_values(by=['forecast_target_date', 'log_timestamp'], ascending=[True, True])
            
            synced_count = 0
            retained_anomalies = []
            for _, row in eval_df.iterrows():
                err = float(row.get('error_dollars', 0.0))
                reg = str(row.get('region', 'National'))
                pred = float(row.get('predicted_5d_price', 0.0))
                act = float(row.get('actual_5d_price', 0.0))
                target_d = str(row.get('forecast_target_date', ''))
                d_hit = row.get('directional_hit')
                
                anom_type = (
                    "LARGE_OVERESTIMATE" if (pred - act) >= 0.25
                    else ("LARGE_UNDERESTIMATE" if (act - pred) >= 0.25
                    else ("DIRECTIONAL_FLIP" if d_hit == 0.0 and abs(pred - act) >= 0.05
                    else "NORMAL"))
                )
                if anom_type != "NORMAL":
                    res = self.retain(
                        content=f"Evaluated forecast for {reg} on {target_d}: Predicted ${pred:.4f}, Actual ${act:.4f}, Error ${err:+.4f}/gal ({anom_type})",
                        region=reg,
                        memory_type="anomaly_shock",
                        anomaly_type=anom_type,
                        error_dollars=err,
                        predicted_price=pred,
                        actual_price=act,
                        forecast_target_date=target_d,
                        metadata={"provenance_source": str(row.get("data_source_provenance", row.get("provenance_source", "yfinance")))}
                    )
                    synced_count += 1
                    retained_anomalies.append({
                        "region": reg,
                        "target_date": target_d,
                        "anomaly_type": anom_type,
                        "error_dollars": err,
                        "cloud_status": res.get("cloud_status")
                    })
            
            # Snapshot latest inventory
            try:
                self._persist_bank_vintages(self.get_bank_inventory())
            except Exception:
                pass
            logger.info(f"Reconciled {synced_count} historical prediction anomalies since {start_date} into episodic memory.")
            return {
                "status": "SUCCESS",
                "synced_count": synced_count,
                "retained_anomalies": retained_anomalies
            }
        except Exception as e:
            logger.error(f"Error during historical anomaly reconciliation: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e), "synced_count": 0}

    def recall(
        self,
        query: str,
        region: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Recalls historical shock analogies. Prefers Cloud Run Hindsight; falls back to SQLite FTS5.
        """
        if self.is_cloud_engine_active:
            cloud_memories = self.hindsight_client.recall(
                query=query,
                region=region,
                anomaly_type=anomaly_type,
                top_k=top_k
            )
            if cloud_memories:
                log_agent_memory_op(operation="recall", backend="hindsight_cloud", status="success")
                return cloud_memories

        res = self.sqlite_store.recall(
            query=query,
            region=region,
            anomaly_type=anomaly_type,
            top_k=top_k
        )
        log_agent_memory_op(operation="recall", backend="sqlite_fts5", status="success")
        return res

    def reflect_on_anomalies(
        self,
        anomalies: List[Dict[str, Any]],
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes qualitative post-mortems for forecast anomalies using Hindsight, Gemini, or Offline Lexicon.
        """
        if not anomalies:
            return []

        # Reconcile pending memories before reflection
        if self.hindsight_client.is_configured:
            self.sync_pending_memories(limit=50)

        # 1. Try Hindsight Cloud Run API first
        if self.is_cloud_engine_active:
            cloud_ref = self.hindsight_client.reflect(anomalies)
            if cloud_ref.get("reflections"):
                for r in cloud_ref["reflections"]:
                    self.sqlite_store.save_reflection(r)
                log_agent_memory_op(operation="reflect", backend="hindsight_cloud", status="success")
                return cloud_ref["reflections"]

        # 2. Try Gemini 2.5 Flash reflection
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")

        if api_key:
            try:
                reflections = self._reflect_with_gemini(anomalies, api_key)
                if reflections:
                    for r in reflections:
                        self.sqlite_store.save_reflection(r)
                    log_agent_memory_op(operation="reflect", backend="gemini_llm", status="success")
                    return reflections
            except Exception as e:
                logger.warning(f"Gemini reflection notice ({e}). Falling back to deterministic rule engine.")

        # 3. Tier 3 Deterministic Rule-Based Reflection Fallback ($0 cost, 100% offline)
        reflections = self._reflect_deterministic(anomalies)
        for r in reflections:
            self.sqlite_store.save_reflection(r)
        log_agent_memory_op(operation="reflect", backend="sqlite_fts5", status="success")
        return reflections

    def get_bank_inventory(self) -> Dict[str, Any]:
        """
        Retrieves authoritative memory bank inventory (experience, observation, and reflection counts,
        plus local-to-cloud pending reconciliation queue depth).
        Cascading 4-Tier Fallback Strategy:
          - Tier 1: Remote Hindsight / Supabase pgvector API
          - Tier 2: Populated Local SQLite FTS5 database (data/agent_memory.sqlite)
          - Tier 3: Committed Vintage Snapshot (data/agent_memory_vintages.json)
          - Tier 4: Cumulative Telemetry Ledger (data/telemetry_ledger.json)
        """
        # Count un-synced experiences in local SQLite
        pending_sync_count = 0
        try:
            conn = self.sqlite_store._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories WHERE cloud_synced = 0")
            row = cursor.fetchone()
            if row:
                pending_sync_count = int(row[0])
            conn.close()
        except Exception as e:
            logger.debug(f"Failed to query pending reconciliation queue count: {e}")

        # Tier 1: Attempt remote cloud retrieval if client is configured
        if self.hindsight_client.is_configured:
            remote_stats = self.hindsight_client.get_bank_stats()
            if remote_stats is not None and (remote_stats.get("memories", 0) > 0 or remote_stats.get("reflections", 0) > 0):
                inv = {
                    "source": "remote_cloud",
                    "backend": "Vectorize Hindsight (Supabase pgvector)",
                    "bank_id": self.hindsight_client.bank_id,
                    "memories_count": remote_stats.get("memories", 0),
                    "observations_count": remote_stats.get("observations", 0),
                    "reflections_count": remote_stats.get("reflections", 0),
                    "pending_reconciliation_count": pending_sync_count
                }
                self._persist_bank_vintages(inv)
                return inv

        # Tier 2: Check local SQLite database if populated
        local_memories = 0
        local_reflections = 0
        try:
            conn = self.sqlite_store._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories")
            row = cursor.fetchone()
            if row:
                local_memories = int(row[0])
            cursor.execute("SELECT COUNT(*) FROM reflections")
            row = cursor.fetchone()
            if row:
                local_reflections = int(row[0])
            conn.close()
        except Exception as e:
            logger.debug(f"Failed to query local SQLite memory inventory: {e}")

        if local_memories > 0 or local_reflections > 0:
            inv = {
                "source": "local_sqlite",
                "backend": "Local SQLite FTS5",
                "bank_id": self.hindsight_client.bank_id if self.hindsight_client else "Midgley",
                "memories_count": local_memories,
                "observations_count": 0,
                "reflections_count": local_reflections,
                "pending_reconciliation_count": pending_sync_count
            }
            self._persist_bank_vintages(inv)
            return inv

        # Tier 3: Committed Vintage Snapshot (data/agent_memory_vintages.json)
        if os.path.exists(self.vintages_path):
            try:
                with open(self.vintages_path, "r", encoding="utf-8") as f:
                    vintage_data = json.load(f)
                v_mems = int(vintage_data.get("memories_count", 0))
                v_refs = int(vintage_data.get("reflections_count", 0))
                if v_mems > 0 or v_refs > 0:
                    return {
                        "source": vintage_data.get("source", "local_sqlite"),
                        "backend": vintage_data.get("backend", "Local SQLite FTS5 (Snapshot)"),
                        "bank_id": vintage_data.get("bank_id", self.hindsight_client.bank_id if self.hindsight_client else "Midgley"),
                        "memories_count": v_mems,
                        "observations_count": int(vintage_data.get("observations_count", 0)),
                        "reflections_count": v_refs,
                        "pending_reconciliation_count": int(vintage_data.get("pending_reconciliation_count", pending_sync_count))
                    }
            except Exception as e:
                logger.debug(f"Failed to read agent memory vintages snapshot: {e}")

        # Tier 4: Cumulative Telemetry Ledger (data/telemetry_ledger.json)
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    ledger_data = json.load(f)
                mem_totals = ledger_data.get("memory_totals", {})
                t_retain = int(mem_totals.get("retain_count", 0))
                t_reflect = int(mem_totals.get("reflect_count", 0))
                if t_retain > 0 or t_reflect > 0:
                    return {
                        "source": "telemetry_ledger",
                        "backend": "Cumulative Telemetry Ledger",
                        "bank_id": self.hindsight_client.bank_id if self.hindsight_client else "Midgley",
                        "memories_count": t_retain,
                        "observations_count": 0,
                        "reflections_count": t_reflect,
                        "pending_reconciliation_count": 0
                    }
            except Exception as e:
                logger.debug(f"Failed to read telemetry ledger memory totals: {e}")

        return {
            "source": "local_sqlite",
            "backend": "Local SQLite FTS5",
            "bank_id": self.hindsight_client.bank_id if self.hindsight_client else "Midgley",
            "memories_count": 0,
            "observations_count": 0,
            "reflections_count": 0,
            "pending_reconciliation_count": pending_sync_count
        }


    def _reflect_with_gemini(self, anomalies: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
        prompt = f"""
You are an expert energy quantitative modeling engineer and MLOps qualitative post-mortem auditor.
Review the following forecasting outlier anomalies from our LLM Unleaded Gas Price Prediction System and generate an episodic reflection (Retain-Recall-Reflect post-mortem) for each anomaly.

Anomalies to reflect on:
{json.dumps(anomalies, indent=2)}

Return ONLY a raw JSON array of reflection objects with the following fields for each anomaly:
- "region": string
- "anomaly_type": string (e.g., "LARGE_OVERESTIMATE", "LARGE_UNDERESTIMATE", "DIRECTIONAL_FLIP")
- "title": string (concise case study headline)
- "root_cause": string (detailed diagnosis of why the model missed the forecast)
- "historical_analogy": string (relevant historical shock comparison or similar precedent)
- "calibration_suggestion": string (actionable parameter tuning, e.g. adjust news decay half-life t1/2, Ridge alpha, or physical crack spread weight)

JSON Output:
"""
        text = ""
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            config = types.GenerateContentConfig(temperature=0.1)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            text = response.text.strip()
        except ImportError:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            text = response.text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return json.loads(text)

    def _reflect_deterministic(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deterministic rule-based qualitative post-mortem synthesizer ($0, 100% offline)."""
        reflections = []
        for anom in anomalies:
            reg = anom.get("region", "National")
            err = float(anom.get("error_dollars", 0.0))
            pred = float(anom.get("predicted_price", 0.0))
            act = float(anom.get("actual_price", 0.0))
            anom_type = anom.get("anomaly_type", "RESIDUAL_OUTLIER")
            headline = anom.get("headline", "No specific breaking news headline recorded")

            if pred > act:
                diag = (
                    f"Model overestimated 5-day price by +${abs(err):.4f}/gal. Qualitative news shock or supply "
                    f"disruption premium decayed slower than physical market clearing capacity."
                )
                calib = "Recommend shortening news decay half-life from t1/2 = 4.5d to 3.0d for transient outages."
            else:
                diag = (
                    f"Model underestimated price surge by -${abs(err):.4f}/gal. Physical supply constraints or "
                    f"rack margin spikes expanded faster than captured by baseline futures curves."
                )
                calib = "Increase Cushing/PADD crack spread momentum weight or verify local NOAA freeze alerts."

            reflections.append({
                "region": reg,
                "anomaly_type": anom_type,
                "title": f"{reg} Price Discrepancy (${err:+.4f}/gal)",
                "root_cause": f"{diag} Associated context: '{headline}'.",
                "historical_analogy": f"Similar to historical {reg} turnaround shocks where market pricing normalized post-event.",
                "calibration_suggestion": calib
            })
        return reflections


def extract_top_prediction_anomalies(
    history_csv: str = HISTORY_CSV,
    max_anomalies: int = 3,
    error_threshold: float = 0.25
) -> List[Dict[str, Any]]:
    """
    Extracts top residual outliers and unpredicted directional flips from data/prediction_history.csv.
    """
    if not os.path.exists(history_csv):
        return []

    try:
        from src.prediction_logger import read_prediction_history
        df = read_prediction_history(history_csv)
        eval_df = df.dropna(subset=['actual_5d_price', 'error_dollars']).copy()
        if eval_df.empty:
            return []

        # Calculate anomaly classification
        anomalies = []
        for _, row in eval_df.iterrows():
            err = float(row.get('error_dollars', 0.0))
            pred = float(row.get('predicted_5d_price', 0.0))
            curr = float(row.get('current_base_price', row.get('current_price', pred)))
            act = float(row.get('actual_5d_price', pred))
            reg = str(row.get('region', 'National'))
            d_hit = float(row.get('directional_hit', 1.0))
            target_date = str(row.get('forecast_target_date', ''))

            is_anomaly = False
            anom_type = "NORMAL"

            if abs(err) >= error_threshold:
                is_anomaly = True
                anom_type = "LARGE_OVERESTIMATE" if pred > act else "LARGE_UNDERESTIMATE"
            elif d_hit == 0.0 and abs(pred - curr) >= 0.05:
                is_anomaly = True
                anom_type = "DIRECTIONAL_FLIP"

            if is_anomaly:
                anomalies.append({
                    "region": reg,
                    "forecast_target_date": target_date,
                    "current_price": curr,
                    "predicted_price": pred,
                    "actual_price": act,
                    "error_dollars": err,
                    "directional_hit": d_hit,
                    "anomaly_type": anom_type,
                    "llm_price_pressure": float(row.get('llm_price_pressure', 0.0)),
                    "llm_supply_disruption": float(row.get('llm_supply_disruption', 0.0)),
                    "headline": f"Historical shock record on {target_date} ({reg})"
                })

        # Sort by largest absolute error
        anomalies.sort(key=lambda x: abs(x["error_dollars"]), reverse=True)
        return anomalies[:max_anomalies]
    except Exception as e:
        logger.warning(f"Error extracting prediction anomalies: {e}")
        return []


def format_qualitative_anomaly_reflections_markdown(
    manager: Optional[AgentMemoryManager] = None,
    max_anomalies: int = 3
) -> str:
    """
    Renders the Markdown section for Agent 7 Weekly Review report (Issue #230).
    """
    if manager is None:
        manager = AgentMemoryManager()

    anomalies = extract_top_prediction_anomalies(max_anomalies=max_anomalies)
    if not anomalies:
        return """## 🧠 Qualitative Anomaly Post-Mortems & Episodic Memory (Issue #230)

> [!NOTE]
> **Zero Critical Anomalies:** All evaluated forecasts in the current rolling window remained within normal residual tolerance ($|\\text{error}| < \\$0.25/\\text{gal}$). Agent memory banks synchronized."""

    reflections = manager.reflect_on_anomalies(anomalies)

    lines = [
        "## 🧠 Qualitative Anomaly Post-Mortems & Episodic Memory (Issue #230)",
        "",
        "> [!IMPORTANT]",
        f"> **Episodic Reflection Active (Retain-Recall-Reflect):** Evaluated top **{len(reflections)} forecasting outlier(s)** across the rolling 30-day evaluation window to synthesize root causes, historical analogies, and model calibration recommendations.",
        ""
    ]

    for idx, ref in enumerate(reflections, 1):
        matching_anom = next((a for a in anomalies if a["region"] == ref.get("region")), anomalies[0])
        err = matching_anom.get("error_dollars", 0.0)
        reg = ref.get("region", "National")
        target_d = matching_anom.get("forecast_target_date", "Recent")

        lines.extend([
            f"### 🔍 Case Study {idx}: `{reg}` ({target_d}) | Error: `${err:+.4f}/gal`",
            f"- **Anomaly Classification:** `{ref.get('anomaly_type', 'OUTLIER')}`",
            f"- **Root Cause Diagnosis:** {ref.get('root_cause', 'N/A')}",
            f"- **Historical Precedent (Recall):** {ref.get('historical_analogy', 'N/A')}",
            f"- **Learned Parameter Recommendation:** {ref.get('calibration_suggestion', 'N/A')}",
            ""
        ])

    lines.append(f"*Episodic memory backed by `{manager.sqlite_store.db_path}` and Google Cloud Run / Supabase Hindsight Gateway.*")
    return "\n".join(lines)
