"""Pytest configuration and shared fixtures."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure pytest
pytest_plugins = []


@pytest.fixture
def sample_10k_path():
    """Path to sample 10-K fixture file."""
    return Path(__file__).parent / "fixtures" / "sample_10k.txt"


@pytest.fixture
def sample_10ka_path():
    """Path to sample 10-K/A fixture file."""
    return Path(__file__).parent / "fixtures" / "sample_10ka.txt"


@pytest.fixture
def sample_10q_path():
    """Path to sample 10-Q fixture file."""
    return Path(__file__).parent / "fixtures" / "sample_10q.txt"


@pytest.fixture
def sample_10q_no10k_path():
    """Path to sample 10-Q-only fixture file (no corresponding 10-K)."""
    return Path(__file__).parent / "fixtures" / "sample_10q_no10k.txt"


@pytest.fixture
def malformed_filing_path():
    """Path to malformed filing fixture file."""
    return Path(__file__).parent / "fixtures" / "malformed_filing.txt"
