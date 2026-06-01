"""
Tests for the response formatter module.
Verifies sentence count enforcement, citation injection, and footer injection.
"""

import sys
import os
import re

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.formatter import format_response, _split_sentences
from config.settings import MAX_SENTENCES, CITATION_TEMPLATE, FOOTER_TEMPLATE, AMFI_EDUCATION_LINK


# ─── Sample chunks for testing ────────────────────────────────────────────────

SAMPLE_CHUNKS = [
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
    {
        "id": "src_002_chunk_0",
        "document": "Exit Load: 1% for units redeemed within 1 year.",
        "metadata": {
            "source_id": "src_002",
            "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "title": "HDFC Mid Cap Fund - Direct Growth",
            "scheme": "HDFC Mid Cap Fund",
            "category": "mid_cap",
            "scrape_date": "2026-05-31",
        },
        "distance": 0.28,
        "similarity": 0.72,
    },
]


# ─── Sentence Splitting Tests ─────────────────────────────────────────────────

class TestSplitSentences:
    """Test the sentence splitting helper."""

    def test_simple_sentences(self):
        text = "First sentence. Second sentence. Third sentence."
        sents = _split_sentences(text)
        assert len(sents) == 3

    def test_empty_string(self):
        assert _split_sentences("") == []

    def test_single_sentence(self):
        sents = _split_sentences("Just one sentence here.")
        assert len(sents) == 1

    def test_question_mark(self):
        sents = _split_sentences("What is the expense ratio? It is 0.98%.")
        assert len(sents) == 2

    def test_exclamation_mark(self):
        sents = _split_sentences("This is important! Note it well.")
        assert len(sents) == 2


# ─── Formatter Constraint Tests ───────────────────────────────────────────────

class TestFormatResponse:
    """Test the format_response function enforces all constraints."""

    def test_empty_response(self):
        """Empty raw response should produce a fallback message."""
        result = format_response("", SAMPLE_CHUNKS)
        assert "could not find" in result.lower() or "check the official" in result.lower()

    def test_none_response(self):
        """None raw response should produce a fallback message."""
        result = format_response(None, SAMPLE_CHUNKS)
        assert "could not find" in result.lower() or "check the official" in result.lower()

    def test_single_sentence(self):
        """1-sentence response should pass through with citation + footer."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, SAMPLE_CHUNKS)
        assert "0.98%" in result
        assert "Source:" in result
        assert "Last updated from sources:" in result

    def test_three_sentences(self):
        """3-sentence response should pass through intact."""
        raw = "The expense ratio is 0.98%. This is a direct plan. The fund is managed by HDFC."
        result = format_response(raw, SAMPLE_CHUNKS)
        # Count answer sentences (before citation/footer section)
        answer_section = result.split("\n\n")[0]
        sents = _split_sentences(answer_section)
        assert len(sents) <= MAX_SENTENCES

    def test_five_sentences_truncated(self):
        """5-sentence response should be truncated to 3."""
        raw = (
            "The expense ratio is 0.98%. "
            "This is a direct plan. "
            "The fund is managed by HDFC. "
            "It was launched in 2005. "
            "The AUM is very large."
        )
        result = format_response(raw, SAMPLE_CHUNKS)
        answer_section = result.split("\n\n")[0]
        sents = _split_sentences(answer_section)
        assert len(sents) <= MAX_SENTENCES

    def test_ten_sentences_truncated(self):
        """10-sentence response should be truncated to 3."""
        raw = ". ".join([
            "Sentence one", "Sentence two", "Sentence three",
            "Sentence four", "Sentence five", "Sentence six",
            "Sentence seven", "Sentence eight", "Sentence nine", "Sentence ten",
        ]) + "."
        result = format_response(raw, SAMPLE_CHUNKS)
        answer_section = result.split("\n\n")[0]
        sents = _split_sentences(answer_section)
        assert len(sents) <= MAX_SENTENCES

    def test_citation_present(self):
        """Formatted response must include a Source citation."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, SAMPLE_CHUNKS)
        assert "Source:" in result

    def test_citation_url_from_chunk(self):
        """Citation should use the URL from the top chunk metadata."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, SAMPLE_CHUNKS)
        expected_url = SAMPLE_CHUNKS[0]["metadata"]["url"]
        assert expected_url in result

    def test_footer_present(self):
        """Formatted response must include the date footer."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, SAMPLE_CHUNKS)
        assert "Last updated from sources:" in result

    def test_footer_date_from_chunk(self):
        """Footer should use the scrape_date from top chunk metadata."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, SAMPLE_CHUNKS)
        expected_date = SAMPLE_CHUNKS[0]["metadata"]["scrape_date"]
        assert expected_date in result

    def test_no_chunks_fallback_citation(self):
        """Without chunks, citation should fall back to AMFI link."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, [])
        assert AMFI_EDUCATION_LINK in result

    def test_no_chunks_fallback_footer(self):
        """Without chunks, footer should use today's date."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, [])
        assert "Last updated from sources:" in result

    def test_none_chunks_fallback(self):
        """None chunks should fall back gracefully."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, None)
        assert "Source:" in result
        assert "Last updated from sources:" in result

    def test_llm_generated_citation_not_duplicated(self):
        """If LLM already included a 'Source:' line, don't duplicate it."""
        raw = "The expense ratio is 0.98%. Source: https://example.com"
        result = format_response(raw, SAMPLE_CHUNKS)
        # Should have exactly one "Source:" line in the output
        source_count = result.lower().count("source:")
        assert source_count == 1

    def test_llm_generated_footer_not_duplicated(self):
        """If LLM already included a footer line, don't duplicate it."""
        raw = "The expense ratio is 0.98%. Last updated from sources: 2026-01-01"
        result = format_response(raw, SAMPLE_CHUNKS)
        footer_count = result.lower().count("last updated from sources:")
        assert footer_count == 1

    def test_full_format_structure(self):
        """Complete formatted response should follow the template structure."""
        raw = "The expense ratio is 0.98%."
        result = format_response(raw, SAMPLE_CHUNKS)

        # Should have: answer text, blank line, Source citation, footer
        lines = result.split("\n")
        assert len(lines) >= 3  # At least answer + source + footer

        # Verify citation line
        citation_line = [l for l in lines if l.startswith("Source:")]
        assert len(citation_line) == 1

        # Verify footer line
        footer_line = [l for l in lines if l.startswith("Last updated from sources:")]
        assert len(footer_line) == 1
