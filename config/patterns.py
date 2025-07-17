"""Regex patterns for MD&A section detection and parsing."""

import re

# Section boundary patterns (case-insensitive)
ITEM_7_START_PATTERNS = [
    # Standard “Management’s Discussion and Analysis”
    r"(?:^|\n)\s*ITEM\s*7\.?\s*MANAGEMENT['’]?S\s*DISCUSSION\s*AND\s*ANALYSIS",
    r"(?:^|\n)\s*ITEM\s*7\.?\s*MANAGEMENT['’]?S\s*DISCUSSION\s*&\s*ANALYSIS",
    # Abbreviated MD&A forms
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+MD&A",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+M\s*D\s*&?\s*A",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+MDA",
    # Spelled‐out “Seven”
    r"(?:^|\n)\s*ITEM\s+SEVEN\.?\s*MANAGEMENT['’]?S\s*DISCUSSION\s*AND\s*ANALYSIS",
    # Roman numeral
    r"(?:^|\n)\s*ITEM\s*VII[\-:\s]+MD&A",
    # Part II prefix
    r"(?:^|\n)\s*PART\s*II[-:\s]+ITEM\s*7\.?\s*MD&A",
    # Extended financial condition variants
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+DISCUSSION\s*AND\s*ANALYSIS\s*OF\s*FINANCIAL\s*CONDITION",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+MANAGEMENT['’]?S\s*ANALYSIS\s*OF\s*FINANCIAL\s*CONDITION",
    # Extended results of operations variants
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+DISCUSSION\s*AND\s*RESULTS\s*OF\s*OPERATIONS",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+ANALYSIS\s*OF\s*RESULTS\s*OF\s*OPERATIONS",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+FINANCIAL\s*CONDITION\s*AND\s*RESULTS\s*OF\s*OPERATIONS",
    # Overview & review headings
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+OVERVIEW\s*AND\s*ANALYSIS",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+REVIEW\s*OF\s*OPERATIONS",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+REVIEW\s*AND\s*RESULTS\s*OF\s*OPERATIONS",
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+OPERATING\s*RESULTS\s*AND\s*DISCUSSION",
    # Outlook
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+DISCUSSION\s*AND\s*OUTLOOK",
    # Liquidity & capital resources
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+LIQUIDITY\s*AND\s*CAPITAL\s*RESOURCES",
    # Critical accounting
    r"(?:^|\n)\s*ITEM\s*7[\-:\s]+CRITICAL\s*ACCOUNTING\s*POLICIES",
]


ITEM_7A_START_PATTERNS = [
    # Standard quantitative/qualitative heading
    r"^\s*ITEM\s*7A\.?\s*QUANTITATIVE\s*AND\s*QUALITATIVE\s*DISCLOSURES",
    r"^\s*ITEM\s*7A\.?\s*QUANTITATIVE\s*AND\s*QUALITATIVE",
    r"^\s*ITEM\s*7A\.?\s*QUANTITATIVE\s*DISCLOSURES",
    r"^\s*ITEM\s*7A\.?\s*QUALITATIVE\s*DISCLOSURES",

    # Market risk variants
    r"^\s*ITEM\s*7A\.?\s*MARKET\s*RISK\s*DISCLOSURES",
    r"^\s*ITEM\s*7A\.?\s*DISCLOSURES\s*ABOUT\s*MARKET\s*RISK",
    r"^\s*ITEM\s*7A\.?\s*MARKET\s*RISK",
    r"^\s*ITEM\s*7A\.?\s*RISK\s*DISCLOSURES",

    # Combined Q&Q and market risk
    r"^\s*ITEM\s*7A\.?\s*QUANTITATIVE\s*AND\s*QUALITATIVE\s*DISCLOSURES\s*ABOUT\s*MARKET\s*RISK",
    r"^\s*ITEM\s*7A\.?\s*QUANTITATIVE\s*AND\s*QUALITATIVE\s*&\s*MARKET\s*RISK\s*DISCLOSURES",

    # Spelled‐out “Seven A”
    r"^\s*ITEM\s+SEVEN\s*A\.?\s*QUANTITATIVE\s*AND\s*QUALITATIVE",
    r"^\s*ITEM\s+SEVEN\s*A\.?\s*MARKET\s*RISK\s*DISCLOSURES",

    # Hyphen and colon variations
    r"^\s*ITEM\s*7A[\-:\s]+QUANTITATIVE\s*AND\s*QUALITATIVE",
    r"^\s*ITEM\s*7A[\-:\s]+MARKET\s*RISK",
    r"^\s*ITEM\s*7A[\-:\s]+QUANTITATIVE\s*DISCLOSURES",
    r"^\s*ITEM\s*7A[\-:\s]+QUALITATIVE\s*DISCLOSURES",

    # Abbreviated forms
    r"^\s*ITEM\s*7A[\-:\s]+Q\s*&\s*Q",
    r"^\s*ITEM\s*7A[\-:\s]+Q\s*&?\s*Q\s*DISCLOSURES",

    # Roman numeral seven
    r"^\s*ITEM\s*VIIA\.?\s*QUANTITATIVE\s*AND\s*QUALITATIVE",
    r"^\s*ITEM\s*VIIA\.?\s*MARKET\s*RISK\s*DISCLOSURES",
    r"^\s*ITEM\s*VIIA[\-:\s]+Q\s*&\s*Q",
]


