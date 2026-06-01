"""
Intent classification module.
Classifies user queries as factual, advisory, or performance
using the Groq LLM with a classification prompt.
"""

import os
from langchain_groq import ChatGroq
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE

# Valid classification labels
VALID_LABELS = {"factual", "advisory", "performance"}

# Path to the classification prompt template
_CLASSIFY_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompts",
    "classify_prompt.txt",
)

# Module-level prompt cache
_classify_prompt_template: str | None = None


def _load_classify_prompt() -> str:
    """Load and cache the classification prompt template."""
    global _classify_prompt_template
    if _classify_prompt_template is None:
        with open(_CLASSIFY_PROMPT_PATH, "r") as f:
            _classify_prompt_template = f.read().strip()
    return _classify_prompt_template


def _get_llm() -> ChatGroq:
    """Create a ChatGroq instance for classification."""
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=GROQ_TEMPERATURE,
        max_tokens=10,  # Classification needs only one word
    )


def classify_query(query: str) -> str:
    """
    Classify a user query as factual, advisory, or performance.

    Args:
        query: The user's query string.

    Returns:
        One of "factual", "advisory", or "performance".
        Defaults to "factual" on errors or unexpected responses.
    """
    if not query or not query.strip():
        return "factual"

    try:
        prompt_template = _load_classify_prompt()
        prompt = prompt_template.format(query=query)

        llm = _get_llm()
        response = llm.invoke(prompt)

        label = response.content.strip().lower()

        # Extract just the classification word if LLM returns extra text
        for valid_label in VALID_LABELS:
            if valid_label in label:
                return valid_label

        # Default to factual if classification is unclear
        print(f"  [CLASSIFIER] Unexpected label: '{label}', defaulting to 'factual'")
        return "factual"

    except Exception as e:
        print(f"  [CLASSIFIER] Error classifying query: {e}")
        return "factual"
