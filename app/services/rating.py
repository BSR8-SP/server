from datetime import datetime

from sqlalchemy.orm import Session

from app.models.rating import (
    OnTheRunRating,
    LateRating,
    GMT_MINUS_3,
)

from app.schemas.rating import (
    OnTheRunRatingCreate,
    LateRatingCreate,
)


def add_on_the_run_rating(
    db: Session,
    rating_data: OnTheRunRatingCreate,
):
    rating = OnTheRunRating(
        bus_line_id=rating_data.bus_line_id,
        direction=rating_data.direction,
        section_start=rating_data.section_start,
        section_end=rating_data.section_end,
        crowdedness=rating_data.crowdedness,
        report_date=datetime.now(GMT_MINUS_3).date(),
        is_exception_day=False,
    )

    db.add(rating)
    db.commit()
    db.refresh(rating)

    return rating


def add_late_rating(
    db: Session,
    rating_data: LateRatingCreate,
):
    rating = LateRating(
        bus_line_id=rating_data.bus_line_id,
        direction=rating_data.direction,
        section_start=rating_data.section_start,
        section_end=rating_data.section_end,

        crowdedness=rating_data.crowdedness,
        perceived_safety=rating_data.perceived_safety,
        infrastructure=rating_data.infrastructure,
        traffic_quality=rating_data.traffic_quality,
        travel_time_minutes=rating_data.travel_time_minutes,

        report_date=(
            rating_data.report_date
            if rating_data.report_date is not None
            else datetime.now(GMT_MINUS_3).date()
        ),

        is_exception_day=False,

        infrastructure_questions_response=(
            rating_data.infrastructure_questions_response
        ),

        perceived_safety_questions_response=(
            rating_data.perceived_safety_questions_response
        ),
    )

    db.add(rating)
    db.commit()
    db.refresh(rating)

    return rating