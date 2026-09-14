"""Mine term/definition pairs from ingested source material.

Generated multiple-choice questions are only as good as their answer text, so
rather than slicing arbitrary sentences we extract genuine definitions: a
sentence whose subject is a known economics term and whose predicate defines
it. Both the answer and its citation then come straight from the lecture.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from econ_rag.database import Chunk, Concept, Document, get_session
from econ_rag.taxonomy import TOPICS

# Curated vocabulary for an intro course. A candidate term must overlap with
# this list, which keeps sentences like "The phone is a physical object" out.
GLOSSARY: List[str] = [
    "economics", "microeconomics", "macroeconomics", "scarcity", "tradeoff",
    "opportunity cost", "explicit cost", "implicit cost", "sunk cost",
    "incentive", "marginal benefit", "marginal cost", "marginal analysis",
    "marginal revenue", "positive statement", "normative statement",
    "correlation", "causation", "economic model", "ceteris paribus",
    "production possibilities frontier", "efficiency",
    "gross domestic product", "gdp", "inflation", "exchange rate",
    "globalization", "international trade",
    "market", "demand", "quantity demanded", "law of demand",
    "demand schedule", "demand curve", "market demand",
    "willingness to pay", "budget constraint", "consumer surplus",
    "substitute", "substitutes", "complement", "complements",
    "normal good", "inferior good", "preferences",
    "firm", "entrepreneur", "revenue", "total revenue", "profit",
    "economic profit", "accounting profit", "economic cost",
    "production cost", "production costs", "fixed cost", "fixed costs",
    "variable cost", "variable costs", "total cost", "average cost",
    "specialization", "productivity",
    "supply", "quantity supplied", "law of supply", "supply schedule",
    "supply curve", "market supply", "input price", "technology",
    "subsidy", "regulation",
    "market equilibrium", "equilibrium", "equilibrium price",
    "equilibrium quantity", "market clearing", "shortage", "surplus",
    "excess demand", "excess supply", "price adjustment",
    "comparative statics", "market shock",
]
_GLOSSARY_SET = {g.lower() for g in GLOSSARY}

# A concept belongs to the topic that owns its vocabulary, which is not always
# the topic of the passage that happens to define it: Lecture 1 defines
# "incentive" inside its vocabulary section, but the concept is an `incentives`
# concept for the purpose of topic-filtered quizzes.
_TERM_TOPIC = {}
for _topic in TOPICS:
    for _keyword in _topic.keywords:
        _TERM_TOPIC.setdefault(_keyword.lower(), _topic.slug)
        _TERM_TOPIC.setdefault(_keyword.lower().rstrip("s"), _topic.slug)


def topic_for_term(canonical: str, fallback: Optional[str]) -> Optional[str]:
    """Resolve a concept's topic from its vocabulary, falling back to context."""
    lowered = canonical.lower()
    return (
        _TERM_TOPIC.get(lowered)
        or _TERM_TOPIC.get(lowered.rstrip("s"))
        or fallback
    )

