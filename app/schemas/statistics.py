from dataclasses import dataclass
from datetime import date, time
from typing import Annotated, Any

from pydantic import BaseModel, Field

class BusLineStatisticsSpecification(BaseModel):
    bus_line_id: str

    section_start: int
    section_end: int

    start_time: time
    end_time: time

    week_days: list[int] | None = None

class RatingMapElement(BaseModel):
    id: int
    latitude: float
    longitude: float

    crowdedness: float | None
    infrastructure: float | None
    perceived_safety: float | None
    traffic_quality: float | None