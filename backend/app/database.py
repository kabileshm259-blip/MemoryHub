import logging
import os
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logger = logging.getLogger("memoryhub.database")

# Automatically load root .env if running locally and variables are not set
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.is_file():
    load_dotenv(dotenv_path=_ENV_FILE)

# Register JSONB compiler for SQLite compatibility
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

Base = declarative_base()

# Determine environment and database requirements
_environment = os.getenv("ENVIRONMENT", "development").strip().lower()
_require_postgres = (
    os.getenv("REQUIRE_POSTGRES", "").strip().lower() in ("true", "1", "yes")
    or _environment == "production"
)

# Parse or construct PostgreSQL URL
_env_db_url = os.getenv("DATABASE_URL", "").strip()

if _env_db_url.startswith("sqlite"):
    IS_SQLITE_FALLBACK = True
    db_url = _env_db_url
    _target_pg_url = None
elif _env_db_url:
    # Normalize postgres:// and postgresql:// to postgresql+psycopg:// for SQLAlchemy with psycopg3
    if _env_db_url.startswith("postgres://"):
        _target_pg_url = "postgresql+psycopg://" + _env_db_url[len("postgres://"):]
    elif _env_db_url.startswith("postgresql://") and not _env_db_url.startswith("postgresql+psycopg://"):
        _target_pg_url = "postgresql+psycopg://" + _env_db_url[len("postgresql://"):]
    else:
        _target_pg_url = _env_db_url
    IS_SQLITE_FALLBACK = False
else:
    _target_pg_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "memoryhub_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "memoryhub"),
    )
    IS_SQLITE_FALLBACK = False

_engine = None

if not IS_SQLITE_FALLBACK and _target_pg_url is not None:
    # Probe PostgreSQL with a fast 2.0s timeout
    try:
        _probe_engine = create_engine(
            _target_pg_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2.0},
        )
        with _probe_engine.connect() as _conn:
            _conn.execute(text("SELECT 1"))
        _probe_engine.dispose()
        db_url = _target_pg_url
        _engine = create_engine(
            _target_pg_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        IS_SQLITE_FALLBACK = False
        logger.info("Successfully connected to PostgreSQL database.")
    except Exception as exc:
        if _require_postgres:
            logger.error("Failed to connect to required PostgreSQL database: %s", exc)
            raise RuntimeError(
                f"Production database connection failure: PostgreSQL is required (ENVIRONMENT={_environment}) "
                f"but could not be reached: {exc}"
            )
        logger.warning(
            "PostgreSQL unreachable (%s). Falling back to persistent local SQLite for development.",
            exc,
        )
        IS_SQLITE_FALLBACK = True

if IS_SQLITE_FALLBACK and _engine is None:
    _local_data_dir = _ROOT_DIR / "data" / "local"
    _local_data_dir.mkdir(parents=True, exist_ok=True)
    _sqlite_file = _local_data_dir / "memoryhub.db"
    db_url = f"sqlite:///{_sqlite_file.resolve().as_posix()}"
    _engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )

engine = _engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables. Ensures schema exists in SQLite fallback mode."""
    if IS_SQLITE_FALLBACK:
        from app import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Initialized schema tables in local SQLite database.")


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing database sessions to request handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_postgres_connection() -> bool:
    """
    Execute a lightweight SELECT 1 query to verify database availability.
    Returns True if the active database engine is operational.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
