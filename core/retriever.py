"""
Retriever module — embeds queries via BGE, performs similarity search
in ChromaDB, and applies optional metadata filters based on scheme
or category detected in the query.
"""

from core.embedder import get_embedding_model, get_chroma_client, get_or_create_collection
from config.settings import (
    RETRIEVAL_TOP_K,
    RETRIEVAL_SCORE_THRESHOLD,
    CHROMA_COLLECTION_NAME,
)

# ─── Scheme / Category Detection ─────────────────────────────────────────────

# Known schemes from sources.json — used for string-matching detection
KNOWN_SCHEMES = {
    "hdfc large cap fund": "HDFC Large Cap Fund",
    "hdfc large cap": "HDFC Large Cap Fund",
    "large cap fund": "HDFC Large Cap Fund",
    "hdfc mid cap fund": "HDFC Mid Cap Fund",
    "hdfc mid cap": "HDFC Mid Cap Fund",
    "mid cap fund": "HDFC Mid Cap Fund",
    "hdfc small cap fund": "HDFC Small Cap Fund",
    "hdfc small cap": "HDFC Small Cap Fund",
    "small cap fund": "HDFC Small Cap Fund",
    "hdfc multi cap fund": "HDFC Multi Cap Fund",
    "hdfc multi cap": "HDFC Multi Cap Fund",
    "multi cap fund": "HDFC Multi Cap Fund",
    "hdfc gold etf fof": "HDFC Gold ETF FoF",
    "hdfc gold etf fund of fund": "HDFC Gold ETF FoF",
    "hdfc gold etf": "HDFC Gold ETF FoF",
    "gold etf fof": "HDFC Gold ETF FoF",
    "gold etf fund": "HDFC Gold ETF FoF",
}

# Known categories from sources.json — used for string-matching detection
KNOWN_CATEGORIES = {
    "large cap": "large_cap",
    "large-cap": "large_cap",
    "largecap": "large_cap",
    "mid cap": "mid_cap",
    "mid-cap": "mid_cap",
    "midcap": "mid_cap",
    "small cap": "small_cap",
    "small-cap": "small_cap",
    "smallcap": "small_cap",
    "multi cap": "multi_cap",
    "multi-cap": "multi_cap",
    "multicap": "multi_cap",
    "gold etf": "gold_etf_fof",
    "gold": "gold_etf_fof",
}


def detect_scheme(query: str) -> str | None:
    """
    Detect a specific scheme name mentioned in the query.

    Uses simple string-matching against known scheme names.
    Returns the full scheme name if found, else None.

    Args:
        query: The user's query string.

    Returns:
        Matched scheme name (e.g., "HDFC Large Cap Fund") or None.
    """
    query_lower = query.lower()

    # Sort by length descending so longer (more specific) matches take priority
    for pattern in sorted(KNOWN_SCHEMES.keys(), key=len, reverse=True):
        if pattern in query_lower:
            return KNOWN_SCHEMES[pattern]

    return None


def detect_category(query: str) -> str | None:
    """
    Detect a fund category mentioned in the query.

    Uses simple string-matching against known category keywords.
    Returns the category key if found, else None.

    Args:
        query: The user's query string.

    Returns:
        Matched category key (e.g., "large_cap") or None.
    """
    query_lower = query.lower()

    # Sort by length descending for more specific matches first
    for pattern in sorted(KNOWN_CATEGORIES.keys(), key=len, reverse=True):
        if pattern in query_lower:
            return KNOWN_CATEGORIES[pattern]

    return None


# ─── Retrieval ────────────────────────────────────────────────────────────────


def retrieve(
    query: str,
    n_results: int | None = None,
    score_threshold: float | None = None,
) -> list[dict]:
    """
    Retrieve the most relevant chunks from ChromaDB for the given query.

    Optionally applies metadata filters if a scheme or category is
    detected in the query.

    Args:
        query: The user's query string.
        n_results: Number of results to return (defaults to RETRIEVAL_TOP_K).
        score_threshold: Minimum similarity score (defaults to RETRIEVAL_SCORE_THRESHOLD).

    Returns:
        List of result dicts with 'document', 'metadata', and 'distance' keys.
        Chunks below the score threshold are filtered out.
    """
    if n_results is None:
        n_results = RETRIEVAL_TOP_K
    if score_threshold is None:
        score_threshold = RETRIEVAL_SCORE_THRESHOLD

    model = get_embedding_model()
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    # Check if collection has data
    if collection.count() == 0:
        print("  [RETRIEVER] ChromaDB collection is empty — no results.")
        return []

    # Embed the query
    query_embedding = model.encode([query]).tolist()

    # Build optional metadata filter
    where_filter = None
    scheme = detect_scheme(query)
    category = detect_category(query)

    if scheme:
        where_filter = {"scheme": scheme}
        print(f"  [RETRIEVER] Scheme filter applied: {scheme}")
    elif category:
        where_filter = {"category": category}
        print(f"  [RETRIEVER] Category filter applied: {category}")

    # Query ChromaDB — request extra results to account for threshold filtering
    fetch_count = n_results * 3 if where_filter else n_results * 2
    fetch_count = min(fetch_count, collection.count())

    query_kwargs = {
        "query_embeddings": query_embedding,
        "n_results": fetch_count,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        query_kwargs["where"] = where_filter

    results = collection.query(**query_kwargs)

    # Format and filter results by similarity threshold
    formatted = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        # ChromaDB cosine distance: lower = more similar
        # Convert distance to similarity score (1 - distance for cosine)
        similarity = 1.0 - distance

        if similarity >= score_threshold:
            formatted.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": distance,
                "similarity": similarity,
            })

    # Sort by similarity descending and take top n_results
    formatted.sort(key=lambda x: x["similarity"], reverse=True)
    formatted = formatted[:n_results]

    print(f"  [RETRIEVER] {len(formatted)} results returned "
          f"(threshold={score_threshold}, filter={where_filter})")

    return formatted
