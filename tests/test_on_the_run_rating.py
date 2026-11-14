from datetime import datetime

from app.models.rating import OnTheRunRating, GMT_MINUS_3


def valid_payload(bus_line):
    return {
        "bus_line_id": bus_line.id,
        "section_start": 2,
        "section_end": 5,
        "start_time": "09:00:00",
        "end_time": "09:15:00",
        "crowdedness": 4.0,
    }


def test_create_on_the_run_rating(client, bus_line):
    response = client.post(
        "/ratings/on-the-run",
        json=valid_payload(bus_line),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] is not None
    assert data["rating_type"] == "on_the_run"
    assert data["bus_line_id"] == bus_line.id
    assert data["section_start"] == 2
    assert data["section_end"] == 5
    assert data["start_time"] == "09:00:00"
    assert data["end_time"] == "09:15:00"
    assert data["crowdedness"] == 4.0


def test_on_the_run_rating_default_values(client, bus_line):
    response = client.post(
        "/ratings/on-the-run",
        json=valid_payload(bus_line),
    )

    data = response.json()

    assert data["is_exception_day"] is False
    assert data["report_date"] == datetime.now(
        GMT_MINUS_3
    ).date().isoformat()

    assert data["created_at"] is not None


def test_on_the_run_rating_persists(db_session, client, bus_line):
    response = client.post(
        "/ratings/on-the-run",
        json=valid_payload(bus_line),
    )

    rating_id = response.json()["id"]

    db_session.expire_all()

    saved_rating = db_session.query(OnTheRunRating).filter_by(
        id=rating_id
    ).first()

    assert saved_rating is not None
    assert saved_rating.bus_line_id == bus_line.id
    assert saved_rating.crowdedness == 4.0


def test_on_the_run_rating_invalid_time_range(client, bus_line):
    payload = valid_payload(bus_line)
    payload["start_time"] = "09:15:00"
    payload["end_time"] = "09:00:00"

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_negative_section_start(client, bus_line):
    payload = valid_payload(bus_line)
    payload["section_start"] = -1

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_negative_section_end(client, bus_line):
    payload = valid_payload(bus_line)
    payload["section_end"] = -1

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_invalid_section_range(client, bus_line):
    payload = valid_payload(bus_line)
    payload["section_start"] = 5
    payload["section_end"] = 5

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_missing_crowdedness(client, bus_line):
    payload = valid_payload(bus_line)
    del payload["crowdedness"]

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_missing_bus_line(client, bus_line):
    payload = valid_payload(bus_line)
    del payload["bus_line_id"]

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422