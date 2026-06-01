"""
Chat orchestrator module.
Orchestrates the full query pipeline:
  query → classify → (advisory? → refusal)
                  → (performance? → factsheet refusal)
                  → (factual? → retrieve → generate → format)

Returns the final formatted response for the user.
"""

from datetime import date
from core.classifier import classify_query
from core.retriever import retrieve, detect_scheme
from core.generator import generate_answer
from core.formatter import format_response
from core.refusal import advisory_refusal, performance_refusal
from config.settings import AMFI_EDUCATION_LINK


def process_query(query: str) -> dict:
    """
    Process a user query through the full pipeline.

    Pipeline flow:
    1. Classify the query intent (factual / advisory / performance)
    2. If advisory → return advisory refusal
    3. If performance → return performance refusal
    4. If factual → retrieve chunks → generate answer → format response

    Args:
        query: The user's raw query string.

    Returns:
        Dict with keys:
          - "response": The final formatted response string
          - "intent": The classified intent ("factual", "advisory", "performance")
          - "chunks": Retrieved chunks (empty list for non-factual queries)
    """
    result = {
        "response": "",
        "intent": "",
        "chunks": [],
    }

    # Step 1: Classify intent
    try:
        intent = classify_query(query)
    except Exception as e:
        print(f"  [CHAT] Classification error: {e}, defaulting to 'factual'")
        intent = "factual"

    result["intent"] = intent

    # Step 2: Route based on intent
    if intent == "advisory":
        result["response"] = advisory_refusal()
        print(f"  [CHAT] Advisory query → refusal response")
        return result

    if intent == "performance":
        # Try to find a relevant factsheet URL for the performance refusal
        factsheet_url = None
        scheme = detect_scheme(query)
        if scheme:
            # Retrieve one chunk just to get the URL for the factsheet link
            try:
                chunks = retrieve(query, n_results=1)
                if chunks:
                    factsheet_url = chunks[0].get("metadata", {}).get("url")
                    scrape_date = chunks[0].get("metadata", {}).get("scrape_date")
                    result["response"] = performance_refusal(
                        factsheet_url=factsheet_url,
                        scrape_date=scrape_date,
                    )
                    print(f"  [CHAT] Performance query → factsheet refusal ({factsheet_url})")
                    return result
            except Exception:
                pass

        result["response"] = performance_refusal()
        print(f"  [CHAT] Performance query → factsheet refusal (default)")
        return result

    # Step 3: Factual query → retrieve → generate → format
    try:
        chunks = retrieve(query)
    except Exception as e:
        print(f"  [CHAT] Retrieval error: {e}")
        result["response"] = (
            "I'm temporarily unable to retrieve information. "
            f"Please check the official source: {AMFI_EDUCATION_LINK}\n\n"
            f"Last updated from sources: {date.today()}"
        )
        return result

    result["chunks"] = chunks

    if not chunks:
        result["response"] = (
            "I couldn't find relevant information on this topic. "
            f"Please check the official source: {AMFI_EDUCATION_LINK}\n\n"
            f"Last updated from sources: {date.today()}"
        )
        print(f"  [CHAT] No chunks retrieved for factual query")
        return result

    # Generate answer
    try:
        raw_answer = generate_answer(query, chunks)
    except Exception as e:
        print(f"  [CHAT] Generation error: {e}")
        # Still format what we can with the chunks metadata
        raw_answer = "I'm temporarily unable to process your query."

    # Format the response
    formatted = format_response(raw_answer, chunks)

    result["response"] = formatted
    print(f"  [CHAT] Factual query → formatted response ({len(chunks)} chunks)")

    return result
