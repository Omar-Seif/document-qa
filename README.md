# document-qa

Nothing has been implemented yet — this document records the setup process
and design decisions made during planning, before any code exists.

## Setup

1. **Claude Code installed** via terminal (PowerShell native installer),
   authenticated with a Claude Pro subscription.

2. **CLAUDE.md created**, defining:
   - a role boundary — design/scope decisions happen in a separate chat
     conversation; Claude Code implements and enforces engineering-quality
     standards, but does not re-decide design
   - non-negotiables — type hints, docstrings, custom exceptions,
     structured logging, no hardcoded values, Pydantic models,
     FastAPI + Pydantic default stack, dependency injection, SOLID/DRY/YAGNI
   - no automated test suites (pytest) at this stage — verification via
     real command output instead
   - a git workflow — branch per roadmap step, README updated per step

3. **Discovered CLAUDE.md text alone does not hard-enforce anything** —
   Claude Code's auto permission mode treats CLAUDE.md as context, not a
   binding rule, so an explicit git-commit instruction in it was not
   sufficient on its own. Fixed by adding `.claude/settings.json` with an
   "ask" permission rule for `Bash(git commit*)` and `Bash(git push*)`,
   which forces a hard confirmation prompt regardless of the auto-mode
   classifier's own risk assessment. Verified working after discovering
   permission settings only load at session start, not live — required a
   full session restart to take effect.

4. **VS Code extension installed** as a second interface to the same
   underlying Claude Code engine/config (reads the same CLAUDE.md and
   `.claude/settings.json` automatically).

5. **Migrated dependency management from pip + conda to uv.** Reasoning:
   `pyproject.toml` (already present from the project template) is uv's
   native format; avoids maintaining two package managers; faster
   dependency resolution. Discovered during migration that ChromaDB does
   not support Python 3.13 (documented upstream build failures), so
   pinned the project to Python 3.12 via `uv python pin` — recorded in
   `.python-version`, committed so this is deterministic for any future
   clone. `requirements.txt` was removed (superseded by `pyproject.toml` +
   `uv.lock`; it was also already broken — version pins were empty).
   Conda environment removed manually after uv's environment was verified
   working.

## Design Decisions

1. **Scope: multiple PDFs, not single-PDF-per-session.** The system
   ingests a corpus of multiple PDFs together; retrieval searches across
   all of them for relevance, not one document picked upfront.

2. **v1 is one-shot Q&A; conversational (multi-turn, session memory) is
   explicitly deferred to v2.** Reasoning: conversational/session-state
   handling is a separate concern layered on top of retrieval, whereas
   multi-PDF retrieval tests core RAG mechanics directly — deferring
   conversation lets embeddings/retrieval be learned in isolation first.

3. **Ingestion happens once, ahead of time** — PDFs are uploaded and
   processed (chunked, embedded, stored) up front; queries afterward
   search the already-built vector store, not re-ingesting per request.

4. **Chunk metadata requirement:** each chunk must carry `source_document`
   and `page_number` — needed both to discriminate between PDFs in a
   multi-document corpus, and to support citation-quality answers (e.g.
   "per page 4 of the vendor contract" rather than an unattributed answer).

5. **Irrelevance handling is hybrid, two layers:**
   - Retrieval-side: a chunk-level distance threshold as a cheap
     pre-filter, rejecting queries that are obviously unrelated to the
     corpus before an LLM call is made. The actual threshold value is
     deliberately undetermined yet — distance is only meaningful relative
     to the specific embedding model and documents in use, so it will be
     tuned empirically once real retrieval output exists (Step 8), not
     guessed now.
   - Generation-side: the LLM is instructed to answer only from the
     provided context and explicitly say it doesn't know if the retrieved
     context doesn't actually answer the question — this is the real
     relevance judge, since distance measures topical closeness, not
     whether retrieved content actually answers the query.

6. **Default stack: FastAPI + Pydantic (Settings + Models)** for all
   projects going forward, with equal emphasis on software engineering
   principles alongside AI/RAG concepts.
