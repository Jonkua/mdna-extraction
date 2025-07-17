"""Logging configuration and utilities."""

import logging
import colorlog
from pathlib import Path
from datetime import datetime
from typing import Optional
from config.settings import LOG_DIR, LOG_FILENAME, LOG_FORMAT, LOG_DATE_FORMAT

# Global error log file
ERROR_LOG_PATH = LOG_DIR / LOG_FILENAME


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    # Determine log level
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create formatters
    file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)

    # Console formatter with colors
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s' + LOG_FORMAT,
        LOG_DATE_FORMAT,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler for errors
    error_handler = logging.FileHandler(ERROR_LOG_PATH, mode='a')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_error(message: str, file_path: Optional[Path] = None) -> None:
    """
    Log an error to the error file.

    Args:
        message: Error message
        file_path: Optional file path related to the error
    """
    logger = get_logger("ERROR_LOGGER")

    if file_path:
        error_msg = f"[{file_path}] {message}"
    else:
        error_msg = message

    logger.error(error_msg)

    # Also write to dedicated error file with timestamp
    with open(ERROR_LOG_PATH, 'a') as f:
        timestamp = datetime.now().strftime(LOG_DATE_FORMAT)
        f.write(f"{timestamp} - ERROR - {error_msg}\n")


def log_summary(stats: dict) -> None:
    """
    Log a processing summary.

    Args:
        stats: Statistics dictionary
    """
    logger = get_logger("SUMMARY")

    logger.info("=" * 60)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 60)

    if "total_files" in stats:
        logger.info(f"Total files: {stats['total_files']}")

    if "processed" in stats:
        logger.info(f"Successfully processed: {stats['processed']}")
    elif "successful" in stats:
        logger.info(f"Successfully processed: {stats['successful']}")

    if "failed" in stats:
        logger.info(f"Failed: {stats['failed']}")

    if stats.get("failed", 0) > 0:
        logger.warning(f"Check {ERROR_LOG_PATH} for details on failures")

    logger.info("=" * 60)