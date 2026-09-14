"""Retrieval and extractive answering over the lecture corpus.

The system is deliberately API-free: retrieval finds the passages that matter,
and the answer is assembled from the highest-scoring sentences in those
passages rather than generated. That keeps every word traceable to a lecture
and the whole system free to run. `answer()` returns the supporting passages
alongside the summary, so a caller that does want a generative layer can pass
`sources` straight to a model as context.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

import numpy as np

from econ_rag.config import settings
from econ_rag.database import Concept, QueryHistory, get_session
from econ_rag.services.embeddings import EmbeddingService
from econ_rag.taxonomy import topic_name

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
# Figure and table captions rank well against a question but read as noise in
# an answer, since the artwork they describe is not carried over.
_CAPTION = re.compile(r"^(Figure|Table)\s*\d+\s*[:.]")


def _sentences(text: str) -> List[str]:
    body = re.sub(r"^\[[^\]]*\]\n", "", text)
    body = re.sub(r"\s+", " ", body).strip()
    return [
        s.strip()
        for s in _SENTENCE_SPLIT.split(body)
        if len(s.strip()) > 30 and not _CAPTION.match(s.strip())
    ]


class RAGEngine:
    """Answers economics questions from the ingested material."""

    def __init__(self, session=None, embedder: EmbeddingService = None):
        self.session = session or get_session()
        self._owns_session = session is None
        self.embedder = embedder or EmbeddingService(session=self.session)

    def search(
        self,
        query: str,
        top_k: int = None,
        topics: Optional[Sequence[str]] = None,
        document_id: Optional[int] = None,
    ) -> List[Dict]:
        """Return ranked passages with their citations."""
        hits = self.embedder.search(
            query,
            top_k=top_k or settings.RAG_TOP_K,
            topics=list(topics) if topics else None,
            document_id=document_id,
        )
        return [
            {
                "chunk_id": chunk.id,
                "citation": chunk.citation,
                "lecture": chunk.document.sequence,
                "document": chunk.document.citation,
                "section": chunk.section_title,
                "page": chunk.page_num,
                "topic": chunk.topic,
                "topic_name": topic_name(chunk.topic),
                "score": round(score, 4),
                "text": re.sub(r"^\[[^\]]*\]\n", "", chunk.content),
            }
            for chunk, score in hits
        ]

    def answer(
        self,
        query: str,
        top_k: int = None,
        topics: Optional[Sequence[str]] = None,
        user_id: Optional[str] = None,
        max_sentences: int = 4,
    ) -> Dict:
        """Compose an extractive answer with inline lecture citations."""
        sources = self.search(query, top_k=top_k, topics=topics)
        if not sources:
            return {
                "query": query,
                "answer": (
                    "Nothing in the ingested lecture notes matches that question. "
                    "Try rephrasing it, or ingest more material."
                ),
                "sources": [],
                "concepts": [],
            }

        query_vector = np.asarray(self.embedder.encode(query), dtype=np.float32)
        scored: List[tuple[float, str, Dict]] = []
        for source in sources:
            candidates = _sentences(source["text"])
            if not candidates:
                continue
            vectors = np.asarray(self.embedder.encode(candidates), dtype=np.float32)
            similarities = vectors @ query_vector
            for sentence, similarity in zip(candidates, similarities):
                scored.append((float(similarity), sentence, source))

        scored.sort(key=lambda row: -row[0])
        chosen: List[tuple[str, Dict]] = []
        seen: set[str] = set()
        for _similarity, sentence, source in scored:
            key = re.sub(r"[^a-z0-9]", "", sentence.lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            chosen.append((sentence, source))
            if len(chosen) >= max_sentences:
                break

        summary = " ".join(
            f"{sentence} [{source['document']}]" for sentence, source in chosen
        )
        record = QueryHistory(
            user_id=user_id,
            query_text=query,
            sources=[s["citation"] for s in sources],
        )
        self.session.add(record)
        self.session.commit()

        return {
            "query": query,
            "answer": summary,
            "sources": sources,
            "concepts": self._related_concepts(query),
        }

    def _related_concepts(self, query: str, limit: int = 3) -> List[Dict]:
        """Surface glossary entries whose term appears in the question."""
        lowered = query.lower()
        matches = [
            concept
            for concept in self.session.query(Concept).all()
            if re.search(rf"\b{re.escape(concept.term.lower())}", lowered)
        ]
        matches.sort(key=lambda c: -len(c.term))
        return [
            {
                "term": c.term,
                "definition": c.definition,
                "citation": c.citation,
                "topic": c.topic,
            }
            for c in matches[:limit]
        ]

    def close(self) -> None:
        if self._owns_session:
            self.session.close()
