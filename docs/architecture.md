# Architecture Design: Mutual Fund FAQ Assistant (RAG)

## 1. System Architecture Overview

The system follows a two-pipeline architecture — **Data Pipeline** (offline ingestion) and **Query Pipeline** (online serving). Both pipelines are orchestrated through a Python backend, with a Streamlit frontend for the user interface.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SYSTEM ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────── DATA PIPELINE ──────────────────────┐    │
│  │                                                             │    │
│  │  Official URLs ──► Scraper ──► Cleaner ──► Chunker         │    │
│  │       │                                       │             │    │
│  │  Metadata JSON                    Text Chunks │             │    │
│  │       │                                       │             │    │
│  │       ▼                                       ▼             │    │
│  │  Source Registry ──► Embedding Model ──► ChromaDB           │    │
│  │                       (BGE/HF)         (Vector Store)        │    │
│  │                                                             │    │
│  │  ┌─ GitHub Actions ────────────────────────────────────┐   │    │
│  │  │  Cron: 10:30 AM IST daily                           │   │    │
│  │  │  → Trigger ingest.py → Commit chroma_db/ to repo    │   │    │
│  │  │  workflow_dispatch: manual trigger for testing       │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────── QUERY PIPELINE ──────────────────────┐   │
│  │                                                              │   │
│  │  User Query ──► Intent Classifier ──► ┌─ Advisory? ──►     │   │
│  │       │                    │          │   Refuse + Link     │   │
│  │       │                    │          │                     │   │
│  │       ▼                    ▼          └─ Factual? ──►      │   │
│  │  Embedding ──► ChromaDB Retrieval        │                 │   │
│  │       │           │                      ▼                 │   │
│  │       │      Retrieved Chunks     Prompt Builder           │   │
│  │       │           │                      │                 │   │
│  │       │           ▼                      ▼                 │   │
│  │       │      Context + Source ──► LLM (Groq)              │   │
│  │       │                              │                     │   │
│  │       │                              ▼                     │   │
│  │       │                    Response Formatter              │   │
│  │       │                     │           │                  │   │
│  │       │                     ▼           ▼                  │   │
│  │       │              Answer (≤3sentences) + Citation       │   │
│  │       │              Footer: "Last updated from sources"  │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────── FRONTEND ────────────────────────────┐   │
│  │                                                              │   │
│  │  Streamlit UI                                                │   │
│  │  ┌────────────────────────────────────────────┐             │   │
│  │  │  Welcome Message                           │             │   │
│  │  │  Disclaimer: "Facts-only. No investment    │             │   │
│  │  │              advice."                      │             │   │
│  │  │  3 Example Questions (clickable)           │             │   │
│  │  │  Chat Input + Response Display             │             │   │
│  │  └────────────────────────────────────────────┘             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Design Decisions

### 2.1 AMC & Scheme Selection

| Decision     | Choice              | Rationale                                                                                 |
| ------------ | ------------------- | ----------------------------------------------------------------------------------------- |
| **AMC**      | HDFC Mutual Fund    | Leading AMC in India; diverse scheme categories; Groww as data source per project context |
| **Scheme 1** | HDFC Large Cap Fund | Large-cap equity — most popular category                                                  |
| **Scheme 2** | HDFC Mid Cap Fund   | Mid-cap — growth-oriented category                                                        |
| **Scheme 3** | HDFC Small Cap Fund | Small-cap — high-risk category diversity                                                  |
| **Scheme 4** | HDFC Multi Cap Fund | Multi-cap — diversified allocation across cap sizes                                       |
| **Scheme 5** | HDFC Gold ETF FoF   | Gold ETF Fund of Fund — commodity/alternative category                                    |

### 2.2 Technology Stack

