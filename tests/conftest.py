from app.main import app
import pytest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base

# Register all models.
from app.models.bus_line import BusLine
from app.models.rating import Rating, LateRating, OnTheRunRating
from app.models.comment import Comment

from fastapi.testclient import TestClient
from app.database.session import get_db

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture
def bus_line(db_session):
    bus_line = BusLine(id="123.1", bus_line_code="123")

    db_session.add(bus_line)
    db_session.commit()
    db_session.refresh(bus_line)

    return bus_line

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def populated_db(db_session, bus_line):
    comments = [
        Comment(
            body=f"Comment {i}",
            bus_line_id=bus_line.id,
        )
        for i in range(1, 6)
    ]

    db_session.add_all(comments)
    db_session.commit()

    return bus_line