ITEM_8_START_PATTERNS = [
    # Basic Financial Statements
    r"^\s*ITEM\s*8\.?\s*FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s*8\.?\s*CONSOLIDATED\s*FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s*8\.?\s*FINANCIAL\s*STATEMENTS\s*(?:AND|&)\s*SUPPLEMENTARY\s*DATA",
    r"^\s*ITEM\s*8\.?\s*CONSOLIDATED\s*STATEMENTS\s*(?:AND|&)\s*SUPPLEMENTARY\s*DATA",

    # Spelled-out Eight
    r"^\s*ITEM\s+EIGHT\.?\s*FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s+EIGHT\.?\s*CONSOLIDATED\s*FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s+EIGHT\.?\s*FINANCIAL\s*STATEMENTS\s*(?:AND|&)\s*SUPPLEMENTARY\s*DATA",
    r"^\s*ITEM\s+EIGHT\.?\s*CONSOLIDATED\s*STATEMENTS\s*(?:AND|&)\s*SUPPLEMENTARY\s*DATA",

    # Roman Numeral
    r"^\s*ITEM\s*VIII\.?\s*FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s*VIII\.?\s*CONSOLIDATED\s*FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s*VIII\.?\s*FINANCIAL\s*STATEMENTS\s*(?:AND|&)\s*SUPPLEMENTARY\s*DATA",
    r"^\s*ITEM\s*VIII\.?\s*CONSOLIDATED\s*STATEMENTS\s*(?:AND|&)\s*SUPPLEMENTARY\s*DATA",

    # Part II prefix
    r"^\s*PART\s*II\s*[-–—]\s*ITEM\s*8\.?\s*FINANCIAL\s*STATEMENTS",
    r"^\s*PART\s*II\s*[-–—]\s*ITEM\s*8\.?\s*FINANCIAL\s*STATEMENTS\s*(?:AND|&)\s*SUPPLEMENTARY\s*DATA",

    # Hyphens, colons and spaces
    r"^\s*ITEM\s*8[\-:\s]+FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s*8[\-:\s]+CONSOLIDATED\s*FINANCIAL\s*STATEMENTS",
    r"^\s*ITEM\s*8[\-:\s]+FINANCIAL\s*STATEMENTS\s*AND\s*SUPPLEMENTARY\s*DATA",
    r"^\s*ITEM\s*8[\-:\s]+CONSOLIDATED\s*STATEMENTS\s*AND\s*SUPPLEMENTARY\s*DATA",

    # Abbreviated forms & variants
    r"^\s*ITEM\s*8[\-:\s]+FS\s*&?\s*SD",  # e.g. “FS & SD”
    r"^\s*ITEM\s*8[\-:\s]+STATEMENTS\s*AND\s*DATA",
    r"^\s*ITEM\s*8[\-:\s]+FINANCIAL\s*DATA",
]


