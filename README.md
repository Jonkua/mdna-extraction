# MD&A Extractor for SEC 10-K/10-K/A Filings

A robust Python tool for extracting Management's Discussion and Analysis (MD&A) sections from SEC filings in text format. The extractor processes ZIP archives and loose text files of pre-downloaded filings, prioritizes and falls back on 10-Q filings only when necessary, identifies MD&A sections using comprehensive regex patterns, extracts tables, resolves cross-references, and outputs clean, normalized text files.

## Key Features

- **Form Prioritization & 10-Q Fallback**  
  Uses `FilingManager` to process filings in priority order (10-K/A > 10-K > 10-Q/A > 10-Q). Quarterly (10-Q) filings are only extracted when no 10-K or 10-K/A is available for the same year, and are clearly labeled and counted as fallback in the summary (`skipped_10q`).

- **Automatic Section Detection**  
  Comprehensive regex patterns (in `config/patterns.py`) detect:
  - **10-K**: Item 7 start/end boundaries (Item 7A, Item 8, fallback markers)
  - **10-Q**: Item 2 start, end at Item 3/Item 4/Part II or fallback cues

- **Unified ZIP & Text Processing**  
  A single `process_mixed_directory` flow gathers all text files (from both ZIP archives and loose `.txt`), registers them with `FilingManager`, selects which to process/skip, and tracks:
  - `combined.processed`  
  - `combined.failed`  
  - `combined.skipped_10q`
  - Separate `zip_results` and `text_results` breakdowns

- **Table Extraction & Embedding**  
  Detects both delimited and aligned tables, embeds them in-place within the MD&A text, preserving original layout.

- **Cross-Reference Resolution**  
  Resolves Note, Item, Exhibit, and Section references with context, without interrupting the main extraction.

- **Text Normalization**  
  Cleans control characters, removes SEC markers, normalizes whitespace, and preserves encoding preferences.

- **Extensive Testing**  
  Unit tests cover:
  - MD&A extraction for 10-K and 10-Q  
  - 10-Q fallback behavior  
  - SectionParser fallback end patterns (`_find_10q_fallback_end`)  
  - FilingManager priority logic  
  - ZipProcessor mixed-directory processing

## Installation

```bash
git clone <repository-url>
cd mdna_extractor
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python -m src.main [OPTIONS]
```

**Options:**
```
  -i, --input PATH      Input directory (default: ./input)
  -o, --output PATH     Output directory (default: ./output)
  -v, --verbose         Enable verbose logging
  --zip-only            Process only ZIP files
  --text-only           Process only text files
  -h, --help            Show help message
```

**Examples:**
```bash
# Mixed ZIP + text with fallback logic
python -m src.main

# Only ZIP archives
python -m src.main --zip-only

# Only loose text files
python -m src.main --text-only

# Custom directories
python -m src.main -i /path/to/input -o /path/to/output -v
```

## Configuration

Edit `config/settings.py` to customize:
- **INPUT_DIR / OUTPUT_DIR**  (default to `./input` / `./output`)
- **VALID_EXTENSIONS**, **ZIP_EXTENSIONS**
- **Processing limits** (`MAX_ERRORS_PER_FILE`, `MAX_CROSS_REFERENCE_DEPTH`, etc.)
- **FILING_PRIORITY** (order of form types)

## Output Structure

For each processed filing, an output text file named:
```
(CIK)_(SanitizedCompanyName)_(YYYY-MM-DD)_(FormType).txt
```
Includes:
1. **Header** (CIK, Company, Date, FormType, Extraction timestamp)
2. **MD&A Text** (with tables embedded in original locations)
3. **Cross-References** (resolved at end)

Example directory:
```
output/
├── (0001234567)_(TestCorp)_(2024-03-15)_(10-K).txt
└── (0001234567)_(TestCorp)_(2024-06-30)_(10-Q).txt
```

## Testing

Run all tests with:
```bash
pytest --cov=src --cov-report=html
```

## Using the Test Scripts

All test modules live under the `tests/` directory, matching their functionality:

- **`tests/test_extractor.py`**: MDNAExtractor functionality (10-K, 10-Q extraction)
- **`tests/test_parsers.py`**: Section, table, and cross-reference parser behaviors
- **`tests/test_filing_manager.py`**: FilingManager priority and fallback logic
- **`tests/test_zip_processor.py`**: ZIPProcessor mixed-directory and fallback processing

You can run tests in several ways:

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_parsers.py

# Run tests with verbose output
pytest -v

# Stop at first failure, disable warnings
pytest --maxfail=1 --disable-warnings -v
```

## Contributing

- Update `config/patterns.py` for new regex needs  
- Add tests for new functionality  
- Ensure `skipped_10q` metrics are accurate  
- Maintain 90%+ test coverage

## Acknowledgments

Built for streamlined MD&A extraction from SEC EDGAR text filings, with prioritized handling of annual and quarterly reports.
