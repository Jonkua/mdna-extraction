"""File handling utilities for reading and writing files."""

import chardet
from pathlib import Path
from typing import Optional, List
from config.settings import (
    ENCODING_PREFERENCES,
    MAX_FILE_SIZE_MB,
    CHUNK_SIZE
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileHandler:
    """Handles file I/O operations with encoding detection."""

    def read_file(self, file_path: Path) -> Optional[str]:
        """
        Read file content with automatic encoding detection.

        Args:
            file_path: Path to file

        Returns:
            File content as string or None if failed
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.error(f"File too large ({file_size_mb:.1f} MB): {file_path}")
            return None

        # Try preferred encodings first
        for encoding in ENCODING_PREFERENCES:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.debug(f"Successfully read file with {encoding} encoding")
                return content
            except UnicodeDecodeError:
                continue

        # If preferred encodings fail, detect encoding
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding']

            if encoding:
                logger.info(f"Detected encoding: {encoding}")
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            else:
                logger.error(f"Could not detect encoding for: {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def read_file_chunked(self, file_path: Path) -> Optional[str]:
        """
        Read large file in chunks.

        Args:
            file_path: Path to file

        Returns:
            File content as string or None if failed
        """
        if not file_path.exists():
            return None

        try:
            # Detect encoding first
            with open(file_path, 'rb') as f:
                sample = f.read(10000)  # Read 10KB sample
                result = chardet.detect(sample)
                encoding = result['encoding'] or 'utf-8'

            # Read in chunks
            chunks = []
            with open(file_path, 'r', encoding=encoding) as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    chunks.append(chunk)

            return ''.join(chunks)

        except Exception as e:
            logger.error(f"Error reading file in chunks {file_path}: {e}")
            return None

    def write_file(self, file_path: Path, content: str, encoding: str = 'utf-8'):
        """
        Write content to file.

        Args:
            file_path: Path to output file
            content: Content to write
            encoding: Output encoding
        """
        try:
            # Create parent directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            logger.debug(f"Successfully wrote file: {file_path}")

        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            raise

    def list_files(self, directory: Path, extensions: List[str]) -> List[Path]:
        """
        List all files with given extensions in directory.

        Args:
            directory: Directory to search
            extensions: List of file extensions (with dots)

        Returns:
            List of file paths
        """
        files = []

        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return files

        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
            # Also check uppercase
            files.extend(directory.glob(f"*{ext.upper()}"))

        # Remove duplicates
        files = list(set(files))

        return sorted(files)