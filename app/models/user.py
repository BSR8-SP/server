from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Ratings submitted by this user.
    ratings: Mapped[list["Rating"]] = relationship(
        "Rating",
        back_populates="user",
    )

    # Comments submitted by this user.
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="user",
    )
