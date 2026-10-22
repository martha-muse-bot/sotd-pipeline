# 🧸 SOTD Pipeline Specification

## 🛠️ Pipeline Structure Overview

The SOTD Fetcher is built as a multi-phase data pipeline designed to extract, normalize, and analyze r/wetshaving content from Reddit. It is structured as follows:

This pipeline extracts, processes, and summarizes Shave of the Day (SOTD) content from Reddit. Each step writes its output to disk, allowing easy reruns of individual phases and inspection of intermediate results.

---

## 🚀 Pipeline Orchestration

The pipeline provides a unified orchestration interface through `run.py` that supports both individual phase execution and complete pipeline workflows.

### Unified CLI Interface
```bash
# Individual phases
python run.py fetch --month 2025-05 --force
python run.py extract --month 2025-05 --force
python run.py match --month 2025-05 --force
python run.py enrich --month 2025-05 --force
python run.py aggregate --month 2025-05 --force
python run.py report --month 2025-05 --force

# Complete pipeline
python run.py --month 2025-05 --force

# Phase ranges
python run.py extract:enrich --month 2025-05 --force  # Run extract through enrich
python run.py match: --month 2025-05 --force          # Run from match to end
python run.py :enrich --month 2025-05 --force         # Run from start to enrich

# Date ranges
python run.py --year 2024 --force                              # Process entire year
python run.py --start 2024-01 --end 2024-06 --force            # Date range
python run.py --range 2024-01:2024-06 --force                  # Alternative range syntax

# Debug mode
python run.py --month 2025-05 --force --debug
```

### Key Features
- **Phase Range Support**: Run subsets of the pipeline using `phase1:phase2` syntax
- **Date Range Support**: Process individual months, years, or custom date ranges
- **Debug Logging**: Enable detailed logging with `--debug` flag
- **Force Processing**: Use `--force` flag to ensure fresh data processing (MANDATORY)
- **Error Handling**: Graceful failure handling with clear error messages
- **Validation**: Comprehensive input validation for phase names and date formats

### Phase Order
The pipeline phases must be executed in this order:
1. **fetch** - Extract Reddit threads/comments
2. **extract** - Parse product mentions from comments
3. **match** - Normalize product names against catalogs
4. **enrich** - Extract additional metadata
5. **aggregate** - Generate statistical summaries
6. **report** - Create human-readable reports

---

## 1. **Fetching**
Extract relevant threads and top-level comments from Reddit using PRAW. Save raw Reddit data locally:

- `data/threads/YYYY-MM.json`
- `data/comments/YYYY-MM.json`

Each file includes metadata (e.g., extraction time, thread/comment counts) and raw Reddit content.

---

## 2. **Extraction**
Parse downloaded comment bodies to identify product mentions:

- `razor`
- `blade`
- `brush`
- `soap`

**Supported Extraction Patterns:**

1. **Standard Markdown Format**: `* **Field:** Value`
   - Example: `* **Razor:** Karve Christopher Bradley`

2. **Checkmark Format**: `✓Field: Value`
   - Example: `✓Brush: Kent Infinity`
   - Example: `✓Razor: Kopparkant +`

3. **Emoji Bold Format**: `* **Field** Value`
   - Example: `* **Straight Razor** - Fontani Scarperia`
   - Example: `* **Shaving Brush** - Leonidam`

**Field Mapping:**
- "Lather" → "soap"
- "Straight Razor" → "razor"
- "Shaving Brush" → "brush"
- "Shaving Soap" → "soap"

Convert each comment into a structured "shave" record. Save to:

- `data/extracted/YYYY-MM.json`

Fields include metadata (`id`, `author`, `created_utc`, etc.) and raw extracted values.

---

## 3. **Matching**
Match extracted product names to known item catalogs to normalize naming:

- `Karve CB` → `Karve Christopher Bradley`
- `RR GC .84` → `RazoRock Game Changer 0.84`

