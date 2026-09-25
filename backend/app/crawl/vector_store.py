"""
Dristik AI Vector Store
Lightweight SQLite-backed vector storage and cosine similarity search.
Stores normalized chunk embeddings directly in SQLite with zero external dependencies.
"""
import os
import json
import math
import struct
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings

logger = logging.getLogger("dristik.vector_store")


def _pack_vector(vec: List[float]) -> bytes:
    """Packs a list of floats into binary format (float32)."""
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack_vector(blob: bytes) -> List[float]:
    """Unpacks binary blob into list of floats."""
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


class VectorStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.AUTH_DATABASE_PATH or "data/dristik.db"
        self._ensure_db()

    def _get_connection(self) -> sqlite3.Connection:
        dir_name = os.path.dirname(self.db_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _ensure_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS page_vector_chunks (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    url TEXT NOT NULL,
                    page_type TEXT DEFAULT 'general',
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    vector BLOB NOT NULL,
                    dimension INTEGER NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            columns = [row[1] for row in conn.execute("PRAGMA table_info(page_vector_chunks)").fetchall()]
            if "analysis_id" not in columns:
                conn.execute("ALTER TABLE page_vector_chunks ADD COLUMN analysis_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pvc_domain ON page_vector_chunks(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pvc_url ON page_vector_chunks(url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pvc_analysis ON page_vector_chunks(analysis_id)")
            conn.commit()

    def save_chunks(
        self,
        domain: str,
        url: str,
        page_type: str,
        chunks: List[str],
        vectors: List[List[float]],
        analysis_id: Optional[str] = None,
    ) -> int:
        """
        Saves text chunks and their corresponding embedding vectors into the database.
        """
        if not chunks or not vectors or len(chunks) != len(vectors):
            return 0

        clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
        import time
        now = time.time()

        rows = []
        for idx, (text, vec) in enumerate(zip(chunks, vectors)):
            if not text.strip() or not vec:
                continue
            scope = analysis_id or clean_domain
            chunk_id = f"{scope}_{hash(url)}_{idx}"
            blob = _pack_vector(vec)
            rows.append((
                chunk_id,
                clean_domain,
                url,
                page_type,
                idx,
                text,
                blob,
                len(vec),
                now,
                analysis_id,
            ))

        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO page_vector_chunks 
                (id, domain, url, page_type, chunk_index, chunk_text, vector, dimension, created_at, analysis_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()

        logger.info("[VectorStore] Indexed %d chunks for %s (%s)", len(rows), url, clean_domain)
        return len(rows)

    def search_similar(
        self,
        query_vector: List[float],
        domain: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.0,
        analysis_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs in-memory cosine similarity ranking against stored vectors.
        """
        if not query_vector:
            return []

        query = "SELECT id, domain, url, page_type, chunk_index, chunk_text, vector FROM page_vector_chunks"
        params: List[Any] = []
        filters: List[str] = []
        if domain:
            clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
            filters.append("domain = ?")
            params.append(clean_domain)
        if analysis_id:
            filters.append("analysis_id = ?")
            params.append(analysis_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        if not rows:
            return []

        scored_results: List[Tuple[float, Dict[str, Any]]] = []
        for row in rows:
            chunk_id, r_domain, url, page_type, chunk_idx, chunk_text, vector_blob = row
            chunk_vec = _unpack_vector(vector_blob)
            sim = _cosine_similarity(query_vector, chunk_vec)
            if sim >= min_score:
                scored_results.append((sim, {
                    "id": chunk_id,
                    "domain": r_domain,
                    "url": url,
                    "page_type": page_type,
                    "chunk_index": chunk_idx,
                    "text": chunk_text,
                    "similarity": round(sim, 4)
                }))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_results[:top_k]]

    def clear_domain(self, domain: str) -> int:
        """Removes all vector chunks for a specific domain."""
        clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM page_vector_chunks WHERE domain = ?", (clean_domain,))
            conn.commit()
            return cur.rowcount

    def count_chunks(self, domain: Optional[str] = None) -> int:
        """Returns total count of indexed vector chunks."""
        query = "SELECT COUNT(*) FROM page_vector_chunks"
        params: List[Any] = []
        if domain:
            clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
            query += " WHERE domain = ?"
            params.append(clean_domain)
        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            return cur.fetchone()[0]


vector_store = VectorStore()