| Layer                 | Technology                                 | Rationale                                                                                                          |
| --------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| **Language**          | Python 3.11+                               | Rich RAG ecosystem (LangChain, ChromaDB, Streamlit)                                                                |
| **Embedding Model**   | BGE `bge-small-en-v1.5` (HuggingFace)      | Free, local inference via HuggingFace; 384-dim; strong semantic quality for English financial text; no API cost    |
| **Vector Store**      | ChromaDB (local, persistent)               | Zero infra cost, persistent mode for offline ingestion, built-in metadata filtering, Python-native                 |
| **LLM**               | Groq (Llama 3.3 70B or Mixtral)            | Ultra-fast inference via Groq Cloud API; free tier available; strong instruction-following for factual constraints |
| **RAG Framework**     | LangChain                                  | Mature ecosystem, modular components; supports Groq via langchain-groq and BGE via HuggingFace embeddings          |
| **Web Scraper**       | BeautifulSoup + requests                   | Simple HTML parsing for Groww mutual fund pages; no JS rendering needed                                            |
| **PDF Parser**        | Not needed initially                       | All current sources are Groww HTML pages; PDF support can be added later for HDFC KIM/SID documents                |
| **Chunking**          | LangChain `RecursiveCharacterTextSplitter` | Preserves semantic boundaries; configurable chunk size + overlap                                                   |
| **Intent Classifier** | LLM-based (prompt classification)          | Zero additional model needed; uses same Groq LLM with a classification prompt                                      |
| **UI Framework**      | Streamlit                                  | Minimal UI requirement fits Streamlit perfectly; rapid prototyping; Python-native; chat components built-in        |
| **Groq Client**       | langchain-groq                             | LangChain integration for Groq Cloud API; provides ChatGroq for LLM calls                                          |
| **Scheduler**         | GitHub Actions                             | Daily cron trigger for ingestion pipeline at 10:30 AM IST; ensures ChromaDB stays fresh with latest source data    |
| **Environment**       | `.env` + `python-dotenv`                   | Standard secrets management for API keys; GROQ_API_KEY stored as GitHub Actions secret                             |

---

## 3. Data Pipeline (Offline Ingestion)

### 3.1 Source Registry

A JSON file (`data/sources.json`) cataloging all source URLs with metadata:

```json
{
  "sources": [
    {
      "id": "src_001",
      "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
      "type": "factsheet",
      "scheme": "HDFC Large Cap Fund",
      "category": "large_cap",
      "format": "html",
      "last_scraped": "2026-05-31",
      "title": "HDFC Large Cap Fund - Direct Growth"
    },
    {
      "id": "src_002",
      "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
      "type": "factsheet",
      "scheme": "HDFC Mid Cap Fund",
      "category": "mid_cap",
      "format": "html",
      "last_scraped": "2026-05-31",
      "title": "HDFC Mid Cap Fund - Direct Growth"
    },
    {
      "id": "src_003",
      "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
      "type": "factsheet",
      "scheme": "HDFC Small Cap Fund",
      "category": "small_cap",
      "format": "html",
      "last_scraped": "2026-05-31",
      "title": "HDFC Small Cap Fund - Direct Growth"
    },
    {
      "id": "src_004",
      "url": "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth",
      "type": "factsheet",
      "scheme": "HDFC Multi Cap Fund",
      "category": "multi_cap",
      "format": "html",
      "last_scraped": "2026-05-31",
      "title": "HDFC Multi Cap Fund - Direct Growth"
    },
    {
      "id": "src_005",
      "url": "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
      "type": "factsheet",
      "scheme": "HDFC Gold ETF FoF",
      "category": "gold_etf_fof",
      "format": "html",
      "last_scraped": "2026-05-31",
      "title": "HDFC Gold ETF Fund of Fund - Direct Plan Growth"
    }
  ]
}
```

Each source entry includes:

- `id`: Unique identifier for citation tracking
- `url`: The Groww mutual fund page URL
- `type`: Document type (currently factsheet for all Groww pages)
- `scheme`: Which scheme it belongs to
- `category`: Fund category for filtering (large_cap, mid_cap, small_cap, multi_cap, gold_etf_fof)
- `format`: html (all Groww pages are HTML)
- `title`: Human-readable title for citations

### 3.2 Document Scraping & Parsing

```
sources.json ──► Scraper Module
                     │
                     ├─ HTML documents ──► BeautifulSoup ──► Clean text + metadata
                     │
                     └─ Store raw extracted text in data/raw/
```

**Scraper responsibilities:**

- Fetch content from each Groww URL
- Parse HTML (all sources are HTML pages from Groww)
- Extract clean text (strip navigation, footers, ads, Groww UI chrome)
- Preserve document structure (key details, riskometer, expense ratio, exit load, etc.)
- Attach metadata: source_id, url, title, scheme, type, scrape_date

### 3.3 Chunking Strategy

Using `RecursiveCharacterTextSplitter` with:

| Parameter       | Value                     | Rationale                                                    |
| --------------- | ------------------------- | ------------------------------------------------------------ |
| `chunk_size`    | 500 characters            | Small enough for precise retrieval; large enough for context |
| `chunk_overlap` | 100 characters            | Prevents losing context at boundaries                        |
| `separators`    | ["\n\n", "\n", ". ", " "] | Splits on paragraphs first, then sentences, then words       |

