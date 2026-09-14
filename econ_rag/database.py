"""Database models for the economics RAG system.

The schema is deliberately source-agnostic: `Document` carries a
`source_type` ("lecture", "textbook", "paper", "case_study") so textbooks and
other materials can be ingested later without a migration.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from econ_rag.config import settings

Base = declarative_base()

_engine = None
_SessionLocal = None


class Document(Base):
    """A source document (lecture notes today; textbooks/papers later)."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    title = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False, default="pdf")
    source_type = Column(String(32), nullable=False, default="lecture")
    # Ordering key within a source_type: lecture number, chapter number, etc.
    sequence = Column(Integer, nullable=True)
    course = Column(String(128), nullable=True)
    total_pages = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True)
    status = Column(String(16), default="pending")
    ingested_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    concepts = relationship("Concept", back_populates="document", cascade="all, delete-orphan")

    @property
    def citation(self) -> str:
        if self.source_type == "lecture" and self.sequence:
            return f"Lecture {self.sequence}"
        return self.title or self.name


class Chunk(Base):
    """A passage of a document, with its embedding and topic assignment."""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_num = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)
    section_num = Column(String(16), nullable=True)
    section_title = Column(String(255), nullable=True)
    page_num = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    # Primary topic slug from econ_rag.taxonomy, assigned at ingest.
    topic = Column(String(64), nullable=True)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_document", "document_id"),
        Index("idx_chunk_topic", "topic"),
    )

    @property
    def citation(self) -> str:
        parts = [self.document.citation]
        if self.section_num and self.section_title:
            parts.append(f"§{self.section_num} {self.section_title}")
        elif self.section_title:
            parts.append(self.section_title)
        if self.page_num:
            parts.append(f"p. {self.page_num}")
        return ", ".join(parts)


class Concept(Base):
    """A term-and-definition pair mined from the source material.

    These power the highest-quality generated questions: the definition is
    lifted verbatim from the lecture, so both the answer and the citation are
    grounded in the source.
    """

    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("chunks.id"), nullable=True)
    term = Column(String(128), nullable=False)
    definition = Column(Text, nullable=False)
    topic = Column(String(64), nullable=True)
    page_num = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    # "definition_block", "key_terms_table", "inline" - how it was extracted.
    extraction = Column(String(32), nullable=True)

    document = relationship("Document", back_populates="concepts")
    chunk = relationship("Chunk")

    __table_args__ = (Index("idx_concept_topic", "topic"),)

    @property
    def citation(self) -> str:
        parts = [self.document.citation]
        if self.section_title:
            parts.append(self.section_title)
        if self.page_num:
            parts.append(f"p. {self.page_num}")
        return ", ".join(parts)


class Test(Base):
    """A generated quiz session."""

    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, default="default_user")
    # "study" (student practice), "self_test", "teaching" (question bank)
    mode = Column(String(32), nullable=False, default="self_test")
    topics = Column(JSON, nullable=True)
    lectures = Column(JSON, nullable=True)
    num_questions = Column(Integer, default=10)
    score = Column(Float, nullable=True)
    num_correct = Column(Integer, nullable=True)
    status = Column(String(16), default="in_progress")
    created_date = Column(DateTime, default=datetime.utcnow)
    completed_date = Column(DateTime, nullable=True)

    questions = relationship(
        "TestQuestion",
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="TestQuestion.question_num",
    )

    __table_args__ = (Index("idx_test_user", "user_id"),)


class TestQuestion(Base):
    """One multiple-choice question belonging to a test."""

    __tablename__ = "test_questions"

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    question_num = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    correct_option = Column(String(1), nullable=False)
    explanation = Column(Text, nullable=True)
    # Which generator produced it: definition, term_id, cloze, calc_equilibrium,
    # comparative_statics, shift_vs_movement, positive_normative.
    question_kind = Column(String(32), nullable=True)
    topic = Column(String(64), nullable=True)
    source_chunk_id = Column(Integer, ForeignKey("chunks.id"), nullable=True)
    source_citation = Column(String(500), nullable=True)

    user_answer = Column(String(1), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answered_date = Column(DateTime, nullable=True)

    test = relationship("Test", back_populates="questions")
    source_chunk = relationship("Chunk")

    __table_args__ = (Index("idx_question_test", "test_id"),)


class TopicProgress(Base):
    """Rolling per-topic performance, updated as tests are completed."""

    __tablename__ = "topic_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    topic = Column(String(64), nullable=False)
    attempted = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_progress_user_topic", "user_id", "topic", unique=True),)


class QueryHistory(Base):
    """Search/Q&A log, used for analytics and for 'recent questions'."""

    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=True)
    query_text = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


def get_engine():
    """Return the process-wide SQLAlchemy engine."""
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, echo=False)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session() -> Session:
    """Return a new database session."""
    get_engine()
    return _SessionLocal()


def init_db() -> None:
    """Create all tables."""
    Base.metadata.create_all(get_engine())
    print(f"Database initialized: {settings.DATABASE_URL}")
