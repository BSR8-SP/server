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

from app.services.section_locator import locate_bus_section
from app.services.gtfs import GTFS, get_gtfs
from app.services.sptrans import SPTransClient, get_sptrans_client


async def add_on_the_run_rating(
    db: Session,
    rating_data: OnTheRunRatingCreate,
    sptrans : SPTransClient,
    gtfs : GTFS,
):
    current_date = datetime.now(GMT_MINUS_3)
    current_time = current_date.time()
    simple_code = rating_data.bus_line_id.split(".")[0]
    direction = int(rating_data.bus_line_id.split(".")[1]) + 1

    estimated_location = await locate_bus_section(
        bus_line_code=simple_code,
        direction=direction,
        latitude=rating_data.latitude,
        longitude=rating_data.longitude,
        sptrans=sptrans,
        gtfs=gtfs,
    )

    print(estimated_location)

    rating = OnTheRunRating(
        bus_line_id=rating_data.bus_line_id,
        section_start=estimated_location["section_start"],
        section_end=estimated_location["section_end"],
        latitude=rating_data.latitude,
        longitude=rating_data.longitude,
        start_time=current_time,
        end_time=current_time,
        crowdedness=rating_data.crowdedness,
        report_date=current_date,
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
        section_start=rating_data.section_start,
        section_end=rating_data.section_end,
        start_time=rating_data.start_time,
        end_time=rating_data.end_time,

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