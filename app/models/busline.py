from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BusLine(Base):
    __tablename__ = "bus_lines"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    busline_code: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )