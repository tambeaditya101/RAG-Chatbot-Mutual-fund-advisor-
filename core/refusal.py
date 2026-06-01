"""
Refusal handler module.
Generates template-based refusal responses for advisory and
performance queries, enforcing compliance guardrails.
"""

import os
from datetime import date
from config.settings import (
    AMFI_EDUCATION_LINK,
    SEBI_EDUCATION_LINK,
    FOOTER_TEMPLATE,
    DISCLAIMER_TEXT,
)

# Path to optional refusal prompt template
_REFUSAL_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompts",
    "refusal_prompt.txt",
)

# Module-level prompt cache
_refusal_prompt_template: str | None = None


def _load_refusal_prompt() -> str | None:
    """Load and cache the refusal prompt template if it exists."""
    global _refusal_prompt_template
    if _refusal_prompt_template is None:
        if os.path.exists(_REFUSAL_PROMPT_PATH):
            with open(_REFUSAL_PROMPT_PATH, "r") as f:
                _refusal_prompt_template = f.read().strip()
    return _refusal_prompt_template


def advisory_refusal(scrape_date: str | None = None) -> str:
    """
    Generate a refusal response for advisory queries.

    Template per architecture.md §4.5:
    - Polite refusal
    - Explanation of facts-only scope
    - AMFI educational link
    - Disclaimer reinforcement
    - Date footer

    Args:
        scrape_date: The scrape date for the footer. Defaults to today.

    Returns:
        Formatted refusal response string.
    """
    if scrape_date is None:
        scrape_date = str(date.today())

    footer = FOOTER_TEMPLATE.format(date=scrape_date)

    return (
        "I'm unable to provide investment advice or recommendations. "
        "This assistant only provides factual, verifiable information "
        "about mutual fund schemes.\n"
        f"For guidance on investment decisions, please visit: {AMFI_EDUCATION_LINK}\n\n"
        f"{footer}"
    )


def performance_refusal(
    factsheet_url: str | None = None,
    scrape_date: str | None = None,
) -> str:
    """
    Generate a refusal response for performance/comparison queries.

    Template per architecture.md §4.5:
    - Refusal to compare or calculate returns
    - Link to relevant factsheet (or AMFI as fallback)
    - Disclaimer reinforcement
    - Date footer

    Args:
        factsheet_url: URL of the relevant factsheet. Falls back to AMFI link.
        scrape_date: The scrape date for the footer. Defaults to today.

    Returns:
        Formatted refusal response string.
    """
    if scrape_date is None:
        scrape_date = str(date.today())

    url = factsheet_url or AMFI_EDUCATION_LINK
    footer = FOOTER_TEMPLATE.format(date=scrape_date)

    return (
        "I cannot provide performance comparisons or return calculations. "
        f"For detailed performance data, please refer to the official factsheet: {url}\n\n"
        f"{footer}"
    )
