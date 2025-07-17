"""Resolver for incorporation by reference documents."""

import re
from pathlib import Path
from typing import Optional, Dict, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReferenceResolver:
    """Resolves MD&A content from referenced documents."""

    def __init__(self, filing_directory: Path):
        self.filing_directory = filing_directory

    def resolve_reference(self, incorporation_ref, original_filing) -> Optional[str]:
        """
        Attempt to resolve MD&A content from referenced document.

        Args:
            incorporation_ref: IncorporationByReference object
            original_filing: Original Filing object

        Returns:
            Extracted MD&A text or None
        """
        # Extract accession number from original filing
        accession_number = self._extract_accession_number(original_filing.file_path)
        if not accession_number:
            logger.warning("Could not extract accession number from filing")
            return None

        # Determine referenced document type and pattern
        ref_doc_pattern = self._get_reference_document_pattern(
            incorporation_ref.document_type,
            accession_number
        )

        if not ref_doc_pattern:
            logger.warning(f"Unknown reference document type: {incorporation_ref.document_type}")
            return None

        # Search for referenced document
        referenced_file = self._find_referenced_document(ref_doc_pattern)
        if not referenced_file:
            logger.warning(f"Could not find referenced document matching: {ref_doc_pattern}")
            return None

        # Extract content from referenced document
        extracted_content = self._extract_from_referenced_document(
            referenced_file,
            incorporation_ref
        )

        return extracted_content

    def _extract_accession_number(self, file_path: Path) -> Optional[str]:
        """Extract SEC accession number from filename or content."""
        # Common patterns in filenames
        filename = file_path.name

        # Pattern: 0000950170-23-061793
        accession_match = re.search(r'(\d{10}-\d{2}-\d{6})', filename)
        if accession_match:
            return accession_match.group(1)

        # Try without dashes: 000095017023061793
        accession_match = re.search(r'(\d{10})(\d{2})(\d{6})', filename)
        if accession_match:
            return f"{accession_match.group(1)}-{accession_match.group(2)}-{accession_match.group(3)}"

        return None

    def _get_reference_document_pattern(self, doc_type: str, accession_number: str) -> Optional[List[str]]:
        """Get search pattern for referenced document."""
        if not doc_type:
            return None

        # Remove dashes from accession number for filename matching
        acc_no_dashes = accession_number.replace('-', '')

        patterns = {
            "DEF 14A": [
                f"*{acc_no_dashes}*def14a*.txt",
                f"*{acc_no_dashes}*proxy*.txt",
                f"*{accession_number}*def14a*.txt",
            ],
            "Exhibit 13": [
                f"*{acc_no_dashes}*ex13*.txt",
                f"*{acc_no_dashes}*ex-13*.txt",
                f"*{accession_number}*ex13*.txt",
            ],
            "Exhibit 99": [
                f"*{acc_no_dashes}*ex99*.txt",
                f"*{acc_no_dashes}*ex-99*.txt",
                f"*{accession_number}*ex99*.txt",
            ],
        }

        # Check for specific exhibit patterns
        for key, patterns_list in patterns.items():
            if key.lower() in doc_type.lower():
                return patterns_list

        return None

    def _find_referenced_document(self, patterns: List[str]) -> Optional[Path]:
        """Find referenced document in filing directory."""
        for pattern in patterns:
            matches = list(self.filing_directory.glob(pattern))
            if matches:
                return matches[0]  # Return first match

        return None

    def _extract_from_referenced_document(
            self,
            file_path: Path,
            incorporation_ref
    ) -> Optional[str]:
        """Extract MD&A content from referenced document."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # If specific caption provided, search for it
            if incorporation_ref.caption:
                mdna_start = self._find_caption_in_text(content, incorporation_ref.caption)
                if mdna_start is not None:
                    # Extract reasonable chunk after caption
                    mdna_end = self._find_next_major_section(content, mdna_start)
                    return content[mdna_start:mdna_end]

            # If page reference provided, try to extract by page markers
            if incorporation_ref.page_reference:
                return self._extract_by_page_reference(content, incorporation_ref.page_reference)

            # Fallback: try to find MD&A section in referenced document
            mdna_section = self._find_mdna_in_document(content)
            return mdna_section

        except Exception as e:
            logger.error(f"Error reading referenced document {file_path}: {e}")
            return None

    def _find_caption_in_text(self, text: str, caption: str) -> Optional[int]:
        """Find caption in text and return start position."""
        # Create pattern from caption
        escaped_caption = re.escape(caption)
        pattern = re.compile(
            rf'(?:^|\n)\s*{escaped_caption}\s*(?:\n|$)',
            re.IGNORECASE | re.MULTILINE
        )

        match = pattern.search(text)
        if match:
            return match.end()

        # Try partial match
        key_words = caption.split()[:3]  # First 3 words
        if len(key_words) >= 2:
            partial_pattern = re.compile(
                rf'(?:^|\n)\s*{re.escape(" ".join(key_words))}.*(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            )
            match = partial_pattern.search(text)
            if match:
                return match.end()

        return None

    def _find_next_major_section(self, text: str, start_pos: int) -> int:
        """Find the next major section after start_pos."""
        search_text = text[start_pos:]

        # Common section headers in proxy statements and exhibits
        section_patterns = [
            r'(?:^|\n)\s*[A-Z][A-Z\s]{10,}\s*(?:\n|$)',  # All caps headers
            r'(?:^|\n)\s*(?:ITEM|PROPOSAL|ARTICLE)\s+\d+',
            r'(?:^|\n)\s*(?:Appendix|Exhibit|Schedule)\s+[A-Z0-9]',
        ]

        min_pos = len(search_text)
        for pattern in section_patterns:
            match = re.search(pattern, search_text, re.MULTILINE)
            if match and match.start() > 500:  # Ensure we get some content
                min_pos = min(min_pos, match.start())

        return start_pos + min(min_pos, 50000)  # Max 50k chars

    def _extract_by_page_reference(self, text: str, page_ref: str) -> Optional[str]:
        """Extract content based on page references."""
        # This is challenging without proper page markers
        # Look for page numbers in text
        page_pattern = re.compile(
            rf'(?:^|\n)\s*(?:Page\s+)?{re.escape(page_ref.split()[0])}\s*(?:\n|$)',
            re.IGNORECASE | re.MULTILINE
        )

        match = page_pattern.search(text)
        if match:
            start = match.end()
            # Extract up to next page marker or section
            end = self._find_next_major_section(text, start)
            return text[start:end]

        return None

    def _find_mdna_in_document(self, text: str) -> Optional[str]:
        """Fallback: try to find MD&A section in any document."""
        mdna_patterns = [
            r"(?:^|\n)\s*Management['']?s?\s+Discussion\s+and\s+Analysis",
            r"(?:^|\n)\s*MD&A",
            r"(?:^|\n)\s*Discussion\s+and\s+Analysis\s+of\s+Financial",
        ]

        for pattern in mdna_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                start = match.start()
                end = self._find_next_major_section(text, start)
                return text[start:end]

        return None