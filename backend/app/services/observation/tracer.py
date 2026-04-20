"""
Trace logger for Janus self-improvement.

Logs every /run call to the SQLite traces table.
Non-blocking — zero overhead on happy path.
"""

import uuid
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR as BASE_DATA_DIR
except ImportError:
    BASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

DATA_DIR = Path(BASE_DATA_DIR) / "memory_graph"
DB_PATH = DATA_DIR / "memory_graph.db"

CREATE_TRACES_SQL = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    query_type TEXT,
    domain TEXT,
    routing_path TEXT,
    provider_used TEXT,
    output TEXT,
    output_length INTEGER,
    latency_ms INTEGER,
    confidence REAL,
    tool_results TEXT,
    errors TEXT,
    score REAL,
    score_breakdown TEXT,
    created_at TEXT
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_traces_score ON traces(score);",
    "CREATE INDEX IF NOT EXISTS idx_traces_domain ON traces(domain);",
    "CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);",
]


class TraceLogger:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Creating traces table at {DB_PATH}")
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute(CREATE_TRACES_SQL)
            for idx_sql in CREATE_INDEXES_SQL:
                conn.execute(idx_sql)
            conn.commit()
            conn.close()
            logger.info("Traces table initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize traces table: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def log_trace(self, trace_data: Dict[str, Any]) -> str:
        """Log a completed trace to SQLite. Returns trace_id."""
        trace_id = trace_data.get("trace_id", str(uuid.uuid4()))
        now = datetime.utcnow().isoformat()

        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute(
                """INSERT OR REPLACE INTO traces 
                   (trace_id, query, query_type, domain, routing_path, 
                    provider_used, output, output_length, latency_ms, 
                    confidence, tool_results, errors, score, score_breakdown, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trace_id,
                    trace_data.get("query", ""),
                    trace_data.get("query_type"),
                    trace_data.get("domain"),
                    trace_data.get("routing_path"),
                    trace_data.get("provider_used"),
                    trace_data.get("output", ""),
                    trace_data.get("output_length", 0),
                    trace_data.get("latency_ms", 0),
                    trace_data.get("confidence", 0.5),
                    json.dumps(trace_data.get("tool_results", [])),
                    json.dumps(trace_data.get("errors", [])),
                    trace_data.get("score", 0.0),
                    json.dumps(trace_data.get("score_breakdown", {})),
                    now,
                ),
            )
            conn.commit()
            conn.close()
            return trace_id
        except Exception as e:
            logger.error(f"Failed to log trace: {e}")
            return trace_id

    def get_traces(
        self,
        limit: int = 50,
        score_min: float = 0.0,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM traces WHERE score >= ?"
            params = [score_min]
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            traces = []
            for row in rows:
                trace = dict(row)
                trace["tool_results"] = json.loads(trace.get("tool_results", "[]"))
                trace["errors"] = json.loads(trace.get("errors", "[]"))
                trace["score_breakdown"] = json.loads(
                    trace.get("score_breakdown", "{}")
                )
                traces.append(trace)
            conn.close()
            return traces
        except Exception as e:
            logger.error(f"Failed to query traces: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            total = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
            avg_score = conn.execute("SELECT AVG(score) FROM traces").fetchone()[0] or 0
            curated = conn.execute(
                "SELECT COUNT(*) FROM traces WHERE score >= 0.7"
            ).fetchone()[0]
            by_domain = {}
            for row in conn.execute(
                "SELECT domain, COUNT(*), AVG(score) FROM traces GROUP BY domain"
            ):
                by_domain[row[0]] = {"count": row[1], "avg_score": round(row[2], 3)}
            conn.close()
            return {
                "total_traces": total,
                "avg_score": round(avg_score, 3),
                "curated_count": curated,
                "by_domain": by_domain,
            }
        except Exception as e:
            logger.error(f"Failed to get trace stats: {e}")
            return {}
