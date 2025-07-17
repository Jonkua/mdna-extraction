"""Main MD&A extractor orchestrator."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from config.patterns import compile_patterns
from src.core.file_handler import FileHandler
from src.parsers.section_parser import SectionParser
from src.parsers.table_parser import TableParser
from src.parsers.cross_reference_parser import CrossReferenceParser
from src.utils.text_normalizer import TextNormalizer
from src.utils.logger import get_logger, log_error
from src.models.filing import Filing, ExtractionResult
from config.settings import MAX_ERRORS_PER_FILE

logger = get_logger(__name__)


class MDNAExtractor:
    """Main class for extracting MD&A sections from SEC filings."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.file_handler = FileHandler()
        self.section_parser = SectionParser()
        self.table_parser = TableParser()
        self.cross_ref_parser = CrossReferenceParser()
        self.normalizer = TextNormalizer()
        self.patterns = compile_patterns()
        self.error_count = 0

    def extract_from_file(self, file_path: Path, reference_resolver=None) -> Optional[ExtractionResult]:
        """
        Extract MD&A from a single filing file.

        Args:
            file_path: Path to the filing file
            reference_resolver: Optional ReferenceResolver instance

        Returns:
            ExtractionResult or None if extraction failed
        """
        logger.info(f"Processing file: {file_path}")
        self.error_count = 0

        try:
            # Read file content
            content = self.file_handler.read_file(file_path)
            if not content:
                log_error(f"Failed to read file: {file_path}")
                return None

            # Parse filing metadata
            filing = self._parse_filing_metadata(content, file_path)
            if not filing:
                log_error(f"Failed to parse metadata from: {file_path}")
                return None

            # Extract MD&A section
            mdna_bounds = self.section_parser.find_mdna_section(content, filing.form_type)
            if not mdna_bounds:
                log_error(f"MD&A section not found in: {file_path}")
                return None

            start_pos, end_pos = mdna_bounds

            # Check for incorporation by reference
            incorporation_ref = self.section_parser.check_incorporation_by_reference(
                content, start_pos, end_pos
            )

            if incorporation_ref:
                logger.warning(f"MD&A incorporated by reference in {file_path}")
                logger.info(f"Reference type: {incorporation_ref.document_type}")
                logger.info(f"Caption: {incorporation_ref.caption}")
                logger.info(f"Pages: {incorporation_ref.page_reference}")

                # Try to resolve the reference if resolver is available
                resolved_mdna = None
                if reference_resolver:
                    try:
                        resolved_mdna = reference_resolver.resolve_reference(
                            incorporation_ref,
                            filing
                        )
                    except Exception as e:
                        logger.error(f"Failed to resolve reference: {e}")

                if resolved_mdna:
                    logger.info(f"Successfully resolved MD&A from {incorporation_ref.document_type}")

                    # Process the resolved content
                    normalized_text = self.normalizer.normalize_text(resolved_mdna, preserve_structure=True)
                    tables = self.table_parser.identify_tables(normalized_text)
                    final_text = self.table_parser.preserve_tables_in_text(normalized_text, tables)

                    # Create result with resolved content
                    result = ExtractionResult(
                        filing=filing,
                        mdna_text=final_text,
                        tables=tables,
                        cross_references=[],
                        extraction_metadata={
                            "start_pos": 0,
                            "end_pos": len(final_text),
                            "word_count": len(final_text.split()),
                            "table_count": len(tables),
                            "cross_ref_count": 0,
                            "warnings": ["MD&A resolved from referenced document"],
                            "incorporation_by_reference": {
                                "document_type": incorporation_ref.document_type,
                                "caption": incorporation_ref.caption,
                                "page_reference": incorporation_ref.page_reference,
                                "resolved": True
                            }
                        }
                    )

                    self._save_extraction_result(result)
                    return result
                else:
                    # Could not resolve - log error and skip this file
                    log_error(
                        f"MD&A incorporated by reference but could not resolve from {incorporation_ref.document_type}",
                        file_path
                    )
                    return None  # Don't save placeholder

            # Continue with normal extraction...
            mdna_text = content[start_pos:end_pos]
            # ... rest of the method remains the same

            # Continue with normal extraction
            mdna_text = content[start_pos:end_pos]

            # Validate section
            # In the extract_from_file method, update the validation call:
            validation = self.section_parser.validate_section(content, start_pos, end_pos, filing.form_type)
            if not validation["is_valid"]:
                log_error(f"Invalid MD&A section in {file_path}: {validation['warnings']}")
                if self.error_count > MAX_ERRORS_PER_FILE:
                    return None

            # Normalize text while preserving structure
            normalized_text = self.normalizer.normalize_text(mdna_text, preserve_structure=True)

            # Identify tables (but keep them in place)
            tables = self.table_parser.identify_tables(normalized_text)
            logger.info(f"Found {len(tables)} tables")

            # Preserve tables in their original positions
            final_text = self.table_parser.preserve_tables_in_text(normalized_text, tables)

            # Find and resolve cross-references
            cross_refs = self.cross_ref_parser.find_cross_references(final_text)

            # Then, resolve them (using the full document for context)
            if cross_refs:
                cross_refs = self.cross_ref_parser.resolve_references(
                    cross_refs,
                    content,
                    self.normalizer
                )
                logger.info(f"Found {len(cross_refs)} cross-references")
            else:
                cross_refs = []

            # 6) Build and save the result
            result = ExtractionResult(
                filing=filing,
                mdna_text=final_text,
                tables=tables,
                cross_references=cross_refs,
                extraction_metadata={
                    "start_pos": start_pos,
                    "end_pos": end_pos,
                    "word_count": validation["word_count"],
                    "table_count": len(tables),
                    "cross_ref_count": len(cross_refs),
                    "warnings": validation["warnings"]
                }
            )

            # Save outputs
            self._save_extraction_result(result)

            return result

        except Exception as e:
            log_error(f"Error processing {file_path}: {str(e)}")
            return None

    def _parse_filing_metadata(self, content: str, file_path: Path) -> Optional[Filing]:
        """Parse filing metadata from document content."""
        try:
            # Extract CIK - try multiple patterns
            cik = None
            cik_patterns = [
                r"(?:CENTRAL\s*INDEX\s*KEY|CIK)[\s:]*(\d{4,10})",
                r"(?:COMPANY\s*CONFORMED\s*NAME).*?(?:CENTRAL\s*INDEX\s*KEY|CIK)[\s:]*(\d{4,10})",
                r"^\s*(\d{10})\s*$",  # Sometimes just the number on a line
            ]

            for pattern_str in cik_patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                match = pattern.search(content[:10000])
                if match:
                    cik = match.group(1).zfill(10)
                    break

            if not cik:
                # Try to extract from filename
                cik_from_name = re.search(r"(\d{4,10})", file_path.name)
                cik = cik_from_name.group(1).zfill(10) if cik_from_name else "0000000000"

            # Extract company name
            company_name = self.normalizer.extract_company_name(content)
            if not company_name:
                company_name = "Unknown Company"

            # Extract filing date - try multiple patterns
            filing_date = None
            date_patterns = [
                r"(?:FILED\s*AS\s*OF\s*DATE|Filing\s*Date)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                r"(?:DATE\s*OF\s*FILING|CONFORMED\s*SUBMISSION\s*TYPE).*?(\d{8})",  # YYYYMMDD format
                r"(?:PERIOD\s*OF\s*REPORT)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            ]

            for pattern_str in date_patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                match = pattern.search(content[:10000])
                if match:
                    date_str = match.group(1)
                    filing_date = self._parse_date(date_str)
                    if filing_date:
                        break

            if not filing_date:
                # Try to extract date from filename (common format: YYYYMMDD)
                date_from_name = re.search(r"(\d{8})", file_path.name)
                if date_from_name:
                    try:
                        filing_date = datetime.strptime(date_from_name.group(1), "%Y%m%d")
                    except:
                        filing_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                else:
                    filing_date = datetime.fromtimestamp(file_path.stat().st_mtime)

            # Extract form type - try multiple patterns
            form_type = "10-K"  # Default

            for pattern in self.patterns["form_type"]:
                match = pattern.search(content[:10000])
                if match:
                    form_type_raw = match.group(1).upper()
                    # Normalize form type
                    if '10-Q' in form_type_raw:
                        if 'A' in form_type_raw or '/A' in form_type_raw:
                            form_type = "10-Q/A"
                        else:
                            form_type = "10-Q"
                    elif '10-K' in form_type_raw:
                        if 'A' in form_type_raw or '/A' in form_type_raw:
                            form_type = "10-K/A"
                        else:
                            form_type = "10-K"
                    break
            else:
                # Infer from filename
                filename_upper = file_path.name.upper()
                if '10-Q' in filename_upper or '10Q' in filename_upper:
                    if '_A' in filename_upper:
                        form_type = "10-Q/A"
                    else:
                        form_type = "10-Q"
                elif '10KSB' in filename_upper:
                    form_type = "10-K"  # Small business 10-K
                elif '10-K_A' in filename_upper or '10KA' in filename_upper or '_A' in filename_upper:
                    form_type = "10-K/A"

            return Filing(
                cik=cik,
                company_name=company_name,
                filing_date=filing_date,
                form_type=form_type,
                file_path=file_path
            )

        except Exception as e:
            logger.error(f"Error parsing metadata: {e}")
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        # Try common date formats
        formats = [
            "%m/%d/%Y", "%m-%d-%Y",
            "%m/%d/%y", "%m-%d-%y",
            "%Y-%m-%d", "%Y/%m/%d",
            "%Y%m%d",  # YYYYMMDD format
            "%B %d, %Y", "%b %d, %Y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        # If all formats fail, return current date
        logger.warning(f"Could not parse date: {date_str}")
        return datetime.now()

    def _save_extraction_result(self, result: ExtractionResult):
        """Save extraction results to output files."""
        # Generate filename according to new format:
        # (CIK)_(SanitizedCompanyName)_(FilingDate:YYYY-MM-DD)_(FormType).txt

        # Prepare components
        cik = result.filing.cik
        company_name = self.normalizer.sanitize_filename(result.filing.company_name)
        filing_date = result.filing.filing_date.strftime("%Y-%m-%d")
        form_type = result.filing.form_type.replace('/', '-')  # Replace / with - for filename

        # Build filename
        filename = f"({cik})_({company_name})_({filing_date})_({form_type}).txt"
        output_path = self.output_dir / filename

        # Prepare final content
        final_content = []

        # Add header with metadata
        final_content.append("=" * 80)
        final_content.append(f"CIK: {cik}")
        final_content.append(f"Company Name: {result.filing.company_name}")
        final_content.append(f"Filing Date: {filing_date}")
        final_content.append(f"Form Type: {form_type}")
        final_content.append(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        final_content.append("=" * 80)
        final_content.append("")

        # Add main content (which already includes tables in their proper positions)
        # The content now includes the original "ITEM 7" header
        final_content.append(result.mdna_text)

        # Add cross-references if any
        if result.cross_references:
            resolved_refs = [ref for ref in result.cross_references if ref.resolved]
            if resolved_refs:
                final_content.append("")
                final_content.append("-" * 80)
                final_content.append("CROSS-REFERENCES")
                final_content.append("-" * 80)
                final_content.append("")

                for ref in resolved_refs:
                    if ref.resolution_text:
                        final_content.append(f"[{ref.reference_text}]:")
                        final_content.append(ref.resolution_text)
                        final_content.append("")

        # Join all content
        output_text = '\n'.join(final_content)

        # Save file
        self.file_handler.write_file(output_path, output_text)
        logger.info(f"Saved MD&A to: {output_path}")

    def process_directory(self, input_dir: Path) -> Dict[str, any]:
        """
        Process all files in a directory.

        Args:
            input_dir: Directory containing filing files

        Returns:
            Processing summary statistics
        """
        stats = {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }

        # Find all text files
        text_files = list(input_dir.glob("*.txt")) + list(input_dir.glob("*.TXT"))
        stats["total_files"] = len(text_files)

        logger.info(f"Found {len(text_files)} text files to process")

        for file_path in text_files:
            result = self.extract_from_file(file_path)
            if result:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
                stats["errors"].append(str(file_path))

        return stats

    def _create_incorporation_placeholder(self, incorporation_ref, filing) -> str:
        """Create placeholder text for incorporation by reference cases."""
        placeholder = []

        placeholder.append("ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS")
        placeholder.append("")
        placeholder.append("=" * 80)
        placeholder.append("NOTE: MD&A INCORPORATED BY REFERENCE")
        placeholder.append("=" * 80)
        placeholder.append("")
        placeholder.append("The Management's Discussion and Analysis for this filing is incorporated by reference.")
        placeholder.append("")

        if incorporation_ref.document_type:
            placeholder.append(f"Referenced Document: {incorporation_ref.document_type}")

        if incorporation_ref.caption:
            placeholder.append(f"Section/Caption: {incorporation_ref.caption}")

        if incorporation_ref.page_reference:
            placeholder.append(f"Page Reference: {incorporation_ref.page_reference}")

        placeholder.append("")
        placeholder.append("Full Reference Text:")
        placeholder.append("-" * 40)
        placeholder.append(incorporation_ref.full_text)
        placeholder.append("-" * 40)
        placeholder.append("")
        placeholder.append("To obtain the complete MD&A content, please refer to the referenced document.")
        placeholder.append(f"This may require locating the {incorporation_ref.document_type or 'referenced document'} ")
        placeholder.append(f"filed under the same accession number or during the same reporting period.")

        return '\n'.join(placeholder)