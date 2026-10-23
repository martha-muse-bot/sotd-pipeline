#!/usr/bin/env python3
"""Public, read-only SOTD analytics API.

Mounts ONLY the three read-only analytics routers. The test
api/__tests__/test_public_main.py asserts the OpenAPI schema contains no
non-GET operations — keep that test green when touching shared routers.
"""

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .monthly_user_posts import router as monthly_user_posts_router  # noqa: E402
from .product_usage import router as product_usage_router  # noqa: E402
from .report_rankings import router as report_rankings_router  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SOTD Public Analytics API",
    description="Read-only SOTD pipeline analytics",
    version="1.0.0",
    docs_url=None,  # don't advertise interactive docs on the public host
    redoc_url=None,
)

app.include_router(product_usage_router)
app.include_router(monthly_user_posts_router)
app.include_router(report_rankings_router)

# Metrics middleware records every request; /metrics is served by the guarded
# route below (NOT Instrumentator.expose — it has no auth hook we control).
Instrumentator(excluded_handlers=["/metrics", "/api/product-usage/health"]).instrument(app)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


_allowed_origin = os.getenv("PUBLIC_ALLOWED_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origin],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_non_get(request, call_next):
    """Second line of defense: never answer anything but GET/OPTIONS/HEAD."""
    if request.method not in ("GET", "OPTIONS", "HEAD"):
        return JSONResponse(status_code=405, content={"detail": "Read-only API"})
    return await call_next(request)
