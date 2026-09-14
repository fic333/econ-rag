"""Quiz generation, delivery, grading, and progress tracking.

Questions come from three sources, blended so a quiz mixes recall with
application:

* `definition` / `term_id` - built from concepts mined out of the lecture text.
* `cloze` - a sentence from the lectures with its key term removed.
* template generators - procedural skills (solving for equilibrium, comparative
  statics, classifying costs) drawn from `question_banks`.

Every question carries an explanation and a citation back to the lecture.
"""

from __future__ import annotations

import random
import re
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

from econ_rag.database import (
    Chunk,
    Concept,
    Document,
    Test,
    TestQuestion,
    TopicProgress,
    get_session,
)
from econ_rag.services.concepts import GLOSSARY
from econ_rag.services.embeddings import EmbeddingService
from econ_rag.services.question_banks import generators_for
from econ_rag.taxonomy import BY_SLUG, topic_name

OPTION_LETTERS = ["a", "b", "c", "d"]

# Diagram labels and flattened tables survive PDF extraction as pseudo-
# sentences ("Price Too Low => Shortage => Upward pressure"). They read as
# nonsense once a word is blanked out, so cloze skips them.
_FIGURE_NOISE = re.compile(r"[\u21d0-\u21d3\u2190-\u2193\u00b7|]|\b(Figure|Table)\s*\d")
_SENTENCE_SHAPE = re.compile(r"^[A-Z(].*[.!?]$")
_COMMON_VERB = re.compile(
    r"\b(is|are|was|were|be|been|has|have|had|does|do|did|can|will|would|"
    r"means|shows|gives|makes|rises|falls|increases|decreases|shifts|moves|"
    r"depends|reflects|equals|leads|causes|explains|represents|occurs|"
    r"produces|buys|sells|wants|chooses|must|should)\b"
)


def _is_list_item(sentence: str, start: int, end: int) -> bool:
    """True when the matched term sits inside a comma-separated enumeration."""
    if sentence.count(",") < 2:
        return False
    before = sentence[:start].rstrip()
    after = sentence[end:].lstrip()
    return before.endswith(",") and after.startswith(",")


def _is_prose(sentence: str) -> bool:
    """True when a sentence reads as prose rather than extracted figure text."""
    if _FIGURE_NOISE.search(sentence):
        return False
    if not _SENTENCE_SHAPE.match(sentence):
        return False
    words = sentence.split()
    if not (10 <= len(words) <= 45):
        return False
    if not _COMMON_VERB.search(sentence):
        return False
    # A flattened table reads as a run of capitalised column headings.
    mid_caps = sum(1 for w in words[1:] if w[:1].isupper())
    return mid_caps / len(words) <= 0.25

# Single words vague enough that a blank could be filled several ways.
_AMBIGUOUS_FOR_CLOZE = {
    "market", "demand", "supply", "profit", "revenue", "technology",
    "preferences", "efficiency", "regulation", "subsidy", "complement",
    "complements", "substitute", "substitutes", "economics", "causation",
    "correlation", "firm", "incentive",
}

# Terms worth blanking out: any multi-word glossary phrase, plus single words
# distinctive enough that the sentence pins them down.
_CLOZE_TERMS = sorted(
    {
        term
        for term in GLOSSARY
        if len(term) > 4
        and (" " in term or term not in _AMBIGUOUS_FOR_CLOZE)
        and term not in {"gdp"}
    },
    key=len,
    reverse=True,
)


class InsufficientContentError(RuntimeError):
    """Raised when the corpus cannot support the requested quiz."""


