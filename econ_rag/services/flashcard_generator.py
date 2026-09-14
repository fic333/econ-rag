"""Flashcard generation from concepts, definitions, and passages."""

from typing import List, Optional
from econ_rag.database import (
    Flashcard,
    FlashcardSet,
    Concept,
    Chunk,
    get_session,
)


class FlashcardGenerator:
    """Generate flashcard sets from course material."""

    def __init__(self):
        self.session = get_session()

    def create_set(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        topics: Optional[List[str]] = None,
        lectures: Optional[List[int]] = None,
    ) -> FlashcardSet:
        """Create a new flashcard set."""
        
        flashcard_set = FlashcardSet(
            user_id=user_id,
            name=name,
            description=description,
            topics=topics,
            lectures=lectures,
        )
        self.session.add(flashcard_set)
        self.session.flush()
        
        # Generate flashcards
        self._generate_flashcards(flashcard_set, topics, lectures)
        
        flashcard_set.card_count = len(flashcard_set.cards)
        self.session.commit()
        return flashcard_set

    def _generate_flashcards(
        self,
        flashcard_set: FlashcardSet,
        topics: Optional[List[str]] = None,
        lectures: Optional[List[int]] = None,
    ) -> None:
        """Generate flashcards from concepts and passages."""
        
        card_num = 1
        seen = set()

        # Query concepts based on filters
        query = self.session.query(Concept)
        if topics:
            query = query.filter(Concept.topic.in_(topics))
        if lectures:
            query = query.join(Concept.document).filter(
                Concept.document.sequence.in_(lectures)
            )

        concepts = query.all()

        # Create definition flashcards from concepts
        for concept in concepts:
            # Skip if we've already added this term
            if concept.term.lower() in seen:
                continue
            seen.add(concept.term.lower())

            card = Flashcard(
                set_id=flashcard_set.id,
                card_num=card_num,
                front=concept.term,
                back=concept.definition,
                source_concept_id=concept.id,
                citation=concept.citation,
                topic=concept.topic,
                card_type="definition",
            )
            self.session.add(card)
            card_num += 1

        # Cloze cards disabled temporarily—definition cards work better
        # (Cloze generation was including heading text and creating confusing blanks)
        # Re-enable with improved sentence filtering if needed

    def _generate_cloze_cards(
        self,
        set_id: int,
        topics: Optional[List[str]],
        lectures: Optional[List[int]],
        start_num: int = 1,
    ) -> List[Flashcard]:
        """Generate cloze (fill-in-the-blank) flashcards from passages."""
        cards = []

        # Query chunks
        query = self.session.query(Chunk)
        if topics:
            query = query.filter(Chunk.topic.in_(topics))
        if lectures:
            query = query.join(Chunk.document).filter(
                Chunk.document.sequence.in_(lectures)
            )

        chunks = query.limit(20).all()

        # Simple cloze: blank out key terms in sentences
        import re
        for chunk in chunks:
            sentences = chunk.content.split(". ")
            for i, sentence in enumerate(sentences[:3]):
                # Skip very short sentences
                if len(sentence) < 30:
                    continue

                # Find concepts in this sentence and create a cloze card
                for concept in self.session.query(Concept).filter(
                    Concept.chunk_id == chunk.id
                ).all():
                    term_lower = concept.term.lower()
                    if term_lower not in sentence.lower():
                        continue

                    # Skip if sentence starts with the term (likely a heading/label)
                    if sentence.strip().lower().startswith(term_lower):
                        continue

                    # Blank only the FIRST occurrence (case-insensitive)
                    pattern = re.compile(re.escape(concept.term), re.IGNORECASE)
                    blanked = pattern.sub("_" * len(concept.term), sentence, count=1)

                    card = Flashcard(
                        set_id=set_id,
                        card_num=start_num + len(cards),
                        front=f"{blanked.strip()}",
                        back=concept.term,
                        source_chunk_id=chunk.id,
                        citation=chunk.citation,
                        topic=chunk.topic,
                        card_type="cloze",
                    )
                    cards.append(card)
                    break

        return cards[:20]

    def get_set(self, set_id: int) -> FlashcardSet:
        """Retrieve a flashcard set with all cards."""
        return self.session.query(FlashcardSet).filter(
            FlashcardSet.id == set_id
        ).first()

    def list_sets(self, user_id: str) -> List[FlashcardSet]:
        """List all flashcard sets for a user."""
        return self.session.query(FlashcardSet).filter(
            FlashcardSet.user_id == user_id
        ).order_by(FlashcardSet.created_date.desc()).all()

    def delete_set(self, set_id: int) -> bool:
        """Delete a flashcard set."""
        s = self.session.query(FlashcardSet).filter(
            FlashcardSet.id == set_id
        ).first()
        if s:
            self.session.delete(s)
            self.session.commit()
            return True
        return False

    def close(self):
        """Close database session."""
        self.session.close()