Each chunk inherits metadata from its parent document:

- `source_id`, `url`, `title`, `scheme`, `category`, `type`, `scrape_date`

### 3.4 Embedding & Storage

```
Text Chunks ──► BGE bge-small-en-v1.5 (HuggingFace) ──► ChromaDB (persistent)
                      │                                │
                      │ 384-dim vectors                │ Collection: "mutual_fund_faq"
                      │                                │ Metadata: source_id, url, title,
                      │                                │           scheme, category, type,
                      │                                │           scrape_date
```

**ChromaDB configuration:**

- Persistent mode: `chroma_db/` directory
- Single collection: `mutual_fund_faq`
- Metadata fields enable filtering by scheme/category
- Cosine similarity for retrieval

### 3.5 Pipeline Script

A single script (`scripts/ingest.py`) that:

1. Reads `sources.json`
2. Scrapes all Groww pages → stores raw text in `data/raw/`
3. Chunks all documents
4. Embeds via BGE model and stores in ChromaDB
5. Logs ingestion stats (chunks count, errors, timestamps)

### 3.6 Scheduled Ingestion (GitHub Actions)

A GitHub Actions workflow triggers the ingestion pipeline **daily at 10:30 AM IST** to keep ChromaDB data fresh.

**Workflow file**: `.github/workflows/ingest.yml`

```yaml
name: Daily Ingestion

on:
  schedule:
    # 10:30 AM IST = 05:00 UTC (IST = UTC+5:30)
    - cron: '0 5 * * *'
  workflow_dispatch: # Allow manual trigger for testing/debugging

jobs:
  ingest:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run ingestion pipeline
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: python scripts/ingest.py

      - name: Commit updated ChromaDB data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add chroma_db/ data/raw/ data/processed/
          git diff --staged --quiet || git commit -m "auto: daily ingestion $(date +%Y-%m-%d)"
          git push
```

**Key design decisions for the scheduler:**

| Aspect               | Choice                     | Rationale                                                                                                                                                              |
| -------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cron schedule        | `0 5 * * *` (05:00 UTC)    | 10:30 AM IST = UTC+5:30 = 05:00 UTC                                                                                                                                    |
| Manual trigger       | `workflow_dispatch`        | Allows ad-hoc ingestion for debugging or after source URL changes                                                                                                      |
| ChromaDB persistence | Git-commit after ingestion | Since ChromaDB runs locally in persistent mode, the updated `chroma_db/` directory is committed and pushed back to the repo so the Streamlit app always has fresh data |
| Secrets management   | GitHub Actions secrets     | GROQ_API_KEY stored as a repository secret, never exposed in logs                                                                                                      |
| Runner environment   | `ubuntu-latest`            | Fresh environment each run; BGE model downloaded on each run (cached via `actions/setup-python` pip cache)                                                             |

**Ingestion freshness guarantee:**

- Source data is re-scraped and re-embedded daily
- `scrape_date` metadata in ChromaDB reflects the actual ingestion date
- Footer in responses will always show the last ingestion date
- If a Groww page changes (e.g., updated expense ratio), the next daily run picks it up

---

## 4. Query Pipeline (Online Serving)

### 4.1 Intent Classification

Before retrieval, every user query passes through an **intent classifier** to determine if it's factual or advisory.

**Classification prompt (sent to Groq LLM):**

```
You are a query classifier for a mutual fund FAQ assistant.
Classify the user's query as one of:
- "factual": The query asks for objective, verifiable information about a mutual fund scheme
  (e.g., expense ratio, exit load, minimum SIP, lock-in period, riskometer, benchmark).
- "advisory": The query asks for investment advice, recommendations, or comparisons
  (e.g., "should I invest", "which fund is better", "best fund for retirement").
- "performance": The query asks about returns, performance, or yield data.

Respond with ONLY one word: factual, advisory, or performance.

User query: {query}
```

**Classification outcomes:**

| Classification | Action                                                     |
| -------------- | ---------------------------------------------------------- |
| `factual`      | Proceed to RAG retrieval → generate factual answer         |
| `advisory`     | Return refusal response with AMFI/SEBI educational link    |
| `performance`  | Return link to official factsheet (no return calculations) |

### 4.2 Retrieval

