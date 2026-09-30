"""
Database Client Module (src/db/client.py)

Unified client interface for Project Midgley data storage:
- Primary: Turso libSQL Cloud Database (TURSO_DATABASE_URL + TURSO_AUTH_TOKEN)
- Edge: Cloudflare D1 / Worker Gateway
- Local Fallback: Embedded SQLite in WAL mode (MIDGLEY_DB_PATH or data/midgley.db)
"""

import os
import json
import sqlite3
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
DEFAULT_SQLITE_PATH = os.path.join("data", "midgley.db")


class DatabaseClient:
    """
    Thread-safe unified database client for Turso libSQL and SQLite.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        sqlite_path: Optional[str] = None
    ):
        is_testing = os.environ.get("TESTING") == "1"
        if sqlite_path is not None or is_testing:
            self.db_url = ""
            self.auth_token = ""
            self.is_turso = False
        else:
            self.db_url = (db_url or os.environ.get("TURSO_DATABASE_URL", "")).strip()
            self.auth_token = (auth_token or os.environ.get("TURSO_AUTH_TOKEN", "")).strip()
            self.is_turso = bool(self.db_url and self.auth_token)

        self.sqlite_path = sqlite_path or os.environ.get("MIDGLEY_DB_PATH", DEFAULT_SQLITE_PATH)
        
        if self.is_turso:
            # Normalize HTTP endpoint for Turso REST API v2
            if self.db_url.startswith("libsql://"):
                self.http_url = self.db_url.replace("libsql://", "https://")
            elif self.db_url.startswith("turso://"):
                self.http_url = self.db_url.replace("turso://", "https://")
            else:
                self.http_url = self.db_url.rstrip("/")
            if not self.http_url.endswith("/v2/pipeline"):
                self.pipeline_url = f"{self.http_url}/v2/pipeline"
            else:
                self.pipeline_url = self.http_url
        else:
            self.http_url = None
            self.pipeline_url = None
            os.makedirs(os.path.dirname(os.path.abspath(self.sqlite_path)), exist_ok=True)
            self._init_sqlite_pragmas()

        self.init_schema()

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        """Creates SQLite connection with foreign keys and busy timeout enabled (Issue #577 N-6)."""
        conn = sqlite3.connect(self.sqlite_path, timeout=5.0)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_sqlite_pragmas(self):
        """Applies high-concurrency WAL pragmas to local SQLite datastore."""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA busy_timeout = 5000;")
        except Exception as e:
            logger.debug(f"Notice initializing SQLite pragmas: {e}")

    def init_schema(self):
        """Idempotently initializes tables and indexes from schema.sql."""
        if not os.path.exists(SCHEMA_PATH):
            logger.warning(f"Schema file not found at {SCHEMA_PATH}")
            return

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
        for stmt in statements:
            try:
                self.execute(stmt)
            except Exception as e:
                logger.debug(f"Notice executing schema statement: {e}")

    def execute(self, sql: str, params: Union[Tuple, List, Dict] = ()) -> List[Dict[str, Any]]:
        """
        Executes a parameterized SQL query and returns rows as a list of dicts.
        """
        if self.is_turso:
            return self._execute_turso(sql, params)
        return self._execute_sqlite(sql, params)

    def execute_batch(self, statements: List[Tuple[str, Union[Tuple, List]]]) -> None:
        """
        Executes multiple parameterized SQL statements within a single transaction.
        """
        if not statements:
            return

        if self.is_turso:
            self._execute_batch_turso(statements)
        else:
            self._execute_batch_sqlite(statements)

    def _execute_sqlite(self, sql: str, params: Union[Tuple, List, Dict]) -> List[Dict[str, Any]]:
        """Executes query on local SQLite."""
        with self._get_sqlite_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if cursor.description:
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            conn.commit()
            return []

    def _execute_batch_sqlite(self, statements: List[Tuple[str, Union[Tuple, List]]]) -> None:
        """Executes batch statements within a single SQLite transaction."""
        with self._get_sqlite_conn() as conn:
            cursor = conn.cursor()
            for sql, params in statements:
                cursor.execute(sql, params)
            conn.commit()

    def _execute_turso(self, sql: str, params: Union[Tuple, List, Dict]) -> List[Dict[str, Any]]:
        """Executes query on remote Turso libSQL cloud database via HTTP REST API."""
        turso_args = self._format_turso_params(params)
        payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": turso_args
                    }
                },
                {"type": "close"}
            ]
        }

        try:
            req = urllib.request.Request(
                self.pipeline_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = data.get("results", [])
            if not results:
                return []

            first_res = results[0]
            if first_res.get("type") == "error":
                raise RuntimeError(f"Turso query error: {first_res.get('error', {}).get('message')}")

            response_stmt = first_res.get("response", {}).get("result", {})
            cols = [col.get("name") for col in response_stmt.get("cols", [])]
            rows_data = response_stmt.get("rows", [])
            
            out_rows = []
            for r in rows_data:
                row_dict = {}
                for idx, col_name in enumerate(cols):
                    val_obj = r[idx]
                    val = val_obj.get("value") if isinstance(val_obj, dict) else val_obj
                    row_dict[col_name] = val
                out_rows.append(row_dict)
            return out_rows
        except Exception as e:
            logger.error(f"Turso execution failed: {e}. Falling back to local SQLite.")
            return self._execute_sqlite(sql, params)

    def _execute_batch_turso(self, statements: List[Tuple[str, Union[Tuple, List]]]) -> None:
        """Executes batched requests to Turso via HTTP REST pipeline in chunks of 50 statements."""
        chunk_size = 50
        for i in range(0, len(statements), chunk_size):
            chunk = statements[i:i + chunk_size]
            requests = []
            for sql, params in chunk:
                requests.append({
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": self._format_turso_params(params)
                    }
                })
            requests.append({"type": "close"})

            payload = {"requests": requests}
            try:
                req = urllib.request.Request(
                    self.pipeline_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                for res in data.get("results", []):
                    if res.get("type") == "error":
                        raise RuntimeError(f"Turso batch error: {res.get('error', {}).get('message')}")
            except Exception as e:
                logger.error(f"Turso batch execution failed: {e}. Falling back to SQLite.")
                self._execute_batch_sqlite(chunk)

    def _format_turso_params(self, params: Union[Tuple, List, Dict]) -> List[Dict[str, Any]]:
        """Converts Python parameters to Turso parameter objects."""
        formatted = []
        if isinstance(params, (list, tuple)):
            for p in params:
                if p is None:
                    formatted.append({"type": "null"})
                elif isinstance(p, int):
                    formatted.append({"type": "integer", "value": str(p)})
                elif isinstance(p, float):
                    formatted.append({"type": "float", "value": p})
                elif isinstance(p, (bytes, bytearray)):
                    formatted.append({"type": "blob", "base64": p.hex()})
                else:
                    formatted.append({"type": "text", "value": str(p)})
        return formatted

    def close(self) -> None:
        """Closes any persistent resources or connections."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Module Singleton Instance
_global_db_client: Optional[DatabaseClient] = None


def get_db(reset: bool = False, sqlite_path: Optional[str] = None) -> DatabaseClient:
    """Returns or initializes the global database client singleton."""
    global _global_db_client
    if reset or _global_db_client is None:
        _global_db_client = DatabaseClient(sqlite_path=sqlite_path)
    return _global_db_client
