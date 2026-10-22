# 🧸 SOTD Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

SOTD Pipeline is a Python data processing system for turning r/wetshaving “Shave of the Day” (SOTD)
threads into structured datasets and readable monthly/annual reports.

### What it does

- **Collects**: Fetches Reddit threads + comments for one month, a range, or a whole year.
- **Parses**: Extracts product mentions from free-form SOTD posts (razors, blades, brushes, soaps).
- **Normalizes**: Matches messy user-entered text to canonical products via YAML catalogs + overrides.
- **Enriches**: Derives additional metadata (e.g., blade-use counts, straight razor attributes) from extracted data.
- **Summarizes**: Aggregates results into statistics (monthly + annual).
- **Reports**: Produces human-readable markdown reports (hardware + software) suitable for sharing.

### How it works (pipeline phases)

The pipeline runs in six sequential phases:

1. **Fetch**: Download thread/comment data from Reddit.
2. **Extract**: Parse SOTD text into structured per-record product fields.
3. **Match**: Resolve product fields against YAML catalogs and pre-validated matches in `data/correct_matches/*.yaml`.
4. **Enrich**: Add derived fields and metadata for analysis/reporting.
5. **Aggregate**: Compute counts, rankings, and other statistics (monthly and annual).
6. **Report**: Render markdown reports (hardware/software) from aggregated data.

### Inputs and outputs

- **Inputs**:
  - Reddit data (threads/comments) fetched via the pipeline
  - Product catalogs in `data/*.yaml` (and manual overrides under `data/`)
  - `praw.ini` in the project root (required for the `fetch` phase)
- **Outputs**:
  - Intermediate JSON artifacts per phase under `--data-dir` (default: `data/`, or `SOTD_DATA_DIR` env var)
  - Final markdown reports under `data/report/` (monthly + annual)

#### Artifact layout (default `--data-dir data`)

- **Fetch**:
  - `data/threads/YYYY-MM.json`
  - `data/comments/YYYY-MM.json`
- **Extract**: `data/extracted/YYYY-MM.json`
- **Match**: `data/matched/YYYY-MM.json`
- **Enrich**: `data/enriched/YYYY-MM.json`
- **Aggregate**:
  - Monthly: `data/aggregated/YYYY-MM.json`
  - Annual: `data/aggregated/annual/YYYY.json`
- **Report**:
  - Monthly: `data/report/YYYY-MM-{hardware|software}.md`
  - Annual: `data/report/annual/YYYY-{hardware|software}.md`

#### Common operator override files

These are the most commonly edited “control” files (all under `data/`):

- **Thread selection (fetch)**: `data/thread_overrides.yaml` (`include` / `exclude` date→URL maps)
- **Extraction fixes (extract)**: `data/extract_overrides.yaml` (default path for `--override-file`)
- **Intentionally unmatched (match)**: `data/intentionally_unmatched.yaml`
- **Enrichment fixes (enrich)**: `data/enrichment_overrides.yaml`
- **Confirmed matches (match)**: `data/correct_matches/*.yaml`

### Design goals

- **Re-runnable and inspectable**: Every phase writes artifacts so you can debug and rerun selectively.
- **Data quality first**: Catalog-backed normalization + explicit override mechanisms.
- **Two interfaces**: CLI-first pipeline with an optional WebUI for interactive analysis.

## 🚀 Quick Start

### Prerequisites
- **Python 3.11** (required, enforced by pyrightconfig.json)
- **Node.js and npm** (optional, for webui component)
- **Reddit API credentials** (required for `fetch`) via a `praw.ini` file

### Setup

1. **Create and activate virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install Python dependencies:**
```bash
pip install -r requirements-dev.txt
```

3. **Install WebUI dependencies (optional):**
```bash
cd webui
npm install
cd ..
```

The WebUI is optional and provides a web-based interface for analyzing pipeline data. The core pipeline can run without it.

### Reddit credentials (required for `fetch`)

