
from datetime import datetime

import pytest

from app.models.rating import LateRating, GMT_MINUS_3


def valid_payload(bus_line):
    return {
        "bus_line_id": bus_line.id,
        "section_start": 1,
        "section_end": 4,
        "start_time": "08:00:00",
        "end_time": "08:30:00",
        "crowdedness": 3,
        "perceived_safety": 4,
        "infrastructure": 2,
        "traffic_quality": 5,
        "travel_time_minutes": 3,
        "report_date": "2026-10-29",
        "infrastructure_questions_response": {
            "lighting": 4,
            "accessibility": 3,
        },
        "perceived_safety_questions_response": {
            "felt_safe": True,
        },
    }


def test_create_late_rating(client, bus_line):
    response = client.post(
        "/ratings/late",
        json=valid_payload(bus_line),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] is not None
    assert data["rating_type"] == "late"
    assert data["bus_line_id"] == bus_line.id
    assert data["section_start"] == 1
    assert data["section_end"] == 4
    assert data["start_time"] == "08:00:00"
    assert data["end_time"] == "08:30:00"


def test_late_rating_values(client, bus_line):
    response = client.post(
        "/ratings/late",
        json=valid_payload(bus_line),
    )

    data = response.json()

    assert data["crowdedness"] == 3
    assert data["perceived_safety"] == 4
    assert data["infrastructure"] == 2
    assert data["traffic_quality"] == 5
    assert data["travel_time_minutes"] == 3


def test_late_rating_default_values(client, bus_line):
    payload = valid_payload(bus_line)

    del payload["crowdedness"]
    del payload["perceived_safety"]
    del payload["infrastructure"]
    del payload["traffic_quality"]
    del payload["travel_time_minutes"]

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["crowdedness"] == -1
    assert data["perceived_safety"] == -1
    assert data["infrastructure"] == -1
    assert data["traffic_quality"] == -1
    assert data["travel_time_minutes"] == -1


def test_late_rating_report_date(client, bus_line):
    response = client.post(
        "/ratings/late",
        json=valid_payload(bus_line),
    )

    assert response.status_code == 200
    assert response.json()["report_date"] == "2026-10-29"


def test_late_rating_null_report_date(client, bus_line):
    payload = valid_payload(bus_line)
    payload["report_date"] = None

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 200

    expected_date = datetime.now(GMT_MINUS_3).date().isoformat()

    assert response.json()["report_date"] == expected_date


def test_late_rating_omitted_report_date(client, bus_line):
    payload = valid_payload(bus_line)
    del payload["report_date"]

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 200

    expected_date = datetime.now(GMT_MINUS_3).date().isoformat()

    assert response.json()["report_date"] == expected_date


def test_late_rating_exception_day(client, bus_line):
    response = client.post(
        "/ratings/late",
        json=valid_payload(bus_line),
    )

    assert response.status_code == 200
    assert response.json()["is_exception_day"] is False


def test_late_rating_json_responses(client, bus_line):
    response = client.post(
        "/ratings/late",
        json=valid_payload(bus_line),
    )

    data = response.json()

    assert data["infrastructure_questions_response"] == {
        "lighting": 4,
        "accessibility": 3,
    }

    assert data["perceived_safety_questions_response"] == {
        "felt_safe": True,
    }


def test_late_rating_invalid_time_range(client, bus_line):
    payload = valid_payload(bus_line)
    payload["start_time"] = "08:30:00"
    payload["end_time"] = "08:00:00"

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 422


def test_late_rating_invalid_section_range(client, bus_line):
    payload = valid_payload(bus_line)
    payload["section_start"] = 4
    payload["section_end"] = 4

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field",
    [
        "crowdedness",
        "perceived_safety",
        "infrastructure",
        "traffic_quality",
        "travel_time_minutes",
    ],
)
@pytest.mark.parametrize("value", [-5, -0.5, 0, 0.5, 6, 10])
def test_late_rating_invalid_rating_values(
    client, bus_line, field, value
):
    payload = valid_payload(bus_line)
    payload[field] = value

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "value",
    [-1, 1, 2, 3, 4, 5],
)
def test_late_rating_valid_rating_values(client, bus_line, value):
    payload = valid_payload(bus_line)
    payload["crowdedness"] = value

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 200


def test_late_rating_missing_bus_line(client, bus_line):
    payload = valid_payload(bus_line)
    del payload["bus_line_id"]

    response = client.post("/ratings/late", json=payload)

    assert response.status_code == 422


def test_late_rating_persistence(db_session, client, bus_line):
    response = client.post(
        "/ratings/late",
        json=valid_payload(bus_line),
    )

    assert response.status_code == 200

    rating_id = response.json()["id"]

    db_session.expire_all()

    saved_rating = (
        db_session.query(LateRating)
        .filter_by(id=rating_id)
        .first()
    )

    assert saved_rating is not None
    assert saved_rating.rating_type == "late"
    assert saved_rating.bus_line_id == bus_line.id
    assert saved_rating.crowdedness == 3
    assert saved_rating.report_date.isoformat() == "2026-10-29"
