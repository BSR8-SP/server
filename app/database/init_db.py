from app.database.base import Base
from app.database.session import engine


def init_db() -> None:
    # Import models so SQLAlchemy registers their tables.
    from app.models.user import User
    from app.models.busline import BusLine
    from app.models.rating import Rating, LateRating, OnTheRunRating
    from app.models.comment import Comment

    Base.metadata.create_all(bind=engine)