# Getting Started

## Setup (one time)

```bash
cd ~/Documents/projects/econ-rag
./setup.sh
```

This creates a Python virtualenv, installs dependencies, and ingests the five
lecture PDFs from `data/lectures/`. (The first run downloads PyTorch, which
takes a minute or two.)

If you are reinstalling, `rm -rf .venv econ_rag.db` first.

## Web interface

```bash
./.venv/bin/econ-rag serve
```

Open <http://127.0.0.1:8100> in your browser.

You'll see:

- **Take a quiz**: Select topics and/or lectures, then generate a 10-question
  practice quiz. Submit to see your score, detailed explanations, and the
  lecture sources for each question.
- **Ask the notes**: Ask any economics question and get a cited answer from the
  lecture notes, plus the passages used and related definitions.
- **Teaching prep**: Generate a question bank with the answer key visible —
  ready to copy into an assignment or exam. Export as Markdown.
- **History**: View all quizzes you have taken.
- **Progress**: Per-topic accuracy, weakest areas highlighted.
- **Glossary**: All 22 defined terms extracted from the lectures, with
  sources.

## Command-line interface

- `econ-rag quiz --topic equilibrium -n 10` — Generate a 10-question practice
  quiz on equilibrium.
- `econ-rag quiz --lecture 3 -n 10 --key` — Generate a question bank from
  Lecture 3, showing the answer key and explanations.
- `econ-rag ask "Why does a shortage put upward pressure on price?"` — Get an
  answer from the lecture notes.
- `econ-rag progress` — Show your per-topic accuracy across all completed
  quizzes.
- `econ-rag glossary --topic demand` — Show all defined terms tagged with
  `demand` topic.
- `econ-rag status` — Show what is indexed: lectures, chunks, concepts, topics.
- `econ-rag topics` — List the 18 topics with how many passages support each.

## Adding more lecture PDFs

If you ingest a new lecture PDF, it will be chunked, embedded, and immediately
available for search and quiz generation. For example:

```bash
./.venv/bin/econ-rag ingest ~/Downloads/lecture06_notes.pdf --sequence 6
```

The ingestor extracts text from PDFs, recognizes numbered section headings
(§1.1, §2, etc.) and strips running headers and page numbers. Each chunk keeps
an exact citation: `Lecture 6, §3 Title, p. 12`.

## Three use modes

### 1. **Student studying**
- Practice mode: try quizzes on specific topics while you study.
- Get immediate feedback with explanations and lecture citations.
- See your progress dashboard to identify weak areas.

### 2. **Self-testing** 
- Generate a fresh quiz each time you want to test your understanding.
- Quizzes pull from the whole course or from specific topics.
- Track your scores across multiple attempts to see improvement.

### 3. **Teaching prep**
- Generate a question bank with the full answer key.
- Questions are uniquely drawn from the lecture material and span multiple
  question types.
- Export as Markdown, then copy into assignments or exams.

## Extending the system

The database schema is flexible:

- **Add more textbook chapters**: ingest a textbook chapter PDF with
  `--source-type textbook`, and it will be available for search and quiz
  generation under the same topics as the lectures.
- **Add research papers**: ingest a paper as `--source-type paper` to extend
  the knowledge base.
- **Customize the topic taxonomy**: Edit `econ_rag/taxonomy.py` to add topics,
  refine keywords, or map section headings to topics.

The system is designed to scale: adding material does not require retraining,
only re-embedding new chunks and re-mining new definitions.

## Troubleshooting

**Q: The server says "port 8100 already in use"**
A: Another instance is running. Kill it: `pkill -f "uvicorn web.app:app"`

**Q: Quizzes look repetitive**
A: Each topic has a finite question pool (scenarios, definitions from lectures,
and cloze extractions from the text). Smaller topics may run through them in
repeated quizzes. Use a different topic or wait for more lecture material to
be ingested.

**Q: A question is incorrect**
A: Every question is cited to its source. If the question is wrong, it's
sourcing a mistake in the material or a mis-extraction. Report it to the
instructor.

## Architecture

For the curious:

- **Ingestor**: Extracts text from PDFs page by page, strips running headers,
  recognizes numbered section headings, and splits on section boundaries so
  chunks stay within topics.
- **Embeddings**: All 130 passages are encoded with `sentence-transformers`
  (all-MiniLM-L6-v2, 384 dimensions) and stored in the SQLite database. Search
  uses cosine similarity.
- **Concepts**: Mined via regex patterns matching `<term> is <definition>`
  sentences, then validated against a course glossary. Both correct answers and
  citations come straight from the text.
- **Questions**: Mixed from three sources: concept recall (mined definitions),
  cloze (key terms blanked from sentences), and templates (procedural skills
  like solving for equilibrium).
- **Database**: One SQLite file with seven tables: documents, chunks,
  concepts, tests, test questions, topic progress, and query history.
- **Web**: FastAPI + vanilla HTML/JS, no build step, no client-side framework.
