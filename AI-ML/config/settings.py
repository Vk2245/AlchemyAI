"""
Central configuration for the AI-ML pipeline.

Loads environment variables and provides default paths, model names,
and provider settings used across all modules.

Provider strategy:
  - vLLM is the SINGLE default for ALL tasks
    (extraction, validation, classification, scoring, reasoning)
  - Groq and Gemini are FALLBACK ONLY (worst case, when local fails)
  - sentence-transformers for text and image embeddings (local)
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# Load unified .env from the project root
_AI_ML_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _AI_ML_ROOT.parent
load_dotenv(_PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.getenv("DATA_DIR", _AI_ML_ROOT / "data"))
CHROMA_DB_DIR = Path(os.getenv("CHROMA_DB_DIR", DATA_DIR / "chroma_db"))
CORRECTION_LOG_PATH = Path(
    os.getenv("CORRECTION_LOG_PATH", DATA_DIR / "corrections.json")
)
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", DATA_DIR / "reports"))
SAMPLE_PDFS_DIR = _AI_ML_ROOT / "tests" / "sample_pdfs"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# vLLM (high-throughput local inference, via OpenAI API format)
# ---------------------------------------------------------------------------

VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
VLLM_MODEL: str = os.getenv("VLLM_MODEL", "Qwen/Qwen2-VL-2B-Instruct-AWQ")


# ---------------------------------------------------------------------------
# Cerebras
# ---------------------------------------------------------------------------

CEREBRAS_API_KEY: str = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL: str = os.getenv("CEREBRAS_MODEL", "cerebras/gpt-oss-120b")
CEREBRAS_EXTRACTION_MODEL: str = os.getenv("CEREBRAS_EXTRACTION_MODEL", "cerebras/qwen-3.8-27b")

# ---------------------------------------------------------------------------
# Groq
# ---------------------------------------------------------------------------

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-20b")  # Chat/text only
GROQ_EXTRACTION_MODEL: str = os.getenv("GROQ_EXTRACTION_MODEL", "groq/openai/gpt-oss-20b")  # Structured JSON

# ---------------------------------------------------------------------------
# Gemini (Fallback for extraction)
# ---------------------------------------------------------------------------

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
FALLBACK_GEMINI_API_KEY: str = os.getenv("FALLBACK_GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini/gemini-1.5-flash")
if "2.5" in GEMINI_MODEL:
    GEMINI_MODEL = "gemini/gemini-1.5-flash"


# ---------------------------------------------------------------------------
# Provider mapping -- litellm model strings
# ---------------------------------------------------------------------------

PROVIDER_MODELS: dict[str, str] = {
    "vllm": f"openai/{VLLM_MODEL}",
    "cerebras": CEREBRAS_MODEL,
    "cerebras_extraction": CEREBRAS_EXTRACTION_MODEL,
    "groq": GROQ_MODEL,                    
    "groq_extraction": GROQ_EXTRACTION_MODEL,  
    "gemini": GEMINI_MODEL,
}

DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "cerebras")
VISION_PROVIDER: str = os.getenv("VISION_PROVIDER", "gemini")

