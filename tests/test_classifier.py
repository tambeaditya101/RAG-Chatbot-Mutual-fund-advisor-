"""
Tests for the intent classifier module.
Tests classification of factual, advisory, and performance queries.
"""

import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.classifier import classify_query, VALID_LABELS


# ─── Factual Queries ──────────────────────────────────────────────────────────

FACTUAL_QUERIES = [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the exit load for HDFC Mid Cap Fund?",
    "What is the minimum SIP amount for HDFC Small Cap Fund?",
    "What category does the HDFC Gold ETF FoF belong to?",
    "Who is the fund manager of HDFC Multi Cap Fund?",
]

# ─── Advisory Queries ─────────────────────────────────────────────────────────

ADVISORY_QUERIES = [
    "Should I invest in HDFC Large Cap Fund?",
    "Which fund is better for retirement?",
    "Is HDFC Mid Cap Fund a good investment?",
    "What is the best mutual fund for long-term growth?",
    "Can you recommend a fund for tax saving?",
]

# ─── Performance Queries ──────────────────────────────────────────────────────

PERFORMANCE_QUERIES = [
    "What are the returns of HDFC Small Cap Fund?",
    "How has HDFC Large Cap Fund performed over the last 3 years?",
    "What is the 1-year return of HDFC Gold ETF FoF?",
]


class TestClassifierLabels:
    """Test that classify_query returns valid labels."""

    def test_empty_query_returns_factual(self):
        """Empty query defaults to factual."""
        result = classify_query("")
        assert result == "factual"

    def test_whitespace_query_returns_factual(self):
        """Whitespace-only query defaults to factual."""
        result = classify_query("   ")
        assert result == "factual"

    def test_valid_labels(self):
        """All possible labels are in the valid set."""
        assert VALID_LABELS == {"factual", "advisory", "performance"}


class TestFactualQueries:
    """Test that factual queries are classified as 'factual'."""

    @pytest.mark.parametrize("query", FACTUAL_QUERIES)
    def test_factual_classification(self, query):
        """Each factual query should be classified as 'factual'."""
        result = classify_query(query)
        assert result == "factual", f"Query '{query}' classified as '{result}', expected 'factual'"


class TestAdvisoryQueries:
    """Test that advisory queries are classified as 'advisory'."""

    @pytest.mark.parametrize("query", ADVISORY_QUERIES)
    def test_advisory_classification(self, query):
        """Each advisory query should be classified as 'advisory'."""
        result = classify_query(query)
        assert result == "advisory", f"Query '{query}' classified as '{result}', expected 'advisory'"


class TestPerformanceQueries:
    """Test that performance queries are classified as 'performance'."""

    @pytest.mark.parametrize("query", PERFORMANCE_QUERIES)
    def test_performance_classification(self, query):
        """Each performance query should be classified as 'performance'."""
        result = classify_query(query)
        assert result == "performance", f"Query '{query}' classified as '{result}', expected 'performance'"
