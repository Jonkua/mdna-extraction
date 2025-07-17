"""Main entry point for MD&A Extractor with unified 10-Q fallback support."""

import argparse
import sys
from pathlib import Path

from src.core.zip_processor import ZipProcessor
from src.core.extractor import MDNAExtractor
from src.utils.logger import setup_logging, get_logger, log_summary
from config.settings import INPUT_DIR, OUTPUT_DIR

logger = get_logger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Extract MD&A sections from 10-K, 10-K/A, and fallback 10-Q filings"
    )

    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=INPUT_DIR,
        help="Input directory containing ZIP files or text files"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for extracted MD&A sections"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--zip-only",
        action="store_true",
        help="Process only ZIP files"
    )

    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Process only text files"
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(verbose=args.verbose)

    # Validate directories
    if not args.input.exists():
        logger.error(f"Input directory does not exist: {args.input}")
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)

    logger.info("MD&A Extractor starting...")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")

    try:
        # Initialize stats container
        stats = {}

        if args.zip_only:
            processor = ZipProcessor(args.output)
            zipped = processor.process_directory(args.input)
            # Normalize to unified stats format
            stats = {
                "combined": {
                    "total_files": zipped.get("total_files", 0),
                    "processed":  zipped.get("processed", 0),
                    "failed":     zipped.get("failed", 0),
                    "skipped_10q": 0
                },
                "errors": []
            }

        elif args.text_only:
            extractor = MDNAExtractor(args.output)
            txt = extractor.process_directory(args.input)
            stats = {
                "combined": {
                    "total_files": txt.get("total_files", 0),
                    "processed":  txt.get("successful", 0),
                    "failed":     txt.get("failed", 0),
                    "skipped_10q": 0
                },
                "errors": txt.get("errors", [])
            }

        else:
            processor = ZipProcessor(args.output)
            # Mixed processing with 10-Q fallback logic
            stats = processor.process_mixed_directory(args.input)

        # Log summary
        log_summary(stats)

        # Log skipped 10-Q fallback count
        skipped = stats.get("combined", {}).get("skipped_10q", 0)
        if skipped:
            logger.info(f"Skipped {skipped} fallback 10-Q filings")

        # Determine failures
        failed_count = stats.get("combined", {}).get("failed", 0)
        if failed_count > 0:
            logger.warning(f"{failed_count} files failed processing")
            sys.exit(1)
        else:
            logger.info("All files processed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