**Matching Priority Order:**
1. **Correct Matches Files**: If the original value is found in `data/correct_matches/*.yaml` (manually confirmed), it is matched directly, and `match_type` is set to `exact`. All catalog specifications (e.g., grind, width, point) are preserved in the match output.
2. **Regex Patterns**: If not found in the correct matches file, regex patterns from the YAML catalogs are used. These matches have `match_type` set to `regex`, and all catalog specifications are also preserved.
3. **Brand/Alias Fallbacks**: If no regex match is found, fallback strategies may be used (e.g., brand-only, alias), with appropriate `match_type` values.

**Field Structure:**
- `original`: The original extracted value
- `matched`: The canonical match result, including all catalog fields
- `match_type`: One of `exact` (from `data/correct_matches/*.yaml`), `regex` (pattern match), `alias`, `brand`, or `None` (unmatched)
- `pattern`: The regex pattern used (if any)

**Example:**
```python
{
    "razor": {
        "original": "Koraat Moarteen",
        "matched": {
            "brand": "Koraat",
            "model": "Moarteen (r/Wetshaving exclusive)",
            "format": "Straight",
            "grind": "Full Hollow",
            "point": "Square",
            "width": "15/16",
        },
        "match_type": "exact",  # From data/correct_matches/*.yaml
        "pattern": None,
    },
    "blade": {
        "original": "Feather (3)",
        "matched": {"brand": "Feather", "model": "Hi-Stainless", "format": "DE"},
        "match_type": "regex",  # From regex pattern
        "pattern": "feather.*hi",
    },
}
```

Track original values, match results, and confidence levels. **Preserves all catalog specifications** (e.g., straight razor grind, width, point type from YAML catalog). Save to:

- `data/matched/YYYY-MM.json`

---

## 4. **Field Metadata Enrichment**
Analyze matched field values to extract structured metadata that benefits from knowing the identified product first, such as:

- Blade usage count (e.g., `Astra SP (3)`)
- Straight razor specifications (grind, width as string fraction, point type; e.g., grind: "full hollow", width: "15/16", point: "barbers_notch").
  - Grind types: full hollow, extra hollow, pretty hollow, half hollow, quarter hollow, three quarter hollow, wedge, near wedge, frameback
  - Width: string fraction (e.g., "6/8", "15/16", "3/4", "1.0")
  - Point: round, square, french, spanish, barbers_notch, spear, spike (with 'tip' as synonym for 'point')
  - Only applies to razors with format: Straight
