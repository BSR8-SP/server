from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # Optional user (anonymous comments are allowed).
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="comments",
    )

    # Comment body.
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Interaction counters.
    interactions_positive: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    interactions_negative: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )