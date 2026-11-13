import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = DATA_DIR / "index.faiss"
CHUNKS_PATH = DATA_DIR / "chunks.json"
DB_PATH = DATA_DIR / "study.db"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 4
