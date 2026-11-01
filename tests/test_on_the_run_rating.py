from datetime import datetime

from app.models.rating import OnTheRunRating, GMT_MINUS_3


def valid_payload(busline):
    return {
        "bus_line_id": busline.id,
        "direction": "forward",
        "section_start": 2,
        "section_end": 5,
        "crowdedness": 4.0,
    }


def test_create_on_the_run_rating(client, busline):
    response = client.post(
        "/ratings/on-the-run",
        json=valid_payload(busline),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] is not None
    assert data["rating_type"] == "on_the_run"
    assert data["bus_line_id"] == busline.id
    assert data["direction"] == "forward"
    assert data["section_start"] == 2
    assert data["section_end"] == 5
    assert data["crowdedness"] == 4.0


def test_on_the_run_rating_default_values(client, busline):
    response = client.post(
        "/ratings/on-the-run",
        json=valid_payload(busline),
    )

    data = response.json()

    assert data["is_exception_day"] is False
    assert data["report_date"] == datetime.now(
        GMT_MINUS_3
    ).date().isoformat()

    assert data["created_at"] is not None


def test_on_the_run_rating_persists(db_session, client, busline):
    response = client.post(
        "/ratings/on-the-run",
        json=valid_payload(busline),
    )

    rating_id = response.json()["id"]

    db_session.expire_all()

    saved_rating = db_session.query(OnTheRunRating).filter_by(
        id=rating_id
    ).first()

    assert saved_rating is not None
    assert saved_rating.bus_line_id == busline.id
    assert saved_rating.crowdedness == 4.0


def test_on_the_run_rating_backward_direction(client, busline):
    payload = valid_payload(busline)
    payload["direction"] = "backward"

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["direction"] == "backward"


def test_on_the_run_rating_invalid_direction(client, busline):
    payload = valid_payload(busline)
    payload["direction"] = "sideways"

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_negative_section_start(client, busline):
    payload = valid_payload(busline)
    payload["section_start"] = -1

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_negative_section_end(client, busline):
    payload = valid_payload(busline)
    payload["section_end"] = -1

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_invalid_section_range(client, busline):
    payload = valid_payload(busline)
    payload["section_start"] = 5
    payload["section_end"] = 5

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_missing_crowdedness(client, busline):
    payload = valid_payload(busline)
    del payload["crowdedness"]

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422


def test_on_the_run_rating_missing_busline(client, busline):
    payload = valid_payload(busline)
    del payload["bus_line_id"]

    response = client.post(
        "/ratings/on-the-run",
        json=payload,
    )

    assert response.status_code == 422