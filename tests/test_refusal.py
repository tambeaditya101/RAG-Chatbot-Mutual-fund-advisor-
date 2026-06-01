"""
Tests for the refusal handler module.
Verifies advisory and performance refusal templates.
"""

import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.refusal import advisory_refusal, performance_refusal
from config.settings import AMFI_EDUCATION_LINK, FOOTER_TEMPLATE


class TestAdvisoryRefusal:
    """Test the advisory refusal template."""

    def test_returns_string(self):
        result = advisory_refusal()
        assert isinstance(result, str)

    def test_contains_refusal_language(self):
        """Should clearly state inability to provide investment advice."""
        result = advisory_refusal()
        assert "unable to provide investment advice" in result.lower() or \
               "cannot provide investment advice" in result.lower()

    def test_contains_amfi_link(self):
        """Should include AMFI educational link."""
        result = advisory_refusal()
        assert AMFI_EDUCATION_LINK in result

    def test_contains_footer(self):
        """Should include the date footer."""
        result = advisory_refusal()
        assert "Last updated from sources:" in result

    def test_polite_tone(self):
        """Should use polite language (e.g., 'please visit')."""
        result = advisory_refusal()
        assert "please" in result.lower()

    def test_facts_only_scope(self):
        """Should explain the facts-only scope."""
        result = advisory_refusal()
        assert "factual" in result.lower()

    def test_custom_scrape_date(self):
        """Should use the provided scrape_date in footer."""
        result = advisory_refusal(scrape_date="2026-05-31")
        assert "2026-05-31" in result

    def test_default_date(self):
        """Without scrape_date, should use today's date."""
        from datetime import date
        today = str(date.today())
        result = advisory_refusal()
        assert today in result


class TestPerformanceRefusal:
    """Test the performance refusal template."""

    def test_returns_string(self):
        result = performance_refusal()
        assert isinstance(result, str)

    def test_contains_refusal_language(self):
        """Should refuse performance comparisons or return calculations."""
        result = performance_refusal()
        assert "cannot provide performance" in result.lower() or \
               "unable to provide performance" in result.lower()

    def test_default_contains_amfi_link(self):
        """Without factsheet_url, should fall back to AMFI link."""
        result = performance_refusal()
        assert AMFI_EDUCATION_LINK in result

    def test_custom_factsheet_url(self):
        """Should use the provided factsheet URL."""
        url = "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
        result = performance_refusal(factsheet_url=url)
        assert url in result

    def test_contains_footer(self):
        """Should include the date footer."""
        result = performance_refusal()
        assert "Last updated from sources:" in result

    def test_custom_scrape_date(self):
        """Should use the provided scrape_date in footer."""
        result = performance_refusal(scrape_date="2026-05-31")
        assert "2026-05-31" in result

    def test_factsheet_referral(self):
        """Should direct user to the official factsheet."""
        result = performance_refusal()
        assert "factsheet" in result.lower()

    def test_none_factsheet_uses_amfi(self):
        """None factsheet_url should use AMFI as fallback."""
        result = performance_refusal(factsheet_url=None)
        assert AMFI_EDUCATION_LINK in result

    def test_empty_string_factsheet_uses_amfi(self):
        """Empty string factsheet_url should use AMFI as fallback."""
        result = performance_refusal(factsheet_url="")
        assert AMFI_EDUCATION_LINK in result
