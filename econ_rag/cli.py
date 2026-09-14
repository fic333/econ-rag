"""Command-line interface for the economics RAG system."""

from __future__ import annotations

import click

from econ_rag.config import settings
from econ_rag.database import Chunk, Concept, Document, get_session, init_db
from econ_rag.services.concepts import ConceptExtractor
from econ_rag.services.embeddings import EmbeddingService
from econ_rag.services.ingestor import DocumentIngestor
from econ_rag.services.rag_engine import RAGEngine
from econ_rag.services.test_generator import InsufficientContentError, TestGenerator
from econ_rag.taxonomy import all_topics, topic_name


@click.group()
def cli() -> None:
    """Study, test, and search intro economics lecture material."""


@cli.command("init")
def init_command() -> None:
    """Create the database tables."""
    init_db()


@cli.command("ingest")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--source-type", default="lecture",
              type=click.Choice(["lecture", "textbook", "paper", "case_study"]))
@click.option("--sequence", type=int, default=None,
              help="Lecture or chapter number; inferred from the filename if omitted.")
def ingest_command(paths, source_type, sequence) -> None:
    """Ingest one or more documents, then embed and index them."""
    if not paths:
        raise click.UsageError("Give at least one file path.")
    init_db()
    session = get_session()
    ingestor = DocumentIngestor(session=session)
    for path in paths:
        ingestor.ingest_file(path, source_type=source_type, sequence=sequence)

    embedder = EmbeddingService(session=session)
    click.echo(f"Embedded {embedder.generate_embeddings()} chunks")
    click.echo(f"Topic-assigned {embedder.assign_missing_topics()} chunks")
    click.echo(f"Extracted {ConceptExtractor(session=session).extract_all()} concepts")
    session.close()


@cli.command("status")
def status_command() -> None:
    """Show what is currently in the knowledge base."""
    session = get_session()
    click.echo(f"Database: {settings.DATABASE_URL}")
    click.echo(
        f"{session.query(Document).count()} documents, "
        f"{session.query(Chunk).count()} chunks, "
        f"{session.query(Concept).count()} concepts"
    )
    for document in session.query(Document).order_by(Document.sequence).all():
        click.echo(
            f"  {document.citation:12} {document.total_pages or '?':>3}pp  "
            f"{len(document.chunks):>3} chunks  {document.name}"
        )
    session.close()


@cli.command("topics")
def topics_command() -> None:
    """List the topic taxonomy."""
    session = get_session()
    for topic in all_topics():
        count = session.query(Chunk).filter(Chunk.topic == topic["slug"]).count()
        lectures = ", ".join(str(x) for x in topic["lectures"]) or "-"
        click.echo(f"  {topic['slug']:22} {count:>3} passages  (lectures {lectures})")
    session.close()


@cli.command("ask")
@click.argument("question")
@click.option("--top-k", default=5, show_default=True)
@click.option("--topic", "topics", multiple=True, help="Restrict to these topic slugs.")
def ask_command(question, top_k, topics) -> None:
    """Answer a question from the lecture notes."""
    engine = RAGEngine()
    result = engine.answer(question, top_k=top_k, topics=list(topics) or None)
    click.echo(f"\n{result['answer']}\n")
    if result["concepts"]:
        click.echo("Definitions:")
        for concept in result["concepts"]:
            click.echo(f"  {concept['term']}: {concept['definition']}")
            click.echo(f"    {concept['citation']}")
    click.echo("\nSources:")
    for source in result["sources"]:
        click.echo(f"  [{source['score']:.3f}] {source['citation']}")
    engine.close()


@cli.command("quiz")
@click.option("--topic", "topics", multiple=True, help="Topic slug; repeatable.")
@click.option("--lecture", "lectures", multiple=True, type=int, help="Lecture number; repeatable.")
@click.option("-n", "--num-questions", default=10, show_default=True)
@click.option("--seed", type=int, default=None)
@click.option("--key/--no-key", default=False, help="Print the answer key and explanations.")
@click.option("--user", "user_id", default="default_user", show_default=True)
def quiz_command(topics, lectures, num_questions, seed, key, user_id) -> None:
    """Generate a quiz and print it."""
    generator = TestGenerator()
    try:
        test_id = generator.create_test(
            user_id=user_id,
            mode="teaching" if key else "self_test",
            topics=list(topics) or None,
            lectures=list(lectures) or None,
            num_questions=num_questions,
            seed=seed,
        )
    except InsufficientContentError as error:
        raise click.ClickException(str(error))

    test = generator.get_test(test_id, include_answers=True)
    scope = ", ".join(test["topic_names"]) or (
        "Lectures " + ", ".join(str(x) for x in lectures) if lectures else "All topics"
    )
    click.echo(f"\nQuiz #{test_id} - {scope}  ({test['num_questions']} questions)\n")
    for question in test["questions"]:
        click.echo(f"{question['question_num']}. {question['question_text']}")
        for letter in ("a", "b", "c", "d"):
            click.echo(f"     {letter}) {question['options'][letter]}")
        if key:
            click.echo(f"   ANSWER: {question['correct_option'].upper()}")
            click.echo(f"   {question['explanation']}")
            click.echo(f"   Source: {question['source_citation']}")
        click.echo("")
    if not key:
        click.echo(f"Answer key:  econ-rag key {test_id}")
    generator.close()


@cli.command("key")
@click.argument("test_id", type=int)
def key_command(test_id) -> None:
    """Print the answer key for a previously generated quiz."""
    generator = TestGenerator()
    test = generator.get_test(test_id, include_answers=True)
    if test is None:
        raise click.ClickException(f"No quiz #{test_id}")
    for question in test["questions"]:
        click.echo(
            f"{question['question_num']}. {question['correct_option'].upper()} - "
            f"{question['explanation']}"
        )
        click.echo(f"   Source: {question['source_citation']}")
    generator.close()


@cli.command("progress")
@click.option("--user", "user_id", default="default_user", show_default=True)
def progress_command(user_id) -> None:
    """Show per-topic performance."""
    generator = TestGenerator()
    data = generator.progress(user_id)
    if not data["questions_answered"]:
        click.echo("No completed quizzes yet.")
        return
    click.echo(
        f"{data['tests_completed']} quizzes, {data['questions_answered']} questions, "
        f"{data['overall_accuracy']}% overall"
    )
    for topic in data["topics"]:
        click.echo(
            f"  {topic['topic_name']:44} {topic['accuracy']:>5}%  "
            f"({topic['correct']}/{topic['attempted']})"
        )
    generator.close()


@cli.command("glossary")
@click.option("--topic", default=None, help="Restrict to one topic slug.")
def glossary_command(topic) -> None:
    """Print the extracted course glossary."""
    session = get_session()
    query = session.query(Concept)
    if topic:
        query = query.filter(Concept.topic == topic)
    for concept in query.order_by(Concept.term).all():
        click.echo(f"{concept.term} [{topic_name(concept.topic)}]")
        click.echo(f"    {concept.definition}")
        click.echo(f"    {concept.citation}")
    session.close()


@cli.command("serve")
def serve_command() -> None:
    """Run the web interface."""
    from web.app import main

    main()


if __name__ == "__main__":
    cli()
