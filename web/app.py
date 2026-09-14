"""FastAPI server for the economics RAG study system."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from pydantic import BaseModel, Field

from econ_rag.config import settings
from econ_rag.database import Chunk, Concept, Document, get_session
from econ_rag.services.embeddings import EmbeddingService
from econ_rag.services.rag_engine import RAGEngine
from econ_rag.services.test_generator import InsufficientContentError, TestGenerator
from econ_rag.taxonomy import all_topics, topic_name

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Intro Economics RAG",
    description="Semantic search, Q&A, and quiz generation over ECON 154 materials.",
    version="0.1.0",
)

# One shared session and one loaded embedding model for the process; the model
# takes a second to load and the corpus is read-mostly.
_session = get_session()
_embedder = EmbeddingService(session=_session)
_rag = RAGEngine(session=_session, embedder=_embedder)


def _generator() -> TestGenerator:
    return TestGenerator(session=_session, embedder=_embedder)


# ------------------------------------------------------------- schemas -----


class AskRequest(BaseModel):
    query: str = Field(..., min_length=2)
    topics: Optional[List[str]] = None
    top_k: int = Field(default=settings.RAG_TOP_K, ge=1, le=20)
    user_id: Optional[str] = None


class TestRequest(BaseModel):
    user_id: str = "default_user"
    mode: str = Field(default="self_test", pattern="^(study|self_test|teaching)$")
    topics: Optional[List[str]] = None
    lectures: Optional[List[int]] = None
    num_questions: int = Field(default=10, ge=1, le=50)
    seed: Optional[int] = None


class SubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)


# ------------------------------------------------------------- endpoints ---


@app.get("/api/topics")
def get_topics() -> Dict:
    """Topic taxonomy, annotated with how much material backs each topic."""
    counts = dict(
        _session.query(Chunk.topic, func.count(Chunk.id))
        .group_by(Chunk.topic)
        .all()
    )
    topics = all_topics()
    for topic in topics:
        topic["chunk_count"] = counts.get(topic["slug"], 0)
    return {"topics": topics}


@app.get("/api/lectures")
def get_lectures() -> Dict:
    """Ingested source documents."""
    documents = (
        _session.query(Document).order_by(Document.source_type, Document.sequence).all()
    )
    return {
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "title": d.title,
                "citation": d.citation,
                "source_type": d.source_type,
                "sequence": d.sequence,
                "pages": d.total_pages,
                "chunks": len(d.chunks),
                "status": d.status,
            }
            for d in documents
        ]
    }


@app.get("/api/concepts")
def get_concepts(topic: Optional[str] = None) -> Dict:
    """The mined glossary, for study and for reviewing question quality."""
    query = _session.query(Concept)
    if topic:
        query = query.filter(Concept.topic == topic)
    return {
        "concepts": [
            {
                "term": c.term,
                "definition": c.definition,
                "topic": c.topic,
                "topic_name": topic_name(c.topic),
                "citation": c.citation,
            }
            for c in query.order_by(Concept.term).all()
        ]
    }


@app.get("/api/stats")
def get_stats() -> Dict:
    return {
        "documents": _session.query(Document).count(),
        "chunks": _session.query(Chunk).count(),
        "concepts": _session.query(Concept).count(),
        "topics": len(all_topics()),
    }


@app.post("/api/ask")
def ask(request: AskRequest) -> Dict:
    """Answer a question from the lecture notes, with citations."""
    return _rag.answer(
        request.query,
        top_k=request.top_k,
        topics=request.topics,
        user_id=request.user_id,
    )


@app.post("/api/search")
def search(request: AskRequest) -> Dict:
    """Return matching passages without composing an answer."""
    return {"results": _rag.search(request.query, top_k=request.top_k, topics=request.topics)}


@app.post("/api/tests")
def create_test(request: TestRequest) -> Dict:
    """Generate a quiz."""
    generator = _generator()
    try:
        test_id = generator.create_test(
            user_id=request.user_id,
            mode=request.mode,
            topics=request.topics,
            lectures=request.lectures,
            num_questions=request.num_questions,
            seed=request.seed,
        )
    except InsufficientContentError as error:
        raise HTTPException(status_code=422, detail=str(error))
    # Teaching mode is question-bank preparation, so the key is shown up front.
    return generator.get_test(test_id, include_answers=request.mode == "teaching")


@app.get("/api/tests")
def list_tests(user_id: str = "default_user", limit: int = Query(50, ge=1, le=200)) -> Dict:
    return {"tests": _generator().list_tests(user_id, limit=limit)}


@app.get("/api/tests/{test_id}")
def get_test(test_id: int, reveal: bool = False) -> Dict:
    test = _generator().get_test(test_id, include_answers=reveal)
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return test


@app.post("/api/tests/{test_id}/submit")
def submit_test(test_id: int, request: SubmitRequest) -> Dict:
    result = _generator().submit_answers(test_id, dict(request.answers))
    if result is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return result


@app.get("/api/tests/{test_id}/export", response_class=PlainTextResponse)
def export_test(test_id: int) -> str:
    """Markdown question bank with an answer key, for teaching prep."""
    test = _generator().get_test(test_id, include_answers=True)
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")

    scope = ", ".join(test["topic_names"]) or (
        "Lectures " + ", ".join(str(x) for x in test["lectures"])
        if test["lectures"]
        else "All topics"
    )
    lines = [
        f"# ECON 154 Question Bank - {scope}",
        "",
        f"{test['num_questions']} questions, generated {test['created_date'][:10]}.",
        "",
    ]
    for question in test["questions"]:
        lines.append(f"**{question['question_num']}.** {question['question_text']}")
        lines.append("")
        for letter in ("a", "b", "c", "d"):
            lines.append(f"   {letter}) {question['options'][letter]}")
        lines.append("")
    lines += ["", "---", "", "## Answer Key", ""]
    for question in test["questions"]:
        lines.append(
            f"**{question['question_num']}.** "
            f"{question['correct_option'].upper()} - {question['explanation']}"
        )
        lines.append(f"   *Source: {question['source_citation']}*")
        lines.append("")
    return "\n".join(lines)


@app.get("/api/progress")
def progress(user_id: str = "default_user") -> Dict:
    return _generator().progress(user_id)


# -------------------------------------------------------------- frontend ---

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)


if __name__ == "__main__":
    main()
