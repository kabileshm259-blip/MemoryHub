import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import chromadb
from chromadb.api import ClientAPI

# Automatically load root .env if running locally and variables are not set
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.is_file():
    load_dotenv(dotenv_path=_ENV_FILE)


def get_chroma_client() -> ClientAPI:
    """Return configured ChromaDB HTTP client using CHROMA_URL."""
    chroma_url = os.getenv("CHROMA_URL", "http://127.0.0.1:8001")
    parsed = urlparse(chroma_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 8000)
    ssl = parsed.scheme == "https"
    return chromadb.HttpClient(host=host, port=port, ssl=ssl)


def check_chroma_connection() -> bool:
    """Verify connectivity to ChromaDB service via heartbeat."""
    try:
        client = get_chroma_client()
        client.heartbeat()
        return True
    except Exception:
        return False
