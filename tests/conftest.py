import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  registers every entity on Base.metadata
from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db_session():
    """An isolated in-memory SQLite database per test, standing in for the Postgres this
    sandbox has no reachable instance of (see tests/test_persistence.py). SQLAlchemy's
    `postgresql.UUID`/`TIMESTAMPTZ` column types degrade to SQLite-compatible generic types,
    so the exact ORM models that generate the real migrations also back these tests.
    """
    # StaticPool: FastAPI runs sync endpoints in a worker thread, and a plain SQLite
    # `:memory:` engine hands each new connection a brand-new, empty database unless every
    # caller is pinned to the exact same connection.
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def db_client(db_session):
    """A `TestClient` whose `get_db` dependency is overridden to the in-memory `db_session`,
    for resource tests that need real persistence instead of mocking the repository layer.
    """

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
