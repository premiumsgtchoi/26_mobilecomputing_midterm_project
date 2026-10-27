"""모델명, 경로, 상수 (design.md §4)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# API 키
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# 모델
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")

# 경로
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHROMA_DIR = DATA_DIR / "chroma"

# 상수
MAX_IMAGE_MB = 5
IMAGE_MAX_SIDE = 1024
RAG_TOP_K = 4
MAX_TOOL_ROUNDS = 3
MAX_SUPERVISOR_CALLS = 2
PALETTE_COLORS = 5
