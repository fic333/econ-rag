"""CLI commands for flashcard management."""

import click
from econ_rag.services.flashcard_generator import FlashcardGenerator


@click.group()
def flashcards():
    """Flashcard management commands."""
    pass


@flashcards.command()
@click.option("--name", prompt="Flashcard set name", help="Name of the set")
@click.option("--topic", multiple=True, help="Topics to include")
@click.option("--lecture", type=int, multiple=True, help="Lecture numbers")
def create(name, topic, lecture):
    """Create a new flashcard set."""
    gen = FlashcardGenerator()
    topics = list(topic) if topic else None
    lectures = list(lecture) if lecture else None
    
    s = gen.create_set(
        user_id="default_user",
        name=name,
        topics=topics,
        lectures=lectures,
    )
    
    click.echo(f"✅ Flashcard set created: {s.name}")
    click.echo(f"   Cards: {s.card_count}")
    click.echo(f"   Set ID: {s.id}")
    gen.close()


@flashcards.command()
def list():
    """List all flashcard sets."""
    gen = FlashcardGenerator()
    sets = gen.list_sets("default_user")
    
    if not sets:
        click.echo("No flashcard sets yet.")
        return
    
    click.echo(f"\n📚 Flashcard Sets ({len(sets)}):\n")
    for s in sets:
        click.echo(f"  {s.name} (ID: {s.id})")
        click.echo(f"    Cards: {s.card_count}")
        click.echo(f"    Created: {s.created_date.strftime('%Y-%m-%d %H:%M')}\n")
    
    gen.close()


@flashcards.command()
@click.option("--set-id", type=int, prompt="Flashcard set ID")
def view(set_id):
    """View flashcards in a set."""
    gen = FlashcardGenerator()
    s = gen.get_set(set_id)
    
    if not s:
        click.echo(f"❌ Set {set_id} not found")
        return
    
    click.echo(f"\n📚 {s.name} ({s.card_count} cards)\n")
    for card in s.cards:
        click.echo(f"Card {card.card_num}: [{card.card_type}]")
        click.echo(f"  Front: {card.front[:80]}...")
        click.echo(f"  Back:  {card.back[:80]}...")
        if card.citation:
            click.echo(f"  Source: {card.citation}")
        click.echo()
    
    gen.close()
