"""ZIP archive processor for handling compressed SEC filings with 10-Q fallback logic."""

import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict

from src.core.extractor import MDNAExtractor
from src.core.file_handler import FileHandler
from src.core.filing_manager import FilingManager
from src.utils.logger import get_logger, log_error
from config.settings import VALID_EXTENSIONS, ZIP_EXTENSIONS

logger = get_logger(__name__)


class ZipProcessor:
    """Handles processing of ZIP archives containing SEC filings."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.extractor = MDNAExtractor(output_dir)
        self.file_handler = FileHandler()

    def process_zip_file(self, zip_path: Path) -> Dict[str, any]:
        """
        Process a single ZIP file.

        Args:
            zip_path: Path to ZIP file

        Returns:
            Processing statistics
        """
        logger.info(f"Processing ZIP file: {zip_path}")

        stats = {
            "zip_file": str(zip_path),
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "errors": []
        }

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                text_files = [f for f in file_list if any(f.endswith(ext) for ext in VALID_EXTENSIONS)]

                stats["total_files"] = len(text_files)
                logger.info(f"Found {len(text_files)} text files in archive")

                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    for file_name in text_files:
                        try:
                            zf.extract(file_name, temp_path)
                            file_path = temp_path / file_name
                            result = self.extractor.extract_from_file(file_path)
                            if result:
                                stats["processed"] += 1
                            else:
                                stats["failed"] += 1
                                stats["errors"].append({"file": file_name, "error": "Extraction failed"})
                        except Exception as e:
                            stats["failed"] += 1
                            stats["errors"].append({"file": file_name, "error": str(e)})
                            log_error(f"Error processing {file_name} from {zip_path}: {e}")
        except zipfile.BadZipFile:
            log_error(f"Invalid ZIP file: {zip_path}")
            stats["errors"].append({"file": str(zip_path), "error": "Invalid ZIP file"})
        except Exception as e:
            log_error(f"Error processing ZIP file {zip_path}: {e}")
            stats["errors"].append({"file": str(zip_path), "error": str(e)})

        return stats

    def process_directory(self, input_dir: Path) -> Dict[str, any]:
        """
        Process all ZIP files in a directory.

        Args:
            input_dir: Directory containing ZIP files

        Returns:
            Overall processing statistics
        """
        overall_stats = {
            "total_zips": 0,
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "zip_stats": []
        }

        zip_files = []
        for ext in ZIP_EXTENSIONS:
            zip_files.extend(input_dir.glob(f"*{ext}"))
        zip_files = list(set(zip_files))
        overall_stats["total_zips"] = len(zip_files)

        logger.info(f"Found {len(zip_files)} ZIP files to process")

        for zip_path in sorted(zip_files):
            stats = self.process_zip_file(zip_path)
            overall_stats["zip_stats"].append(stats)
            overall_stats["total_files"] += stats["total_files"]
            overall_stats["processed"] += stats["processed"]
            overall_stats["failed"] += stats["failed"]

        return overall_stats

    def process_mixed_directory(
            self,
            input_dir: Path,
            resolve_references: bool = True
    ) -> Dict[str, any]:
        """
        Process directory containing both ZIP files and loose text files,
        applying 10-Q fallback logic centrally via FilingManager.

        Args:
            input_dir: Input directory
            resolve_references: Whether to attempt resolving incorporation by reference

        Returns:
            Combined processing statistics
        """
        stats = {
            "zip_results": {"total_files": 0, "processed": 0, "failed": 0},
            "text_results": {"total_files": 0, "processed": 0, "failed": 0},
            "combined": {"total_files": 0, "processed": 0, "failed": 0, "skipped_10q": 0},
            "errors": []
        }

        # 1) Discover all text files (from ZIPs and loose)
        zip_text_files: List[Path] = []
        for zip_path in {*input_dir.glob("*.zip"), *input_dir.glob("*.ZIP")}:
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    for member in zf.namelist():
                        if any(member.endswith(ext) for ext in VALID_EXTENSIONS):
                            tmp = tempfile.mkdtemp()
                            zf.extract(member, tmp)
                            zip_text_files.append(Path(tmp) / member)
            except Exception as e:
                log_error(f"Error listing {zip_path}: {e}")

        loose_files: List[Path] = []
        for ext in VALID_EXTENSIONS:
            loose_files.extend(input_dir.glob(f"*{ext}"))

        # ─── Dedupe any duplicates (e.g. .txt vs .TXT) ───
        zip_text_files = list(dict.fromkeys(zip_text_files))
        loose_files = list(dict.fromkeys(loose_files))

        stats["zip_results"]["total_files"] = len(zip_text_files)
        stats["text_results"]["total_files"] = len(loose_files)

        all_text_files = zip_text_files + loose_files
        stats["combined"]["total_files"] = len(all_text_files)

        # 2) Register with FilingManager
        fm = FilingManager()
        for fp in all_text_files:
            cik, year, form_type = fm._parse_filename_metadata(fp)
            if cik and year and form_type:
                fm.add_filing(fp, cik, year, form_type)

        # 3) Select which to process and skip
        selection = fm._select_filings_to_process()
        to_process = set(selection["process"])
        to_skip = set(selection["skip"])

        # Initialize reference resolver if requested
        reference_resolver = None
        if resolve_references:
            from src.core.reference_resolver import ReferenceResolver
            reference_resolver = ReferenceResolver(input_dir)

        # 4) Process only selected filings
        for fp in to_process:
            try:
                result = self.extractor.extract_from_file(fp, reference_resolver)
                if result:
                    stats["combined"]["processed"] += 1
                    if fp in zip_text_files:
                        stats["zip_results"]["processed"] += 1
                    else:
                        stats["text_results"]["processed"] += 1
                else:
                    stats["combined"]["failed"] += 1
                    stats["errors"].append(str(fp))
                    if fp in zip_text_files:
                        stats["zip_results"]["failed"] += 1
                    else:
                        stats["text_results"]["failed"] += 1
            except Exception as e:
                stats["combined"]["failed"] += 1
                stats["errors"].append(f"{fp}: {e}")
                if fp in zip_text_files:
                    stats["zip_results"]["failed"] += 1
                else:
                    stats["text_results"]["failed"] += 1

        # 5) Count skipped 10-Qs
        for fp in to_skip:
            _, _, ft = fm._parse_filename_metadata(fp)
            if ft and ft.startswith("10-Q"):
                stats["combined"]["skipped_10q"] += 1

        return stats
