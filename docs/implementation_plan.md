# Phase-wise Implementation Plan: Mutual Fund FAQ Assistant (RAG)

> Derived from [architecture.md](architecture.md). Each phase produces a verifiable deliverable and ends with a validation checkpoint.

---

## Phase 0: Project Setup & Infrastructure

**Goal**: Initialize the project skeleton, configure dependencies, and validate that all infrastructure pieces connect.

### Tasks

| #    | Task                                | Files                                | Details                                                                                                                                                                                                        |
| ---- | ----------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.1  | Create project directory structure  | All dirs per §5.1 of architecture.md | `app/`, `core/`, `data/raw/`, `data/processed/`, `scripts/`, `chroma_db/`, `.github/workflows/`, `prompts/`, `config/`, `tests/`                                                                               |
| 0.2  | Create `requirements.txt`           | `requirements.txt`                   | streamlit, langchain, langchain-groq, langchain-community, chromadb, beautifulsoup4, requests, sentence-transformers, python-dotenv, pytest                                                                    |
| 0.3  | Create `config/settings.py`         | `config/settings.py`                 | All tunable parameters from §7 of architecture.md (GROQ_MODEL, EMBEDDING_MODEL=BGE, CHUNK_SIZE, RETRIEVAL_TOP_K, etc.)                                                                                         |
| 0.4  | Create `.env.example`               | `config/.env.example`                | GROQ_API_KEY placeholder                                                                                                                                                                                       |
| 0.5  | Create `.gitignore`                 | `.gitignore`                         | Exclude `.env`, `__pycache__/`; NOTE: `chroma_db/` and `data/raw/` NOT excluded — these are committed by GitHub Actions after daily ingestion                                                                  |
| 0.6  | Create `.env` (local only)          | `.env`                               | Actual API key — not committed                                                                                                                                                                                 |
| 0.7  | Install dependencies and verify     | -                                    | `pip install -r requirements.txt` → confirm all packages importable                                                                                                                                            |
| 0.8  | Verify Groq API connectivity        | `config/settings.py`                 | Test a simple chat completion call with Groq (Llama 3.3 70B)                                                                                                                                                   |
| 0.9  | Verify ChromaDB persistence         | -                                    | Create a test collection, insert a doc, persist, reload — confirm roundtrip works                                                                                                                              |
| 0.10 | Create GitHub Actions workflow file | `.github/workflows/ingest.yml`       | Daily cron at 10:30 AM IST (`0 5 * * *` UTC); `workflow_dispatch` for manual trigger; steps: checkout → setup Python → install deps → run ingest.py → commit chroma_db/ to repo; GROQ_API_KEY as GitHub secret |

### Deliverable

- Complete project skeleton with verified dependency installation and API connectivity

### Validation Checkpoint

- `python -c "import streamlit, langchain, chromadb, sentence_transformers"` succeeds
- BGE embedding model loads and produces 384-dim vectors
- Groq chat completion returns a non-empty string
- ChromaDB persist + reload roundtrip works
- GitHub Actions workflow file created and syntax validated (YAML lint)
- GROQ_API_KEY configured as GitHub repository secret

---

## Phase 1: Source Registry & Data Pipeline

**Goal**: Build the offline ingestion pipeline — from source URLs to vector store.

### Tasks

| #    | Task                                          | Files                         | Details                                                                                                                                   |
| ---- | --------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1  | Create `data/sources.json`                    | `data/sources.json`           | Full 5-source registry per §8 of architecture.md (5 Groww HDFC URLs with id, url, type, scheme, category, format, title)                  |
| 1.2  | Validate source URLs reachability             | `scripts/validate_sources.py` | Script that checks each URL returns HTTP 200; log failures; update `sources.json` with actual working URLs                                |
| 1.3  | Build HTML scraper                            | `core/scraper.py` (new)       | BeautifulSoup-based scraper: fetch HTML, strip nav/ads/footers, extract main content text, return `Document` with metadata                |
| 1.4  | Build Groww page scraper                      | `core/scraper.py` (extended)  | BeautifulSoup-based: fetch Groww HTML pages, extract fund details (metrics, riskometer, exit load, etc.), return `Document` with metadata |
| 1.5  | Build chunker module                          | `core/chunker.py` (new)       | LangChain `RecursiveCharacterTextSplitter` with params from config (chunk_size=500, overlap=100); propagate metadata to each chunk        |
| 1.6  | Build embedding + ChromaDB storage module     | `core/embedder.py` (new)      | BGE `bge-small-en-v1.5` embedder via HuggingFace; ChromaDB persistent collection `mutual_fund_faq`; store chunks + embeddings + metadata  |
| 1.7  | Build full ingestion pipeline script          | `scripts/ingest.py`           | Orchestrates: load sources → scrape → chunk → embed → store; logs stats (total chunks, errors, timestamp)                                 |
| 1.8  | Run ingestion pipeline end-to-end             | -                             | Execute `python scripts/ingest.py`; verify ChromaDB populated with all chunks                                                             |
| 1.9  | Inspect ChromaDB contents                     | -                             | Query ChromaDB collection count; sample a few entries to verify metadata fields present                                                   |
| 1.10 | Test GitHub Actions workflow (manual trigger) | -                             | Trigger `workflow_dispatch` on GitHub Actions; verify: ingest runs → chroma_db/ committed → data freshness updated                        |

