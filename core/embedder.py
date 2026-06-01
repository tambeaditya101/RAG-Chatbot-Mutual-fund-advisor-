"""
Embedding and ChromaDB storage module.
Embeds text chunks using BGE bge-small-en-v1.5 and stores them
in a persistent ChromaDB collection.
"""

import chromadb
from sentence_transformers import SentenceTransformer
from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
)


# Module-level model singleton — loaded once and reused
_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Load and cache the BGE embedding model (singleton pattern)."""
    global _model
    if _model is None:
        print(f"  [EMBEDDER] Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"  [EMBEDDER] Model loaded. Embedding dim: {_model.get_embedding_dimension()}")
    return _model


def get_chroma_client() -> chromadb.PersistentClient:
    """Create and return a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_or_create_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """Get or create the mutual_fund_faq collection."""
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_and_store(chunks: list) -> int:
    """
    Embed text chunks and store them in ChromaDB.

    For each chunk:
    - Generate embedding via BGE bge-small-en-v1.5
    - Store in ChromaDB with the chunk text and metadata

    If the collection already contains documents, it will be reset
    to avoid duplicates from re-ingestion.

    Args:
        chunks: List of LangChain Document objects (from chunker).

    Returns:
        Number of chunks successfully stored.
    """
    if not chunks:
        print("  [EMBEDDER] No chunks to embed.")
        return 0

    model = get_embedding_model()
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    # Reset collection to avoid duplicates on re-ingestion
    existing_count = collection.count()
    if existing_count > 0:
        print(f"  [EMBEDDER] Clearing existing collection ({existing_count} docs)")
        client.delete_collection(CHROMA_COLLECTION_NAME)
        collection = get_or_create_collection(client)

    # Prepare batch data
    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    # Generate unique IDs for each chunk
    ids = [f"{meta['source_id']}_chunk_{i}" for i, meta in enumerate(metadatas)]

    # Generate embeddings
    print(f"  [EMBEDDER] Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32).tolist()

    # Store in ChromaDB
    print(f"  [EMBEDDER] Storing {len(texts)} chunks in ChromaDB...")
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    final_count = collection.count()
    print(f"  [EMBEDDER] Stored {final_count} chunks in collection '{CHROMA_COLLECTION_NAME}'")

    return final_count


def similarity_search(query: str, n_results: int = 3) -> list[dict]:
    """
    Perform a similarity search against the ChromaDB collection.

    Args:
        query: The search query string.
        n_results: Number of results to return.

    Returns:
        List of result dicts with 'document', 'metadata', and 'distance' keys.
    """
    model = get_embedding_model()
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    # Embed the query
    query_embedding = model.encode([query]).tolist()

    # Search
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    # Format results
    formatted = []
    for i in range(len(results["ids"][0])):
        formatted.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })

    return formatted
