"""Parser for resolving cross-references in MD&A sections."""

import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from config.patterns import COMPILED_PATTERNS
from config.settings import MAX_CROSS_REFERENCE_DEPTH
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CrossReference:
    """Represents a cross-reference in the text."""
    reference_text: str
    reference_type: str  # 'note', 'item', 'exhibit', 'section'
    target_id: str
    start_pos: int
    end_pos: int
    resolved: bool = False
    resolution_text: Optional[str] = None


class CrossReferenceParser:
    """Handles cross-reference detection and resolution."""

    def __init__(self):
        self.patterns = COMPILED_PATTERNS["cross_reference"]
        self.resolved_cache: Dict[str, str] = {}

    def find_cross_references(self, text: str) -> List[CrossReference]:
        """
        Find all cross-references in the text.

        Args:
            text: Text to search for cross-references

        Returns:
            List of CrossReference objects
        """
        references = []

        for pattern in self.patterns:
            for match in pattern.finditer(text):
                ref = self._parse_reference(match, text)
                if ref:
                    references.append(ref)

        # Remove duplicates
        references = self._deduplicate_references(references)

        return references

    def resolve_references(
            self,
            references: List[CrossReference],
            full_document: str,
            normalizer=None,  # Add normalizer parameter
            depth: int = 0
    ) -> List[CrossReference]:
        """
        Resolve cross-references by finding referenced content.

        Args:
            references: List of references to resolve
            full_document: Complete document text
            normalizer: TextNormalizer instance for cleaning text
            depth: Current recursion depth

        Returns:
            List of resolved references
        """
        if depth >= MAX_CROSS_REFERENCE_DEPTH:
            logger.warning(f"Maximum cross-reference depth {MAX_CROSS_REFERENCE_DEPTH} reached")
            return references

        for ref in references:
            if ref.resolved:
                continue

            # Check cache first
            cache_key = f"{ref.reference_type}:{ref.target_id}"
            if cache_key in self.resolved_cache:
                ref.resolution_text = self.resolved_cache[cache_key]
                ref.resolved = True
                continue

            # Resolve based on type
            if ref.reference_type == 'note':
                resolution = self._resolve_note_reference(ref.target_id, full_document)
            elif ref.reference_type == 'item':
                resolution = self._resolve_item_reference(ref.target_id, full_document)
            elif ref.reference_type == 'exhibit':
                resolution = self._resolve_exhibit_reference(ref.target_id, full_document)
            elif ref.reference_type == 'section':
                resolution = self._resolve_section_reference(ref.target_id, full_document)
            else:
                resolution = None

            if resolution:
                # Apply normalization if normalizer provided
                if normalizer:
                    resolution = normalizer.normalize_text(resolution, preserve_structure=True)

                ref.resolution_text = resolution
                ref.resolved = True
                self.resolved_cache[cache_key] = resolution

                # Check for nested references
                nested_refs = self.find_cross_references(resolution)
                if nested_refs:
                    self.resolve_references(nested_refs, full_document, normalizer, depth + 1)

        return references

    def _parse_reference(self, match: re.Match, text: str) -> Optional[CrossReference]:
        """Parse a regex match into a CrossReference object."""
        full_match = match.group(0)

        # Determine reference type and target
        if 'note' in full_match.lower():
            ref_type = 'note'
            # Extract note number
            numbers = re.findall(r'\d+', full_match)
            target_id = numbers[0] if numbers else None
        elif 'item' in full_match.lower():
            ref_type = 'item'
            # Extract item number (may include letter)
            item_match = re.search(r'item\s*(\d+[a-z]?)', full_match, re.IGNORECASE)
            target_id = item_match.group(1) if item_match else None
        elif 'exhibit' in full_match.lower():
            ref_type = 'exhibit'
            # Extract exhibit number
            exhibit_match = re.search(r'exhibit\s*([\d.]+)', full_match, re.IGNORECASE)
            target_id = exhibit_match.group(1) if exhibit_match else None
        elif 'section' in full_match.lower():
            ref_type = 'section'
            # Extract section title
            quote_match = re.search(r'["\']([^"\']+)["\']', full_match)
            target_id = quote_match.group(1) if quote_match else None
        else:
            return None

        if not target_id:
            return None

        return CrossReference(
            reference_text=full_match,
            reference_type=ref_type,
            target_id=target_id,
            start_pos=match.start(),
            end_pos=match.end()
        )

    def _resolve_note_reference(self, note_num: str, document: str) -> Optional[str]:
        """Resolve a note reference to financial statements."""
        # Common patterns for note sections
        note_patterns = [
            rf"(?:^|\n)\s*NOTE\s*{note_num}\s*[-–—:.\s]+([^\n]+)",
            rf"(?:^|\n)\s*Note\s*{note_num}\s*[-–—:.\s]+([^\n]+)",
            rf"(?:^|\n)\s*\({note_num}\)\s*([^\n]+)",
        ]

        for pattern_str in note_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
            match = pattern.search(document)

            if match:
                # Extract note content
                start_pos = match.start()

                # Find end of note (next note or section)
                end_pattern = re.compile(
                    r'(?:^|\n)\s*(?:NOTE\s*\d+|ITEM\s*\d+|SIGNATURES)',
                    re.IGNORECASE | re.MULTILINE
                )

                end_match = end_pattern.search(document, start_pos + len(match.group(0)))
                end_pos = end_match.start() if end_match else min(start_pos + 5000, len(document))

                note_text = document[start_pos:end_pos].strip()

                # Clean up the text
                note_text = self._clean_reference_text(note_text)

                return note_text

        return None

    def _resolve_item_reference(self, item_id: str, document: str) -> Optional[str]:
        """Resolve an item reference."""
        # Pattern for item sections
        item_pattern = re.compile(
            rf"(?:^|\n)\s*ITEM\s*{item_id}\.?\s*[-–—:.\s]*([^\n]+)",
            re.IGNORECASE | re.MULTILINE
        )

        match = item_pattern.search(document)
        if match:
            start_pos = match.start()

            # Find next item or major section
            end_pattern = re.compile(
                r'(?:^|\n)\s*(?:ITEM\s*\d+|PART\s*[IVX]+|SIGNATURES)',
                re.IGNORECASE | re.MULTILINE
            )

            end_match = end_pattern.search(document, start_pos + len(match.group(0)))
            end_pos = end_match.start() if end_match else min(start_pos + 10000, len(document))

            # Extract first few paragraphs as summary
            item_text = document[start_pos:end_pos]
            paragraphs = item_text.split('\n\n')[:3]  # First 3 paragraphs

            summary = '\n\n'.join(paragraphs).strip()
            return self._clean_reference_text(summary)

        return None

    def _resolve_exhibit_reference(self, exhibit_id: str, document: str) -> Optional[str]:
        """Resolve an exhibit reference."""
        # For exhibits, we typically just note what it is
        exhibit_pattern = re.compile(
            rf"(?:^|\n)\s*(?:Exhibit\s*)?{exhibit_id}\s*[-–—:.\s]*([^\n]+)",
            re.IGNORECASE | re.MULTILINE
        )

        # Look in exhibit index
        index_section = re.search(
            r'EXHIBIT\s*INDEX.*?(?=SIGNATURES|$)',
            document,
            re.IGNORECASE | re.DOTALL
        )

        if index_section:
            match = exhibit_pattern.search(index_section.group(0))
            if match:
                description = match.group(1).strip()
                return f"[Exhibit {exhibit_id}: {description}]"

        return f"[Reference to Exhibit {exhibit_id}]"

    def _resolve_section_reference(self, section_title: str, document: str) -> Optional[str]:
        """Resolve a section reference by title."""
        # Create pattern from section title
        escaped_title = re.escape(section_title)
        section_pattern = re.compile(
            rf"(?:^|\n)\s*{escaped_title}\s*(?:\n|$)",
            re.IGNORECASE | re.MULTILINE
        )

        match = section_pattern.search(document)
        if match:
            start_pos = match.end()

            # Extract a summary (first 2 paragraphs)
            text_after = document[start_pos:start_pos + 3000]
            paragraphs = text_after.split('\n\n')[:2]

            summary = '\n\n'.join(paragraphs).strip()
            return self._clean_reference_text(summary)

        return None

    def _clean_reference_text(self, text: str) -> str:
        """Clean up referenced text."""
        # Remove excess whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove page numbers and headers
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'Table\s*of\s*Contents', '', text, flags=re.IGNORECASE)

        # Trim to reasonable length
        if len(text) > 2000:
            text = text[:2000] + "..."

        return text.strip()

    def _deduplicate_references(self, references: List[CrossReference]) -> List[CrossReference]:
        """Remove duplicate references."""
        seen = set()
        unique_refs = []

        for ref in references:
            key = (ref.reference_type, ref.target_id, ref.start_pos)
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)

        return unique_refs

    def format_resolved_references(self, references: List[CrossReference]) -> str:
        """Format resolved references for output."""
        if not any(ref.resolved for ref in references):
            return ""

        output = ["\n\n--- CROSS-REFERENCES ---\n"]

        for ref in references:
            if ref.resolved and ref.resolution_text:
                output.append(f"\n[{ref.reference_text}]:")
                output.append(ref.resolution_text)
                output.append("")

        return '\n'.join(output)