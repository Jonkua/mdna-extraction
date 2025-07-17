"""Parser for detecting and preserving tables within MD&A sections."""

import re

import pandas as pd
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from config.patterns import COMPILED_PATTERNS
from config.settings import TABLE_MIN_COLUMNS, TABLE_MIN_ROWS
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Table:
    """Represents a detected table."""
    content: List[List[str]]  # Table as list of rows
    start_pos: int
    end_pos: int
    start_line: int
    end_line: int
    title: Optional[str]
    confidence: float
    table_type: str  # 'delimited', 'aligned', 'mixed'
    original_text: str  # Preserve original formatting


class TableParser:
    """Detects and preserves tables within text."""

    def __init__(self):
        self.patterns = COMPILED_PATTERNS

    def identify_tables(self, text: str) -> List[Table]:
        """
        Identify tables in text while preserving their original formatting.

        Args:
            text: Text containing potential tables

        Returns:
            List of Table objects with position information
        """
        tables = []
        lines = text.split('\n')

        # Track which lines are part of tables
        table_lines = set()

        # Try different detection methods
        tables.extend(self._identify_delimited_tables(lines, table_lines))
        tables.extend(self._identify_aligned_tables(lines, table_lines))

        # Remove duplicates and overlaps
        tables = self._deduplicate_tables(tables)

        # Sort by position
        tables.sort(key=lambda t: t.start_line)

        return tables

    def preserve_tables_in_text(self, text: str, tables: List[Table]) -> str:
        """
        Return text with tables preserved in their original positions.

        Args:
            text: Original text
            tables: List of identified tables

        Returns:
            Text with tables properly formatted and preserved
        """
        if not tables:
            return text

        lines = text.split('\n')

        # Mark table boundaries for preservation
        for table in tables:
            # Add subtle markers to indicate table boundaries
            if table.title and table.start_line > 0:
                # Check if title line exists
                title_line = table.start_line - 1
                if title_line >= 0 and not self._is_table_line(lines[title_line]):
                    lines[title_line] = f"\n{lines[title_line]}\n"

            # Ensure table content is preserved with proper spacing
            for i in range(table.start_line, min(table.end_line + 1, len(lines))):
                if i < len(lines):
                    # Preserve original formatting of table lines
                    lines[i] = lines[i].rstrip()

        return '\n'.join(lines)

    def _identify_delimited_tables(self, lines: List[str], table_lines: Set[int]) -> List[Table]:
        """Identify tables with clear delimiters."""
        tables = []
        i = 0

        while i < len(lines):
            # Skip lines already identified as part of tables
            if i in table_lines:
                i += 1
                continue

            # Check for horizontal delimiter
            if self._is_horizontal_delimiter(lines[i]):
                table = self._extract_delimited_table(lines, i, table_lines)
                if table:
                    tables.append(table)
                    # Mark lines as part of table
                    for line_num in range(table.start_line, table.end_line + 1):
                        table_lines.add(line_num)
                    i = table.end_line + 1
                else:
                    i += 1
            # Check for pipe-delimited table
            elif '|' in lines[i] and lines[i].count('|') >= 2:
                table = self._extract_pipe_table(lines, i, table_lines)
                if table:
                    tables.append(table)
                    for line_num in range(table.start_line, table.end_line + 1):
                        table_lines.add(line_num)
                    i = table.end_line + 1
                else:
                    i += 1
            else:
                i += 1

        return tables

    def _identify_aligned_tables(self, lines: List[str], table_lines: Set[int]) -> List[Table]:
        """Identify space-aligned tables."""
        tables = []
        i = 0

        while i < len(lines):
            # Skip lines already identified as part of tables
            if i in table_lines:
                i += 1
                continue

            # Look for potential table headers
            if self._looks_like_table_header(lines[i]):
                table = self._extract_aligned_table(lines, i, table_lines)
                if table:
                    tables.append(table)
                    for line_num in range(table.start_line, table.end_line + 1):
                        table_lines.add(line_num)
                    i = table.end_line + 1
                else:
                    i += 1
            else:
                i += 1

        return tables

    def _is_horizontal_delimiter(self, line: str) -> bool:
        """Check if line is a horizontal delimiter."""
        stripped = line.strip()
        if len(stripped) < 3:
            return False

        # Check for lines made of dashes, equals, or underscores
        delimiter_chars = {'-', '=', '_'}
        unique_chars = set(stripped.replace(' ', ''))

        return len(unique_chars) == 1 and unique_chars.issubset(delimiter_chars)

    def _is_table_line(self, line: str) -> bool:
        """Check if a line appears to be part of a table."""
        # Has multiple segments separated by significant spaces
        if re.search(r'\s{3,}', line):
            segments = re.split(r'\s{3,}', line.strip())
            if len(segments) >= 2:
                return True

        # Has pipe delimiters
        if '|' in line and line.count('|') >= 2:
            return True

        # Is a delimiter line
        if self._is_horizontal_delimiter(line):
            return True

        return False

    def _looks_like_table_header(self, line: str) -> bool:
        """Check if line looks like a table header."""
        # Check for date headers
        if re.search(r'(?:Year|Period|Quarter|Month)\s+End(?:ed|ing)', line, re.IGNORECASE):
            return True

        # Check for financial statement headers
        if re.search(r'(?:December|June|March|September)\s+\d{1,2},?\s+20\d{2}', line, re.IGNORECASE):
            return True

        # Check for columnar structure with common headers
        segments = re.split(r'\s{3,}', line.strip())
        if len(segments) >= TABLE_MIN_COLUMNS:
            header_keywords = ['total', 'year', 'quarter', 'revenue', 'income', 'assets',
                             'change', 'increase', 'decrease', '%', '$', '2019', '2020',
                             '2021', '2022', '2023', '2024']
            matches = sum(1 for seg in segments
                         if any(keyword in seg.lower() for keyword in header_keywords))
            if matches >= 1:
                return True

        return False

    def _extract_delimited_table(self, lines: List[str], delimiter_line: int,
                                table_lines: Set[int]) -> Optional[Table]:
        """Extract a table with horizontal delimiter."""
        # Look for header above delimiter
        if delimiter_line > 0 and not lines[delimiter_line - 1].strip():
            return None

        start_line = delimiter_line - 1 if delimiter_line > 0 else delimiter_line

        # Find table bounds
        table_content = []
        current_line = start_line

        # Add header if exists
        if delimiter_line > 0:
            table_content.append(lines[delimiter_line - 1])

        # Skip delimiter
        current_line = delimiter_line + 1

        # Collect data rows
        consecutive_empty = 0
        while current_line < len(lines) and consecutive_empty < 2:
            line = lines[current_line]

            if not line.strip():
                consecutive_empty += 1
            else:
                consecutive_empty = 0
                # Check if line looks like table data
                if self._looks_like_table_data(line):
                    table_content.append(line)
                else:
                    break

            current_line += 1

        if len(table_content) < TABLE_MIN_ROWS:
            return None

        # Find title
        title = self._extract_table_title(lines, start_line)

        # Preserve original text
        end_line = start_line + len(table_content)
        original_lines = lines[start_line:end_line + 1]
        original_text = '\n'.join(original_lines)

        return Table(
            content=[line.split() for line in table_content],
            start_pos=0,  # Will be calculated later if needed
            end_pos=0,
            start_line=start_line,
            end_line=end_line,
            title=title,
            confidence=0.9,
            table_type='delimited',
            original_text=original_text
        )

    def _extract_pipe_table(self, lines: List[str], start_line: int,
                           table_lines: Set[int]) -> Optional[Table]:
        """Extract a pipe-delimited table."""
        table_content = []
        current_line = start_line

        while current_line < len(lines):
            line = lines[current_line]
            if '|' in line:
                table_content.append(line)
                current_line += 1
            else:
                break

        if len(table_content) < TABLE_MIN_ROWS:
            return None

        # Parse pipe-delimited content
        parsed_content = []
        for line in table_content:
            cells = [cell.strip() for cell in line.split('|')]
            # Remove empty cells at start/end
            if cells and not cells[0]:
                cells = cells[1:]
            if cells and not cells[-1]:
                cells = cells[:-1]
            if cells:
                parsed_content.append(cells)

        # Find title
        title = self._extract_table_title(lines, start_line)

        # Preserve original
        end_line = start_line + len(table_content) - 1
        original_text = '\n'.join(lines[start_line:end_line + 1])

        return Table(
            content=parsed_content,
            start_pos=0,
            end_pos=0,
            start_line=start_line,
            end_line=end_line,
            title=title,
            confidence=0.95,
            table_type='delimited',
            original_text=original_text
        )

    def _extract_aligned_table(self, lines: List[str], start_line: int,
                              table_lines: Set[int]) -> Optional[Table]:
        """Extract a space-aligned table."""
        # Determine column positions from header
        header = lines[start_line]
        column_positions = self._find_column_boundaries(header)

        if len(column_positions) < TABLE_MIN_COLUMNS:
            return None

        table_content = [header]
        current_line = start_line + 1
        consecutive_empty = 0

        while current_line < len(lines) and consecutive_empty < 2:
            line = lines[current_line]

            if not line.strip():
                consecutive_empty += 1
                current_line += 1
                continue
            else:
                consecutive_empty = 0

            # Check if line aligns with columns
            if self._line_matches_columns(line, column_positions):
                table_content.append(line)
            else:
                # Check if it's a continuation or total line
                if self._is_table_continuation(line):
                    table_content.append(line)
                else:
                    break

            current_line += 1

        if len(table_content) < TABLE_MIN_ROWS:
            return None

        # Find title
        title = self._extract_table_title(lines, start_line)

        # Preserve original formatting
        end_line = start_line + len(table_content) - 1
        original_text = '\n'.join(table_content)

        # Parse content while preserving alignment
        parsed_content = []
        for line in table_content:
            cells = self._extract_cells_by_position(line, column_positions)
            parsed_content.append(cells)

        return Table(
            content=parsed_content,
            start_pos=0,
            end_pos=0,
            start_line=start_line,
            end_line=end_line,
            title=title,
            confidence=0.8,
            table_type='aligned',
            original_text=original_text
        )

    def _find_column_boundaries(self, header: str) -> List[Tuple[int, int]]:
        """Find column boundaries in header line."""
        # Look for transitions between text and spaces
        boundaries = []
        in_text = False
        start = 0

        for i, char in enumerate(header + ' '):
            if char != ' ' and not in_text:
                start = i
                in_text = True
            elif char == ' ' and in_text:
                # Check if we've hit a column boundary (multiple spaces)
                spaces_ahead = 0
                j = i
                while j < len(header) and header[j] == ' ':
                    spaces_ahead += 1
                    j += 1

                if spaces_ahead >= 2 or j >= len(header):
                    boundaries.append((start, i))
                    in_text = False

        return boundaries

    def _line_matches_columns(self, line: str, column_positions: List[Tuple[int, int]]) -> bool:
        """Check if line content aligns with column positions."""
        matches = 0

        for start, end in column_positions:
            if start < len(line):
                segment = line[start:min(end + 5, len(line))].strip()
                if segment:
                    matches += 1

        return matches >= len(column_positions) / 2

    def _extract_cells_by_position(self, line: str, column_positions: List[Tuple[int, int]]) -> List[str]:
        """Extract cell values based on column positions."""
        cells = []

        for i, (start, end) in enumerate(column_positions):
            if i < len(column_positions) - 1:
                next_start = column_positions[i + 1][0]
                cell = line[start:next_start].strip() if start < len(line) else ''
            else:
                cell = line[start:].strip() if start < len(line) else ''
            cells.append(cell)

        return cells

    def _looks_like_table_data(self, line: str) -> bool:
        """Check if line looks like table data."""
        # Contains numbers
        if re.search(r'\d', line):
            return True

        # Has columnar structure
        if re.search(r'\s{3,}', line):
            segments = re.split(r'\s{3,}', line.strip())
            if len(segments) >= 2:
                return True

        return False

    def _is_table_continuation(self, line: str) -> bool:
        """Check if line is a table continuation (like totals)."""
        continuation_keywords = ['total', 'subtotal', 'net', 'gross', 'sum']
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in continuation_keywords)

    def _extract_table_title(self, lines: List[str], table_start: int) -> Optional[str]:
        """Extract table title from preceding lines."""
        # Look at previous 3 lines
        for i in range(1, min(4, table_start + 1)):
            line_idx = table_start - i
            if line_idx < 0:
                break

            line = lines[line_idx].strip()

            # Skip empty lines
            if not line:
                continue

            # Check if it looks like a title
            if (len(line) < 200 and
                not self._is_table_line(line) and
                not line.endswith('.') and
                not re.match(r'^\d+$', line)):  # Not just a number
                return line

        return None

    def _deduplicate_tables(self, tables: List[Table]) -> List[Table]:
        """Remove duplicate and overlapping tables."""
        if not tables:
            return tables

        # Sort by start position
        tables.sort(key=lambda t: t.start_line)

        deduped = []
        for table in tables:
            # Check if overlaps with existing tables
            overlap = False
            for existing in deduped:
                if (table.start_line >= existing.start_line and
                    table.start_line <= existing.end_line):
                    overlap = True
                    break

            if not overlap:
                deduped.append(table)

        return deduped