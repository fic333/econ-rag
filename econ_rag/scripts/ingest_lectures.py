"""Ingest every lecture PDF, embed it, assign topics, and mine concepts."""

from __future__ import annotations

import sys
from pathlib import Path

from econ_rag.config import settings
from econ_rag.database import Chunk, Concept, Document, get_session, init_db
from econ_rag.services.concepts import ConceptExtractor
from econ_rag.services.embeddings import EmbeddingService
from econ_rag.services.ingestor import DocumentIngestor


def main(directory: str = None) -> None:
    directory = Path(directory or settings.LECTURE_DIR)
    pdfs = sorted(directory.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {directory}")
        sys.exit(1)

    init_db()
    session = get_session()

    print(f"\nIngesting {len(pdfs)} document(s) from {directory}")
    ingestor = DocumentIngestor(session=session)
    for pdf in pdfs:
        ingestor.ingest_file(str(pdf), source_type="lecture")

    print("\nGenerating embeddings...")
    embedder = EmbeddingService(session=session)
    count = embedder.generate_embeddings()
    print(f"  + embedded {count} chunks")

    assigned = embedder.assign_missing_topics()
    print(f"  + topic-assigned {assigned} previously unlabeled chunks")

    print("\nExtracting concepts...")
    extractor = ConceptExtractor(session=session)
    concepts = extractor.extract_all()
    print(f"  + {concepts} concept definitions")

    docs = session.query(Document).count()
    chunks = session.query(Chunk).count()
    print(
        f"\nDone: {docs} documents, {chunks} chunks, "
        f"{session.query(Concept).count()} concepts."
    )
    session.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
