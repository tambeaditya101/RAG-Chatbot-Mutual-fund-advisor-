"""
Streamlit app entry point for the HDFC Mutual Fund FAQ Assistant.

Sets up the page configuration, session state, sidebar disclaimer,
welcome message, example questions, and the chat interface.
"""

import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from app.chat import process_query
from app.ui_components import (
    render_welcome,
    render_disclaimer,
    render_example_questions,
    render_response_with_links,
)

# ─── Page Configuration ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="HDFC Mutual Fund FAQ Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session State Initialization ─────────────────────────────────────────────

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # List of {"role": "user"/"assistant", "content": str}

if "selected_example" not in st.session_state:
    st.session_state.selected_example = None

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📊 HDFC MF FAQ")
    st.caption("Facts-only mutual fund assistant")

    render_disclaimer()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **About this app**

        This assistant retrieves factual information about HDFC mutual fund
        schemes from official Groww sources. Data is refreshed daily via
        automated ingestion.

        **Covered schemes:**
        - HDFC Large Cap Fund
        - HDFC Mid Cap Fund
        - HDFC Small Cap Fund
        - HDFC Multi Cap Fund
        - HDFC Gold ETF FoF
        """
    )

    # Clear chat button
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

# ─── Main Chat Area ───────────────────────────────────────────────────────────

st.title("HDFC Mutual Fund FAQ Assistant")
st.caption("Ask factual questions about HDFC mutual fund schemes")

# Show welcome + examples only when chat is empty
if not st.session_state.chat_history:
    render_welcome()
    render_example_questions()

# ─── Chat Display ─────────────────────────────────────────────────────────────

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_response_with_links(message["content"])
        else:
            st.markdown(message["content"])

# ─── Chat Input ───────────────────────────────────────────────────────────────

def _process_and_respond(query: str) -> None:
    """Process a user query and append the response to chat history."""
    # Append user message
    st.session_state.chat_history.append({"role": "user", "content": query})

    # Process through the pipeline
    with st.spinner("Thinking..."):
        result = process_query(query)

    # Append assistant response
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": result["response"],
    })

    # Rerun to re-render the chat display with the updated history
    st.rerun()


# Handle example question selection (from button clicks)
if st.session_state.selected_example:
    user_input = st.session_state.selected_example
    st.session_state.selected_example = None
    _process_and_respond(user_input)

# Chat input field
if prompt := st.chat_input("Ask about HDFC mutual fund schemes..."):
    _process_and_respond(prompt)
