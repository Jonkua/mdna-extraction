"""Manager for handling filing selection logic (10-K vs 10-Q fallback)."""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FilingManager:
    """Manages filing selection and prioritization logic."""

    def __init__(self):
        self.filings_by_cik_year = {}  # {cik: {year: {form_type: [file_paths]}}}

    def add_filing(self, file_path: Path, cik: str, year: int, form_type: str):
        """
        Add a filing to the manager.

        Args:
            file_path: Path to filing
            cik: Central Index Key
            year: Filing year
            form_type: Type of form (10-K, 10-K/A, 10-Q, 10-Q/A)
        """
        if cik not in self.filings_by_cik_year:
            self.filings_by_cik_year[cik] = {}

        if year not in self.filings_by_cik_year[cik]:
            self.filings_by_cik_year[cik][year] = {}

        if form_type not in self.filings_by_cik_year[cik][year]:
            self.filings_by_cik_year[cik][year][form_type] = []

        self.filings_by_cik_year[cik][year][form_type].append(file_path)

    def analyze_directory(self, directory: Path) -> Dict[str, List[Path]]:
        """
        Analyze directory and categorize filings.

        Args:
            directory: Directory containing filings

        Returns:
            Dictionary of categorized filings
        """
        text_files = list(directory.glob("*.txt")) + list(directory.glob("*.TXT"))

        for file_path in text_files:
            # Try to extract metadata from filename
            cik, year, form_type = self._parse_filename_metadata(file_path)

            if cik and year and form_type:
                self.add_filing(file_path, cik, year, form_type)

        return self._select_filings_to_process()

    def _parse_filename_metadata(self, file_path: Path) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Parse CIK, year, and form type from filename.

        Args:
            file_path: Path to filing

        Returns:
            Tuple of (cik, year, form_type) or (None, None, None)
        """
        filename = file_path.name

        # Extract CIK (look for 4-10 digit number)
        cik_match = re.search(r'(\d{4,10})', filename)
        cik = cik_match.group(1).zfill(10) if cik_match else None

        # Extract year (look for 4-digit year between 1994-2025)
        year_match = re.search(r'(199[4-9]|20[0-2][0-9])', filename)
        year = int(year_match.group(1)) if year_match else None

        # Extract form type
        form_type = None
        filename_upper = filename.upper()

        if '10-Q' in filename_upper or '10Q' in filename_upper:
            if '_A' in filename_upper or '-A' in filename_upper:
                form_type = "10-Q/A"
            else:
                form_type = "10-Q"
        elif '10-K' in filename_upper or '10K' in filename_upper:
            if '_A' in filename_upper or '-A' in filename_upper:
                form_type = "10-K/A"
            else:
                form_type = "10-K"

        return cik, year, form_type

    def _select_filings_to_process(self) -> Dict[str, List[Path]]:
        """
        Select which filings to process based on prioritization rules.

        Returns:
            Dictionary with keys 'process' and 'skip'
        """
        to_process = []
        to_skip = []

        for cik, years in self.filings_by_cik_year.items():
            for year, form_types in years.items():
                # Priority order: 10-K/A > 10-K > 10-Q/A > 10-Q
                if "10-K/A" in form_types:
                    # Process 10-K/A, skip everything else
                    to_process.extend(form_types["10-K/A"])
                    for ft in ["10-K", "10-Q/A", "10-Q"]:
                        if ft in form_types:
                            to_skip.extend(form_types[ft])

                elif "10-K" in form_types:
                    # Process 10-K, skip 10-Qs
                    to_process.extend(form_types["10-K"])
                    for ft in ["10-Q/A", "10-Q"]:
                        if ft in form_types:
                            to_skip.extend(form_types[ft])

                else:
                    # No 10-K available, use 10-Q as fallback
                    if "10-Q/A" in form_types:
                        to_process.extend(form_types["10-Q/A"])
                        if "10-Q" in form_types:
                            to_skip.extend(form_types["10-Q"])
                    elif "10-Q" in form_types:
                        # Use the latest 10-Q for the year
                        to_process.append(form_types["10-Q"][-1])
                        to_skip.extend(form_types["10-Q"][:-1])

        # Log the selection results
        logger.info(f"Selected {len(to_process)} filings to process")
        logger.info(f"Skipping {len(to_skip)} filings (lower priority forms)")

        # Log 10-Q fallbacks
        for file_path in to_process:
            if '10-Q' in file_path.name.upper() or '10Q' in file_path.name.upper():
                logger.info(f"Using 10-Q as fallback (no 10-K available): {file_path.name}")

        return {
            "process": to_process,
            "skip": to_skip
        }

    def should_process_file(self, file_path: Path) -> bool:
        """
        Check if a file should be processed based on the selection logic.

        Args:
            file_path: Path to check

        Returns:
            True if file should be processed, False if it should be skipped
        """
        selected = self._select_filings_to_process()
        return file_path in selected["process"]