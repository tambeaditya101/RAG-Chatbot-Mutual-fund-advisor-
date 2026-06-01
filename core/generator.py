"""
Answer generation module.
Constructs a constrained prompt from retrieved context and calls
the Groq LLM to generate a factual answer.
"""

import os
from langchain_groq import ChatGroq
from config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
)

# Path to the answer generation prompt template
_ANSWER_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompts",
    "answer_prompt.txt",
)

# Module-level prompt cache
_answer_prompt_template: str | None = None


def _load_answer_prompt() -> str:
    """Load and cache the answer generation prompt template."""
    global _answer_prompt_template
    if _answer_prompt_template is None:
        with open(_ANSWER_PROMPT_PATH, "r") as f:
            _answer_prompt_template = f.read().strip()
    return _answer_prompt_template


def _get_llm() -> ChatGroq:
    """Create a ChatGroq instance for answer generation."""
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
    )


def _format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a context string for the LLM prompt.

    Each chunk includes its text content and source metadata (url, title, scheme).

    Args:
        chunks: List of retrieved chunk dicts with 'document' and 'metadata' keys.

    Returns:
        Formatted context string.
    """
    if not chunks:
        return "No relevant context available."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get("document", "")
        meta = chunk.get("metadata", {})
        url = meta.get("url", "N/A")
        title = meta.get("title", "Unknown")
        scheme = meta.get("scheme", "Unknown")

        context_parts.append(
            f"[Source {i}]\n"
            f"Title: {title}\n"
            f"Scheme: {scheme}\n"
            f"URL: {url}\n"
            f"Content: {text}"
        )

    return "\n\n".join(context_parts)


def generate_answer(query: str, chunks: list[dict]) -> str:
    """
    Generate a factual answer to the query using retrieved context.

    Args:
        query: The user's query string.
        chunks: List of retrieved chunk dicts from the retriever.

    Returns:
        The raw LLM response string.
        Returns an error message string if generation fails.
    """
    if not query or not query.strip():
        return "Please provide a valid question."

    if not chunks:
        return (
            "I could not find relevant information. "
            "Please check the official source: https://www.amfiindia.com/"
        )

    try:
        prompt_template = _load_answer_prompt()
        context = _format_context(chunks)
        prompt = prompt_template.format(context=context, query=query)

        llm = _get_llm()
        response = llm.invoke(prompt)

        return response.content.strip()

    except Exception as e:
        print(f"  [GENERATOR] Error generating answer: {e}")
        return (
            "I'm temporarily unable to process your query. Please try again later."
        )
