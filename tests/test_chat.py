"""
Tests for the chat orchestrator module.
Tests the full pipeline routing for factual, advisory, and performance queries.
Uses mocking to avoid actual API calls and ChromaDB queries.
"""

import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from app.chat import process_query


# ─── Mock Data ────────────────────────────────────────────────────────────────

MOCK_CHUNKS = [
    {
        "id": "src_001_chunk_0",
        "document": "Expense Ratio: 0.98%.",
        "metadata": {
            "source_id": "src_001",
            "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "title": "HDFC Large Cap Fund - Direct Growth",
            "scheme": "HDFC Large Cap Fund",
            "category": "large_cap",
            "scrape_date": "2026-05-31",
        },
        "distance": 0.24,
        "similarity": 0.76,
    },
]

MOCK_RAW_ANSWER = "The expense ratio of HDFC Large Cap Fund is 0.98%."


class TestFactualQuery:
    """Test that factual queries route through retrieve → generate → format."""

    @patch("app.chat.format_response")
    @patch("app.chat.generate_answer")
    @patch("app.chat.retrieve")
    @patch("app.chat.classify_query")
    def test_factual_route(self, mock_classify, mock_retrieve, mock_generate, mock_format):
        """Factual query should go through retrieve → generate → format."""
        mock_classify.return_value = "factual"
        mock_retrieve.return_value = MOCK_CHUNKS
        mock_generate.return_value = MOCK_RAW_ANSWER
        mock_format.return_value = (
            "The expense ratio of HDFC Large Cap Fund is 0.98%.\n\n"
            "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth\n"
            "Last updated from sources: 2026-05-31"
        )

        result = process_query("What is the expense ratio of HDFC Large Cap Fund?")

        assert result["intent"] == "factual"
        mock_classify.assert_called_once()
        mock_retrieve.assert_called_once()
        mock_generate.assert_called_once()
        mock_format.assert_called_once()

    @patch("app.chat.format_response")
    @patch("app.chat.generate_answer")
    @patch("app.chat.retrieve")
    @patch("app.chat.classify_query")
    def test_factual_response_format(self, mock_classify, mock_retrieve, mock_generate, mock_format):
        """Factual response should have citation and footer."""
        mock_classify.return_value = "factual"
        mock_retrieve.return_value = MOCK_CHUNKS
        mock_generate.return_value = MOCK_RAW_ANSWER
        mock_format.return_value = (
            f"{MOCK_RAW_ANSWER}\n\n"
            "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth\n"
            "Last updated from sources: 2026-05-31"
        )

        result = process_query("What is the expense ratio of HDFC Large Cap Fund?")

        assert "Source:" in result["response"]
        assert "Last updated from sources:" in result["response"]
        assert result["chunks"] == MOCK_CHUNKS

    @patch("app.chat.retrieve")
    @patch("app.chat.classify_query")
    def test_factual_no_chunks(self, mock_classify, mock_retrieve):
        """Factual query with no retrieved chunks should return fallback message."""
        mock_classify.return_value = "factual"
        mock_retrieve.return_value = []

        result = process_query("What is the expense ratio of some unknown fund?")

        assert result["intent"] == "factual"
        assert "could not find" in result["response"].lower() or \
               "couldn't find" in result["response"].lower()


class TestAdvisoryQuery:
    """Test that advisory queries route to refusal."""

    @patch("app.chat.advisory_refusal")
    @patch("app.chat.classify_query")
    def test_advisory_route(self, mock_classify, mock_refusal):
        """Advisory query should return advisory refusal."""
        mock_classify.return_value = "advisory"
        mock_refusal.return_value = (
            "I'm unable to provide investment advice or recommendations. "
            "This assistant only provides factual, verifiable information "
            "about mutual fund schemes.\n"
            "For guidance on investment decisions, please visit: https://www.amfiindia.com/\n\n"
            "Last updated from sources: 2026-05-31"
        )

        result = process_query("Should I invest in HDFC Large Cap Fund?")

        assert result["intent"] == "advisory"
        mock_refusal.assert_called_once()
        assert result["chunks"] == []

    @patch("app.chat.advisory_refusal")
    @patch("app.chat.classify_query")
    def test_advisory_has_amfi_link(self, mock_classify, mock_refusal):
        """Advisory refusal should contain AMFI link."""
        mock_classify.return_value = "advisory"
        mock_refusal.return_value = (
            "I'm unable to provide investment advice or recommendations. "
            "This assistant only provides factual, verifiable information "
            "about mutual fund schemes.\n"
            "For guidance on investment decisions, please visit: https://www.amfiindia.com/\n\n"
            "Last updated from sources: 2026-05-31"
        )

        result = process_query("Is HDFC Mid Cap Fund a good investment?")
        assert "amfiindia.com" in result["response"]


class TestPerformanceQuery:
    """Test that performance queries route to factsheet refusal."""

    @patch("app.chat.performance_refusal")
    @patch("app.chat.classify_query")
    def test_performance_route(self, mock_classify, mock_refusal):
        """Performance query should return performance refusal."""
        mock_classify.return_value = "performance"
        mock_refusal.return_value = (
            "I cannot provide performance comparisons or return calculations. "
            "For detailed performance data, please refer to the official factsheet: "
            "https://www.amfiindia.com/\n\n"
            "Last updated from sources: 2026-05-31"
        )

        result = process_query("What are the returns of HDFC Small Cap Fund?")

        assert result["intent"] == "performance"
        mock_refusal.assert_called_once()

    @patch("app.chat.performance_refusal")
    @patch("app.chat.classify_query")
    def test_performance_has_factsheet_referral(self, mock_classify, mock_refusal):
        """Performance refusal should direct to factsheet."""
        mock_classify.return_value = "performance"
        mock_refusal.return_value = (
            "I cannot provide performance comparisons or return calculations. "
            "For detailed performance data, please refer to the official factsheet: "
            "https://www.amfiindia.com/\n\n"
            "Last updated from sources: 2026-05-31"
        )

        result = process_query("Which fund has better returns?")
        assert "factsheet" in result["response"].lower()


class TestErrorHandling:
    """Test error handling in the chat orchestrator."""

    @patch("app.chat.classify_query")
    def test_classification_error_defaults_to_factual(self, mock_classify):
        """Classification error should default to factual."""
        mock_classify.side_effect = Exception("API error")

        result = process_query("What is the expense ratio?")

        assert result["intent"] == "factual"

    @patch("app.chat.retrieve")
    @patch("app.chat.classify_query")
    def test_retrieval_error_returns_fallback(self, mock_classify, mock_retrieve):
        """Retrieval error should return a graceful fallback message."""
        mock_classify.return_value = "factual"
        mock_retrieve.side_effect = Exception("ChromaDB error")

        result = process_query("What is the expense ratio?")

        assert "unable to retrieve" in result["response"].lower() or \
               "temporarily" in result["response"].lower()
