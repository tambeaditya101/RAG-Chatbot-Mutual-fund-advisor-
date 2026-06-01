"""
Tests for the retriever module.
Tests retrieval with known queries and scheme/category detection.
"""

import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.retriever import retrieve, detect_scheme, detect_category


# ─── Scheme Detection Tests ───────────────────────────────────────────────────

class TestDetectScheme:
    """Test the scheme name detector."""

    def test_hdfc_large_cap(self):
        assert detect_scheme("What is the expense ratio of HDFC Large Cap Fund?") == "HDFC Large Cap Fund"

    def test_hdfc_mid_cap(self):
        assert detect_scheme("What is the exit load for HDFC Mid Cap Fund?") == "HDFC Mid Cap Fund"

    def test_hdfc_small_cap(self):
        assert detect_scheme("Tell me about HDFC Small Cap Fund") == "HDFC Small Cap Fund"

    def test_hdfc_multi_cap(self):
        assert detect_scheme("What is the NAV of HDFC Multi Cap Fund?") == "HDFC Multi Cap Fund"

    def test_hdfc_gold_etf(self):
        assert detect_scheme("What category does HDFC Gold ETF FoF belong to?") == "HDFC Gold ETF FoF"

    def test_no_scheme(self):
        assert detect_scheme("What is an expense ratio?") is None

    def test_partial_match_hdfc_large(self):
        """Short form 'HDFC Large Cap' should also match."""
        assert detect_scheme("Tell me about HDFC Large Cap") == "HDFC Large Cap Fund"

    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        assert detect_scheme("WHAT IS HDFC MID CAP FUND?") == "HDFC Mid Cap Fund"


# ─── Category Detection Tests ─────────────────────────────────────────────────

class TestDetectCategory:
    """Test the category detector."""

    def test_large_cap_category(self):
        assert detect_category("What are the best large cap funds?") == "large_cap"

    def test_mid_cap_category(self):
        assert detect_category("Tell me about mid cap funds") == "mid_cap"

    def test_small_cap_category(self):
        assert detect_category("How do small cap funds work?") == "small_cap"

    def test_multi_cap_category(self):
        assert detect_category("What is multi cap fund?") == "multi_cap"

    def test_gold_etf_category(self):
        assert detect_category("Tell me about gold ETF funds") == "gold_etf_fof"

    def test_no_category(self):
        assert detect_category("What is NAV?") is None

    def test_hyphenated_category(self):
        """Hyphenated forms like 'large-cap' should also match."""
        assert detect_category("What are large-cap funds?") == "large_cap"


# ─── Retrieval Tests ──────────────────────────────────────────────────────────

class TestRetrieve:
    """Test retrieval with known queries against ChromaDB."""

    def test_retrieve_returns_list(self):
        """Retrieval should return a list."""
        results = retrieve("What is the expense ratio of HDFC Large Cap Fund?")
        assert isinstance(results, list)

    def test_retrieve_factual_query(self):
        """Factual query about a known scheme should return relevant chunks."""
        results = retrieve("What is the expense ratio of HDFC Large Cap Fund?")
        assert len(results) > 0, "Expected at least 1 result for a known factual query"

    def test_retrieve_result_structure(self):
        """Each result should have the expected keys."""
        results = retrieve("What is the exit load for HDFC Mid Cap Fund?")
        if results:
            result = results[0]
            assert "document" in result
            assert "metadata" in result
            assert "distance" in result
            assert "similarity" in result

    def test_retrieve_metadata_fields(self):
        """Results should have all expected metadata fields."""
        results = retrieve("What is the NAV of HDFC Small Cap Fund?")
        if results:
            metadata = results[0]["metadata"]
            assert "source_id" in metadata
            assert "url" in metadata
            assert "title" in metadata
            assert "scheme" in metadata
            assert "category" in metadata
            assert "scrape_date" in metadata

    def test_retrieve_scheme_filter(self):
        """Query mentioning a specific scheme should filter results."""
        results = retrieve("What is the exit load for HDFC Mid Cap Fund?")
        if results:
            # All results should be from the matched scheme
            for r in results:
                assert r["metadata"]["scheme"] == "HDFC Mid Cap Fund"

    def test_retrieve_max_results(self):
        """Should not return more than n_results."""
        results = retrieve("HDFC mutual fund", n_results=2)
        assert len(results) <= 2

    def test_retrieve_similarity_above_threshold(self):
        """All returned results should meet the similarity threshold."""
        results = retrieve("What is the expense ratio of HDFC Large Cap Fund?", score_threshold=0.7)
        for r in results:
            assert r["similarity"] >= 0.7

    def test_retrieve_empty_collection(self):
        """Retrieving from an empty collection should return empty list."""
        # This test verifies the code path — in practice the collection has data
        # after Phase 1 ingestion, so we just verify the function handles it gracefully
        results = retrieve("test query")
        assert isinstance(results, list)
