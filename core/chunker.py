"""
Chunker module — splits documents into chunks using LangChain's
RecursiveCharacterTextSplitter with parameters from config.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_SEPARATORS


def get_chunker() -> RecursiveCharacterTextSplitter:
    """
    Create and return a configured RecursiveCharacterTextSplitter.
    Metadata from parent documents is propagated to each chunk.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
        length_function=len,
    )


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Split a list of documents into chunks.

    Each chunk inherits all metadata from its parent document.

    Args:
        documents: List of LangChain Document objects with page_content and metadata.

    Returns:
        List of chunked Document objects with propagated metadata.
    """
    chunker = get_chunker()
    chunks = chunker.split_documents(documents)

    # Verify metadata propagation — each chunk should have source metadata
    for i, chunk in enumerate(chunks):
        if "source_id" not in chunk.metadata:
            print(f"  [CHUNKER] Warning: chunk {i} missing source_id metadata")

    print(f"  [CHUNKER] {len(documents)} documents → {len(chunks)} chunks "
          f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    return chunks
