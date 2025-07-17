# Tests for FilingManager prioritization and 10-Q fallback logic
import pytest
from pathlib import Path
from src.core.filing_manager import FilingManager


def make_path(name: str) -> Path:
    # Utility to create a Path without touching filesystem
    return Path(name)


class TestFilingManager:
    """Verify that FilingManager selects the correct filing by priority."""

    @pytest.fixture
    def fm(self):
        return FilingManager()

    @pytest.fixture
    def cik(self):
        return "0000123456"

    def test_priority_10ka_over_all(self, fm, cik):
        # Add one of each form for 2020
        year = 2020
        files = {
            '10-K':   make_path(f"{cik}_2020_10-K.txt"),
            '10-K/A': make_path(f"{cik}_2020_10-K_A.txt"),
            '10-Q/A': make_path(f"{cik}_2020_10-Q_A.txt"),
            '10-Q':   make_path(f"{cik}_2020_10-Q.txt"),
        }
        for ft, path in files.items():
            fm.add_filing(path, cik, year, ft)

        sel = fm._select_filings_to_process()
        # Should process only 10-K/A
        assert set(sel['process']) == {files['10-K/A']}
        # All others skipped
        assert set(sel['skip']) == {files['10-K'], files['10-Q/A'], files['10-Q']}

    def test_priority_10k_over_q(self, fm, cik):
        # Remove 10-K/A, test 10-K preference
        year = 2021
        files = {
            '10-K':   make_path(f"{cik}_2021_10-K.txt"),
            '10-Q/A': make_path(f"{cik}_2021_10-Q_A.txt"),
            '10-Q':   make_path(f"{cik}_2021_10-Q.txt"),
        }
        for ft, path in files.items():
            fm.add_filing(path, cik, year, ft)

        sel = fm._select_filings_to_process()
        assert sel['process'] == [files['10-K']]
        assert set(sel['skip']) == {files['10-Q/A'], files['10-Q']}

    def test_priority_10qa_over_q(self, fm, cik):
        # Only 10-Q/A and 10-Q for year 2022
        year = 2022
        files = {
            '10-Q/A': make_path(f"{cik}_2022_10-Q_A.txt"),
            '10-Q':   make_path(f"{cik}_2022_10-Q.txt"),
        }
        for ft, path in files.items():
            fm.add_filing(path, cik, year, ft)

        sel = fm._select_filings_to_process()
        assert sel['process'] == [files['10-Q/A']]
        assert sel['skip'] == [files['10-Q']]

    def test_fallback_10q_when_no_10k(self, fm, cik):
        # Only 10-Q entries, multiple versions; should pick last added
        year = 2023
        q1 = make_path(f"{cik}_2023_04-01_10-Q.txt")
        q2 = make_path(f"{cik}_2023_10-01_10-Q.txt")
        fm.add_filing(q1, cik, year, '10-Q')
        fm.add_filing(q2, cik, year, '10-Q')

        sel = fm._select_filings_to_process()
        assert sel['process'] == [q2]
        assert sel['skip'] == [q1]

    def test_multiple_years_independence(self, fm, cik):
        # Tests that selection is per year, not across years
        # Year 2020: only 10-K
        path_k = make_path(f"{cik}_2020_10-K.txt")
        fm.add_filing(path_k, cik, 2020, '10-K')
        # Year 2021: only 10-Q
        path_q = make_path(f"{cik}_2021_10-Q.txt")
        fm.add_filing(path_q, cik, 2021, '10-Q')

        sel = fm._select_filings_to_process()
        assert set(sel['process']) == {path_k, path_q}
        assert sel['skip'] == []
