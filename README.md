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

6. **Folder structure finalized for Step 1 (foundation):**
   ```
   src/
   ├── api/
   ├── config/
   ├── schemas/
   │   ├── answer.py
   │   ├── chunk.py
   │   └── retrieval.py
   ├── core/
   │   ├── ingestion.py
   │   ├── chunking.py
   │   ├── embeddings.py
   │   ├── vectorstore.py
   │   ├── retrieval.py
   │   ├── generation.py
   │   └── pipeline.py
   └── utils/
       └── exceptions.py
   ```
   `core/*.py` files and `schemas/` contents are placeholders — Steps 4+
   fill in real code. `core/tools/` and `tests/` from the original
   template were removed outright (not just emptied): `tools/` doesn't
   fit RAG's fixed pipeline sequence (see Design Decision 13), and no
   automated test suite is used at this stage (see Setup, item 2).

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

7. **API surface — 5 endpoints:**
   - `POST /documents` — upload a PDF; returns immediately with
     `document_id` and `status: "processing"`; chunking/embedding happens
     as a background task, not synchronously in this request
   - `GET /documents/{document_id}` — status check (polling), returns
     `status: "processing" | "ready" | "failed"`
   - `GET /documents` — lists all uploaded documents (id, filename,
     status) — needed so a client can discover valid `document_id` values
     to use for scoping
   - `POST /search` — debug/inspection endpoint; given a query, returns
     matching chunks with chunk text, source document id/name, page
     number, and similarity score. Optional `document_id` to scope to one
     document.
   - `POST /answer` — given a query (and optional `document_id` to scope
     to a single document, otherwise searches the whole corpus), returns
     the answer, an `answered: bool` field, and the `sources` used —
     sources are populated even when `answered: false`, for both
     rejection paths (see point 9), so retrieval behavior stays
     inspectable rather than a black box

8. **Answer scoping is single-document, not multi-select:** a request can
   optionally include one `document_id` to restrict the answer to that
   document; omitting it searches the entire corpus. Deliberately binary
   (one document vs. all), not an arbitrary subset — matches the actual
   use case, not built more flexible than needed.

9. **Relevance rejection is two-layer, and both layers surface their
   findings in the response, not just internally:**
   - Retrieval-side: a chunk-level distance threshold as a cheap
     pre-filter for obviously unrelated queries. Chunk-level, not
     document-level — each chunk has its own embedding and its own
     distance from the query. Threshold value intentionally undetermined
     until Step 9 (retrieval) produces real distance scores to tune
     against.
   - Generation-side: the LLM is instructed to answer only from provided
     context and say so explicitly if it can't. This is the real
     relevance judge — distance measures topical closeness, not whether
     retrieved content actually answers the question.
   - Sources are returned in the response for both rejection cases (empty
     list if nothing crossed the retrieval threshold; populated-but-
     unhelpful list if generation rejected despite retrieval finding
     something plausible) — specifically so retrieval behavior can be
     verified (low scores, unrelated chunk content) rather than trusted
     blindly.

10. **Embeddings: Groq's `nomic-embed-text-v1_5`**, via the same
    OpenAI-compatible client and API key already used for generation — no
    local embedding model, no second provider/API key to manage.

11. **Generation model: also Groq** (same provider as embeddings, for the
    same reason — one client, one key). Specific model starts as
    `llama-3.1-8b-instant` (fast, most generous free-tier limits), with
    the explicit caveat that this is a starting point, not a final
    choice — smaller/faster models are more prone to confidently
    answering from weak evidence instead of correctly refusing, which
    matters more here than in prior projects, so this will be
    re-evaluated once Step 10 (generation) produces real output to judge
    against, not decided from raw capability alone.

12. **Background processing: FastAPI `BackgroundTasks` for v1, not a
    task queue (Celery/Redis).** Reasoning: this is a solo local learning
    project, not a deployed multi-user service — losing an in-progress
    job on a server restart during local development is a trivial cost
    (re-upload), not worth the added infrastructure (a message broker, a
    separate worker process) that teaches nothing about RAG itself.
    Revisit only if this project is ever actually deployed under real
    traffic.

13. **Folder structure reflects the RAG pipeline's fixed sequence, not
    research-agent's pluggable-tool pattern.** research-agent's
    `core/tools/` suited an agent choosing which tool to call and when;
    RAG here is a fixed sequence (ingest → chunk → embed/store → retrieve
    → generate → orchestrate), always in that order, so `core/` modules
    map directly to roadmap steps instead (`ingestion.py`, `chunking.py`,
    `embeddings.py`, `vectorstore.py`, `retrieval.py`, `generation.py`,
    `pipeline.py`). `tools/` and `tests/` (no automated test suites, see
    above) were dropped from the template. Custom exceptions live in
    `src/utils/exceptions.py`, matching research-agent's precedent
    despite being cross-cutting rather than a generic utility — confirmed
    deliberately, not by default.

14. Considered validating configured model names against Groq's live
    `/v1/models` list at startup — deferred; no consumer exists until
    Step 12 (API/lifespan). Revisit if a deprecated-model issue recurs.

## Roadmap

| Step | Branch | Content |
|---|---|---|
| 1 | feature/step-1-foundation | Folder structure, dependency file, git/GitHub, .gitignore, README skeleton |
| 2 | feature/step-2-config | Pydantic Settings |
| 3 | feature/step-3-logger | Structured logging setup |
| 4 | feature/step-4-exceptions | Custom exception hierarchy (src/utils/exceptions.py) |
| 5 | feature/step-5-schemas | Pydantic data models |
| 6 | feature/step-6-ingestion | PDF text extraction |
| 7 | feature/step-7-chunking | Chunking |
| 8 | feature/step-8-vectorstore | Embedding + ChromaDB storage |
| 9 | feature/step-9-retrieval | Retrieval |
| 10 | feature/step-10-generation | LLM generation |
| 11 | feature/step-11-orchestration | Pipeline wiring 6–10 |
| 12 | feature/step-12-api | FastAPI interface |
| 13 | feature/step-13-docker | Containerize |
| 14 | feature/step-14-polish | README finalize |
