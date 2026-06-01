# Project Context: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Project Overview

Build a facts-only FAQ assistant for mutual fund schemes (Groww as reference product context) using a RAG-based architecture. The assistant answers objective, verifiable queries from official public sources only — no investment advice, opinions, or recommendations.

## Target Users

- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

---

## Corpus Definition

### AMC Selection

- Pick **1 Asset Management Company (AMC)**

### Scheme Selection

- Pick **3–5 mutual fund schemes** with category diversity:
  - Large-cap
  - Flexi-cap
  - ELSS
  - (Other categories as needed)

### Source Collection

- Collect **15–25 official public URLs** including:
  - Scheme factsheets
  - KIM (Key Information Memorandum)
  - SID (Scheme Information Document)
  - AMC FAQ/help pages
  - AMFI/SEBI guidance pages
  - Statement and tax document download guides

---

## FAQ Assistant Requirements

### Supported Query Types

- Expense ratio of a scheme
- Exit load details
- Minimum SIP amount
- ELSS lock-in period
- Riskometer classification
- Benchmark index
- Process to download statements or capital gains reports

### Response Constraints

- **Max 3 sentences** per response
- **Exactly 1 citation link** per response
- Footer format: `"Last updated from sources: <date>"`

---

## Refusal Handling

### Must Refuse

- Advisory queries (e.g., "Should I invest in this fund?")
- Comparative queries (e.g., "Which fund is better?")

### Refusal Response Requirements

- Polite and clearly worded
- Reinforce facts-only limitation
- Provide a relevant educational link (AMFI or SEBI resource)

---

## User Interface Requirements

- Welcome message
- Three example questions
- Visible disclaimer: **"Facts-only. No investment advice."**

---

## Constraints

### Data & Sources

- Use **only official public sources** (AMC, AMFI, SEBI)
- **No** third-party blogs or aggregator websites

### Privacy & Security

- **Do not** collect, store, or process:
  - PAN or Aadhaar numbers
  - Account numbers
  - OTPs
  - Email addresses or phone numbers

### Content Restrictions

- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries → provide a link to the official factsheet only

### Transparency

- Responses must be short, factual, and verifiable
- Every answer must include a source link and last updated date

---

## Success Criteria

1. Accurate retrieval of factual mutual fund information
2. Strict adherence to facts-only responses
3. Consistent inclusion of valid source citations
4. Proper refusal of advisory queries
5. Clean, minimal, and user-friendly interface

---

## Disclaimer

**"Facts-only. No investment advice."**

---

## Architecture Approach

**Retrieval-Augmented Generation (RAG)**:

1. Curated corpus of official mutual fund documents (factsheets, KIM, SID, etc.)
2. Document ingestion → chunking → embedding → vector store
3. User query → embedding → retrieval of relevant chunks
4. Retrieved context + query → LLM generation with strict factual constraints
5. Source citation appended from retrieved document metadata
6. Refusal logic for non-factual/advisory queries

## Key Design Decisions (Resolved)

| Decision        | Choice                                                      | Status  |
| --------------- | ----------------------------------------------------------- | ------- |
| AMC Selection   | HDFC Mutual Fund                                            | Decided |
| Schemes (5)     | HDFC Large Cap, Mid Cap, Small Cap, Multi Cap, Gold ETF FoF | Decided |
| Embedding Model | BGE `bge-small-en-v1.5` (HuggingFace)                       | Decided |
| Vector Store    | ChromaDB (local, persistent)                                | Decided |
| LLM             | Groq (Llama 3.3 70B Versatile)                              | Decided |
| UI Framework    | Streamlit                                                   | Decided |
| Source URLs (5) | Groww HDFC fund pages                                       | Decided |