The fetch phase uses PRAW and calls `praw.Reddit()` (i.e., it relies on a `praw.ini` file in the **project root**).

- If you only run `extract`/`match`/`enrich`/`aggregate`/`report` against already-fetched data, you may not need Reddit credentials.
- If you run `fetch` (directly or via the full pipeline), you must provide a working `praw.ini`.

See PRAW docs for the exact `praw.ini` format (client id/secret, user agent, etc.).

### Running the Pipeline

**Important**: Always use the `--force` flag during development to ensure fresh data processing and avoid cached results.

#### Individual Phases
```bash
# Run a single phase (defaults to previous month)
python run.py fetch --force
python run.py extract --force
python run.py match --force
python run.py enrich --force
python run.py aggregate --force
python run.py report --type hardware --force

# Run with specific month
python run.py fetch --month 2025-05 --force
python run.py extract --month 2025-05 --force
```

#### Complete Pipeline
```bash
# Run all phases (defaults to previous month)
python run.py --force

# Run all phases with specific month
python run.py --month 2025-05 --force
```

#### Phase Ranges
```bash
# Run phases from extract through enrich
python run.py extract:enrich --month 2025-05 --force

# Run from match to end
python run.py match: --month 2025-05 --force

# Run from start to aggregate
python run.py :aggregate --month 2025-05 --force
```

#### Date Ranges
```bash
# Process specific month
python run.py --month 2025-05 --force

# Process entire year
python run.py --year 2024 --force

# Process date range
python run.py --start 2024-01 --end 2024-06 --force
python run.py --range 2024-01:2024-06 --force

# Year-to-date (January 1st to current month)
python run.py --ytd --force

# Annual reports (requires --year or --range)
python run.py aggregate --year 2024 --annual --force
python run.py report --year 2024 --annual --type hardware --force
```

#### Debug Mode
```bash
# Enable debug logging
python run.py --month 2025-05 --force --debug
```

### Development Workflow
```bash
# Fast development testing (recommended during development)
make test-fast

# Complete validation (run before commits)
make format lint typecheck test

# Run WebUI development server (optional)
cd webui && npm run dev
```

## 📊 Pipeline Overview

The pipeline consists of 6 sequential phases:

1. **Fetch** - Extract Reddit threads and comments from r/wetshaving
2. **Extract** - Parse product mentions (razors, blades, brushes, soaps) from comments
3. **Match** - Normalize product names against YAML catalogs
4. **Enrich** - Extract additional metadata (blade counts, straight razor attributes, etc.)
5. **Aggregate** - Generate statistical summaries (monthly and annual)
6. **Report** - Create human-readable reports (hardware and software)

Each phase writes its output to phase-specific directories under `data/` (e.g., `data/extracted/`, `data/matched/`, `data/enriched/`, etc.) with files named `YYYY-MM.json`, allowing easy reruns of individual phases and inspection of intermediate results. The pipeline supports both monthly processing and annual aggregation for year-over-year analysis.

## 🌐 WebUI (Optional)

The project includes an optional web-based interface for analyzing pipeline data. The WebUI provides:

- Interactive data analysis tools
- Unmatched product analyzer
- Mismatch analyzer
- React-based frontend with TypeScript
- FastAPI backend for data processing

### WebUI Setup

```bash
# Install dependencies
cd webui
npm install

# Start both servers (recommended)
./scripts/manage-servers.sh start
# Frontend: http://localhost:3000
# API: http://localhost:8000

# Stop both servers
./scripts/manage-servers.sh stop
```

### WebUI Development

```bash
# Run React tests
cd webui && npm run test

# Run E2E tests (make target manages servers)
make test-e2e

# Build for production
cd webui && npm run build
```

See [webui/README.md](webui/README.md) for detailed WebUI documentation.

## 🛠️ Development Features

### Enhanced Error Reporting

The pipeline includes **enhanced regex error reporting** that provides detailed context when regex pattern compilation fails in YAML catalog files. Error messages include:

