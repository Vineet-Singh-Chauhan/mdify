"""FastAPI application entry point.

Globally defuses the Python standard XML library at startup to prevent
XXE and Billion Laughs attacks across all XML-parsing code paths.
"""
import defusedxml
defusedxml.defuse_stdlib()  # Must execute before any XML-consuming import

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.exceptions import (
    domain_exception_handler,
    IngestionError,
    ParsingError,
    AssetError,
)
from src.IngestionContext.routers import router as ingestion_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="mdify API",
    description="Universal File-to-Markdown Converter — Backend API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global opaque exception handler (Principle VI)
app.add_exception_handler(IngestionError, domain_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ParsingError, domain_exception_handler)    # type: ignore[arg-type]
app.add_exception_handler(AssetError, domain_exception_handler)      # type: ignore[arg-type]

app.include_router(ingestion_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["observability"])
async def health_check() -> dict[str, object]:
    """Readiness probe used by Docker healthcheck and CI smoke tests."""
    return {
        "status": "healthy",
        "services": {
            "api": "online",
        },
    }
