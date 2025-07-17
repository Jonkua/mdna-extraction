"""Tests for parser modules, including 10-Q fallback end logic."""

import pytest
from src.parsers.section_parser import SectionParser, SectionBoundary


class TestSectionParser:
    """Test suite for SectionParser including 10-Q fallback logic."""

    @pytest.fixture
    def parser(self):
        return SectionParser()

    def test_find_mdna_section_standard(self, parser):
        text = """
Some intro text.

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION

MD&A content.

ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES
"""
        result = parser.find_mdna_section(text)
        assert result is not None
        start, end = result
        assert 'MD&A content' in text[start:end]
        assert 'QUANTITATIVE AND QUALITATIVE' not in text[start:end]

    def test_find_10q_fallback_end_legal_proceedings(self, parser):
        """Ensure fallback end at 'LEGAL PROCEEDINGS' for 10-Q."""
        content = (
            "ITEM 2. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION\n"
            "This is the MD&A for quarter.\n"
            "Some additional discussion.\n"
            "LEGAL PROCEEDINGS\n"
            "Subsequent text should be excluded."
        )
        # Find start boundary
        section = parser._find_section_start(content, 'item_2_start')
        assert isinstance(section, SectionBoundary)
        # Fallback end
        end_pos = parser._find_10q_fallback_end(content, section.end_pos)
        assert end_pos == content.find('LEGAL PROCEEDINGS')

    def test_find_10q_fallback_end_market_risk(self, parser):
        """Ensure fallback end at 'MARKET RISK DISCLOSURES' for 10-Q."""
        content = (
            "ITEM 2. MD&A Analysis\n"
            "Quarterly review text.\n"
            "MARKET RISK DISCLOSURES\n"
            "Remaining content."
        )
        section = parser._find_section_start(content, 'item_2_start')
        assert isinstance(section, SectionBoundary)
        end_pos = parser._find_10q_fallback_end(content, section.end_pos)
        assert end_pos == content.find('MARKET RISK DISCLOSURES')

    def test_find_10q_fallback_end_none(self, parser):
        """When no fallback end patterns exist, return None."""
        content = (
            "ITEM 2. MD&A Content\n"
            "This MD&A has no clear fallback boundary.\n"
            "Just runs to end."
        )
        section = parser._find_section_start(content, 'item_2_start')
        end_pos = parser._find_10q_fallback_end(content, section.end_pos)
        assert end_pos is None

# Additional parser tests omitted for brevity
