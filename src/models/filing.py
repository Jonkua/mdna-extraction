"""Data models for SEC filings and extraction results."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


@dataclass
class Filing:
    """Represents a 10-K or 10-K/A filing."""
    cik: str
    company_name: str
    filing_date: datetime
    form_type: str  # "10-K" or "10-K/A"
    file_path: Path

    def __post_init__(self):
        # Ensure CIK is 10 digits
        self.cik = self.cik.zfill(10)

    @property
    def is_amended(self) -> bool:
        """Check if this is an amended filing."""
        return self.form_type == "10-K/A"


@dataclass
class ExtractionResult:
    """Results from MD&A extraction."""
    filing: Filing
    mdna_text: str
    tables: List[Any]  # List of Table objects from table_parser
    cross_references: List[Any]  # List of CrossReference objects
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return bool(self.mdna_text)

    @property
    def statistics(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return {
            "cik": self.filing.cik,
            "filing_date": self.filing.filing_date.isoformat(),
            "form_type": self.filing.form_type,
            "word_count": self.extraction_metadata.get("word_count", 0),
            "table_count": len(self.tables),
            "cross_reference_count": len(self.cross_references),
            "has_warnings": bool(self.extraction_metadata.get("warnings", [])),
        }


@dataclass
class ProcessingError:
    """Represents an error during processing."""
    file_path: Path
    error_type: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for logging."""
        return {
            "file": str(self.file_path),
            "type": self.error_type,
            "message": self.error_message,
            "timestamp": self.timestamp.isoformat()
        }