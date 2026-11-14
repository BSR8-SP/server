
from collections import Counter, defaultdict
from statistics import pstdev
from datetime import time

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer, case

from app.schemas.statistics import BusLineStatisticsSpecification
from app.models.rating import LateRating, OnTheRunRating, Rating
from app import config

from app.services.sptrans import SPTransClient
from app.services.gtfs import GTFS


# ============================================================
# 1. DATABASE QUERIES
# ============================================================

async def apply_rating_filters(
    query,
    bus_line_id: str | None,
    section_start: int | None,
    section_end: int | None,
    start_time: time | None,
    end_time: time | None,
    week_days: list[int] | None,
    strict: bool = False,
):
    """Apply optional filters to a ratings query."""

    if bus_line_id is not None:
        query = query.filter(
            Rating.bus_line_id == bus_line_id
        )

    if section_start is not None:
        condition = (
            Rating.section_start == section_start
            if strict
            else Rating.section_start >= section_start
        )
        query = query.filter(condition)

    if section_end is not None:
        condition = (
            Rating.section_end == section_end
            if strict
            else Rating.section_end <= section_end
        )
        query = query.filter(condition)

    if start_time is not None:
        query = query.filter(
            Rating.start_time >= start_time
        )

    if end_time is not None:
        query = query.filter(
            Rating.end_time <= end_time
        )

    if week_days:
        # SQLite: Sunday = 0, Monday = 1, ..., Saturday = 6.
        # Application: Monday = 0, ..., Sunday = 6.
        weekday = case(
            (
                func.strftime("%w", Rating.report_date) == "0",
                6,
            ),
            else_=cast(
                func.strftime("%w", Rating.report_date),
                Integer,
            ) - 1,
        )

        query = query.filter(
            weekday.in_(week_days)
        )

    return query


def get_ratings_in_date_range(
    db: Session,
    bus_line_id: str | None,
    section_start: int | None,
    section_end: int | None,
    start_time: time | None,
    end_time: time | None,
    week_days: list[int] | None,
    strict: bool = False,
):
    """Retrieve ratings matching the specified filters."""

    query = db.query(Rating)

    query = apply_rating_filters(
        query=query,
        bus_line_id=bus_line_id,
        section_start=section_start,
        section_end=section_end,
        start_time=start_time,
        end_time=end_time,
        week_days=week_days,
        strict=strict,
    )

    return query.all()


# ============================================================
# 2. RATING ORGANIZATION
# ============================================================

def split_ratings_by_type(ratings: list[Rating]):
    """Separate ratings into their respective subclasses."""

    return {
        "late_ratings": [
            rating
            for rating in ratings
            if isinstance(rating, LateRating)
        ],
        "on_the_run_ratings": [
            rating
            for rating in ratings
            if isinstance(rating, OnTheRunRating)
        ],
    }


# ============================================================
# 3. GENERAL CALCULATIONS
# ============================================================

def calculate_average(scores: list[float]) -> float:
    """Calculate an average ignoring negative/invalid scores."""

    valid_scores = [
        score for score in scores
        if score is not None and score >= 0
    ]

    if not valid_scores:
        return 0

    return sum(valid_scores) / len(valid_scores)


def get_valid_scores(ratings, attribute: str):
    """Extract valid scores from a rating attribute."""

    return [
        getattr(rating, attribute)
        for rating in ratings
        if getattr(rating, attribute) is not None
        and getattr(rating, attribute) >= 0
    ]


# ============================================================
# 4. CATEGORY STATISTICS
# ============================================================

def calculate_rating_averages(
    late_ratings: list[LateRating],
    on_the_run_ratings: list[OnTheRunRating],
):
    """Calculate averages for all rating categories."""

    all_ratings = late_ratings + on_the_run_ratings

    averages = {
        "average_crowdedness": calculate_average(
            get_valid_scores(all_ratings, "crowdedness")
        ),
        "average_infrastructure": 0,
        "average_perceived_safety": 0,
        "average_traffic_quality": 0,
    }

    minimum_ratings = config.min_ratings_per_statistic()

    if len(late_ratings) > minimum_ratings:

        averages["average_infrastructure"] = calculate_average(
            get_valid_scores(late_ratings, "infrastructure")
        )

        averages["average_perceived_safety"] = calculate_average(
            get_valid_scores(late_ratings, "perceived_safety")
        )

        averages["average_traffic_quality"] = calculate_average(
            get_valid_scores(late_ratings, "traffic_quality")
        )

    return averages


