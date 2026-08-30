"""
Alchemy AI Backend — FastAPI Application.

Production-grade backend with:
  - JWT authentication
  - Rate limiting (slowapi)
  - CORS (configurable origins)
  - Security headers (HSTS, X-Frame, CSP, etc.)
  - Async SQLAlchemy (SQLite dev / PostgreSQL prod)
  - SSE streaming for pipeline progress
  - Tamper-proof HMAC content hashing
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import ALLOWED_ORIGINS, RATE_LIMIT, REPORTS_DIR, AI_ML_DIR
from app.core.security import SECURITY_HEADERS
from app.models.database import init_db


# ---------------------------------------------------------------------------
# Add AI-ML to Python path so pipeline imports work
# ---------------------------------------------------------------------------

if str(AI_ML_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ML_DIR))


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    print("Database initialized.")
    yield
    print("Shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Alchemy AI API",
    description="Product Intelligence Platform — AI-powered product analysis from PDFs",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return Response(
        content='{"detail":"Rate limit exceeded. Please try again later."}',
        status_code=429,
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


# ---------------------------------------------------------------------------
# Static Files (reports)
# ---------------------------------------------------------------------------

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.api.auth import router as auth_router
from app.api.process import router as process_router
from app.api.records import router as records_router
from app.api.chat import router as chat_router

app.include_router(auth_router)
app.include_router(process_router)
app.include_router(records_router)
app.include_router(chat_router)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Alchemy AI API",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# CLI: run the server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
