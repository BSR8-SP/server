from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Fixed UTC-3 timezone (e.g. Brasília time).
GMT_MINUS_3 = timezone(timedelta(hours=-3))


def now_gmt_minus_3() -> datetime:
    return datetime.now(GMT_MINUS_3)


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Single-table discriminator for the inheritance hierarchy.
    rating_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    
    # Bus line is mandatory.
    bus_line_id: Mapped[int] = mapped_column(
        ForeignKey("bus_lines.id"),
        nullable=False,
    )

    busline: Mapped["BusLine"] = relationship("BusLine")

    section_start: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    section_end: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Optional aspects: -1 means unanswered.
    crowdedness: Mapped[float] = mapped_column(
        Float,
        default=-1,
        nullable=False,
    )

    # Calendar date and timestamp are separate concepts.
    report_date: Mapped[date] = mapped_column(
        Date,
        default=lambda: now_gmt_minus_3().date(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_gmt_minus_3,
        nullable=False,
    )

    is_exception_day: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    __mapper_args__ = {
        "polymorphic_on": rating_type,
        "polymorphic_identity": "rating",
    }


class LateRating(Rating):
    __tablename__ = "late_ratings"

    id: Mapped[int] = mapped_column(
        ForeignKey("ratings.id"),
        primary_key=True,
    )

    perceived_safety: Mapped[float] = mapped_column(
        Float,
        default=-1,
        nullable=False,
    )

    infrastructure: Mapped[float] = mapped_column(
        Float,
        default=-1,
        nullable=False,
    )

    traffic_quality: Mapped[float] = mapped_column(
        Float,
        default=-1,
        nullable=False,
    )

    travel_time_minutes: Mapped[float] = mapped_column(
        Float,
        default=-1,
        nullable=False,
    )

    # JSON objects/arrays are stored as native JSON.
    infrastructure_questions_response: Mapped[dict[str, Any] | list[Any] | None] = (
        mapped_column(JSON, nullable=True)
    )

    perceived_safety_questions_response: Mapped[
        dict[str, Any] | list[Any] | None
    ] = mapped_column(JSON, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "late",
    }


class OnTheRunRating(Rating):
    __tablename__ = "on_the_run_ratings"

    id: Mapped[int] = mapped_column(
        ForeignKey("ratings.id"),
        primary_key=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": "on_the_run",
    }