class TestGenerator:
    """Builds quizzes from the ingested corpus."""

    def __init__(self, session=None, embedder: EmbeddingService = None):
        self.session = session or get_session()
        self._owns_session = session is None
        self._embedder = embedder

    @property
    def embedder(self) -> EmbeddingService:
        if self._embedder is None:
            self._embedder = EmbeddingService(session=self.session)
        return self._embedder

    # ------------------------------------------------------------ building --

    def build_questions(
        self,
        topics: Optional[Sequence[str]] = None,
        lectures: Optional[Sequence[int]] = None,
        num_questions: int = 10,
        seed: Optional[int] = None,
    ) -> List[Dict]:
        """Produce `num_questions` unique questions for the given scope."""
        rng = random.Random(seed)
        topics = [t for t in (topics or []) if t in BY_SLUG] or None

        # Targets must be in scope; distractors may come from anywhere, since a
        # wrong option only has to be wrong.
        concepts = self._concepts_in_scope(topics, lectures)
        concept_pool = self.session.query(Concept).all()
        chunks = self._chunks_in_scope(topics, lectures)
        templates = generators_for(
            list(topics) if topics else None,
            list(lectures) if lectures else None,
        )

        if not concepts and not chunks and not templates:
            raise InsufficientContentError(
                "No lecture content matches that selection. Try another topic or "
                "lecture, or ingest more material."
            )

        # Each builder is (tag, callable) - a bound method is a fresh object on
        # every attribute access, so the builders must be tagged rather than
        # compared by identity.
        builders: List = []
        if concepts and len(concept_pool) >= 4:
            builders.append(("concept", self._definition_question))
            builders.append(("concept", self._term_id_question))
        if chunks:
            builders.append(("chunk", self._cloze_question))
        if templates:
            builders.append(("template", lambda r: rng.choice(templates)(r)))
        if not builders:
            raise InsufficientContentError(
                "Not enough distinct material in that selection to build a quiz."
            )

        questions: List[Dict] = []
        seen_signatures = set()
        seen_content: set = set()
        attempts = 0
        max_attempts = num_questions * 40

        while len(questions) < num_questions and attempts < max_attempts:
            attempts += 1
            # Rotate through the builders first so every quiz mixes question
            # types, then fall back to random choice to fill any shortfall.
            tag, builder = (
                builders[len(questions) % len(builders)]
                if attempts <= num_questions
                else rng.choice(builders)
            )
            try:
                if tag == "concept":
                    question = builder(rng, concepts, concept_pool)
                elif tag == "chunk":
                    question = builder(rng, chunks)
                else:
                    question = builder(rng)
            except InsufficientContentError:
                continue
            if question is None:
                continue
            signature = self._signature(question)
            content_key = question.get("content_key")
            if signature in seen_signatures or (
                content_key and content_key in seen_content
            ):
                continue
            seen_signatures.add(signature)
            if content_key:
                seen_content.add(content_key)
            questions.append(question)

        if not questions:
            raise InsufficientContentError(
                "Could not generate any questions for that selection."
            )
        return questions

    @staticmethod
    def _signature(question: Dict) -> str:
        """Identify duplicates by what is actually being asked."""
        return re.sub(r"\s+", " ", f"{question['question']}|{question['correct']}").lower()

    def _concepts_in_scope(
        self, topics: Optional[Sequence[str]], lectures: Optional[Sequence[int]]
    ) -> List[Concept]:
        query = self.session.query(Concept)
        if topics:
            query = query.filter(Concept.topic.in_(list(topics)))
        if lectures:
            query = query.join(Document).filter(Document.sequence.in_(list(lectures)))
        return query.all()

    def _chunks_in_scope(
        self, topics: Optional[Sequence[str]], lectures: Optional[Sequence[int]]
    ) -> List[Chunk]:
        query = self.session.query(Chunk)
        if topics:
            query = query.filter(Chunk.topic.in_(list(topics)))
        if lectures:
            query = query.join(Document).filter(Document.sequence.in_(list(lectures)))
        return query.all()

    # ------------------------------------------------- question generators --

    def _definition_question(
        self,
        rng: random.Random,
        targets: List[Concept],
        concept_pool: List[Concept],
    ) -> Optional[Dict]:
        """Which of these is the definition of <term>?"""
        if not targets or len(concept_pool) < 4:
            raise InsufficientContentError("fewer than four concepts available")

        target = rng.choice(targets)
        pool = [c for c in concept_pool if c.id != target.id]
        # Prefer same-topic distractors: confusable options make a better test.
        same_topic = [c for c in pool if c.topic == target.topic]
        rng.shuffle(same_topic)
        rng.shuffle(pool)
        chosen, seen = [], {self._normalize(target.definition)}
        for candidate in same_topic + pool:
            text = self._normalize(candidate.definition)
            if text in seen:
                continue
            seen.add(text)
            chosen.append(candidate)
            if len(chosen) == 3:
                break
        if len(chosen) < 3:
            return None

        return {
            "kind": "definition",
            "topic": target.topic,
            "question": f"Which of the following best defines {self._term_phrase(target.term)}?",
            "correct": self._as_option(target.definition),
            "distractors": [self._as_option(c.definition) for c in chosen],
            "explanation": (
                f"{self._term_phrase(target.term).capitalize()} is "
                f"{target.definition.rstrip('.')}."
            ),
            "citation": target.citation,
            "chunk_id": target.chunk_id,
            "content_key": f"term:{target.term.lower()}",
        }

    def _term_id_question(
        self,
        rng: random.Random,
        targets: List[Concept],
        concept_pool: List[Concept],
    ) -> Optional[Dict]:
        """Which term matches this definition? (the reverse direction)"""
        if not targets or len(concept_pool) < 4:
            raise InsufficientContentError("fewer than four concepts available")

        target = rng.choice(targets)
        pool = [
            c for c in concept_pool
            if self._normalize(c.term) != self._normalize(target.term)
        ]
        same_topic = [c for c in pool if c.topic == target.topic]
        rng.shuffle(same_topic)
        rng.shuffle(pool)
        chosen, seen = [], {self._normalize(target.term)}
        for candidate in same_topic + pool:
            name = self._normalize(candidate.term)
            if name in seen:
                continue
            seen.add(name)
            chosen.append(candidate)
            if len(chosen) == 3:
                break
        if len(chosen) < 3:
            return None

        return {
            "kind": "term_id",
            "topic": target.topic,
            "question": (
                f'Which term does the course define as "'
                f'{target.definition.rstrip(".")}"?'
            ),
            "correct": self._term_phrase(target.term).capitalize(),
            "distractors": [self._term_phrase(c.term).capitalize() for c in chosen],
            "explanation": (
                f"That is the definition of "
                f"{self._term_phrase(target.term)}, given in {target.citation}."
            ),
            "citation": target.citation,
            "chunk_id": target.chunk_id,
            "content_key": f"term:{target.term.lower()}",
        }

    def _cloze_question(self, rng: random.Random, chunks: List[Chunk]) -> Optional[Dict]:
        """Blank out a key term in a sentence taken from the lectures."""
        candidates = [
            c for c in chunks if "key terms" not in (c.section_title or "").lower()
        ]
        rng.shuffle(candidates)
        for chunk in candidates[:40]:
            body = re.sub(r"^\[[^\]]*\]\n", "", chunk.content)
            body = re.sub(r"\s+", " ", body)
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body)]
            rng.shuffle(sentences)
            for sentence in sentences:
                if not (60 <= len(sentence) <= 260) or "•" in sentence or "=" in sentence:
                    continue
                if not _is_prose(sentence):
                    continue
                for term in _CLOZE_TERMS:
                    match = re.search(rf"\b{re.escape(term)}\b", sentence, re.IGNORECASE)
                    if not match:
                        continue
                    if _is_list_item(sentence, match.start(), match.end()):
                        # "...tariffs, international trade, exchange rates, ..."
                        # blanks to a guess among interchangeable list items
                        # rather than to a concept being used.
                        continue
                    blanked = re.sub(
                        rf"\b{re.escape(term)}\b", "________", sentence,
                        flags=re.IGNORECASE,
                    )
                    distractors = [
                        t for t in _CLOZE_TERMS
                        if t != term and t not in sentence.lower()
                    ]
                    if len(distractors) < 3:
                        continue
                    picks = rng.sample(distractors, 3)
                    return {
                        "kind": "cloze",
                        "topic": chunk.topic,
                        "question": (
                            f"Fill in the blank with the term used in the lectures:\n"
                            f"{blanked}"
                        ),
                        "correct": term,
                        "distractors": picks,
                        "explanation": (
                            f'The passage reads: "{sentence}" '
                            f"(from {chunk.citation})."
                        ),
                        "citation": chunk.citation,
                        "chunk_id": chunk.id,
                        "content_key": f"term:{term.lower()}",
                    }
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()

    @staticmethod
    def _term_phrase(term: str) -> str:
        term = term.strip()
        return term if term.isupper() else term[0].lower() + term[1:]

    @staticmethod
    def _as_option(definition: str) -> str:
        definition = definition.strip().rstrip(".")
        return definition[0].upper() + definition[1:] if definition else definition

    # ------------------------------------------------------- persistence ----

    def create_test(
        self,
        user_id: str = "default_user",
        mode: str = "self_test",
        topics: Optional[Sequence[str]] = None,
        lectures: Optional[Sequence[int]] = None,
        num_questions: int = 10,
        seed: Optional[int] = None,
    ) -> int:
        """Generate a quiz, persist it, and return its id."""
        questions = self.build_questions(
            topics=topics, lectures=lectures, num_questions=num_questions, seed=seed
        )
        test = Test(
            user_id=user_id,
            mode=mode,
            topics=list(topics) if topics else None,
            lectures=list(lectures) if lectures else None,
            num_questions=len(questions),
            status="in_progress",
        )
        self.session.add(test)
        self.session.flush()

        rng = random.Random(seed)
        for index, question in enumerate(questions, start=1):
            options = [question["correct"]] + list(question["distractors"])[:3]
            rng.shuffle(options)
            correct_index = options.index(question["correct"])
            self.session.add(
                TestQuestion(
                    test_id=test.id,
                    question_num=index,
                    question_text=question["question"],
                    option_a=options[0],
                    option_b=options[1],
                    option_c=options[2],
                    option_d=options[3],
                    correct_option=OPTION_LETTERS[correct_index],
                    explanation=question.get("explanation"),
                    question_kind=question.get("kind"),
                    topic=question.get("topic"),
                    source_chunk_id=question.get("chunk_id"),
                    source_citation=question.get("citation"),
                )
            )
        self.session.commit()
        return test.id

    def get_test(self, test_id: int, include_answers: bool = False) -> Optional[Dict]:
        """Return a test. Answers are withheld until it is submitted."""
        test = self.session.get(Test, test_id)
        if test is None:
            return None
        reveal = include_answers or test.status == "completed"
        return {
            "id": test.id,
            "user_id": test.user_id,
            "mode": test.mode,
            "topics": test.topics,
            "topic_names": [topic_name(t) for t in (test.topics or [])],
            "lectures": test.lectures,
            "status": test.status,
            "score": test.score,
            "num_correct": test.num_correct,
            "num_questions": test.num_questions,
            "created_date": test.created_date.isoformat(),
            "completed_date": (
                test.completed_date.isoformat() if test.completed_date else None
            ),
            "questions": [
                self._serialize_question(q, reveal) for q in test.questions
            ],
        }

    @staticmethod
    def _serialize_question(question: TestQuestion, reveal: bool) -> Dict:
        payload = {
            "id": question.id,
            "question_num": question.question_num,
            "question_text": question.question_text,
            "options": {
                "a": question.option_a,
                "b": question.option_b,
                "c": question.option_c,
                "d": question.option_d,
            },
            "kind": question.question_kind,
            "topic": question.topic,
            "topic_name": topic_name(question.topic),
            "user_answer": question.user_answer,
        }
        if reveal:
            payload.update(
                {
                    "correct_option": question.correct_option,
                    "explanation": question.explanation,
                    "source_citation": question.source_citation,
                    "is_correct": question.is_correct,
                }
            )
        return payload

    def submit_answers(self, test_id: int, answers: Dict[int, str]) -> Optional[Dict]:
        """Grade a test from a {question_id: letter} mapping."""
        test = self.session.get(Test, test_id)
        if test is None:
            return None

        for question in test.questions:
            answer = answers.get(question.id) or answers.get(str(question.id))
            if answer:
                answer = answer.strip().lower()[:1]
            question.user_answer = answer if answer in OPTION_LETTERS else None
            question.is_correct = question.user_answer == question.correct_option
            question.answered_date = datetime.utcnow()

        correct = sum(1 for q in test.questions if q.is_correct)
        total = len(test.questions)
        test.num_correct = correct
        test.score = round(correct / total * 100, 1) if total else 0.0
        test.status = "completed"
        test.completed_date = datetime.utcnow()
        self._record_progress(test)
        self.session.commit()
        return self.get_test(test_id, include_answers=True)

    def _record_progress(self, test: Test) -> None:
        """Fold this test's results into the user's per-topic tallies."""
        for question in test.questions:
            if not question.topic:
                continue
            row = (
                self.session.query(TopicProgress)
                .filter(
                    TopicProgress.user_id == test.user_id,
                    TopicProgress.topic == question.topic,
                )
                .first()
            )
            if row is None:
                row = TopicProgress(
                    user_id=test.user_id, topic=question.topic, attempted=0, correct=0
                )
                self.session.add(row)
            row.attempted += 1
            if question.is_correct:
                row.correct += 1
            row.last_seen = datetime.utcnow()

    # ---------------------------------------------------------- analytics ----

    def list_tests(self, user_id: str, limit: int = 50) -> List[Dict]:
        tests = (
            self.session.query(Test)
            .filter(Test.user_id == user_id)
            .order_by(Test.created_date.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": t.id,
                "mode": t.mode,
                "topics": t.topics,
                "topic_names": [topic_name(x) for x in (t.topics or [])],
                "lectures": t.lectures,
                "num_questions": t.num_questions,
                "status": t.status,
                "score": t.score,
                "num_correct": t.num_correct,
                "created_date": t.created_date.isoformat(),
            }
            for t in tests
        ]

    def progress(self, user_id: str) -> Dict:
        """Per-topic accuracy plus an overall summary for the dashboard."""
        rows = (
            self.session.query(TopicProgress)
            .filter(TopicProgress.user_id == user_id)
            .all()
        )
        topics = [
            {
                "topic": row.topic,
                "topic_name": topic_name(row.topic),
                "attempted": row.attempted,
                "correct": row.correct,
                "accuracy": round(row.correct / row.attempted * 100, 1)
                if row.attempted
                else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in rows
        ]
        topics.sort(key=lambda t: (t["accuracy"] if t["accuracy"] is not None else 101))

        completed = (
            self.session.query(Test)
            .filter(Test.user_id == user_id, Test.status == "completed")
            .all()
        )
        attempted = sum(t["attempted"] for t in topics)
        correct = sum(t["correct"] for t in topics)
        return {
            "user_id": user_id,
            "tests_completed": len(completed),
            "questions_answered": attempted,
            "overall_accuracy": round(correct / attempted * 100, 1) if attempted else None,
            "average_score": (
                round(sum(t.score or 0 for t in completed) / len(completed), 1)
                if completed
                else None
            ),
            "weakest_topics": [t for t in topics if t["accuracy"] is not None][:3],
            "topics": topics,
        }

    def close(self) -> None:
        if self._owns_session:
            self.session.close()