- DE razor plate information (Game Changer gaps, Christopher Bradley plates, Blackbird plates)
  - Game Changer: gap (.68, .76, .84, 1.05), variant (OC, JAWS)
  - Christopher Bradley: plate (A-G), material (brass, copper, stainless)
  - Blackbird: plate (Standard, Lite, OC/Open Comb)
  - Super Speed: variant (40's Style (NDC), Black Tip, Flare Tip, Blue Tip, Red Tip, TV Special, Black Handle, Unknown)

Uses an extensible enricher strategy pattern for sophisticated analysis. Save to:

- `data/enriched/YYYY-MM.json`

**Detailed specification**: See [Enrich Phase Specification](enrich_phase_spec.md)

---

## 5. **Aggregation**
Summarize enriched product data for downstream reporting:

- Usage counts by brand/model
- Most-used products
- User statistics
- Product category summaries

Save aggregate summaries to:

- `data/aggregated/YYYY-MM.json`

**Detailed specification**: See [Aggregate Phase Specification](aggregate_phase_spec.md)

---

## 6. **Report Generation**
Generate human-readable summaries for publication on r/wetshaving. Include product rankings, trends, and commentary excerpts. Save reports to:

- Monthly reports: `data/reports/YYYY-MM-{hardware|software}.md`
- Annual reports: `data/reports/annual/YYYY-{hardware|software}.md`

---

Each step is isolated and writes its output to disk, enabling traceable processing and modular development.

Additional steps may be introduced as the project evolves.

This specification defines the structure, configuration, and operational behavior of the Shave of the Day (SOTD) pipeline for extracting, normalizing, and reporting shaving-related content from Reddit's r/wetshaving community.

## Phase 0: Project Setup

### 📄 Environment
- Python version: **3.11.8**
- Type checking: **Pyright** (`typeCheckingMode: "standard"`)
- Code formatting: **Black**
- Linting: **Ruff**v
- Testing: **Pytest + Pytest-Cov**
- Credentials: **praw.ini** (section name set via SOTD_REDDIT_SITE, default "sotd_bot")

### 🌍 Directory Layout
```plaintext
sotd_fetcher/
├── data/
│   ├── threads/
│   ├── comments/
│   └── thread_overrides.yaml
├── sotd/
│   ├── fetch/
│   │   ├── run.py
│   │   ├── reddit.py
│   │   ├── overrides.py
│   │   ├── merge.py
│   │   └── save.py
│   ├── extract/
│   │   └── ...
│   ├── match/
│   │   └── ...
│   ├── enrich/
│   │   ├── run.py
│   │   ├── enrich.py
│   │   ├── base_enricher.py
│   │   └── ...
│   └── ...
├── tests/
│   ├── test_fetch.py
│   └── ...
├── cli.py (optional)
├── run.py (pipeline orchestration)
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── Makefile
└── .gitignore
```

### 🚀 Installation Steps
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### 📁 requirements.txt
```
praw
dateparser
```

### 📁 requirements-dev.txt
```
-r requirements.txt
black
ruff
pytest
pytest-cov
pytest-xdist
pyright
rich
```

### 📝 pyproject.toml
```toml
[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
exclude = ["data", "tests", ".venv", "venv"]

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
```

### 📁 .gitignore
```
__pycache__/
*.pyc
venv/
.venv/
.env/
.vscode/
.coverage
coverage/
htmlcov/
data/
```

### 📂 Makefile
```makefile
.PHONY: all lint format ruff-format typecheck test coverage fetch

all: lint format typecheck test

# Ruff linting
lint:
	ruff check .

# Ruff auto‑formatter then Black
ruff-format:
	ruff format .

format: ruff-format
	black .

typecheck:
	pyright

test:
	pytest tests/

test-fast:
	PYTHONPATH=. pytest tests/ -n 4 -q

test-parallel:
	PYTHONPATH=. pytest tests/ -n auto -q

test-slow:
	PYTHONPATH=. pytest tests/ --durations=10 -v

coverage:
	pytest --cov=sotd --cov-report=term-missing tests/

fetch:
	python -m sotd.fetch.run --month 2025-05 --debug
```

---

## 🚀 Development Workflow

### **Optimized Testing Strategy**

The pipeline includes an optimized testing strategy designed for fast development feedback while maintaining comprehensive coverage.

#### **Test Execution Options**

1. **Fast Development Testing** (`make test-fast`):
   - **Execution Time**: ~4.6 seconds (57% faster than sequential)
   - **Configuration**: 4 parallel workers for optimal performance
   - **Use Case**: Quick feedback during active development
   - **Command**: `make test-fast`

2. **Sequential Validation** (`make test`):
   - **Execution Time**: ~10.8 seconds
   - **Configuration**: Single-threaded execution
   - **Use Case**: Complete validation before commits
   - **Command**: `make test`

3. **Performance Analysis** (`make test-slow`):
   - **Output**: Shows slowest 10 tests with execution times
   - **Use Case**: Identify performance bottlenecks
   - **Command**: `make test-slow`

4. **Auto-Parallel Testing** (`make test-parallel`):
   - **Configuration**: Automatic worker detection
   - **Use Case**: CI/CD environments with varying resources
   - **Command**: `make test-parallel`

#### **Test Optimization Results**

- **Test Count**: 1,255 tests (optimized from 1,332 baseline)
- **Test Reduction**: 77 tests removed (5.8% reduction)
- **Coverage**: Maintained at 71% with no meaningful loss
- **Performance**: 57% improvement in execution time

#### **Quality Assurance Workflow**

**Pre-Commit Validation** (MANDATORY):
```bash
make format lint typecheck test
```

**Development Loop**:
```bash
# Fast feedback during development
make test-fast

# Complete validation before commit
make format lint typecheck test
```

**Performance Monitoring**:
```bash
# Identify slow tests
make test-slow

# Run with coverage
make coverage
```

#### **Test Categories**

1. **Fast Tests** (< 0.1s): Unit tests, validation tests, utility tests
2. **Medium Tests** (0.1-0.5s): Integration tests, CLI tests
3. **Slow Tests** (> 0.5s): Rate limit tests, real catalog integration tests

**Note**: Slow tests are legitimate and should remain as-is:
- Rate limit tests include intentional delays for testing rate limiting
- Integration tests load real YAML catalogs for comprehensive validation
- Performance tests do actual performance measurements

#### **Parallel Execution Requirements**

- **Dependency**: pytest-xdist (included in requirements-dev.txt)
- **Optimal Workers**: 4 workers for most development machines
- **Auto-Detection**: `-n auto` for automatic worker configuration
- **CI/CD Ready**: Compatible with GitHub Actions and other CI systems

### **Development Environment Setup**

#### **Updated requirements-dev.txt**
```
-r requirements.txt
black
ruff
pytest
pytest-cov
pytest-xdist
pyright
rich
```

#### **Quality Check Commands**

```bash
# Complete quality check (MANDATORY before commits)
make all

# Individual checks
make lint      # Ruff linting
make format    # Black + Ruff formatting
make typecheck # Pyright type checking
make test      # Sequential test execution
make test-fast # Fast parallel test execution
```

#### **Pipeline Development Rules**

1. **Always Use --force**: Use `--force` flag for fresh data processing during development
2. **Test-First Development**: Write tests before implementing features
3. **Fast Feedback**: Use `make test-fast` during active development
4. **Complete Validation**: Use `make test` before commits
5. **Documentation Sync**: Update documentation with code changes

#### **Performance Monitoring**

The pipeline includes comprehensive performance monitoring:

- **Test Execution Time**: Tracked and optimized
- **Memory Usage**: Monitored during large data processing
- **File I/O Performance**: Optimized for large datasets
- **Parallel Processing**: Configurable for different environments

#### **CI/CD Integration**

The optimized testing strategy is designed for CI/CD integration:

```yaml
# Example GitHub Actions configuration
- name: Run Tests
  run: |
    make test-fast  # Fast parallel execution
    make coverage   # Generate coverage report
```

---

## Phase 1: Fetch (Thread + Comment Collection)

### ✅ Overview
Fetches SOTD threads and top-level comments from r/wetshaving for a specified month, with local caching and override support.

### ⚖️ Search Strategy
- Use **PRAW subreddit search**: `flair:SOTD mar march 2025`
- Fallback title matching via regex: `\b(SOTD|Shave of the Day)\b.*\bThread\b`
- Post-processing filters:
  - Title date must be parsable (via `dateparser`)
  - Thread must be a `self` post
  - Title date used to determine calendar coverage (not created_utc)

### 📁 File Outputs

#### `threads/YYYY-MM.json`
```json
{
  "meta": {
    "month": "2025-04",
    "extracted_at": "2025-05-21T18:40:00Z",
    "thread_count": 29,
    "expected_days": 30,
    "missing_days": ["2025-04-01", "2025-04-17"],
    "notes": "Based on title dates. Includes manual overrides."
  },
  "data": [
    {
      "id": "t3_abc123",
      "title": "Tuesday SOTD Thread - Apr 2, 2025",
      "url": "https://www.reddit.com/r/wetshaving/comments/abc123/",
      "author": "AutoModerator",
      "created_utc": "2025-04-02T12:00:00Z",
      "num_comments": 42,
      "flair": null
    }
  ]
}
```

#### `comments/YYYY-MM.json`
```json
{
  "meta": {
    "month": "2025-04",
    "extracted_at": "2025-05-21T18:40:00Z",
    "comment_count": 407,
    "thread_count_with_comments": 28,
    "missing_days": ["2025-04-01", "2025-04-17"],
    "threads_missing_comments": ["t3_abc123", "t3_def456"],
    "notes": "Only top-level comments included. Some threads empty or removed."
  },
  "data": [
    {
      "id": "t1_xyz789",
      "thread_id": "t3_abc123",
      "thread_title": "Tuesday SOTD Thread - Apr 2, 2025",
      "url": "https://www.reddit.com/r/wetshaving/comments/abc123/comment/xyz789/",
      "author": "shaver_joe",
      "created_utc": "2025-04-02T13:15:47Z",
      "body": "Razor: Karve CB\nBlade: Astra SP\nBrush: Simpson T3\nSoap: Stirling Bay Rum"
    }
  ]
}
```

### 📂 data/thread_overrides.yaml
```yaml
include:
  2025-06-25:
    - https://www.reddit.com/r/Wetshaving/comments/1lk3ooa/wednesday_sotd_25_june/
exclude:
  2026-06-01:
    # Joke / non-SOTD thread that search still finds
    - https://www.reddit.com/r/Wetshaving/comments/1ttrafo/monday_lather_games_sotd_thread_jun_1_2026/
```

- **include**: force-fetch threads missed by search (date → list of Reddit URLs)
- **exclude**: drop joke / non-SOTD threads found by search (date → list of Reddit URLs; matched by submission id extracted from URL)
- Month-scoped: only entries whose date keys start with the fetched `YYYY-MM` apply
- Re-fetch with `--force` is required to drop an already-saved excluded thread from monthly JSON

### 🔁 Merging Behavior
- Files are **merged** by default
- For threads/comments with duplicate IDs, the version with the **latest `created_utc`** is retained
- If `--force` is passed, files are overwritten completely
- Files are **always written** even if unchanged, with normalized sort and fresh metadata
- Entries are sorted by `created_utc` ascending

### ⚠️ Warnings & Logging
- Warn on threads with no top-level comments
- Warn if a thread can't parse a date from title
- Log a final summary:
  ```
  [INFO] SOTD fetch complete for Apr 2025: 29 threads, 407 comments, 2 missing days (2025-04-01, 2025-04-17)
  ```
- Use `--debug` to log skipped threads/comments and reasons


---

## 📌 Version History

### v1.0 – Initial MVP Extraction Pipeline (2025-05-23)
This version marks the completion of the minimal viable product for the Extraction phase of the SOTD pipeline.

**Highlights:**
- Added field extractors for `razor`, `blade`, `brush`, and `soap`, using strict markdown pattern: `* **Field:** Value`
- Implemented comment-level parsing to generate structured shave records
- Batched extraction per month from `data/comments/YYYY-MM.json`
- Generated enriched metadata including field coverage and record counts
- Saved outputs to `data/extracted/YYYY-MM.json` with meta, data, and skipped sections
- Built CLI entry point with `--month` and `--debug` options
- Added full unit test coverage and CLI integration test

### v1.1 – Extraction Pattern Enhancement (2025-07-22)
This version enhances the extraction phase with support for additional comment formats identified through data-driven analysis.

**Highlights:**
- Added checkmark format support: `✓Field: Value` (28 occurrences in analysis)
- Added emoji bold format support: `* **Field** Value` (168 occurrences in analysis)
- Enhanced field mapping for multi-word field names: "Straight Razor" → "razor", "Shaving Brush" → "brush"
- Updated field aliases to support new patterns while maintaining backward compatibility
- Added comprehensive unit and integration tests with real examples from analysis data
- Performance validation shows <5ms per comment with no regression in existing patterns
- All existing extraction patterns continue to work unchanged

# SOTD Pipeline - Core Development Rules
# Shave of the Day Data Processing Pipeline

## Project Overview
This is a Python 3.11 data processing pipeline that extracts, processes, and analyzes "Shave of the Day" posts from Reddit's r/wetshaving community. The pipeline consists of 6 sequential phases: fetch, extract, match, enrich, aggregate, and report.

## Pipeline --force Rule (MANDATORY)
- **When running any pipeline step, ALWAYS use the `--force` flag unless the user explicitly says NOT to use `--force`.**
- This ensures fresh data processing, avoids cached results, and guarantees that all code changes are actually tested.
- If you want to run without --force, specify that explicitly in your request.

## Development Environment
- **Python Version**: 3.11 (enforced by pyrightconfig.json)
- **Virtual Environment**: Use `.venv` directory
- **Package Manager**: pip with requirements.txt/requirements-dev.txt
- **Code Style**: Black (100 char line length)
- **Linting**: Ruff (E, F, I rules)
- **Type Checking**: Pyright in standard mode
- **Testing**: pytest with coverage via pytest-cov
