# SOTD Pipeline Analyzer Web UI

## Overview

The SOTD Pipeline Analyzer WebUI is an optional web-based interface for analyzing, validating, and improving the quality of data processed by the SOTD Pipeline. It provides interactive tools for operators to identify data quality issues, validate matching results, explore product usage patterns, and manage catalog entries.

### What it does

The WebUI provides a comprehensive suite of analysis and validation tools:

- **Data Quality Analysis**: Identify unmatched products, mismatched entries, and catalog conflicts across multiple months
- **Product Validation**: Validate and correct product matching results (brushes, razors, blades, soaps)
- **Catalog Management**: Validate catalog entries, identify duplicates, and suggest pattern improvements
- **Usage Analytics**: Explore product usage patterns, user behavior, and trends over time
- **Data Alignment**: Compare pipeline data with external sources (e.g., Wet Shaving Database)
- **Interactive Exploration**: View original Reddit comments, navigate between related entries, and make corrections directly

### Available Tools

1. **Unmatched Analyzer** - Identify products that failed to match against catalogs, helping discover potential catalog additions
2. **Mismatch Analyzer** - Analyze mismatched items to find catalog conflicts, regex issues, and data inconsistencies
3. **Soap Analyzer** - Detect duplicate soap entries, suggest pattern improvements, and analyze neighbor similarity
4. **Brush Validation** - Validate brush matching results, compare legacy vs. scoring systems, and manage correct matches
5. **Brush Split Validator** - Validate and manage brush split configurations (handle/knot combinations)
6. **Catalog Validator** - Validate catalog entries, identify conflicts, and test regex patterns
7. **Product Usage** - Explore product usage statistics, user patterns, and yearly summaries with calendar/list views
8. **Monthly User Posts** - Analyze user posting patterns and activity across months
9. **Brush Matching Analyzer** - Analyze brush matching strategies and scoring results (`/brush-matching-analyzer?brush=...` prefills and auto-runs; also linked from the Edit Brush Split modal)
10. **Format Compatibility Analyzer** - Analyze format compatibility issues (e.g., razor/blade mismatches)
11. **WSDB Alignment Analyzer** - Compare pipeline soap data with Wet Shaving Database for alignment and validation. CLI companion: `scripts/auto_assign_single_100_slugs.py` auto-applies slugs to `data/soaps.yaml` where a soap has exactly one 100% match (run `--dry-run` first to preview).

### How it works

The WebUI consists of two components:

- **Frontend (React/TypeScript)**: Interactive web interface running on port 3000
- **Backend (FastAPI)**: REST API server running on port 8000 that processes pipeline data and provides analysis endpoints

The frontend communicates with the backend via REST API calls, and the backend reads from the same `data/` directory structure used by the CLI pipeline. This allows operators to analyze pipeline results, validate matches, and make corrections without leaving the browser.

### Key Features

- **Multi-month Analysis**: Select and compare data across multiple months or date ranges
- **Delta Comparisons**: Automatically include historical comparison months (1 month ago, 1 year ago, 5 years ago)
- **Interactive Comment Viewing**: View original Reddit comments for any matched/unmatched entry
- **Correct Match Management**: Mark items as correct matches or remove incorrect entries directly from the UI
- **Real-time Validation**: Validate catalog entries and regex patterns before committing changes
- **Export Capabilities**: Export analysis results and corrected data for use in pipeline catalogs

## Setup

1. **Install dependencies:**
```bash
npm install
```

2. **Start the development servers:**

The WebUI consists of two servers that must run together:
- **Frontend** (Vite/React): http://localhost:3000
- **Backend** (FastAPI): http://localhost:8000

**Recommended approach** (starts both servers):
```bash
./scripts/manage-servers.sh start
```

**Manual approach** (start servers separately):
```bash
# Terminal 1: Start frontend
npm run dev

# Terminal 2: Start backend (requires Python virtual environment)
source ../.venv/bin/activate  # Activate venv from project root
ENVIRONMENT=test DEBUG=true PYTHONPATH=. python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Note**: The backend requires the Python virtual environment from the project root (`.venv`). The `manage-servers.sh` script automatically activates it.

## Server Management

The recommended way to manage WebUI servers is using the `manage-servers.sh` script:

```bash
# Start all servers (admin frontend, backend, and the public site)
./scripts/manage-servers.sh start

# Stop all servers
./scripts/manage-servers.sh stop

# Restart all servers
./scripts/manage-servers.sh restart

# Check server status
./scripts/manage-servers.sh status

# View logs
./scripts/manage-servers.sh logs frontend   # Frontend server logs
./scripts/manage-servers.sh logs backend   # Backend server logs
./scripts/manage-servers.sh logs public    # Public site server logs
./scripts/manage-servers.sh logs api-debug # API debug logs
./scripts/manage-servers.sh logs api-errors # API error logs

# Clean up PID files and logs
./scripts/manage-servers.sh clean