```
User Query ──► BGE Embedding ──► ChromaDB.similarity_search()
                                         │
                                         │  Parameters:
                                         │  - k = 3 (top 3 chunks)
                                         │  - filter: scheme (if query mentions a specific scheme)
                                         │  - score_threshold = 0.7 (minimum relevance)
                                         │
                                         ▼
                                   Retrieved Chunks (with metadata)
```

**Retrieval strategy:**

- Default: `k=3` top chunks for general queries
- Scheme-specific: metadata filter on `scheme` field when user mentions a fund name (e.g., "HDFC Large Cap")
- Category-specific: metadata filter on `category` when query mentions a fund type (e.g., "mid-cap", "gold")
- Relevance threshold: discard chunks with similarity score below 0.7

### 4.3 Prompt Construction

The LLM receives a carefully constructed prompt with strict constraints:

```
You are a facts-only mutual fund FAQ assistant. You MUST follow these rules:

RULES:
1. Answer ONLY with factual, verifiable information from the provided context.
2. NEVER provide investment advice, opinions, or recommendations.
3. NEVER compare fund performance or calculate returns.
4. Your response MUST be at most 3 sentences.
5. Include exactly ONE source citation URL from the context at the end.
6. If the context does not contain enough information, say:
   "I could not find specific information on this. Please check the official source: [most relevant URL]"
7. Do NOT invent or infer information not present in the context.

CONTEXT:
{retrieved_chunks_with_metadata}

USER QUESTION: {query}

Provide your factual answer below:
```

### 4.4 Response Formatting

The raw LLM output is post-processed to enforce format constraints:

1. **Sentence count check**: If >3 sentences, truncate to 3
2. **Citation injection**: Append the source URL from the top-ranked chunk's metadata
3. **Footer injection**: Append `"Last updated from sources: <scrape_date from metadata>"`
4. **Format template**:

   ```
   [Answer text - max 3 sentences]

   Source: [URL from top chunk metadata]
   Last updated from sources: YYYY-MM-DD
   ```

### 4.5 Refusal Response Templates

**For advisory queries:**

```
I'm unable to provide investment advice or recommendations. This assistant
only provides factual, verifiable information about mutual fund schemes.
For guidance on investment decisions, please visit: https://www.amfiindia.com/

Last updated from sources: 2026-05-31
```

**For performance/comparison queries:**

```
I cannot provide performance comparisons or return calculations. For detailed
performance data, please refer to the official factsheet: [relevant factsheet URL]

Last updated from sources: 2026-05-31
```

---

## 5. Application Module Architecture

### 5.1 Project Structure

```
RAG-chatbot/
├── app/
│   ├── main.py                  # Streamlit app entry point
│   ├── chat.py                  # Chat logic (classify → retrieve → generate → format)
│   └── ui_components.py         # Streamlit UI helpers (welcome, disclaimer, examples)
│
├── core/
│   ├── classifier.py            # Intent classification (factual/advisory/performance)
│   ├── retriever.py             # ChromaDB retrieval with metadata filtering
│   ├── generator.py             # LLM call with constrained prompt
│   ├── formatter.py             # Response post-processing (truncate, cite, footer)
│   └── refusal.py               # Refusal response templates
│
├── data/
│   ├── sources.json             # Source registry (15–25 URLs with metadata)
│   ├── raw/                     # Raw scraped text files
│   └── processed/               # Chunked text with metadata (before embedding)
│
├── scripts/
│   ├── ingest.py                # Full ingestion pipeline (scrape → chunk → embed → store)
│   └── validate_sources.py      # Verify all source URLs are reachable
│
├── chroma_db/                   # ChromaDB persistent storage directory
│
├── .github/
│   └── workflows/
│       └── ingest.yml            # GitHub Actions workflow: daily ingestion at 10:30 AM IST
│
├── prompts/
│   ├── classify_prompt.txt      # Intent classification prompt
│   ├── answer_prompt.txt        # Factual answer generation prompt
│   └── refusal_prompt.txt       # Advisory refusal prompt (if dynamic)
│
├── config/
│   ├── settings.py              # App settings (model names, chunk params, thresholds)
│   └── .env.example             # Template for environment variables
│
├── tests/
│   ├── test_classifier.py       # Test intent classification
│   ├── test_retriever.py        # Test retrieval with known queries
│   ├── test_formatter.py        # Test response format constraints
│   ├── test_refusal.py          # Test refusal on advisory queries
│   └── test_end_to_end.py       # Full pipeline test with sample queries
│
├── docs/
│   ├── problemStatement.txt
│   ├── context.md
│   └── architecture.md          # This file
│
├── .env                         # API keys (not committed)
├── .gitignore
├── requirements.txt
└── README.md
```

