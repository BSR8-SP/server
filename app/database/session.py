from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from collections.abc import Generator
from sqlalchemy.orm import Session

DATABASE_URL = "sqlite:///db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()