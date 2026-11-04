from sqlalchemy import String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BusLine(Base):
    __tablename__ = "bus_lines"

    __table_args__ = (
        CheckConstraint(
            "id GLOB '?*.[01]'",
            name="ck_bus_lines_id_format_sqlite",
        ).ddl_if(dialect="sqlite"),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        nullable=False,
        autoincrement=False,
    )

    bus_line_code: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    comments = relationship(
        "Comment",
        back_populates="bus_line",
        cascade="all, delete-orphan",
    )

    ratings = relationship(
        "Rating",
        back_populates="bus_line",
        cascade="all, delete-orphan",
    )