def calculate_overall_average(averages: dict) -> float:
    """Calculate the overall score from category averages."""

    categories = [
        averages["average_crowdedness"]
    ]

    minimum_ratings = config.min_ratings_per_statistic()

    # The caller must provide the late-rating count.
    if averages["late_rating_count"] > minimum_ratings:
        categories.extend([
            averages["average_infrastructure"],
            averages["average_perceived_safety"],
            averages["average_traffic_quality"],
        ])

    return sum(categories) / len(categories)


# ============================================================
# 5. INDIVIDUAL SCORES AND VARIABILITY
# ============================================================

def calculate_individual_scores(
    late_ratings: list[LateRating],
    on_the_run_ratings: list[OnTheRunRating],
):
    """Calculate one overall score per rating."""

    individual_scores = []

    for rating in late_ratings:
        scores = [
            rating.crowdedness,
            rating.infrastructure,
            rating.perceived_safety,
            rating.traffic_quality,
        ]

        valid_scores = [
            score for score in scores
            if score is not None and score >= 0
        ]

        if valid_scores:
            individual_scores.append(
                sum(valid_scores) / len(valid_scores)
            )

    for rating in on_the_run_ratings:
        if rating.crowdedness is not None and rating.crowdedness >= 0:
            individual_scores.append(rating.crowdedness)

    return individual_scores


def calculate_score_variability(individual_scores: list[float]):
    """Calculate standard deviation and identify high variability."""

    if len(individual_scores) < 2:
        return 0, []

    std_score = pstdev(individual_scores)

    additional_info = []

    if std_score > config.max_score_std_dev():
        additional_info.append("high_score_variability")

    return std_score, additional_info


# ============================================================
# 6. PROBLEM STATISTICS
# ============================================================

def collect_problem_counts(late_ratings: list[LateRating]):
    """Count safety and infrastructure problems."""

    safety_counts = Counter()
    infrastructure_counts = Counter()

    for rating in late_ratings:

        if rating.perceived_safety_questions_response:
            safety_counts.update(
                rating.perceived_safety_questions_response
            )

        if rating.infrastructure_questions_response:
            infrastructure_counts.update(
                rating.infrastructure_questions_response
            )

    return safety_counts, infrastructure_counts


def get_problem_statistics(
    problem_counts: Counter,
    total_ratings: int,
    minimum_percentage: float,
):
    """Calculate problem percentages and filter main problems."""

    if total_ratings == 0:
        return [], []

    all_problems = [
        {
            "problem": problem,
            "percentage": round(
                count / total_ratings * 100,
                2,
            ),
        }
        for problem, count in problem_counts.most_common()
    ]

    main_problems = [
        problem
        for problem in all_problems
        if problem["percentage"] >= minimum_percentage
    ]

    return main_problems, all_problems


def calculate_problem_statistics(
    late_ratings: list[LateRating],
):
    """Calculate safety and infrastructure problem statistics."""

    safety_counts, infrastructure_counts = (
        collect_problem_counts(late_ratings)
    )

    total_ratings = len(late_ratings)
    minimum_percentage = config.min_problem_percentage()

    main_safety, all_safety = get_problem_statistics(
        safety_counts,
        total_ratings,
        minimum_percentage,
    )

    main_infrastructure, all_infrastructure = get_problem_statistics(
        infrastructure_counts,
        total_ratings,
        minimum_percentage,
    )

    return {
        "main_safety_problems": main_safety,
        "all_safety_problems": all_safety,
        "main_infrastructure_problems": main_infrastructure,
        "all_infrastructure_problems": all_infrastructure,
    }


# ============================================================
# 7. TRAVEL TIME
# ============================================================

def calculate_average_travel_time(
    late_ratings: list[LateRating],
    section_start: int | None,
    section_end: int | None,
):
    """Calculate average travel time for an exact section."""

    if section_start is None or section_end is None:
        return None

    travel_times = [
        rating.travel_time_minutes
        for rating in late_ratings
        if (
            rating.section_start == section_start
            and rating.section_end == section_end
            and rating.travel_time_minutes is not None
            and rating.travel_time_minutes >= 0
        )
    ]

    if not travel_times:
        return None

    return sum(travel_times) / len(travel_times)


# ============================================================
# 8. RESPONSE CONSTRUCTION
# ============================================================

