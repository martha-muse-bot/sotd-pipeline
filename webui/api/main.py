#!/usr/bin/env python3
"""FastAPI backend for SOTD pipeline analyzer web UI."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .analysis import router as analysis_router
from .brush_matching import router as brush_matching_router
from .brush_splits import router as brush_splits_router
from .brush_validation import router as brush_validation_router
from .catalogs import router as catalogs_router
from .extract_overrides import router as extract_overrides_router
from .files import router as files_router
from .filtered import router as filtered_router
from .format_compatibility import router as format_compatibility_router
from .home_overview import router as home_overview_router
from .monthly_user_posts import router as monthly_user_posts_router
from .product_usage import router as product_usage_router
from .report_rankings import router as report_rankings_router
from .soap_analyzer import router as soap_analyzer_router
from .validation import configure as configure_validation
from .validation import router as validation_router
from .wsdb_alignment import router as wsdb_alignment_router

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure comprehensive logging


def setup_logging():
    """Setup comprehensive logging for the API."""
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Create handlers
    # File handler for detailed logs
    file_handler = logging.FileHandler(logs_dir / "api_debug.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler for stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Error file handler
    error_handler = logging.FileHandler(logs_dir / "api_errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)

    # Configure specific loggers
    api_logger = logging.getLogger("webui.api")
    api_logger.setLevel(logging.DEBUG)

    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting SOTD Pipeline Analyzer API")
    logger.info(f"📁 Logs directory: {logs_dir.absolute()}")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info("📊 Log levels - File: DEBUG, Console: INFO, Errors: ERROR")


# Setup logging
setup_logging()


logger = logging.getLogger(__name__)

# Global queue manager instance
_queue_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler - manage background queue worker lifecycle."""
    global _queue_manager
    # Startup
    try:
        from webui.api.queue_manager import QueueManager

        # Support SOTD_DATA_DIR environment variable for containerized deployments
        sotd_data_dir = os.environ.get("SOTD_DATA_DIR")
        if sotd_data_dir:
            data_dir = Path(sotd_data_dir)
            correct_matches_path = data_dir / "correct_matches"
        else:
            # Fallback to relative path for development
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            correct_matches_path = data_dir / "correct_matches"

        # Configure validation router with data directory
        configure_validation(data_dir)

        _queue_manager = QueueManager(correct_matches_path)
        _queue_manager.start_background_worker()
        logger.info("✅ Background queue worker started")
    except Exception as e:
        logger.error(f"❌ Failed to start background queue worker: {e}", exc_info=True)

    yield

    # Shutdown
    if _queue_manager:
        try:
            _queue_manager.stop_background_worker()
            logger.info("✅ Background queue worker stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping background queue worker: {e}")


# Create FastAPI app
app = FastAPI(
    title="SOTD Pipeline Analyzer API",
    description="API for analyzing SOTD pipeline data",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(files_router)
app.include_router(catalogs_router)
app.include_router(analysis_router)
app.include_router(extract_overrides_router)
app.include_router(filtered_router)
app.include_router(brush_splits_router)
app.include_router(brush_validation_router)
app.include_router(brush_matching_router)
app.include_router(soap_analyzer_router)
app.include_router(monthly_user_posts_router)
app.include_router(home_overview_router)
app.include_router(product_usage_router)
app.include_router(report_rankings_router)
app.include_router(format_compatibility_router)
app.include_router(validation_router)
app.include_router(wsdb_alignment_router)

# Add CORS middleware for local development
# Vite dev server uses port 5173; include 3000 and 8000 for other setups
_app_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if os.getenv("ENVIRONMENT") == "test":
    _app_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_app_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    start_time = datetime.now()

    # Log request
    logger.info(f"📥 {request.method} {request.url.path} - Query: {dict(request.query_params)}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"📤 {request.method} {request.url.path} - Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    logger.debug("Root endpoint called")
    return {"message": "SOTD Pipeline Analyzer API"}


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    logger.debug("Health check endpoint called")
    return {"status": "healthy", "version": "1.0.0", "service": "SOTD Pipeline Analyzer API"}


@app.get("/api/debug/logs")
async def get_log_info() -> Dict[str, Any]:
    """Get logging information for debugging."""
    logger.info("Log info endpoint called")
    return {
        "logs_directory": str(logs_dir.absolute()),
        "log_files": [str(f.name) for f in logs_dir.glob("*.log")],
        "log_levels": {
            "root": logging.getLogger().level,
            "api": logging.getLogger("webui.api").level,
        },
        "handlers": [
            {
                "type": type(handler).__name__,
                "level": handler.level,
                "formatter": type(handler.formatter).__name__ if handler.formatter else None,
            }
            for handler in logging.getLogger().handlers
        ],
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    # Don't override HTTPException with custom status codes
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        raise exc

    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred",
        },
    )


# Serve the built frontend when present (container deploy); harmless in dev (no dist).
_frontend_dist = Path(__file__).parent.parent / "dist"
if _frontend_dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    logger.info("🎯 Starting API server with uvicorn")
    uvicorn.run("webui.api.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
