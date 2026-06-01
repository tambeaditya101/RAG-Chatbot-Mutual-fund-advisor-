"""
Application settings and tunable parameters.
All configurable values are centralized here per architecture.md §7.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── API Keys ────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ─── Embedding ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384

# ─── Chunking ────────────────────────────────────────────────────────────────
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " "]

# ─── Retrieval ───────────────────────────────────────────────────────────────
RETRIEVAL_TOP_K = 3
RETRIEVAL_SCORE_THRESHOLD = 0.7
CHROMA_COLLECTION_NAME = "mutual_fund_faq"
CHROMA_PERSIST_DIR = "chroma_db/"

# ─── Generation ──────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.1
GROQ_MAX_TOKENS = 150

# ─── Response Formatting ─────────────────────────────────────────────────────
MAX_SENTENCES = 3
CITATION_TEMPLATE = "Source: {url}"
FOOTER_TEMPLATE = "Last updated from sources: {date}"

# ─── Refusal ─────────────────────────────────────────────────────────────────
AMFI_EDUCATION_LINK = "https://www.amfiindia.com/"
SEBI_EDUCATION_LINK = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetId=699"
DISCLAIMER_TEXT = "Facts-only. No investment advice."
