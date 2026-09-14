"""Embedding generation, semantic search, and topic assignment.

Embeddings are stored as JSON arrays on the chunk rows, which keeps the whole
system inside one SQLite file. At the scale of a course (hundreds to a few
thousand chunks) an in-memory cosine scan is well under a millisecond, so no
vector index is needed yet.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from econ_rag.config import settings
from econ_rag.database import Chunk, get_session
from econ_rag.taxonomy import TOPICS


@lru_cache(maxsize=2)
def _load_model(name: str) -> SentenceTransformer:
    """Load (and cache) the sentence-transformer model."""
    return SentenceTransformer(name)


def _as_array(value) -> np.ndarray:
    if isinstance(value, str):
        value = json.loads(value)
    return np.asarray(value, dtype=np.float32)


class EmbeddingService:
    """Generates embeddings and answers similarity queries over chunks."""

    def __init__(self, model_name: str = None, session=None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.session = session or get_session()
        self._owns_session = session is None
        self._matrix: Optional[np.ndarray] = None
        self._matrix_ids: List[int] = []

    @property
    def model(self) -> SentenceTransformer:
        return _load_model(self.model_name)

    def encode(self, texts, normalize: bool = True) -> np.ndarray:
        """Encode text(s) to unit-length vectors."""
        return self.model.encode(
            texts, normalize_embeddings=normalize, show_progress_bar=False
        )

    # ---------- generation ----------

    def generate_embeddings(self, document_id: int = None, batch_size: int = 32) -> int:
        """Embed every chunk that does not yet have an embedding."""
        query = self.session.query(Chunk).filter(Chunk.embedding.is_(None))
        if document_id:
            query = query.filter(Chunk.document_id == document_id)
        chunks = query.all()
        if not chunks:
            return 0

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            vectors = self.encode([c.content for c in batch])
            for chunk, vector in zip(batch, vectors):
                chunk.embedding = [float(x) for x in vector]
        self.session.commit()
        self._matrix = None
        return len(chunks)

    # ---------- topic assignment ----------

    def assign_missing_topics(self, min_similarity: float = 0.15) -> int:
        """Label chunks the section-title heuristic could not place.

        Section titles cover most of the lecture notes, but front matter and
        example sections carry no hint. Those are assigned to the nearest topic
        by embedding similarity against the topic name plus its keywords.
        """
        chunks = (
            self.session.query(Chunk)
            .filter(Chunk.topic.is_(None), Chunk.embedding.isnot(None))
            .all()
        )
        if not chunks:
            return 0

        topic_vectors = self._topic_matrix()
        slugs = [t.slug for t in TOPICS]
        assigned = 0
        for chunk in chunks:
            scores = topic_vectors @ _as_array(chunk.embedding)
            best = int(np.argmax(scores))
            if float(scores[best]) >= min_similarity:
                chunk.topic = slugs[best]
                assigned += 1
        self.session.commit()
        return assigned

    def _topic_matrix(self) -> np.ndarray:
        descriptions = [
            f"{t.name}. {t.description} " + ", ".join(t.keywords) for t in TOPICS
        ]
        return np.asarray(self.encode(descriptions), dtype=np.float32)

    # ---------- search ----------

    def _ensure_matrix(self) -> None:
        """Load all chunk embeddings into one matrix for fast scanning."""
        if self._matrix is not None:
            return
        rows = (
            self.session.query(Chunk.id, Chunk.embedding)
            .filter(Chunk.embedding.isnot(None))
            .all()
        )
        self._matrix_ids = [r[0] for r in rows]
        if rows:
            self._matrix = np.vstack([_as_array(r[1]) for r in rows])
        else:
            self._matrix = np.zeros((0, 384), dtype=np.float32)

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: int = None,
        topics: List[str] = None,
        min_similarity: float = 0.0,
    ) -> List[Tuple[Chunk, float]]:
        """Return the top-k (chunk, similarity) pairs for a query."""
        self._ensure_matrix()
        if self._matrix is None or not len(self._matrix_ids):
            return []

        query_vector = _as_array(self.encode(query))
        scores = self._matrix @ query_vector

        # Rank everything, then filter, so filters never truncate the candidate
        # pool before the best matches are considered.
        order = np.argsort(-scores)
        allowed: Optional[Dict[int, Chunk]] = None
        if document_id or topics:
            filter_query = self.session.query(Chunk)
            if document_id:
                filter_query = filter_query.filter(Chunk.document_id == document_id)
            if topics:
                filter_query = filter_query.filter(Chunk.topic.in_(topics))
            allowed = {c.id: c for c in filter_query.all()}

        results: List[Tuple[Chunk, float]] = []
        for index in order:
            score = float(scores[index])
            if score < min_similarity:
                break
            chunk_id = self._matrix_ids[int(index)]
            if allowed is not None:
                chunk = allowed.get(chunk_id)
                if chunk is None:
                    continue
            else:
                chunk = self.session.get(Chunk, chunk_id)
            if chunk is not None:
                results.append((chunk, score))
            if len(results) >= top_k:
                break
        return results

    def find_similar_chunks(self, query: str, top_k: int = 5, **kwargs) -> List[Chunk]:
        """Convenience wrapper returning chunks without scores."""
        return [chunk for chunk, _ in self.search(query, top_k=top_k, **kwargs)]

    def close(self) -> None:
        if self._owns_session:
            self.session.close()