def build_statistics_response(
    spec: BusLineStatisticsSpecification,
    averages: dict,
    average_score: float,
    std_score: float,
    average_travel_time: float | None,
    problem_statistics: dict,
    additional_info: list,
):
    """Build the final statistics response."""

    return {
        "bus_line_id": spec.bus_line_id,
        "average_score": round(average_score, 2),
        "average_crowdedness": round(
            averages["average_crowdedness"], 2
        ),
        "average_infrastructure": round(
            averages["average_infrastructure"], 2
        ),
        "average_perceived_safety": round(
            averages["average_perceived_safety"], 2
        ),
        "average_traffic_quality": round(
            averages["average_traffic_quality"], 2
        ),
        "std_score": round(std_score, 2),
        "average_travel_time_minutes": (
            round(average_travel_time, 2)
            if average_travel_time is not None
            else None
        ),
        **problem_statistics,
        "additional_info": additional_info,
    }


# ============================================================
# 9. MAIN SERVICE
# ============================================================

def get_bus_line_statistics(
    spec: BusLineStatisticsSpecification,
    db: Session,
):
    """Orchestrate bus line statistics calculations."""

    # Retrieve ratings
    ratings = get_ratings_in_date_range(
        db=db,
        bus_line_id=spec.bus_line_id,
        section_start=spec.section_start,
        section_end=spec.section_end,
        start_time=spec.start_time,
        end_time=spec.end_time,
        week_days=spec.week_days,
        strict=False,
    )

    # Organize ratings
    grouped_ratings = split_ratings_by_type(ratings)

    late_ratings = grouped_ratings["late_ratings"]
    on_the_run_ratings = grouped_ratings["on_the_run_ratings"]

    # Category averages
    averages = calculate_rating_averages(
        late_ratings,
        on_the_run_ratings,
    )

    averages["late_rating_count"] = len(late_ratings)

    # Overall average
    average_score = calculate_overall_average(averages)

    # Score variability
    individual_scores = calculate_individual_scores(
        late_ratings,
        on_the_run_ratings,
    )

    std_score, additional_info = calculate_score_variability(
        individual_scores
    )

    # Problem statistics
    problem_statistics = calculate_problem_statistics(
        late_ratings
    )

    # Travel time
    average_travel_time = calculate_average_travel_time(
        late_ratings,
        spec.section_start,
        spec.section_end,
    )

    # Build response
    return build_statistics_response(
        spec=spec,
        averages=averages,
        average_score=average_score,
        std_score=std_score,
        average_travel_time=average_travel_time,
        problem_statistics=problem_statistics,
        additional_info=additional_info,
    )



def build_rating_map_points(
    ratings: list[Rating],
    stops: list[tuple[float, float]],
):
    """Expand ratings into one map point per covered bus stop."""

    points = []

    for rating in ratings:
        section_stops = stops[
            rating.section_start:rating.section_end + 1
        ]

        for latitude, longitude in section_stops:
            points.append({
                "rating_id": rating.id,
                "latitude": latitude,
                "longitude": longitude,
                "crowdedness": (
                    rating.crowdedness
                    if rating.crowdedness >= 0
                    else None
                ),
                "infrastructure": (
                    rating.infrastructure
                    if isinstance(rating, LateRating)
                    and rating.infrastructure >= 0
                    else None
                ),
                "perceived_safety": (
                    rating.perceived_safety
                    if isinstance(rating, LateRating)
                    and rating.perceived_safety >= 0
                    else None
                ),
                "traffic_quality": (
                    rating.traffic_quality
                    if isinstance(rating, LateRating)
                    and rating.traffic_quality >= 0
                    else None
                ),
            })

    return points


async def get_all_ratings_for_map(
    db: Session,
    sptrans_client: SPTransClient,
):
    """Retrieve all ratings and expand them into bus stop map points."""

    ratings = db.query(Rating).all()

    # Group ratings by database bus line ID.
    ratings_by_line = defaultdict(list)

    for rating in ratings:
        ratings_by_line[rating.bus_line_id].append(rating)

    map_points = []

    # Fetch stops once for each distinct bus line.
    for bus_line_id, line_ratings in ratings_by_line.items():

        # Obtain the complete SPTrans bus line code from the database.
        bus_line_code = line_ratings[0].bus_line.code

        stops = await bus_stop_positions(
            bus_line_code,
            sptrans_client,
        )

        map_points.extend(
            build_rating_map_points(
                line_ratings,
                stops,
            )
        )

    return map_points