# 10-Q specific end patterns
ITEM_2_START_PATTERNS = [
    r"(?:^|\n)\s*ITEM\s*2[\.\:\-\s]*MANAGEMENT['’`]?[S]?\s*DISCUSSION\s*(?:AND|&)\s*ANALYSIS",
    r"(?:^|\n)\s*ITEM\s+TWO[\.\:\-\s]*MANAGEMENT['’`]?[S]?\s*DISCUSSION\s*(?:AND|&)\s*ANALYSIS",
    r"(?:^|\n)\s*ITEM\s*2[\.\:\-\s]*M\s*D\s*&?\s*A",
    r"(?:^|\n)\s*ITEM\s*2[\.\:\-\s]*DISCUSSION\s+OF\s+OPERATIONS",
    r"(?:^|\n)\s*MANAGEMENT['’`]?[S]?\s*DISCUSSION\s+AND\s+ANALYSIS\s+OF\s+FINANCIAL\s+CONDITION\s+AND\s+RESULTS\s+OF\s+OPERATIONS",
]


ITEM_3_START_PATTERNS = [
    r"^\s*ITEM\s*3[\.\:\-\s]*QUANTITATIVE\s+AND\s+QUALITATIVE\s+DISCLOSURES\s+ABOUT\s+MARKET\s+RISK",
    r"^\s*ITEM\s+THREE[\.\:\-\s]*QUANTITATIVE\s+AND\s+QUALITATIVE\s+MARKET\s+RISK",
    r"^\s*ITEM\s*3[\.\:\-\s]*MARKET\s+RISK\s+DISCLOSURES",
    r"^\s*ITEM\s*3[\.\:\-\s]*QUANT\s*&?\s*QUAL\s+DISCLOSURES",
]


ITEM_4_START_PATTERNS = [
    r"^\s*ITEM\s*4[\.\:\-\s]*CONTROLS\s+AND\s+PROCEDURES",
    r"^\s*ITEM\s*4[\.\:\-\s]*DISCLOSURE\s+CONTROLS\s+AND\s+PROCEDURES",
    r"^\s*ITEM\s*4[\.\:\-\s]*EVALUATION\s+OF\s+DISCLOSURE\s+CONTROLS",
    r"^\s*ITEM\s+FOUR[\.\:\-\s]*CONTROLS\s+AND\s+PROCEDURES",
]


PART_II_START_PATTERNS = [
    r"^\s*PART\s*II[\.\:\-\s]*OTHER\s+INFORMATION",
    r"^\s*PART\s+TWO[\.\:\-\s]*OTHER\s+INFORMATION",
    r"^\s*PART\s*II[\.\:\-\s]*ITEM\s*1[\.\:\-\s]*LEGAL\s+PROCEEDINGS",
    r"^\s*PART\s*II[\.\:\-\s]*DISCLOSURE\s+ITEMS",
]


# Form type patterns - expanded to properly detect 10-Q
FORM_TYPE_PATTERNS = [
    r"(?:FORM|CONFORMED\s*SUBMISSION\s*TYPE)[\s:\-]*(\d{1,2}-[KQ](?:/A|A)?)",
    r"^\s*(?:FORM\s*)?(\d{1,2}-[KQ](?:/A|A)?)\s*$",
    r"(?:QUARTERLY\s*REPORT\s*(?:ON\s*)?FORM\s*)(\d{1,2}-Q(?:/A|A)?)",
    r"(?:ANNUAL\s*REPORT\s*(?:ON\s*)?FORM\s*)(\d{1,2}-K(?:/A|A)?)",
    r"(?:Filed\s+on\s+Form\s*)(\d{1,2}-[KQ](?:/A|A)?)",
    r"Form\s+(10-[KQ])(?:/A|A)?",
]


