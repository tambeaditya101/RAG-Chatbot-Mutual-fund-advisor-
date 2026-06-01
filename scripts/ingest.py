"""
Full ingestion pipeline script.
Orchestrates: load sources → scrape → chunk → embed → store.

Usage:
    python scripts/ingest.py
"""

import json
import os
import sys
from datetime import datetime

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scraper import scrape_source
from core.chunker import chunk_documents
from core.embedder import embed_and_store

SOURCES_PATH = "data/sources.json"
RAW_DATA_DIR = "data/raw"


def load_sources(path: str) -> list[dict]:
    """Load source registry from JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return data["sources"]


def save_raw_text(source_id: str, text: str) -> None:
    """Save raw scraped text to data/raw/{source_id}.txt."""
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    filepath = os.path.join(RAW_DATA_DIR, f"{source_id}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  [INGEST] Saved raw text: {filepath}")


def run_ingestion() -> dict:
    """
    Run the full ingestion pipeline.

    Returns:
        Dict with ingestion stats: total_sources, scraped, failed, total_chunks.
    """
    start_time = datetime.now()
    print("=" * 60)
    print(f"INGESTION PIPELINE — Started at {start_time.isoformat()}")
    print("=" * 60)

    # Step 1: Load sources
    print("\n[STEP 1] Loading sources...")
    sources = load_sources(SOURCES_PATH)
    print(f"  Found {len(sources)} sources")

    # Step 2: Scrape all sources
    print("\n[STEP 2] Scraping sources...")
    documents = []
    failed = []
    for source in sources:
        doc = scrape_source(source)
        if doc is not None:
            documents.append(doc)
            # Save raw text for reference
            save_raw_text(source["id"], doc.page_content)
        else:
            failed.append(source["id"])
            print(f"  [INGEST] FAILED: {source['id']} — {source['url']}")

    print(f"\n  Scraped: {len(documents)}/{len(sources)}")
    print(f"  Failed: {len(failed)}/{len(sources)}")

    if not documents:
        print("\n[ERROR] No documents scraped. Aborting ingestion.")
        return {
            "total_sources": len(sources),
            "scraped": 0,
            "failed": len(failed),
            "total_chunks": 0,
            "error": "No documents scraped",
        }

    # Step 3: Chunk documents
    print("\n[STEP 3] Chunking documents...")
    chunks = chunk_documents(documents)

    # Step 4: Embed and store in ChromaDB
    print("\n[STEP 4] Embedding and storing in ChromaDB...")
    total_stored = embed_and_store(chunks)

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    stats = {
        "total_sources": len(sources),
        "scraped": len(documents),
        "failed": len(failed),
        "total_chunks": total_stored,
        "duration_seconds": round(duration, 1),
        "started_at": start_time.isoformat(),
        "completed_at": end_time.isoformat(),
    }

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Sources:    {stats['scraped']}/{stats['total_sources']} scraped "
          f"({stats['failed']} failed)")
    print(f"  Chunks:     {stats['total_chunks']} stored in ChromaDB")
    print(f"  Duration:   {stats['duration_seconds']}s")
    if failed:
        print(f"  Failed IDs: {', '.join(failed)}")
    print("=" * 60)

    return stats


if __name__ == "__main__":
    stats = run_ingestion()
    if stats.get("error") or stats["scraped"] == 0:
        sys.exit(1)
