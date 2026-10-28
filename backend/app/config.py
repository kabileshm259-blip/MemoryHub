import os
from pathlib import Path
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

    # ChromaDB
    CHROMA_URL: str = os.getenv("CHROMA_URL", "http://127.0.0.1:8001")

    # Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    def get_jwt_secret(self) -> str:
        """Return the JWT secret or raise an error if not configured properly."""
        secret = self.JWT_SECRET.strip()
        if not secret or len(secret) < 32:
            raise RuntimeError(
                "JWT_SECRET environment variable is missing or too short (minimum 32 characters required)."
            )
        return secret


settings = Settings()