### Deliverable

- Populated ChromaDB with all sourced documents chunked, embedded, and stored with metadata

### Validation Checkpoint

- All 5 Groww source URLs reachable (or logged failures with alternatives found)
- ChromaDB collection `mutual_fund_faq` has >0 documents
- Each document in ChromaDB has metadata: `source_id`, `url`, `title`, `scheme`, `category`, `type`, `scrape_date`
- Sample similarity search on a known query (e.g., "expense ratio of HDFC Large Cap Fund") returns relevant chunks
- GitHub Actions workflow_dispatch runs successfully; chroma_db/ auto-committed to repo

---

## Phase 2: Query Pipeline — Core Modules

**Goal**: Build the three core query pipeline modules: classifier, retriever, generator.

### Tasks

| #   | Task                                | Files                                                      | Details                                                                                                                                                                                      |
| --- | ----------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.1 | Create prompt templates             | `prompts/classify_prompt.txt`, `prompts/answer_prompt.txt` | Classification prompt from §4.1; Answer generation prompt from §4.3 of architecture.md                                                                                                       |
| 2.2 | Build intent classifier             | `core/classifier.py`                                       | LLM-based classification: sends query + classify_prompt to Groq LLM; returns "factual", "advisory", or "performance"; handles API errors (default to "factual")                              |
| 2.3 | Build retriever                     | `core/retriever.py`                                        | Embed query via BGE → ChromaDB `similarity_search(k=3, score_threshold=0.7)`; optional metadata filter on `scheme` or `category` if detected in query; returns top chunks with full metadata |
| 2.4 | Build scheme/category detector      | `core/retriever.py` (helper)                               | Simple string-matching or LLM-based extraction of scheme name or category from query; used to set metadata filters                                                                           |
| 2.5 | Build generator                     | `core/generator.py`                                        | Construct prompt: answer_prompt + retrieved chunks (with source metadata) + user query; call Groq LLM with temperature=0.1, max_tokens=150; return raw LLM response                          |
| 2.6 | Test classifier with sample queries | `tests/test_classifier.py`                                 | 5 factual queries → "factual"; 5 advisory queries → "advisory"; 3 performance queries → "performance"                                                                                        |
| 2.7 | Test retriever with sample queries  | `tests/test_retriever.py`                                  | Known factual queries → verify top-3 chunks contain relevant info + correct metadata                                                                                                         |
| 2.8 | Test generator with sample queries  | -                                                          | Feed retrieved context + query to generator; verify raw response is non-empty and factual                                                                                                    |

### Deliverable

- Working classifier, retriever, and generator modules with unit tests

### Validation Checkpoint

- Classifier correctly labels ≥90% of test queries across all 3 categories
- Retriever returns chunks with relevant content and proper metadata for known queries
- Generator produces factual, non-advisory raw responses for factual queries with context

---

## Phase 3: Response Formatting & Refusal Handling

**Goal**: Build post-processing (formatter) and refusal templates to enforce all response constraints.

### Tasks

| #   | Task                                        | Files                        | Details                                                                                                                                                                                                            |
| --- | ------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 3.1 | Build formatter module                      | `core/formatter.py`          | (1) Sentence count enforcement — split on `.!?`, truncate to ≤3; (2) Citation injection — append `Source: {url}` from top chunk metadata; (3) Footer injection — append `Last updated from sources: {scrape_date}` |
| 3.2 | Build refusal handler                       | `core/refusal.py`            | Template-based: advisory refusal (polite + AMFI link + footer); performance refusal (factsheet link + footer); both include disclaimer reinforcement                                                               |
| 3.3 | Create refusal prompt template (if dynamic) | `prompts/refusal_prompt.txt` | Optional: for cases where refusal needs context-aware educational link                                                                                                                                             |
| 3.4 | Build chat orchestrator                     | `app/chat.py`                | Full pipeline: query → classify → (advisory? → refusal) / (performance? → factsheet refusal) / (factual? → retrieve → generate → format); returns final formatted response                                         |
| 3.5 | Test formatter                              | `tests/test_formatter.py`    | Input: raw LLM response of varying lengths (1, 3, 5, 10 sentences); verify output ≤3 sentences, has citation URL, has footer with date                                                                             |
| 3.6 | Test refusal handler                        | `tests/test_refusal.py`      | Advisory queries → refusal template with AMFI link; performance queries → factsheet link; verify polite tone + disclaimer reinforcement                                                                            |
| 3.7 | Test chat orchestrator (mocked)             | `tests/test_chat.py` (new)   | Mock classifier/retriever/generator; test full pipeline routing for factual, advisory, and performance queries                                                                                                     |