- **File path** where the error occurred
- **Brand/maker** information
- **Model/scent** information
- **Section** information (for handles)
- **Field** information (for filters)
- **Specific regex error** details

Example error message:
```
Invalid regex pattern '[invalid' in File: data/handles.yaml, Brand: Test Maker, Model: Test Model, Section: artisan_handles: unterminated character set at position 7
```

This significantly improves debugging efficiency when working with regex patterns in catalog files.

### Testing Strategy
- **Fast Tests**: `make test-fast` - Parallel test execution for quick feedback
- **Complete Validation**: `make test` - Full test suite with coverage
- **Performance Analysis**: `make test-slow` - Identify bottlenecks
- **Integration Tests**: `make test-integration` - Test with real data
- **WebUI Tests**: `make test-react` - React component tests
- **E2E Tests**: `make test-e2e` - End-to-end browser tests

### Quality Assurance
- **Code Formatting**: Black + Ruff
- **Linting**: Ruff (E, F, I rules)
- **Type Checking**: Pyright (standard mode)
- **Test Coverage**: pytest-cov
- **Pre-commit Validation**: `make format lint typecheck test`

## 📚 Documentation

- **[Pipeline Specification](docs/SOTD_Pipeline_Spec.md)** - Complete pipeline documentation
- **[Development Workflow](docs/SOTD_Pipeline_Spec.md#-development-workflow)** - Optimized testing and development process
- **[Phase Specifications](docs/)** - Detailed specifications for each pipeline phase

## 🔧 Configuration

- **Python**: 3.11 (required, enforced by pyrightconfig.json)
- **Environment**: Virtual environment with `.venv`
- **Dependencies**: 
  - Python: See `requirements.txt` (runtime) and `requirements-dev.txt` (development)
  - WebUI: Node.js and npm (see `webui/package.json`)
- **Configuration**: `pyproject.toml`, `pyrightconfig.json`

### Key Features

- **Monthly Processing**: Process individual months or date ranges
- **Annual Aggregation**: Generate year-over-year statistics with `--annual` flag
- **Year-to-Date (YTD)**: Process from January 1st to current month with `--ytd` flag
- **Delta Mode**: Process current month(s) plus historical comparisons (1 month ago, 1 year ago, 5 years ago) with `--delta` flag
- **Phase Ranges**: Run subsets of the pipeline using `phase1:phase2` syntax
- **Parallel Processing**: Month-level parallelization for improved performance

## 📁 Project Structure

```
sotd_pipeline/
├── sotd/                    # Main pipeline modules
│   ├── fetch/              # Reddit data extraction
│   ├── extract/            # Product mention parsing
│   ├── match/              # Product name normalization
│   ├── enrich/             # Metadata enrichment
│   ├── aggregate/          # Statistical aggregation
│   └── report/             # Report generation
├── tests/                  # Comprehensive test suite
├── data/                   # Pipeline data storage
│   ├── threads/            # Fetch phase output (Reddit threads)
│   ├── comments/           # Fetch phase output (Reddit comments)
│   ├── extracted/          # Extract phase output
│   ├── matched/            # Match phase output
│   ├── enriched/           # Enrich phase output
│   ├── aggregated/         # Aggregate phase output
│   ├── reports/            # Report phase output
│   ├── *.yaml              # Product catalogs
│   └── correct_matches/    # Manual match overrides
├── webui/                  # Optional web interface
│   ├── src/                # React frontend
│   ├── api/                # FastAPI backend
│   └── tests/              # WebUI tests
├── docs/                   # Detailed documentation
├── run.py                  # Pipeline orchestration
└── Makefile               # Development commands
```

## 🤝 Contributing

1. Follow the **Pipeline --force Rule**: Always use `--force` flag during development to ensure fresh data processing
2. Use **Test-First Development**: Write tests before implementing features
3. Run **Fast Tests** during development: `make test-fast`
4. Run **Complete Validation** before commits: `make format lint typecheck test`
5. Update documentation with code changes (including this README)
6. For WebUI changes: Run `make test-react` and `make test-e2e` as appropriate

## 📈 Performance

- **Parallel Processing**: Month-level parallelization for improved throughput
- **Test Execution**: Parallel test execution for faster feedback during development
- **Comprehensive Coverage**: Extensive test suite covering edge cases and integration scenarios

## Product Matching Normalization (2024-07)

All correct match lookups in the pipeline now use a single, canonical normalization function:

```
from sotd.utils.extract_normalization import normalize_for_matching
```

- This function is the only allowed normalization for correct match lookups.
- The old `normalize_for_storage` function is deprecated and should not be used.
- See [docs/product_matching_validation.md](docs/product_matching_validation.md) for details and examples.

This change ensures that all entries in `data/correct_matches/*.yaml` are always found as exact matches, eliminating normalization inconsistencies and "confirmed but not exact" mismatches.

---

For detailed information, see the [Pipeline Specification](docs/SOTD_Pipeline_Spec.md). 

## Brush Correct Matches Enhancement (2025-07)

The brush matcher supports advanced correct matching for combo brushes using the split correct-matches files under `data/correct_matches/` (e.g., `handle.yaml` and `knot.yaml`). For brushes like `DG B15 w/ C&H Zebra`, the matcher extracts and stores handle and knot details separately, and may defer the decision of top-level brand/model to reporting. Simple brushes continue to use complete-brush entries (in `data/correct_matches/brush.yaml`) as before.

### Example YAML
```yaml
# data/correct_matches/handle.yaml
Chisel & Hound:
  Zebra:
    - "DG B15 w/ C&H Zebra"

# data/correct_matches/knot.yaml
Declaration Grooming:
  B15:
    strings:
      - "DG B15 w/ C&H Zebra"
    fiber: "Badger"
    knot_size_mm: 26.0
```

### Example Match Output
```python
{
    "matched": {
        "brand": None,  # Deferred to reporting
        "model": None,  # Deferred to reporting
        "handle_maker": "Chisel & Hound",
        "handle": {
            "brand": "Chisel & Hound",
            "model": "Zebra",
            "source_text": "DG B15 w/ C&H Zebra",
        },
        "knot": {
            "brand": "Declaration Grooming",
            "model": "B15",
            "fiber": "Badger",
            "knot_size_mm": 26.0,
            "source_text": "DG B15 w/ C&H Zebra",
        },
    },
    "match_type": "exact",
}
```

- For combo brushes, reporting/aggregation code should use the `knot` and `handle` fields for display.
- For simple brushes, `brand` and `model` are set as before.
- Backward compatibility is maintained for all existing data and workflows.

## User Intent Preservation Fix (2025-08)

**Critical Bug Fix**: The system now preserves user intent information when processing correct matches, preventing data loss.

### Problem
Previously, when brushes were added to correct-matches overrides, the system would lose user intent information (whether the user considered the brush "handle-primary" or "knot-primary") that was previously captured through automated matching.

### Solution
All correct match processing methods now include user intent detection:
- `_process_handle_knot_correct_match()`
- `_process_split_brush_correct_match()`
- `_process_regular_correct_match()`
- `_process_split_result()`

### User Intent Detection
The system detects user intent based on component order in the input string:
- **"knot_primary"**: When knot component appears before handle component (e.g., "G5C Rad Dinosaur")
- **"handle_primary"**: When handle component appears before knot component (e.g., "Rad Dinosaur G5C")

### Data Quality Enhancement
Correct matches now enhance rather than degrade data quality by preserving all available information, including user intent. This ensures that adding brushes to `data/correct_matches/*.yaml` improves data quality without any information loss.

### Example
```python
# Input: "G5C Rad Dinosaur Creation"
# User intent: "knot_primary" (G5C appears first)
{
    "matched": {
        "user_intent": "knot_primary",  # Preserved in correct matches
        "handle": {"brand": "Rad Dinosaur", "model": "Creation"},
        "knot": {"brand": "AP Shave Co", "model": "G5C"},
    }
}
``` 