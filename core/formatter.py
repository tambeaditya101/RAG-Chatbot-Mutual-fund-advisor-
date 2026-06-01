"""
Response formatting module.
Post-processes raw LLM output to enforce format constraints:
1. Sentence count enforcement — truncate to ≤3 sentences
2. Citation injection — append Source: {url} from top chunk metadata
3. Footer injection — append Last updated from sources: {scrape_date}
"""

import re
from datetime import date
from config.settings import MAX_SENTENCES, CITATION_TEMPLATE, FOOTER_TEMPLATE, AMFI_EDUCATION_LINK


def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences using punctuation boundaries.

    Handles common abbreviations (e.g., "Mr.", "Rs.", "N.A.") to
    avoid false sentence splits.

    Args:
        text: The text to split into sentences.

    Returns:
        List of sentence strings.
    """
    if not text or not text.strip():
        return []

    # Common abbreviations that should NOT trigger a sentence split
    abbreviations = [
        r"Mr\.", r"Mrs\.", r"Ms\.", r"Dr\.", r"Prof\.",
        r"Rs\.", r"No\.", r"N\.A\.", r"e\.g\.", r"i\.e\.",
        r"vs\.", r"approx\.", r"inc\.", r"ltd\.",
    ]

    # Temporarily replace abbreviations with placeholders
    working = text
    placeholders = {}
    for i, abbr in enumerate(abbreviations):
        placeholder = f"__ABBR{i}__"
        working = re.sub(abbr, placeholder, working, flags=re.IGNORECASE)
        placeholders[placeholder] = abbr.replace(r"\.", ".")

    # Split on sentence-ending punctuation followed by space and capital letter
    # or end of string
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', working)

    # Restore abbreviations
    result = []
    for sent in sentences:
        for placeholder, original in placeholders.items():
            sent = sent.replace(placeholder, original)
        sent = sent.strip()
        if sent:
            result.append(sent)

    return result


def format_response(
    raw_response: str,
    chunks: list[dict] | None = None,
) -> str:
    """
    Format the raw LLM response to enforce all response constraints.

    Applies in order:
    1. Sentence count enforcement (≤ MAX_SENTENCES)
    2. Citation injection (Source: URL from top chunk metadata)
    3. Footer injection (Last updated from sources: date)

    Args:
        raw_response: The raw LLM output string.
        chunks: List of retrieved chunk dicts with 'metadata' keys.
                Used for citation URL and scrape date. May be empty/None.

    Returns:
        Formatted response string meeting all constraints.
    """
    if not raw_response or not raw_response.strip():
        url = AMFI_EDUCATION_LINK
        today = str(date.today())
        return (
            "I could not find specific information on this. "
            f"Please check the official source: {url}\n\n"
            f"{FOOTER_TEMPLATE.format(date=today)}"
        )

    # Extract metadata from top chunk for citation and footer
    top_meta = {}
    if chunks and len(chunks) > 0:
        top_meta = chunks[0].get("metadata", {})

    citation_url = top_meta.get("url", AMFI_EDUCATION_LINK)
    scrape_date = top_meta.get("scrape_date", str(date.today()))

    # Step 1: Sentence count enforcement
    sentences = _split_sentences(raw_response)

    # Remove any existing citation/footer lines that the LLM may have included
    # to avoid duplication (we'll inject our own)
    filtered_sentences = []
    for sent in sentences:
        lower = sent.lower().strip()
        # Skip if this looks like a citation or footer line the LLM generated
        if lower.startswith("source:") or lower.startswith("last updated"):
            continue
        # Skip if it's just a bare URL
        if re.match(r'^https?://\S+$', sent.strip()):
            continue
        filtered_sentences.append(sent)

    # Truncate to max sentences
    truncated = filtered_sentences[:MAX_SENTENCES]

    if not truncated:
        # If all sentences were citations/footers, use a generic message
        truncated = ["I could not find specific information on this."]

    answer_text = " ".join(truncated)

    # Step 2: Citation injection
    citation = CITATION_TEMPLATE.format(url=citation_url)

    # Step 3: Footer injection
    footer = FOOTER_TEMPLATE.format(date=scrape_date)

    # Compose final response
    formatted = f"{answer_text}\n\n{citation}\n{footer}"

    return formatted
