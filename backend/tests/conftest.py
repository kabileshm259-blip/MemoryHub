import os
from pathlib import Path
from typing import Dict, Generator, Tuple
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.database import Base, get_db
from app.main import app

# Ensure root .env is loaded
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.is_file():
    load_dotenv(dotenv_path=_ENV_FILE)

# Explicitly configure dedicated test database URL
TEST_DB_NAME = os.getenv("TEST_POSTGRES_DB", "memoryhub_test")
test_db_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("POSTGRES_USER", "memoryhub_user"),
    password=os.getenv("POSTGRES_PASSWORD", ""),
    host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=TEST_DB_NAME,
)

# Register JSONB compiler for SQLite compatibility
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

# Initialize test engine with graceful PostgreSQL detection and SQLite fallback
try:
    pg_engine = create_engine(
        test_db_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 1},
    )
    with pg_engine.connect() as conn:
        pass
    test_engine = pg_engine
    is_sqlite = False
except Exception:
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    is_sqlite = True

# Ensure all schema tables exist in the test database
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Yields a database session wrapped in an outer transaction with savepoints.
    Automatically rolls back all operations at the end of each test,
    ensuring complete test isolation without altering or truncating tables.
    """
    if is_sqlite:
        connection = test_engine.connect()
        transaction = connection.begin()
        session = Session(bind=connection)
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()
    else:
        connection = test_engine.connect()
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")

        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with the database dependency overridden
    to use the isolated transactional test session.
    """
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_helper(client: TestClient):
    """Helper utility for registering and logging in test users."""

    def _create_and_login(
        email: str, password: str = "StrongPass123!", display_name: str = "Test User"
    ) -> Tuple[Dict, Dict[str, str]]:
        # Register user
        reg_res = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": display_name,
            },
        )
        assert reg_res.status_code == 201, reg_res.text
        user_data = reg_res.json()

        # Login
        login_res = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200, login_res.text
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        return user_data, headers

    return _create_and_login