# Subjects that look like terms but are deictic or generic.
STOP_TERMS = {
    "it", "this", "that", "there", "these", "those", "they", "we", "you",
    "he", "she", "one", "some", "many", "most", "what", "how", "why",
    "the goal", "the key", "the point", "the idea", "the answer",
    "the result", "the central idea", "the standard benchmark",
    "the graphical analysis", "the phone", "the word", "the first",
    "the second", "the third", "the same", "the following", "the question",
    "willing", "able", "coffee", "the market", "the lecture", "the course",
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
# Sentence-anchored definition: <term> <copula> <definition>. The term is
# capped at four tokens because intro-course vocabulary is short, and a longer
# match is almost always a clause that swallowed part of the sentence.
DEF_PATTERN = re.compile(
    r"^(?:(?:The|A|An)\s+)?"
    r"((?:[A-Za-z][A-Za-z'\-]*)(?:\s+(?:[A-Za-z][A-Za-z'\-]*|of|to|a|the)){0,3})"
    r"\s+(?:simply\s+|generally\s+|therefore\s+)?"
    r"(is|are|refers\s+to|is\s+defined\s+as|means|is\s+called|describes)\s+"
    r"(.{25,400})$",
    re.DOTALL,
)

# "We define opportunity cost as the value of ..." / "economists call this X"
DEF_PATTERN_ALT = re.compile(
    r"^(?:Economists\s+)?(?:We\s+)?define\s+"
    r"((?:[A-Za-z][A-Za-z'\-]*)(?:\s+(?:[a-z][a-z'\-]*|of|to)){0,3})"
    r"\s+as\s+(.{25,400})$",
    re.DOTALL | re.IGNORECASE,
)

# "The law of demand states that ..." - laws are phrased this way, not with a copula.
DEF_PATTERN_STATES = re.compile(
    r"^(?:The\s+)?((?:[A-Za-z][A-Za-z'\-]*)(?:\s+(?:[a-z][a-z'\-]*|of|to)){0,3})"
    r"\s+states\s+that,?\s+(.{25,400})$",
    re.DOTALL,
)

# "Two goods are substitutes when a rise in the price of one ..."
DEF_PATTERN_TWO_GOODS = re.compile(
    r"^Two\s+goods\s+are\s+([a-z]+)\s+(when\s+.{20,400})$", re.DOTALL
)

# Words that reveal the "term" is really a clause, not a noun phrase.
TERM_BLOCKLIST = re.compile(
    r"\b(is|are|was|were|means|summari[sz]es|describes|whether|once|when|"
    r"because|which|that|refers|helps|shows|makes|gives|simply|important|"
    r"lesson|question|answer|goal|point|idea|benchmark|analysis|insight)\b",
    re.IGNORECASE,
)

# A definition should describe, not merely assert something incidental.
BAD_DEFINITION_START = re.compile(
    r"^(also|often|not|only|sometimes|therefore|thus|simply\s+one|clear|"
    r"important|useful|helpful|central|true|false|possible|likely|"
    r"greater|less|higher|lower|broader|narrower|wider|similar|different|"
    r"equal\s+to\s+the\s+number)\b",
    re.IGNORECASE,
)


def _normalize_term(term: str) -> str:
    term = re.sub(r"\s+", " ", term).strip().strip(",;:")
    term = re.sub(r"^(the|a|an)\s+", "", term, flags=re.IGNORECASE)
    # Possessive framing: "a consumer's willingness to pay" -> "willingness to pay".
    term = re.sub(r"^\w+'s\s+", "", term)
    # "opportunity cost of a choice" and "opportunity cost" are one concept.
    term = re.sub(r"\s+(of|to)\s+(a|an|the)\s+\w+$", "", term, flags=re.IGNORECASE)
    term = re.sub(r"\s+(simply|generally|therefore|also)$", "", term, flags=re.IGNORECASE)
    return term.strip()


def _glossary_match(term: str) -> Optional[str]:
    """Return the glossary entry this term corresponds to, if any.

    Matching is exact (after normalization and singularisation) rather than by
    containment: containment lets a clause like "important lesson in economics"
    pass on the strength of the word "economics".
    """
    lowered = term.lower()
    if lowered in _GLOSSARY_SET:
        return lowered
    singular = re.sub(r"s$", "", lowered)
    if singular in _GLOSSARY_SET:
        return singular
    if lowered + "s" in _GLOSSARY_SET:
        return lowered + "s"

    # A subsection heading often runs into the first sentence, giving terms
    # like "Fixed Costs Fixed costs" or "Incentives An incentive". Match a
    # trailing sub-phrase, but only when the discarded prefix is an article or
    # a repeat of the term itself - never when it is real extra wording.
    tokens = lowered.split()
    for start in range(1, len(tokens)):
        tail = " ".join(tokens[start:])
        canonical = (
            tail if tail in _GLOSSARY_SET
            else re.sub(r"s$", "", tail) if re.sub(r"s$", "", tail) in _GLOSSARY_SET
            else None
        )
        if canonical is None:
            continue
        prefix = tokens[:start]
        if len(prefix) > 2:
            continue
        tail_stems = {word.rstrip("s") for word in tail.split()}
        if all(
            token in {"a", "an", "the", "two", "goods"}
            or token.rstrip("s") in tail_stems
            for token in prefix
        ):
            return canonical
    return None


def _clean_definition(text: str) -> Optional[str]:
    text = re.sub(r"\s+", " ", text).strip()
    # "Scarcity means that available resources are limited" - the conjunction
    # belongs to the copula, not the definition.
    text = re.sub(r"^that\s+", "", text)
    # The notes cite their own sources inline; that belongs in the citation
    # line, not inside a multiple-choice option.
    text = re.sub(r"\s*\([A-Z][A-Za-z.&\s]+,\s*\d{4}[a-z]?\)", "", text)
    # Cut at the first sentence end; definitions are single sentences.
    text = re.split(r"(?<=[.!?])\s", text)[0].strip().rstrip(".")
    if len(text) < 25 or len(text) > 320:
        return None
    if BAD_DEFINITION_START.match(text):
        return None
    # Reject fragments carrying list markers, equations, or figure noise.
    if any(marker in text for marker in ("•", "|", "=", "$", "  ",
                                         "\u2264", "\u2265", "\u00d7")):
        return None
    if re.search(r"\b\d+\.\s", text):
        return None
    # An algebraic expression is not a usable multiple-choice option.
    if re.match(r"^[\d(]", text) or len(re.findall(r"\d", text)) > 4:
        return None
    return text


def _sentences(text: str) -> List[str]:
    body = re.sub(r"^\[[^\]]*\]\n", "", text)  # strip the heading prefix
    body = re.sub(r"\s+", " ", body)
    return [s.strip() for s in _SENTENCE_SPLIT.split(body) if s.strip()]


class ConceptExtractor:
    """Extract, score, and persist concept definitions."""

    def __init__(self, session=None):
        self.session = session or get_session()
        self._owns_session = session is None

    def extract_from_chunk(self, chunk: Chunk) -> List[Dict]:
        """Return candidate concepts found in one chunk."""
        found: List[Dict] = []
        in_definition_block = "(Definition)" in (chunk.section_title or "")

        for sentence in _sentences(chunk.content):
            parsed = self._parse_sentence(sentence)
            if parsed is None:
                continue
            term, glossary_term, definition = parsed
            # "Incentives An incentive" is an artefact of the heading running
            # into the sentence; the concept's name is the vocabulary term.
            display_term = term if term.lower() == glossary_term else glossary_term
            found.append(
                {
                    "term": display_term,
                    "canonical": glossary_term,
                    "definition": definition,
                    "topic": topic_for_term(glossary_term, chunk.topic),
                    "page_num": chunk.page_num,
                    "section_title": chunk.section_title,
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "extraction": "definition_block" if in_definition_block else "inline",
                }
            )
        return found

    @staticmethod
    def _parse_sentence(sentence: str):
        """Return (term, canonical term, definition) for a definitional sentence."""
        for pattern in (DEF_PATTERN, DEF_PATTERN_ALT, DEF_PATTERN_STATES,
                        DEF_PATTERN_TWO_GOODS):
            match = pattern.match(sentence)
            if not match:
                continue
            groups = match.groups()
            raw_term, raw_def = (groups[0], groups[-1])
            if TERM_BLOCKLIST.search(raw_term):
                continue
            term = _normalize_term(raw_term)
            if not term or term.lower() in STOP_TERMS or len(term) < 3:
                continue
            glossary_term = _glossary_match(term)
            if glossary_term is None:
                continue
            definition = _clean_definition(raw_def)
            if definition is None:
                continue
            if pattern is DEF_PATTERN_TWO_GOODS:
                # "complements when they are often consumed together" has a
                # dangling pronoun once the subject is dropped.
                definition = re.sub(
                    r"\bthey\b", "the two goods", definition, count=1
                )
            return term, glossary_term, definition
        return None

    def extract_all(self, document_id: int = None) -> int:
        """Extract concepts across chunks, de-duplicating by canonical term."""
        query = self.session.query(Chunk)
        if document_id:
            query = query.filter(Chunk.document_id == document_id)
            self.session.query(Concept).filter(
                Concept.document_id == document_id
            ).delete()
        else:
            self.session.query(Concept).delete()
        self.session.commit()

        best: Dict[str, Dict] = {}
        for chunk in query.all():
            for candidate in self.extract_from_chunk(chunk):
                key = candidate["canonical"]
                incumbent = best.get(key)
                if incumbent is None or self._score(candidate) > self._score(incumbent):
                    best[key] = candidate

        for candidate in best.values():
            self.session.add(
                Concept(
                    document_id=candidate["document_id"],
                    chunk_id=candidate["chunk_id"],
                    term=candidate["term"],
                    definition=candidate["definition"],
                    topic=candidate["topic"],
                    page_num=candidate["page_num"],
                    section_title=candidate["section_title"],
                    extraction=candidate["extraction"],
                )
            )
        self.session.commit()
        return len(best)

    @staticmethod
    def _score(candidate: Dict) -> float:
        """Prefer explicit Definition callouts and substantive wording."""
        score = 0.0
        if candidate["extraction"] == "definition_block":
            score += 10.0
        if candidate["topic"]:
            score += 2.0
        length = len(candidate["definition"])
        # Favour 60-200 characters: long enough to be a real definition,
        # short enough to read as a multiple-choice option.
        score += 3.0 if 60 <= length <= 200 else 0.0
        score += min(len(candidate["term"].split()), 3) * 0.5
        # A definition that opens with a determiner reads as a proper
        # "X is <a thing that...>" gloss rather than an aside about X.
        if re.match(r"^(the|a|an|any|when|anything|all)\b",
                    candidate["definition"], re.IGNORECASE):
            score += 4.0
        # A definition given in the section devoted to the term beats a
        # passing mention of it elsewhere.
        section = (candidate["section_title"] or "").lower()
        head = candidate["canonical"].split()[-1].rstrip("s")
        if head and head in section:
            score += 5.0
        return score

    def close(self) -> None:
        if self._owns_session:
            self.session.close()
