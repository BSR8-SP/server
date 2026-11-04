from datetime import date, time
from typing import Any

from pydantic import BaseModel, Field, model_validator, field_validator


class OnTheRunRatingCreate(BaseModel):
    bus_line_id: str = Field(min_length=1)

    section_start: int = Field(ge=0)
    section_end: int = Field(ge=0)

    start_time: time
    end_time: time

    crowdedness: float

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.section_end <= self.section_start:
            raise ValueError(
                "section_end must be greater than section_start"
            )
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")

        return self


class LateRatingCreate(BaseModel):
    bus_line_id: str = Field(min_length=1)

    section_start: int = Field(ge=0)
    section_end: int = Field(ge=0)

    start_time: time
    end_time: time

    crowdedness: float = -1
    perceived_safety: float = -1
    infrastructure: float = -1
    traffic_quality: float = -1
    travel_time_minutes: float = -1

    report_date: date | None = None

    infrastructure_questions_response: dict[str, Any] | list[Any] | None = None
    perceived_safety_questions_response: dict[str, Any] | list[Any] | None = None

    @field_validator(
        "crowdedness",
        "perceived_safety",
        "infrastructure",
        "traffic_quality",
        "travel_time_minutes",
    )
    @classmethod
    def validate_rating_value(cls, value: float) -> float:
        if value == -1 or 1 <= value <= 5:
            return value

        raise ValueError(
            "Rating must be -1 (unanswered) or between 1 and 5"
        )

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.section_end <= self.section_start:
            raise ValueError(
                "section_end must be greater than section_start"
            )
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self