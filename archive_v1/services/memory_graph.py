"""
SQLite Memory Graph — Persistent memory for Janus.
Stores queries, entities, insights, and connections in SQLite.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR as BASE_DATA_DIR
except ImportError:
    BASE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR = Path(BASE_DATA_DIR) / "memory_graph"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "memory_graph.db"


class MemoryGraph:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS queries (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                type TEXT DEFAULT 'unknown',
                domain TEXT DEFAULT 'general',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0.5,
                response_summary TEXT
            );
            
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'unknown',
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                mention_count INTEGER DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source_query TEXT,
                confidence REAL DEFAULT 0.5,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS query_entity (
                query_id TEXT,
                entity_id TEXT,
                relevance REAL DEFAULT 0.5,
                PRIMARY KEY (query_id, entity_id)
            );
            
            CREATE TABLE IF NOT EXISTS query_query (
                source_id TEXT,
                target_id TEXT,
                relationship TEXT DEFAULT 'related',
                strength REAL DEFAULT 0.5,
                PRIMARY KEY (source_id, target_id)
            );
            
            CREATE TABLE IF NOT EXISTS entity_entity (
                source_id TEXT,
                target_id TEXT,
                relationship TEXT DEFAULT 'related',
                strength REAL DEFAULT 0.5,
                PRIMARY KEY (source_id, target_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON queries(timestamp);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_insights_timestamp ON insights(timestamp);
        """)

        conn.commit()
        conn.close()

    def add_query(
        self,
        query_id: str,
        text: str,
        type: str = "unknown",
        domain: str = "general",
        confidence: float = 0.5,
        response_summary: str = None,
    ):
        """Record a query."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO queries (id, text, type, domain, confidence, response_summary)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (query_id, text, type, domain, confidence, response_summary),
        )
        conn.commit()
        conn.close()

    def add_entity(self, entity_id: str, name: str, type: str = "unknown"):
        """Add or update an entity."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO entities (id, name, type) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET mention_count = mention_count + 1
        """,
            (entity_id, name, type),
        )
        conn.commit()
        conn.close()

    def add_insight(
        self,
        insight_id: str,
        content: str,
        source_query: str = None,
        confidence: float = 0.5,
    ):
        """Add an insight."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO insights (id, content, source_query, confidence)
            VALUES (?, ?, ?, ?)
        """,
            (insight_id, content, source_query, confidence),
        )
        conn.commit()
        conn.close()

    def link_query_entity(self, query_id: str, entity_id: str, relevance: float = 0.5):
        """Link a query to an entity."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO query_entity (query_id, entity_id, relevance)
            VALUES (?, ?, ?)
        """,
            (query_id, entity_id, relevance),
        )
        conn.commit()
        conn.close()

    def link_query_query(
        self,
        source_id: str,
        target_id: str,
        relationship: str = "related",
        strength: float = 0.5,
    ):
        """Link two queries."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO query_query (source_id, target_id, relationship, strength)
            VALUES (?, ?, ?, ?)
        """,
            (source_id, target_id, relationship, strength),
        )
        conn.commit()
        conn.close()

    def link_entity_entity(
        self,
        source_id: str,
        target_id: str,
        relationship: str = "related",
        strength: float = 0.5,
    ):
        """Link two entities."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO entity_entity (source_id, target_id, relationship, strength)
            VALUES (?, ?, ?, ?)
        """,
            (source_id, target_id, relationship, strength),
        )
        conn.commit()
        conn.close()

    def get_related_queries(self, query_id: str, limit: int = 5) -> List[Dict]:
        """Get queries related to a given query."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT q.* FROM queries q
            JOIN query_query qq ON q.id = qq.target_id
            WHERE qq.source_id = ?
            ORDER BY qq.strength DESC
            LIMIT ?
        """,
            (query_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_queries_by_domain(self, domain: str, limit: int = 10) -> List[Dict]:
        """Get queries by domain."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT * FROM queries WHERE domain = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (domain, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_entity_connections(self, entity_id: str) -> List[Dict]:
        """Get all connections for an entity."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT e.name, e.type, ee.relationship, ee.strength
            FROM entities e
            JOIN entity_entity ee ON e.id = ee.target_id
            WHERE ee.source_id = ?
            UNION
            SELECT e.name, e.type, ee.relationship, ee.strength
            FROM entities e
            JOIN entity_entity ee ON e.id = ee.source_id
            WHERE ee.target_id = ?
        """,
            (entity_id, entity_id),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        """Get memory graph statistics."""
        conn = self._get_conn()
        query_count = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        insight_count = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
        conn.close()

        return {
            "queries": query_count,
            "entities": entity_count,
            "insights": insight_count,
        }

    def search_queries(self, text: str, limit: int = 10) -> List[Dict]:
        """Search queries by text."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT * FROM queries WHERE text LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (f"%{text}%", limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
