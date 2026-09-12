"""
Application configuration loaded from environment variables.

All secrets come from .env or environment — never hardcoded.
Supports SQLite (dev) and PostgreSQL (production) via DATABASE_URL.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths & Environment
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # DEV/backend/
PROJECT_ROOT = BASE_DIR.parent.parent  # UNI-HACK/

# Load unified .env from the project root
load_dotenv(PROJECT_ROOT / ".env")

AI_ML_DIR = PROJECT_ROOT / "AI-ML"
UPLOAD_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{BASE_DIR / 'Alchemy AI.db'}",
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv("SECRET_KEY", "Alchemy AI-dev-secret-change-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
HMAC_KEY: str = os.getenv("HMAC_KEY", "Alchemy AI-hmac-key-change-in-production")

# CAPTCHA (Altcha — open-source, self-hosted, proof-of-work)
ALTCHA_HMAC_KEY: str = os.getenv("ALTCHA_HMAC_KEY", "altcha-dev-key")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS: list[str] = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

RATE_LIMIT: str = os.getenv("RATE_LIMIT", "30/minute")

# ---------------------------------------------------------------------------
# File Upload
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".xlsx", ".csv"}

# ---------------------------------------------------------------------------
# AI/ML Provider
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "gemini")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")


if __name__ == "__main__":
    print(f"BASE_DIR:      {BASE_DIR}")
    print(f"AI_ML_DIR:     {AI_ML_DIR}")
    print(f"DATABASE_URL:  {DATABASE_URL}")
    print(f"UPLOAD_DIR:    {UPLOAD_DIR}")
    print(f"ALLOWED_ORIGINS: {ALLOWED_ORIGINS}")
    print(f"RATE_LIMIT:    {RATE_LIMIT}")
