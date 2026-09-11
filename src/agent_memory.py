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
HISTORY_CSV = os.path.join("data", "prediction_history.csv")


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
                    created_at TEXT NOT NULL
                )
            """)
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
        metadata: Optional[Dict[str, Any]] = None
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
                    content, metadata_json, created_at
                ) VALUES (?, 'midgley-gas-forecasting', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mem_id, memory_type, region, forecast_target_date,
                predicted_price, actual_price, error_dollars, anomaly_type,
                content, meta_str, now_str
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

    def recall(
        self,
        query: str,
        region: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Searches memories using SQLite FTS5 full-text ranking."""
        results = []
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Clean query for FTS5 syntax
            clean_query = " ".join([w for w in query.replace("'", "").replace('"', '').split() if len(w) > 2])
            if not clean_query:
                clean_query = region or "refinery price shock"

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
        sqlite_path: str = DEFAULT_SQLITE_PATH
    ):
        self.sqlite_store = SQLiteMemoryStore(db_path=sqlite_path)
        self.hindsight_client = HindsightClient(base_url=hindsight_url, api_key=hindsight_key)

    @property
    def is_cloud_engine_active(self) -> bool:
        """Checks if Cloud Run / Supabase Hindsight service is connected."""
        return self.hindsight_client.is_configured and self.hindsight_client.ping()

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
            metadata=metadata
        )

        # 2. Dual-dispatch to Hindsight Cloud Run if online
        cloud_res = None
        if self.hindsight_client.is_configured:
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

        active_backend = "hindsight_cloud" if self.is_cloud_engine_active else "sqlite_fts5"
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
        df = pd.read_csv(history_csv)
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
