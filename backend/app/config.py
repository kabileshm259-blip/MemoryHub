import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Ensure root .env is loaded
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.is_file():
    load_dotenv(dotenv_path=_ENV_FILE)


class Settings:
    """Application settings loaded from environment variables."""

    # Database
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "memoryhub")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "memoryhub_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", "").strip() or None
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").strip().lower()

    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "").strip()

    # ChromaDB
    CHROMA_URL: str = os.getenv("CHROMA_URL", "http://127.0.0.1:8001")

    # Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # AI Provider (heuristic by default; safe offline mode)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "heuristic").strip().lower()
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "").strip() or None
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15.0"))
    GEMINI_MAX_OUTPUT_TOKENS: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1024"))

    def get_jwt_secret(self) -> str:
        """Return the JWT secret or raise an error if not configured properly."""
        secret = self.JWT_SECRET.strip()
        if not secret or len(secret) < 32:
            raise RuntimeError(
                "JWT_SECRET environment variable is missing or too short (minimum 32 characters required)."
            )
        return secret

    def is_gemini_enabled(self) -> bool:
        """Check whether Gemini provider is explicitly selected."""
        return self.AI_PROVIDER == "gemini"

    def get_gemini_api_key(self) -> str:
        """Return the configured Gemini API key or raise a descriptive configuration error."""
        if not self.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not configured. "
                "Set GEMINI_API_KEY in .env or switch AI_PROVIDER=heuristic for deterministic offline operation."
            )
        return self.GEMINI_API_KEY


settings = Settings()
