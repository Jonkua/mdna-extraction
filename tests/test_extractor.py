import pytest
from pathlib import Path
from datetime import datetime

from src.core.extractor import MDNAExtractor
from src.core.zip_processor import ZipProcessor
from src.models.filing import Filing, ExtractionResult
from src.utils.logger import setup_logging


class TestMDNAExtractor:
    """Test suite for MDNAExtractor and 10-Q fallback logic."""

    @pytest.fixture(autouse=True)
    def init_logging(self):
        setup_logging(verbose=False)

    @pytest.fixture
    def extractor(self, tmp_path):
        return MDNAExtractor(tmp_path)

    @pytest.fixture
    def sample_10k_content(self):
        return """
FORM 10-K

CIK: 0001234567
FILED AS OF DATE: 03/15/2024

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Overview

Detail about operations.

ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK
"""

    @pytest.fixture
    def sample_10q_content(self):
        return """
FORM 10-Q

CIK: 0001234567
PERIOD OF REPORT: 06/30/2024

ITEM 2. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Quarterly overview text here.

ITEM 3. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK
"""

    def test_extract_mdna_success_10q(self, extractor, tmp_path, sample_10q_content):
        """MDNAExtractor should extract MD&A from a standalone 10-Q."""
        test_file = tmp_path / "test_10q.txt"
        test_file.write_text(sample_10q_content)

        result = extractor.extract_from_file(test_file)

        assert result is not None, "Extractor should find MD&A in 10-Q"
        assert isinstance(result, ExtractionResult)
        assert "Quarterly overview text" in result.mdna_text
        # Ensure it stops before ITEM 3
        assert "ITEM 3" not in result.mdna_text

    def test_skip_10q_when_10k_exists(self, tmp_path, sample_10k_content, sample_10q_content):
        """ZipProcessor should skip 10-Q when a 10-K exists for the same year."""
        # Prepare files
        tenk = tmp_path / "0001234567_20240315_10-K.txt"
        tenk.write_text(sample_10k_content)
        tenq = tmp_path / "0001234567_20240630_10-Q.txt"
        tenq.write_text(sample_10q_content)

        processor = ZipProcessor(tmp_path)
        stats = processor.process_mixed_directory(tmp_path)

        assert stats["combined"]["processed"] == 1
        assert stats["combined"]["skipped_10q"] == 1

    def test_process_10q_fallback_when_no_10k(self, tmp_path, sample_10q_content):
        """ZipProcessor should process 10-Q when no 10-K is present."""
        tenq = tmp_path / "0001234567_20240630_10-Q.txt"
        tenq.write_text(sample_10q_content)

        processor = ZipProcessor(tmp_path)
        stats = processor.process_mixed_directory(tmp_path)

        assert stats["combined"]["processed"] == 1
        assert stats["combined"]["skipped_10q"] == 0
