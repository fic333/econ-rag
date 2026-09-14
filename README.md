# Intro Economics RAG Learning System

A retrieval-augmented study system for **ECON 154: The Global Economy — Trade,
Finance, and Policy** (Bates College, Prof. Daniel Riera-Crichton, Fall 2026).

It ingests the course lecture notes, indexes them for semantic search, and
generates cited multiple-choice quizzes for three audiences: students
studying, students self-testing, and instructors preparing assessments.

Everything runs locally. There are no API keys and no per-query costs —
embeddings are computed on-device with `sentence-transformers`, and the whole
corpus lives in one SQLite file.

---

## What it does

| Capability | Detail |
|---|---|
| **Ingestion** | Structure-aware PDF extraction: strips running headers, page numbers, and front-matter tables of contents; splits on numbered LaTeX section headings so every passage keeps an exact citation. |
| **Semantic search** | 384-dimension `all-MiniLM-L6-v2` embeddings over 130 passages, filterable by topic or lecture. |
| **Q&A** | Extractive answers assembled from the highest-scoring sentences in the retrieved passages, each tagged with its lecture. |
| **Glossary** | 22 term/definition pairs mined from the lecture text, each traceable to a section and page. |
| **Quiz generation** | 10+ unique questions for every one of the 18 topics, mixing recall with applied reasoning and calculation. |
| **Grading & progress** | Automatic scoring, per-question explanations with sources, and rolling per-topic accuracy. |
| **Teaching prep** | Question banks with answer keys, exportable as Markdown. |

## Course coverage

| Lecture | Topic | Pages | Passages |
|---|---|---|---|
| 1 | What Is Economics, and Why Study the Global Economy? | 7 | 11 |
| 2 | Scarcity, Incentives, Marginal Reasoning, Evidence, and Models | 15 | 18 |
| 3 | Markets and Prices I: Demand, Willingness to Pay, Consumer Behavior | 17 | 27 |
| 4 | Markets and Prices II: Firms in Markets — Costs and Supply | 26 | 43 |
| 5 | Markets in Action: How Prices Coordinate Buyers and Sellers | 22 | 31 |

Those five lectures are indexed under 18 topics, from `what-is-economics`
through `comparative-statics`. Run `econ-rag topics` for the full list.

## How questions are generated

Three sources are blended so a quiz tests more than recall:

1. **Concept questions** (`definition`, `term_id`) are built from definitions
   mined out of the lecture text. Both the correct answer and its citation are
   verbatim from the notes; distractors are other real definitions, preferring
   same-topic ones so the options are genuinely confusable.
2. **Cloze questions** blank a key term out of a lecture sentence. Figure
   labels, flattened tables, and enumerations are filtered out, so what remains
   reads as prose and has one defensible answer.
3. **Template generators** cover the procedural skills that narrative text
   cannot test: solving `QD = a − bP` against `QS = c + dP` for equilibrium,
   finding a shortage or surplus at an off-equilibrium price, predicting
   comparative statics after a shock, separating a shift from a movement,
   computing accounting versus economic profit, and so on. Numbers and
   scenarios vary between quizzes; the reasoning mirrors the worked examples in
   the lectures, and each template cites the section it comes from.

Every question carries an explanation and a lecture citation. Quizzes are
deduplicated both by rendered text and by underlying material, so one term is
not tested twice from two angles in the same quiz.

Topic and lecture filters propagate all the way down: a Lecture 3 quiz never
cites Lecture 4, and a `demand-shifts` quiz never serves a supply scenario.

## Quick start

```bash
cd ~/Documents/projects/econ-rag
./setup.sh
./.venv/bin/econ-rag serve
```

Then open <http://127.0.0.1:8100>. See [GETTING_STARTED.md](GETTING_STARTED.md)
for the full walkthrough.

## CLI

```bash
econ-rag status                                  # what is indexed
econ-rag topics                                  # the topic taxonomy
econ-rag ask "why does a shortage raise price?"  # cited answer
econ-rag quiz --topic equilibrium -n 10          # practice quiz
econ-rag quiz --lecture 3 -n 10 --key            # question bank with answers
econ-rag progress --user michael                 # per-topic accuracy
econ-rag glossary                                # extracted definitions
econ-rag serve                                   # web interface
```

## Adding more material

The schema is source-agnostic: `Document.source_type` distinguishes lectures
from textbooks, papers, and case studies, and the topic taxonomy is
subject-level rather than lecture-level, so a textbook chapter on demand lands
under the same `demand` topic as Lecture 3.

```bash
econ-rag ingest ~/Downloads/mankiw_ch4.pdf --source-type textbook --sequence 4
```

Ingestion re-embeds only what is new, assigns topics (by section heading where
available, otherwise by embedding similarity), and re-mines the glossary. New
material immediately widens search, Q&A, and the cloze question pool. To extend
the taxonomy itself, add a `Topic` to `econ_rag/taxonomy.py`.

## Layout

```
econ_rag/
  config.py            settings (paths, model, chunk sizes)
  database.py          SQLAlchemy models
  taxonomy.py          18-topic economics taxonomy + section-title mapping
  cli.py               command-line interface
  services/
    ingestor.py        PDF -> cleaned, section-aware, citable chunks
    embeddings.py      embedding generation, search, topic assignment
    concepts.py        term/definition mining
    question_banks.py  template question generators
    test_generator.py  quiz assembly, grading, progress
    rag_engine.py      retrieval and extractive answering
  scripts/
    ingest_lectures.py end-to-end ingestion
web/
  app.py               FastAPI server
  static/index.html    web interface
data/lectures/         source PDFs
```

## Stack

Python 3.11 · FastAPI · SQLAlchemy + SQLite · sentence-transformers
(`all-MiniLM-L6-v2`) · pypdf · plain HTML/JS (no build step)