# Cross-reference patterns
CROSS_REFERENCE_PATTERNS = [
    # --- Note references ---
    r"(?:see|refer(?:red)?\s*to|as\s*discussed\s*in)\s*Note\s+(\d+)",  # See Note 3
    r"Note\s+(\d+)\s*(?:to|of)?\s*(?:the\s*)?(?:consolidated\s*)?financial\s*statements",  # Note 4 of FS
    r"Notes?\s+(\d+)\s*(?:through|and)\s+(\d+)",  # Notes 3 through 5

    # --- Part/Item references ---
    r"(?:see|refer(?:red)?\s*to|discussed\s*in|included\s*in)\s*Part\s*([IVX]+)[,\s]*Item\s*(\d+[A-Z]?)",  # Part II, Item 8
    r"Part\s*([IVX]+)[,\s]*Item\s*(\d+[A-Z]?)",  # Part II, Item 7A
    r"Item\s*(\d+[A-Z]?)\s*(?:of|in)?\s*Part\s*([IVX]+)",  # Item 7A of Part II
    r"(?:discussed|described)\s*(?:in|under)?\s*Item\s*(\d+[A-Z]?)",
    r"as\s+(?:set\s+forth|described)\s+in\s+Item\s*(\d+[A-Z]?)",
    r"discussed\s+in\s+(?:Item|Part\s+[IVX]+\s+Item)\s*(\d+[A-Z]?)",

    # --- Exhibit references ---
    r"(?:see|refer\s*to|contained\s*in)\s*Exhibit\s*(\d+(?:\.\d+)?)",
    r"Exhibit\s+(\d+(?:\.\d+)?)[\s\)]*(?:to|of)?\s*(?:this\s+Form\s+10-K|this\s+filing)?",

    # --- Section references (titled/quoted) ---
    r"(?:see|refer\s*to|discussed\s*in)?\s*(?:the\s*)?section\s*(?:entitled|captioned)?\s*['\"]([^'\"]+)['\"]",  # 'Liquidity and Capital Resources'
    r"(?:see|refer\s*to)?\s*(?:discussion\s*under\s*)?['\"]([^'\"]+)[\"']",  # "Results of Operations"
    r"(?:see|refer\s*to)\s*(?:the\s*)?(?:discussion\s*under\s*)?section\s*(?:called|titled)?\s*['\"]([^'\"]+)['\"]",

    # --- Generic backward/forward references ---
    r"(?:as\s+described\s+above|as\s+noted\s+below)\s+in\s+Item\s*(\d+[A-Z]?)",
    r"(?:refer\s*back\s*to|see\s*also)\s+Note\s+(\d+)",

    # --- Embedded table note reference ---
    r"see\s+accompanying\s+Notes?\s*(\d+)?\s*(?:through\s*(\d+))?",

    # --- Edge-case phrasing ---
    r"(?:see\s+also|refer\s+to)\s+(?:Note|Item|Section)\s*(\d+[A-Z]?)",
]


# Table detection patterns
TABLE_DELIMITER_PATTERNS = [
    r"^\s*[-=]{3,}\s*$",                      # --- or === line
    r"^\s*\|.*\|.*\|",                        # Pipe-delimited
    r"(?:\s{2,}|\t)",                         # Multiple spaces or tabs
    r"^\s*(?:\d+\s+){2,}",                    # Rows of numeric columns
    r"^\s*[A-Za-z]+\s+(?:[-–]\s+)?\$\(?\d",   # Label followed by number (e.g., Revenue - $1,000)
    r"^\s*\(?\$?\d[\d,\.]+\)?\s+(?:\(?\$?\d[\d,\.]+\)?\s+)+$",  # Rows of numeric entries
]


TABLE_HEADER_PATTERNS = [
    r"^\s*(?:Year|Period|Quarter|Month)\s+Ended",                      # "Year Ended December 31"
    r"^\s*(?:December|June|March|September)\s+\d{1,2},?\s+20\d{2}",    # Full date
    r"^\s*\$?\s*(?:in\s+)?(?:thousands|millions|billions)",            # Units
    r"^\s*(?:Revenue|Income|Assets|Liabilities|Equity)",               # Key financial labels
    r"^\s*Statements?\s+of\s+(?:Operations|Cash\s+Flows|Income)",      # "Statement of Operations"
    r"^\s*(?:Unaudited|Audited)\s+Financial\s+Statements?",            # Audit status
    r"^\s*(?:Balance\s+Sheets?|Cash\s+Flows?|Stockholders['’]?\s+Equity)",  # More statement types
    r"^\s*(?:Total|Net|Gross|Operating)\s+(?:Income|Loss|Profit)",     # Descriptive headers
]


