"""
UI components module for the Streamlit app.
Provides reusable UI elements: welcome message, disclaimer banner,
and clickable example questions.
"""

import streamlit as st
from config.settings import DISCLAIMER_TEXT

# ─── Example Questions ────────────────────────────────────────────────────────

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the exit load for HDFC Mid Cap Fund?",
    "What category does the HDFC Gold ETF FoF belong to?",
]


def render_welcome() -> None:
    """Render the welcome message explaining the facts-only scope of the assistant."""
    st.markdown(
        """
        👋 **Welcome to the HDFC Mutual Fund FAQ Assistant!**

        I can help you find **factual, verifiable information** about HDFC mutual fund
        schemes — such as expense ratios, exit loads, minimum SIP amounts, risk levels,
        and more.

        ⚠️ **I do not provide investment advice, recommendations, or performance comparisons.**

        Try asking a question below, or click one of the examples to get started.
        """
    )


def render_disclaimer() -> None:
    """Render the persistent disclaimer banner in the sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.warning(f"⚠️ **{DISCLAIMER_TEXT}**")
    st.sidebar.markdown(
        """
        This assistant provides only factual, verifiable information
        about HDFC mutual fund schemes from official sources.

        - No investment advice
        - No performance comparisons
        - No recommendations

        For investment guidance, visit [AMFI](https://www.amfiindia.com/)
        """
    )


def render_example_questions() -> None:
    """
    Render 3 clickable example question buttons.

    When a button is clicked, the question text is stored in
    session state under the key "selected_example" so the
    main app can pick it up and process it.
    """
    st.markdown("**Try an example question:**")

    cols = st.columns(len(EXAMPLE_QUESTIONS))
    for i, (col, question) in enumerate(zip(cols, EXAMPLE_QUESTIONS)):
        with col:
            # Use a short label for the button
            label = question
            if len(label) > 50:
                label = label[:47] + "..."
            if st.button(label, key=f"example_{i}"):
                st.session_state["selected_example"] = question


def render_response_with_links(response: str) -> None:
    """
    Render a chat response, converting URLs to clickable hyperlinks.

    Detects URLs in the response text (especially in the Source line)
    and renders them as clickable markdown links.

    Args:
        response: The formatted response string from the pipeline.
    """
    # Process line by line to handle URLs and formatting
    lines = response.split("\n")
    rendered_parts = []

    for line in lines:
        if not line.strip():
            rendered_parts.append("")
            continue

        # Check if this is a Source line with a URL
        if line.strip().startswith("Source:"):
            url = line.strip().replace("Source:", "").strip()
            rendered_parts.append(f"📎 **Source:** [{url}]({url})")
        elif line.strip().startswith("Last updated from sources:"):
            rendered_parts.append(f"📅 *{line.strip()}*")
        else:
            rendered_parts.append(line)

    st.markdown("\n".join(rendered_parts))