### 5.2 Module Responsibilities

| Module                  | File                           | Responsibility                                                                     |
| ----------------------- | ------------------------------ | ---------------------------------------------------------------------------------- |
| **App Entry**           | `app/main.py`                  | Streamlit app setup, page config, session state                                    |
| **Chat Orchestrator**   | `app/chat.py`                  | Orchestrates classify → retrieve → generate → format pipeline via Groq LLM         |
| **UI Components**       | `app/ui_components.py`         | Welcome message, disclaimer banner, example question buttons                       |
| **Intent Classifier**   | `core/classifier.py`           | LLM-based query classification (factual/advisory/performance)                      |
| **Retriever**           | `core/retriever.py`            | Embed query via BGE, similarity search in ChromaDB, metadata filtering             |
| **Generator**           | `core/generator.py`            | Build prompt from context, call Groq API, return raw response                      |
| **Formatter**           | `core/formatter.py`            | Enforce max 3 sentences, inject citation URL, append footer                        |
| **Refusal Handler**     | `core/refusal.py`              | Template-based refusal responses for advisory/performance queries                  |
| **Ingestion Pipeline**  | `scripts/ingest.py`            | Scrape Groww pages → parse → chunk → embed via BGE → store in ChromaDB             |
| **Scheduled Ingestion** | `.github/workflows/ingest.yml` | GitHub Actions cron trigger (10:30 AM IST daily); commits updated ChromaDB to repo |
| **Config**              | `config/settings.py`           | All tunable parameters (chunk_size, k, threshold, model names)                     |

---

## 6. Data Flow — Complete Walkthrough

### 6.1 Ingestion Flow (Offline)

```
1. sources.json loaded
2. For each source:
   a. Fetch Groww URL content
   b. Parse HTML via BeautifulSoup
   c. Extract clean text, preserve structure (fund details, key metrics)
   d. Save raw text to data/raw/{source_id}.txt
   e. Create document object with metadata
3. All documents chunked via RecursiveCharacterTextSplitter
   - chunk_size=500, chunk_overlap=100
4. Chunks embedded via BGE bge-small-en-v1.5
5. Embeddings + chunks + metadata stored in ChromaDB
6. Ingestion stats logged (total chunks, errors, timestamp)
7. Updated chroma_db/ and data/raw/ committed and pushed to repo (automated via GitHub Actions)
```

**Scheduled execution:** The ingestion flow above runs automatically every day at 10:30 AM IST via the GitHub Actions workflow (`.github/workflows/ingest.yml`). It can also be triggered manually via `workflow_dispatch` for testing or after source URL changes.

### 6.2 Query Flow (Online)

```
1. User submits query via Streamlit chat input
2. Query → classifier.py → intent classification (factual/advisory/performance)
3. If advisory:
   → refusal.py → return refusal template + AMFI link + footer
4. If performance:
   → refusal.py → return factsheet link + footer (no calculations)
5. If factual:
   a. Query → BGE embedding → retriever.py
   b. ChromaDB similarity_search(k=3, threshold=0.7)
      - Optional metadata filter if scheme/category detected
   c. Retrieved chunks + metadata → generator.py
   d. Construct constrained prompt with context
   e. Groq LLM generates response
   f. Response → formatter.py
      - Truncate to ≤3 sentences
      - Inject citation URL from top chunk metadata
      - Append footer with scrape date
   g. Formatted response returned to Streamlit UI
```

---

## 7. Configuration Parameters

All tunable settings in `config/settings.py`:

```python
# Embedding
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384

# Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " "]

# Retrieval
RETRIEVAL_TOP_K = 3
RETRIEVAL_SCORE_THRESHOLD = 0.7
CHROMA_COLLECTION_NAME = "mutual_fund_faq"
CHROMA_PERSIST_DIR = "chroma_db/"

# Generation
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.1         # Low temperature for factual precision
GROQ_MAX_TOKENS = 150          # Short responses (≈3 sentences)

# Response Formatting
MAX_SENTENCES = 3
CITATION_TEMPLATE = "Source: {url}"
FOOTER_TEMPLATE = "Last updated from sources: {date}"

# Refusal
AMFI_EDUCATION_LINK = "https://www.amfiindia.com/"
SEBI_EDUCATION_LINK = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetId=699"
DISCLAIMER_TEXT = "Facts-only. No investment advice."
```

