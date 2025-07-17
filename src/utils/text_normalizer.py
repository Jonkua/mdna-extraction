"""Text normalization utilities for cleaning SEC filings while preserving structure."""

import re
import unicodedata

from typing import List, Set, Tuple
from config.patterns import COMPILED_PATTERNS
from config.settings import CONTROL_CHAR_REPLACEMENT, MULTIPLE_WHITESPACE_PATTERN


class TextNormalizer:
    """Handles text cleaning and normalization for SEC filings while preserving document structure."""

    def __init__(self):
        self.control_char_pattern = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]')  # Preserve \t, \n, \r
        self.non_ascii_pattern = re.compile(r'[^\x00-\x7F]+')

    def normalize_text(self, text: str, preserve_structure: bool = True) -> str:
        """
        Apply normalization pipeline to text while preserving document structure.

        Args:
            text: Raw text from filing
            preserve_structure: Whether to preserve columnar/table structure

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # First pass: Remove SEC markers but preserve structure
        text = self._remove_sec_markers(text)

        # Replace control characters (except tabs and newlines)
        text = self._replace_control_chars(text)

        # Normalize unicode
        text = self._normalize_unicode(text)

        # Fix encoding issues
        text = self._fix_encoding_issues(text)

        if preserve_structure:
            # Preserve columnar structure and tables
            text = self._preserve_document_structure(text)
        else:
            # Standard whitespace normalization
            text = self._normalize_whitespace(text)
            text = self._remove_empty_lines(text)

        return text.strip()

    def _preserve_document_structure(self, text: str) -> str:
        """
        Preserve the original document structure including columns and tables.
        """
        lines = text.split('\n')
        processed_lines = []

        for line in lines:
            # Preserve lines that appear to be part of tables or columnar data
            if self._is_structured_line(line):
                # Keep original spacing for structured content
                processed_lines.append(line.rstrip())  # Remove only trailing spaces
            else:
                # For regular text, normalize internal spacing but preserve indentation
                indent = len(line) - len(line.lstrip())
                cleaned = ' '.join(line.split())
                if cleaned:
                    processed_lines.append(' ' * min(indent, 4) + cleaned)
                elif processed_lines and processed_lines[-1].strip():
                    # Keep one empty line between paragraphs
                    processed_lines.append('')

        # Clean up multiple consecutive empty lines
        result = []
        empty_count = 0
        for line in processed_lines:
            if not line.strip():
                empty_count += 1
                if empty_count <= 2:  # Allow up to 2 consecutive empty lines
                    result.append(line)
            else:
                empty_count = 0
                result.append(line)

        return '\n'.join(result)

    def _is_structured_line(self, line: str) -> bool:
        """
        Determine if a line is part of structured content (table, columnar data).
        """
        # Check for table delimiters
        if re.match(r'^\s*[-=_]{3,}\s*$', line):
            return True

        # Check for multiple consecutive spaces (columnar data)
        if re.search(r'\s{3,}', line):
            # Count segments separated by multiple spaces
            segments = re.split(r'\s{3,}', line.strip())
            if len(segments) >= 2 and any(s.strip() for s in segments):
                return True

        # Check for pipe-delimited content
        if '|' in line and line.count('|') >= 2:
            return True

        # Check for numeric data in columns
        if self._has_columnar_numbers(line):
            return True

        return False

    def _has_columnar_numbers(self, line: str) -> bool:
        """Check if line contains numbers in a columnar format."""
        # Pattern for financial numbers (with or without currency symbols)
        number_pattern = re.compile(r'(?:\$\s*)?\(?[\d,]+(?:\.\d+)?\)?(?:\s*[%KMB])?')
        matches = list(number_pattern.finditer(line))

        if len(matches) >= 2:
            # Check if numbers are spaced out (suggesting columns)
            positions = [m.start() for m in matches]
            for i in range(1, len(positions)):
                if positions[i] - positions[i-1] > 10:  # Arbitrary spacing threshold
                    return True

        return False

    def _remove_sec_markers(self, text: str) -> str:
        """Remove SEC-specific markers while preserving document structure."""
        # Remove page markers
        text = re.sub(r'<PAGE>\s*\d+', '', text, flags=re.IGNORECASE)

        # Remove "Table of Contents" headers but keep the structure
        text = re.sub(r'^\s*Table\s+of\s+Contents\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

        # Remove standalone page numbers at line start/end
        text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)

        # Remove HTML-like tags
        text = re.sub(r'</?[A-Z]+>', '', text)

        return text

    def _replace_control_chars(self, text: str) -> str:
        """Replace control characters except tabs and newlines."""
        return self.control_char_pattern.sub(CONTROL_CHAR_REPLACEMENT, text)

    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to ASCII equivalents where possible."""
        # Normalize to NFKD form
        text = unicodedata.normalize('NFKD', text)

        # Replace common unicode characters
        replacements = {
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u201C': '"',  # Left double quotation mark
            '\u201D': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash (use double dash to preserve width)
            '\u2026': '...',  # Ellipsis
            '\u00A0': ' ',  # Non-breaking space
            '\u2022': '*',  # Bullet
            '\u00B7': '*',  # Middle dot
            '\u2212': '-',  # Minus sign
        }

        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)

        return text

    def _fix_encoding_issues(self, text: str) -> str:
        """Fix common encoding issues in text."""
        # Fix mojibake patterns
        encoding_fixes = {
            'â€™': "'",
            'â€œ': '"',
            'â€': '"',
            'â€"': '--',
            'â€"': '-',
            'Ã¢': '',
            'Â': '',
            'â\x80\x99': "'",
            'â\x80\x9c': '"',
            'â\x80\x9d': '"',
            'â\x80\x93': '-',
            'â\x80\x94': '--',
        }

        for pattern, replacement in encoding_fixes.items():
            text = text.replace(pattern, replacement)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize multiple whitespace to single spaces."""
        # Replace multiple spaces, tabs, etc. with single space
        text = re.sub(r'[ \t]+', ' ', text)

        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        return text

    def _remove_empty_lines(self, text: str) -> str:
        """Remove excessive empty lines while preserving paragraph structure."""
        lines = text.split('\n')
        non_empty_lines = []

        for line in lines:
            if line.strip():
                non_empty_lines.append(line)
            elif non_empty_lines and non_empty_lines[-1].strip():
                # Keep one empty line between paragraphs
                non_empty_lines.append('')

        return '\n'.join(non_empty_lines)

    def clean_for_csv(self, text: str) -> str:
        """
        Additional cleaning for CSV output.

        Args:
            text: Text to clean

        Returns:
            CSV-safe text
        """
        # Remove newlines and extra spaces
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text)

        # Escape quotes
        text = text.replace('"', '""')

        return text.strip()

    def extract_company_name(self, text: str) -> str:
        """
        Extract company name from filing header.

        Args:
            text: Filing text

        Returns:
            Company name or empty string
        """
        # Common patterns for company name in SEC filings
        patterns = [
            r"(?:COMPANY\s*CONFORMED\s*NAME|CONFORMED\s*NAME|COMPANY\s*NAME)[\s:]+([^\n]+)",
            r"(?:^|\n)\s*([A-Z][A-Z0-9\s,.\-&]+(?:INC|CORP|LLC|LP|LTD|COMPANY|CO)\.?)\s*\n",
            r"(?:REGISTRANT\s*NAME)[\s:]+([^\n]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:5000], re.IGNORECASE | re.MULTILINE)
            if match:
                company_name = match.group(1).strip()
                # Clean up the name
                company_name = re.sub(r'\s+', ' ', company_name)
                company_name = company_name.strip(' .')
                if len(company_name) > 3 and len(company_name) < 100:
                    return company_name

        return ""

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string for use in filenames.

        Args:
            name: String to sanitize

        Returns:
            Sanitized string safe for filenames
        """
        # Replace illegal filename characters
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']
        for char in illegal_chars:
            name = name.replace(char, ' ')

        # Replace multiple spaces with single space
        name = re.sub(r'\s+', ' ', name)

        # Remove leading/trailing spaces and periods
        name = name.strip(' .')

        # Limit length
        if len(name) > 50:
            name = name[:50].strip()

        return name