# SEC document markers to remove
SEC_MARKERS = [
    r"<PAGE>\s*\d+",                                 # Page number
    r"Table\s*of\s*Contents",                         # TOC mention
    r"^\s*\d+\s*$",                                   # Bare page numbers
    r"</?[A-Z]+>",                                    # Fake HTML tags
    r"^\s*Form\s+10-?K/A?",                           # Form identifiers
    r"^\s*Filed\s+with\s+the\s+SEC",                  # Filing metadata
    r"^\s*Commission\s+File\s+Number",                # Header block
    r"\b(SECURITIES\s+AND\s+EXCHANGE\s+COMMISSION)\b",# SEC letterhead
    r"\bUNITED\s+STATES\b",                           # SEC letterhead (cont.)
    r"^\s*Index\s*to\s*Financial\s*Statements",       # Indexed tables
    r"^\s*Fiscal\s+Year\s+Ended",                     # Often boilerplate
    r"^\s*\[.*\]$",                                   # Inline flags like [LOGO], [TEXT], etc.
]


# Incorporation by reference patterns
INCORPORATION_BY_REFERENCE_PATTERNS = [
    # Standard incorporation language
    r"(?:information\s+required\s+by\s+)?Item\s*7.*?(?:is\s+)?incorporated\s+(?:herein\s+)?by\s+reference",
    r"Management['']?s?\s+Discussion\s+and\s+Analysis.*?incorporated\s+by\s+reference",
    r"MD&A.*?incorporated\s+by\s+reference",

    # Reference to proxy statements
    r"incorporated\s+by\s+reference.*?(?:from|to).*?(?:Proxy\s+Statement|DEF\s*14A)",
    r"(?:see|refer\s+to).*?Proxy\s+Statement.*?(?:pages?\s+[\d\-A-Z]+|Appendix)",

    # Reference to exhibits
    r"incorporated\s+by\s+reference.*?Exhibit\s*(?:13|99|[\d\.]+)",
    r"(?:see|refer\s+to).*?Exhibit\s*(?:13|99|[\d\.]+).*?(?:Annual\s+Report|10-K)",

    # Reference to appendices
    r"(?:see|refer\s+to).*?Appendix\s*[A-Z]?.*?(?:pages?\s+[\d\-A-Z]+)?",
    r"incorporated.*?from.*?Appendix",

    # Caption references
    r"under\s+(?:the\s+)?caption\s+[\"']([^\"']+)[\"']",
    r"(?:section|item)\s+(?:entitled|titled)\s+[\"']([^\"']+)[\"'].*?incorporated",

    # Page references
    r"(?:on\s+)?pages?\s+([\d\-A-Z]+(?:\s+through\s+[\d\-A-Z]+)?)",

    # General incorporation phrases
    r"information.*?set\s+forth.*?incorporated\s+by\s+reference",
    r"hereby\s+incorporated\s+by\s+reference",
]

# Compile patterns for efficiency
def compile_patterns():
    """Compile all regex patterns for better performance."""
    compiled = {
        "item_7_start": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in ITEM_7_START_PATTERNS],
        "item_7a_start": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in ITEM_7A_START_PATTERNS],
        "item_8_start": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in ITEM_8_START_PATTERNS],
        "item_2_start": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in ITEM_2_START_PATTERNS],
        "item_3_start": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in ITEM_3_START_PATTERNS],
        "item_4_start": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in ITEM_4_START_PATTERNS],
        "part_ii_start": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in PART_II_START_PATTERNS],
        "form_type": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in FORM_TYPE_PATTERNS],
        "cross_reference": [re.compile(p, re.IGNORECASE) for p in CROSS_REFERENCE_PATTERNS],
        "table_delimiter": [re.compile(p, re.MULTILINE) for p in TABLE_DELIMITER_PATTERNS],
        "table_header": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in TABLE_HEADER_PATTERNS],
        "sec_markers": [re.compile(p, re.MULTILINE) for p in SEC_MARKERS],
        "incorporation_by_reference": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in INCORPORATION_BY_REFERENCE_PATTERNS],
    }
    return compiled

COMPILED_PATTERNS = compile_patterns()