---

## 8. Source URLs (HDFC Mutual Fund via Groww — 5 Sources)

| #   | Type      | Scheme              | Category     | URL Source                                                                  |
| --- | --------- | ------------------- | ------------ | --------------------------------------------------------------------------- |
| 1   | Factsheet | HDFC Large Cap Fund | large_cap    | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth             |
| 2   | Factsheet | HDFC Mid Cap Fund   | mid_cap      | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth               |
| 3   | Factsheet | HDFC Small Cap Fund | small_cap    | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth             |
| 4   | Factsheet | HDFC Multi Cap Fund | multi_cap    | https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth             |
| 5   | Factsheet | HDFC Gold ETF FoF   | gold_etf_fof | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth |

_Note: These 5 Groww pages serve as the initial corpus. Additional HDFC official sources (factsheets, KIM, SID from HDFC AMC website) and AMFI/SEBI guidance pages can be added later to expand the corpus to 15–25 sources per the problem statement scope._

---

## 9. Security & Compliance Design

### 9.1 Privacy Guardrails

- **No PII collection**: Streamlit app does not request or store PAN, Aadhaar, account numbers, OTPs, email, or phone
- **No session logging of PII**: Chat history stored in Streamlit session state only (ephemeral, per-browser)
- **No database of user queries**: Queries are processed in-memory and discarded

### 9.2 Content Guardrails

- **Intent classifier**: First line of defense — routes advisory queries to refusal
- **LLM prompt constraints**: Hard rules in system prompt forbid advice/recommendations
- **Response formatter**: Post-processing truncates and validates format
- **Citation enforcement**: Every factual response MUST include a source URL from retrieved metadata

### 9.3 Compliance Checklist

| Requirement                | Implementation                                           |
| -------------------------- | -------------------------------------------------------- |
| No investment advice       | Intent classifier + LLM prompt rules + refusal templates |
| No performance comparisons | Intent classifier (performance type) + refusal template  |
| Max 3 sentences            | Formatter truncation                                     |
| Exactly 1 citation         | Formatter citation injection from top chunk metadata     |
| Footer with date           | Formatter footer injection from scrape_date metadata     |
| Facts-only disclaimer      | UI banner + welcome message                              |

---

## 10. Error Handling

| Scenario                         | Handling                                                                                      |
| -------------------------------- | --------------------------------------------------------------------------------------------- |
| Source URL unreachable           | Log error, skip source, continue ingestion; Groww pages should be stable                      |
| ChromaDB empty / no results      | Return: "I don't have information on this topic yet. Please check [AMFI link]"                |
| LLM API failure                  | Return: "I'm temporarily unable to process your query. Please try again later."               |
| Classification uncertain         | Default to `factual` (safe path — RAG will handle out-of-scope via prompt constraints)        |
| Retrieved chunks below threshold | Return: "I couldn't find relevant information. Please check the official source: [AMFI link]" |
| Query mentions unknown scheme    | No metadata filter applied; general retrieval across all schemes                              |

---

## 11. Testing Strategy

| Test Type            | Scope                                            | Key Assertions                                       |
| -------------------- | ------------------------------------------------ | ---------------------------------------------------- |
| **Classifier tests** | Known advisory, factual, performance queries     | Correct classification label                         |
| **Retriever tests**  | Known factual queries with expected sources      | Relevant chunks returned, correct scheme metadata    |
| **Formatter tests**  | Raw LLM responses                                | ≤3 sentences, citation URL present, footer with date |
| **Refusal tests**    | Advisory and comparison queries                  | Refusal template returned, educational link included |
| **End-to-end tests** | Full pipeline with sample queries                | Complete formatted response meets all constraints    |
| **Edge case tests**  | Empty queries, very long queries, mixed-language | Graceful handling, no crashes                        |

---

## 12. Known Limitations

1. **Source freshness**: Mitigated by GitHub Actions daily cron at 10:30 AM IST; data is at most ~24 hours stale. If a run fails, data may be older until next successful run
2. **URL structure changes**: AMC website redesigns may break scraper logic
3. **PDF parsing quality**: Some SID/KIM PDFs may have complex layouts that reduce extraction accuracy
4. **Classification accuracy**: LLM-based classifier may occasionally misclassify borderline queries
5. **Single AMC scope**: Only covers HDFC Mutual Fund schemes — cannot answer about other AMCs
6. **No real-time data**: NAV, AUM, and daily performance data are not ingested
7. **Language**: Only English queries supported
