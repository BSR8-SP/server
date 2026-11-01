from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BusLine(Base):
    __tablename__ = "bus_lines"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    bus_line_code: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    comments = relationship(
        "Comment",
        back_populates="busline",
        cascade="all, delete-orphan",
    )