# Force start (kills external processes using ports)
./scripts/manage-servers.sh start --force
```

The public analytics site runs alongside the admin frontend at
http://localhost:3200 — it serves the built `dist-public/` bundle
(built automatically on first start if missing) and proxies `/api/` to the
same backend on :8000. To pick up frontend changes in the public site,
rebuild and it serves the new bundle immediately:

```bash
npm run build:public   # ~2s; server keeps serving the fresh bundle
```

See [`scripts/README.md`](scripts/README.md) for detailed server management documentation.

## Development

- **Frontend Port**: 3000 (configured in vite.config.ts)
- **Backend Port**: 8000 (FastAPI)
- **API Proxy**: Requests to `/api/*` are proxied to `http://localhost:8000` (FastAPI backend)
- **TypeScript**: Full TypeScript support with strict mode
- **Routing**: React Router for navigation between analyzers
- **Hot Reload**: Both frontend (Vite) and backend (uvicorn --reload) support hot reloading

## Project Structure

```
src/
├── components/     # Reusable UI components
├── pages/         # Page components
├── services/      # API service layer
├── utils/         # Utility functions
└── types/         # TypeScript type definitions
```

## Available Scripts

### Development
- `npm run dev` - Start frontend development server (Vite on port 3000)
- `npm run build` - Build for production
- `npm run build:public` - Build the public frontend (see [Public build](#public-build))
- `npm run preview` - Preview production build

### Code Quality
- `npm run lint` - Run ESLint with error reporting
- `npm run lint:fix` - Run ESLint with auto-fix
- `npm run format` - Format code with Prettier
- `npm run format:check` - Check code formatting with Prettier

### Testing
- `npm run test` - Run Jest unit tests
- `npm run test:watch` - Run Jest tests in watch mode
- `npm run test:coverage` - Run Jest tests with coverage report
- `npm run test:unit` - Run unit tests only (testPathPattern=src)

### End-to-End Testing
- `npm run test:e2e` - Run Playwright E2E tests (requires servers running)
- `npm run test:e2e:safari` - Run E2E tests on Safari
- `npm run test:e2e:ui` - Run E2E tests in UI mode (interactive)
- `npm run test:e2e:headed` - Run E2E tests in headed mode (visible browser)
- `npm run test:e2e:debug` - Run E2E tests in debug mode

**Note**: E2E tests require both frontend and backend servers to be running. Use `make test-e2e` from the project root (manages servers automatically) or start servers manually before running E2E tests.

## Code Quality & Linting

This project uses ESLint and Prettier for code quality and formatting:

### ESLint Configuration
- **TypeScript**: Full TypeScript support with strict rules
- **React**: React-specific linting rules and best practices
- **Hooks**: React Hooks linting rules
- **Prettier Integration**: ESLint works with Prettier for consistent formatting

### Prettier Configuration
- **Formatting**: Consistent code formatting across the project
- **Line Length**: 100 characters
- **Quotes**: Single quotes
- **Semicolons**: Always included
- **Trailing Commas**: ES5 style

### Running Linting
```bash
# Check for linting errors
npm run lint

# Auto-fix linting errors
npm run lint:fix

# Format code with Prettier
npm run format

# Check formatting without making changes
npm run format:check
```

### Current Status
- **Formatting**: ✅ All files are properly formatted
- **Linting**: ⚠️ 286 issues remaining (mostly TypeScript `any` types and React imports)
- **Auto-fix**: Most formatting issues can be auto-fixed

## Public build

The repo ships **two frontend builds**:

- **Admin** (default): `npm run build` — the full operator app with all
  analyzers, served by the FastAPI backend or the dev server.
- **Public**: `npm run build:public` (`vite build --config
  vite.config.public.ts`) — a read-only analytics subset built from
  `src/public/`, output to `dist-public/`. It contains three pages:
  Product Usage (`/product-usage`), Monthly User Posts
  (`/monthly-user-posts`), and Report Placement Over Time
  (`/report-placement`), plus a public home page.

The public build talks to the public API (`webui/api/public_main.py`),
which exposes only the read-only routers those pages need
(product_usage, monthly_user_posts, report_rankings). The container
images build and serve both halves — see `deploy/README.md` for the NAS
deployment runbook, and
`docs/superpowers/specs/2026-10-22-webui-containerization-public-admin-split-design.md`
for the design.

## Backend Integration

The frontend is designed to work with the FastAPI backend running on port 8000. The Vite dev server is configured to proxy API requests to the backend.

### Backend Architecture

- **Location**: `webui/api/` directory
- **Framework**: FastAPI
- **Entry Point**: `webui/api/main.py`
- **Port**: 8000
- **Virtual Environment**: Requires Python virtual environment from project root (`.venv`)
- **Auto-activation**: The `manage-servers.sh` script automatically activates the venv when starting the backend

### Starting the Backend

**Recommended**: Use `./scripts/manage-servers.sh start` (starts both servers)

**Manual**:
```bash
# From webui directory
source ../.venv/bin/activate
ENVIRONMENT=test DEBUG=true PYTHONPATH=. python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Backend Logs

Logs are written to `webui/logs/`:
- `api_debug.log` - Detailed debug logs (DEBUG level)
- `api_errors.log` - Error logs only (ERROR level)

View logs using:
```bash
./scripts/manage-servers.sh logs backend    # Backend server stdout/stderr
./scripts/manage-servers.sh logs api-debug # API debug log file
./scripts/manage-servers.sh logs api-errors # API error log file
```

### API Documentation

Once the backend is running, interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

The backend provides a standardized REST API with the following endpoint structure:

#### Analysis Endpoints (`/api/analysis/`)
- `GET /api/analysis/comment/{comment_id}` - Get comment detail
- `POST /api/analysis/match-phase` - Run match phase analysis
- `POST /api/analysis/unmatched` - Run unmatched analysis
- `POST /api/analysis/mismatch` - Run mismatch analysis
- `GET /api/analysis/correct-matches/{field}` - Get correct matches
- `POST /api/analysis/mark-correct` - Mark matches as correct
- `POST /api/analysis/remove-correct` - Remove from correct matches
- `DELETE /api/analysis/correct-matches/{field}` - Delete correct matches
- `DELETE /api/analysis/correct-matches` - Delete all correct matches
- `POST /api/analysis/validate-catalog` - Validate catalog
- `POST /api/analysis/remove-catalog-entries` - Remove catalog entries

#### Soap Endpoints (`/api/soaps/`)
- `GET /api/soaps/duplicates` - Get soap duplicates
- `GET /api/soaps/pattern-suggestions` - Get pattern suggestions
- `GET /api/soaps/neighbor-similarity` - Get neighbor similarity
- `GET /api/soaps/group-by-matched` - Group by matched string

#### Brush Endpoints (`/api/brushes/`)
- `GET /api/brushes/splits/load` - Load brush splits
- `GET /api/brushes/splits/validate` - Validate brush splits
- `POST /api/brushes/splits/save` - Save brush splits
- `POST /api/brushes/splits/save-split` - Save a single brush split correction
- `DELETE /api/brushes/splits/split` - Remove a brush split override (revert to automatic parsing)
- `GET /api/brushes/splits/yaml` - Get YAML brush splits
- `GET /api/brushes/validation/months` - Get validation months
- `GET /api/brushes/validation/data/{month}/{system}` - Get validation data
- `GET /api/brushes/validation/statistics/{month}` - Get validation statistics
- `POST /api/brushes/validation/action` - Perform validation action
- `POST /api/brushes/matching/analyze` - Analyze brush matching

#### Product Usage Endpoints (`/api/product-usage/`)
- `GET /api/product-usage/products/{month}/{product_type}` - Get list of available products for a month and product type
  - Query parameters: `search` (optional) - Filter products by brand/model
  - Product types: `razor`, `blade`, `brush`, `soap`
  - Returns: List of products with `key`, `brand`, `model`, `usage_count`, `unique_users`
- `GET /api/product-usage/analysis/{month}/{product_type}/{brand}/{model}` - Get product usage analysis
  - Returns: Product usage analysis with users, usage counts, dates, and comment IDs
- `GET /api/product-usage/yearly-summary/{month}/{product_type}/{brand}/{model}` - Get yearly summary for a product
  - Returns: Yearly summary with monthly statistics (shaves, unique users, rank) for the past 12 months
  - Uses aggregated data files for performance
  - Returns data for selected month and previous 11 months
- `GET /api/product-usage/health` - Health check endpoint

#### Other Endpoints
- `GET /api/catalogs/` - Get all catalogs
- `GET /api/catalogs/{field}` - Get specific catalog
- `GET /api/files/available-months` - Get available months
- `GET /api/files/{month}` - Get month data
- `GET /api/filtered/` - Get filtered entries
- `GET /api/users/months` - Get user months
- `GET /api/users/users/{month}` - Get users for month

## Development Workflow

### Typical Development Session

1. **Start servers:**
   ```bash
   ./scripts/manage-servers.sh start
   ```

2. **Verify servers are running:**
   ```bash
   ./scripts/manage-servers.sh status
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API docs: http://localhost:8000/docs

4. **Make changes:**
   - Frontend changes: Hot reload via Vite (automatic)
   - Backend changes: Hot reload via uvicorn --reload (automatic)

5. **Run tests during development:**
   ```bash
   # Unit tests (fast feedback)
   npm run test:watch
   
   # E2E tests (requires servers running)
   make test-e2e  # From project root (manages servers)
   # OR
   npm run test:e2e  # If servers already running
   ```

6. **View logs for debugging:**
   ```bash
   ./scripts/manage-servers.sh logs frontend
   ./scripts/manage-servers.sh logs backend
   ./scripts/manage-servers.sh logs api-debug
   ```

7. **Stop servers when done:**
   ```bash
   ./scripts/manage-servers.sh stop
   ```

### Troubleshooting

**Port already in use:**
```bash
# Check what's using the port
lsof -i :3000  # Frontend
lsof -i :8000  # Backend

# Force start (kills external processes)
./scripts/manage-servers.sh start --force
```

**Servers won't start:**
```bash
# Clean up and try again
./scripts/manage-servers.sh clean
./scripts/manage-servers.sh start
```

**Backend errors:**
- Check `webui/logs/api_errors.log` for error details
- Verify Python virtual environment is activated
- Ensure all Python dependencies are installed: `pip install -r requirements-dev.txt` 