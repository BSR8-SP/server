from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    bus_line_id: Mapped[int] = mapped_column(
        ForeignKey("bus_lines.id"),
        nullable=False,
    )

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

    busline = relationship("BusLine", back_populates="comments")