### Deliverable

- Complete query pipeline from raw query to formatted response, with refusal handling

### Validation Checkpoint

- Formatter always produces ≤3 sentences, 1 citation, and a date footer
- Refusal handler returns correct template for advisory and performance queries
- Chat orchestrator routes all 3 query types correctly through the pipeline
- End-to-end test with real API calls: factual query → complete formatted response meeting all §4 constraints

---

## Phase 4: Streamlit UI

**Goal**: Build the minimal Streamlit interface per §4 of the problem statement.

### Tasks

| #    | Task                                    | Files                  | Details                                                                                                                                                                                                                   |
| ---- | --------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4.1  | Build Streamlit app entry point         | `app/main.py`          | Page config (title, icon), session state init (chat history), layout (sidebar disclaimer + main chat area)                                                                                                                |
| 4.2  | Build UI components module              | `app/ui_components.py` | (1) `render_welcome()` — welcome message explaining facts-only scope; (2) `render_disclaimer()` — persistent banner "Facts-only. No investment advice."; (3) `render_example_questions()` — 3 clickable example questions |
| 4.3  | Define 3 example questions              | `app/ui_components.py` | Example 1: "What is the expense ratio of HDFC Large Cap Fund?"; Example 2: "What is the exit load for HDFC Mid Cap Fund?"; Example 3: "What category does the HDFC Gold ETF FoF belong to?"                               |
| 4.4  | Build chat display logic                | `app/main.py`          | Streamlit `st.chat_message` for user/assistant; iterate session state history; display formatted responses with citation links                                                                                            |
| 4.5  | Build chat input handler                | `app/main.py`          | `st.chat_input` → on submit: append user message to history → call `app/chat.py` pipeline → append assistant response to history → rerender                                                                               |
| 4.6  | Run Streamlit app locally               | -                      | `streamlit run app/main.py`; verify UI renders correctly                                                                                                                                                                  |
| 4.7  | Interactive testing — factual query     | -                      | Type "What is the exit load for HDFC Mid Cap Fund?" → verify factual response with citation + footer                                                                                                                      |
| 4.8  | Interactive testing — advisory query    | -                      | Type "Should I invest in HDFC Large Cap Fund?" → verify refusal response with AMFI link                                                                                                                                   |
| 4.9  | Interactive testing — performance query | -                      | Type "Which fund has better returns?" → verify factsheet link refusal                                                                                                                                                     |
| 4.10 | Interactive testing — example questions | -                      | Click each example question → verify correct response                                                                                                                                                                     |

### Deliverable

- Working Streamlit UI with welcome message, disclaimer, example questions, and chat interface

### Validation Checkpoint

- Streamlit app starts without errors
- Welcome message and disclaimer banner visible
- 3 example questions are clickable and produce correct responses
- Factual, advisory, and performance queries all route correctly through UI
- Responses display with citation links and date footer
- No PII fields present in UI (no login, no email/phone collection)

---

## Phase 5: Integration, Edge Cases & Polish

**Goal**: Harden the system — handle edge cases, add error recovery, and polish the UX.

### Tasks

| #   | Task                                    | Files                                 | Details                                                                                                                                                            |
| --- | --------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 5.1 | Add error handling to chat orchestrator | `app/chat.py`                         | Catch: LLM API errors → graceful message; ChromaDB empty → AMFI redirect; classification timeout → default to factual                                              |
| 5.2 | Add empty/off-topic query handling      | `core/classifier.py`                  | If query is empty/gibberish → return "I can only answer factual questions about mutual fund schemes."; if off-topic (not MF related) → polite redirect to AMFI     |
| 5.3 | Add citation fallback                   | `core/formatter.py`                   | If LLM response doesn't include a source URL → force-inject from top chunk metadata; if no chunks retrieved → use AMFI link as fallback                            |
| 5.4 | Add date freshness to footer            | `core/formatter.py`                   | Use the `scrape_date` from top chunk metadata; if unavailable → use current date with "sources last checked" qualifier                                             |
| 5.5 | Improve Streamlit UX                    | `app/main.py`, `app/ui_components.py` | (1) Clear chat button; (2) Loading spinner during LLM call; (3) Citation links rendered as clickable hyperlinks; (4) Disclaimer always visible (sticky or sidebar) |
| 5.6 | Handle concurrent Streamlit sessions    | `app/main.py`                         | Ensure ChromaDB client is thread-safe; use session-scoped state (no global mutable state)                                                                          |
| 5.7 | End-to-end test suite                   | `tests/test_end_to_end.py`            | 10 diverse queries (3 factual, 3 advisory, 2 performance, 1 edge case, 1 off-topic); verify all constraints for each                                               |
| 5.8 | Edge case tests                         | `tests/test_edge_cases.py` (new)      | Empty string, very long query, mixed English/Hindi, repeated same query, rapid sequential queries                                                                  |

### Deliverable

- Robust, production-ready chatbot with error handling and polished UX

### Validation Checkpoint

- All edge cases handled gracefully (no crashes, no wrong routing)
- Error scenarios produce user-friendly messages (not raw stack traces)
- End-to-end test suite passes 100% for all 10 diverse queries
- Streamlit UX is clean: disclaimer visible, spinner on load, clickable citations

---

## Phase 6: Documentation & Final Validation

**Goal**: Produce all required deliverables per the problem statement and validate against success criteria.

### Tasks

| #   | Task                           | Files                                 | Details                                                                                                                                        |
| --- | ------------------------------ | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 6.1 | Write README                   | `README.md`                           | Setup instructions (install, ingest, run); selected AMC + schemes; architecture overview (RAG approach); known limitations; disclaimer snippet |
| 6.2 | Validate source citations      | -                                     | Run 10 factual queries → verify each response has a valid, clickable source URL that resolves to an official AMC/AMFI/SEBI page                |
| 6.3 | Validate refusal compliance    | -                                     | Run 10 advisory/comparison queries → verify 100% refusal rate with polite tone + educational link                                              |
| 6.4 | Validate response format       | -                                     | Run 20 queries across all types → verify every factual response has ≤3 sentences, exactly 1 citation, and a date footer                        |
| 6.5 | Validate privacy compliance    | -                                     | Review codebase → confirm no PII collection, no session logging, no database of user queries                                                   |
| 6.6 | Validate disclaimer visibility | -                                     | Confirm "Facts-only. No investment advice." is always visible in the UI (sidebar or header)                                                    |
| 6.7 | Final integration test         | `tests/test_end_to_end.py` (extended) | Full suite: 30 queries covering all categories, edge cases, and format constraints; all must pass                                              |

### Deliverable

- Complete project with README, all validation passing, and all success criteria met

### Validation Checkpoint — Success Criteria Mapping

| #   | Success Criterion                                     | Validation Method                                                            |
| --- | ----------------------------------------------------- | ---------------------------------------------------------------------------- |
| 1   | Accurate retrieval of factual mutual fund information | 10 factual queries return correct, verifiable answers                        |
| 2   | Strict adherence to facts-only responses              | 10 advisory queries → 100% refusal; 0 advisory content in factual responses  |
| 3   | Consistent inclusion of valid source citations        | Every factual response has 1 clickable, resolving URL from official sources  |
| 4   | Proper refusal of advisory queries                    | All advisory/comparative queries return polite refusal + educational link    |
| 5   | Clean, minimal, and user-friendly interface           | Streamlit UI has welcome, disclaimer, 3 examples, chat input — no PII fields |

---

## Implementation Timeline

| Phase     | Duration Estimate | Key Milestone                                                |
| --------- | ----------------- | ------------------------------------------------------------ |
| Phase 0   | 1 day             | Project skeleton + verified API connectivity                 |
| Phase 1   | 2–3 days          | ChromaDB populated with all 5 Groww sources                  |
| Phase 2   | 2 days            | Classifier + retriever + generator working with unit tests   |
| Phase 3   | 1–2 days          | Formatter + refusal + chat orchestrator passing mocked tests |
| Phase 4   | 1–2 days          | Streamlit UI live with all 3 query types working             |
| Phase 5   | 1–2 days          | Edge cases handled, error recovery, UX polish                |
| Phase 6   | 1 day             | README + final validation against all 5 success criteria     |
| **Total** | **8–11 days**     | **Production-ready RAG chatbot**                             |

---

## Dependency Graph

```
Phase 0 (Setup) ─────────────────────────────────────────────┐
                                                               │
Phase 1 (Data Pipeline) ─── depends on Phase 0 ──────────────┤
                                                               │
Phase 2 (Query Core) ──── depends on Phase 1 (ChromaDB) ─────┤
                                                               │
Phase 3 (Format + Refusal) ── depends on Phase 2 ────────────┤
                                                               │
Phase 4 (Streamlit UI) ──── depends on Phase 3 ──────────────┤
                                                               │
Phase 5 (Polish) ────────── depends on Phase 4 ──────────────┤
                                                               │
Phase 6 (Documentation) ─── depends on Phase 5 ──────────────┘
```

Each phase must pass its validation checkpoint before the next phase begins. If a checkpoint fails, fix issues within the current phase before proceeding.
