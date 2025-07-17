# Tests for ZipProcessor.process_mixed_directory, focusing on 10-Q fallback/skipping
import pytest
import zipfile

from pathlib import Path
from src.core.zip_processor import ZipProcessor


@pytest.fixture(autouse=True)
def setup_logging():
    # Ensure logging is configured if needed
    import src.utils.logger as _log
    _log.setup_logging(verbose=False)


class TestZipProcessorMixed:
    @pytest.fixture
    def input_dir(self, tmp_path):
        # create separate input and output dirs
        d = tmp_path / "input"
        d.mkdir()
        return d

    @pytest.fixture
    def output_dir(self, tmp_path):
        d = tmp_path / "output"
        d.mkdir()
        return d

    @pytest.fixture
    def processor(self, output_dir):
        return ZipProcessor(output_dir)

    @pytest.fixture
    def sample_10k(self):
        return """
FORM 10-K

CIK: 0001112223
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS
MD&A content for 10-K.
"""

    @pytest.fixture
    def sample_10q(self):
        return """
FORM 10-Q

CIK: 0001112223
ITEM 2. MANAGEMENT'S DISCUSSION AND ANALYSIS
MD&A content for 10-Q.
ITEM 3. QUANTITATIVE AND QUALITATIVE DISCLOSURES
"""

    def test_skip_10q_when_10k_exists(self, input_dir, processor, sample_10k, sample_10q):
        # Create both 10-K and 10-Q in loose files
        f10k = input_dir / "0001112223_20240101_10-K.txt"
        f10k.write_text(sample_10k)
        f10q = input_dir / "0001112223_20240630_10-Q.txt"
        f10q.write_text(sample_10q)

        stats = processor.process_mixed_directory(input_dir)

        # Only 10-K processed, 10-Q skipped
        assert stats["combined"]["processed"] == 1
        assert stats["combined"]["skipped_10q"] == 1
        # Ensure skip counted as one
        assert stats["combined"]["total_files"] == 2

    def test_process_10q_when_no_10k(self, input_dir, processor, sample_10q):
        # Only 10-Q present
        f10q = input_dir / "0001112223_20240630_10-Q.txt"
        f10q.write_text(sample_10q)

        stats = processor.process_mixed_directory(input_dir)

        # 10-Q processed, none skipped
        assert stats["combined"]["processed"] == 1
        assert stats["combined"]["skipped_10q"] == 0
        assert stats["combined"]["total_files"] == 1

    def test_zip_and_text_combined(self, input_dir, processor, sample_10k, sample_10q, output_dir):
        # Prepare a ZIP containing a 10-Q
        zip_path = input_dir / "archive.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # create a temp file to write content
            temp_txt = input_dir / "temp10q.txt"
            temp_txt.write_text(sample_10q)
            zf.write(temp_txt, arcname="0001112223_20240630_10-Q.txt")
            temp_txt.unlink()

        # Also drop a 10-K loose
        f10k = input_dir / "0001112223_20240101_10-K.txt"
        f10k.write_text(sample_10k)

        stats = processor.process_mixed_directory(input_dir)

        # Should process only the 10-K from loose and skip the 10-Q inside zip
        assert stats["combined"]["processed"] == 1
        assert stats["combined"]["skipped_10q"] == 1
        # zip_results total_files should be 1, text_results total_files should be 1
        assert stats["zip_results"]["total_files"] == 1
        assert stats["text_results"]["total_files"] == 1
        # processed breakdown
        assert stats["zip_results"]["processed"] == 0
        assert stats["text_results"]["processed"] == 1

    def test_multiple_10q_versions_in_zip(self, input_dir, processor, sample_10q):
        # ZIP with two 10-Qs for same year; should process only the last in ZIP
        zip_path = input_dir / "multi.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # first quarter
            q1 = input_dir / "tmp1.txt"
            q1.write_text(sample_10q.replace('06/30/2024', '03/31/2024'))
            zf.write(q1, arcname="0001112223_20240331_10-Q.txt")
            q1.unlink()
            # second quarter
            q2 = input_dir / "tmp2.txt"
            q2.write_text(sample_10q.replace('06/30/2024', '06/30/2024'))
            zf.write(q2, arcname="0001112223_20240630_10-Q.txt")
            q2.unlink()

        stats = processor.process_mixed_directory(input_dir)

        # Only one 10-Q processed
        assert stats["combined"]["processed"] == 1
        assert stats["combined"]["skipped_10q"] == 1
        # zip_results should reflect 2 total, processed 1, skipped not counted here
        assert stats["zip_results"]["total_files"] == 2
        assert stats["zip_results"]["processed"] == 1
        assert stats["zip_results"]["failed"] == 0
