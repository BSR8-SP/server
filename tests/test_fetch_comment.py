from fastapi.testclient import TestClient

from app.database.session import get_db
from app.services import comment as comment_service


def test_fetch_comments_route(client, populated_db):
    response = client.get("/comments/fetch")

    assert response.status_code == 200
    assert len(response.json()) == 5


def test_fetch_comments_route_by_busline(client, populated_db):
    response = client.get(
        "/comments/fetch",
        params={"bus_line_id": populated_db.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 5

    for comment in response.json():
        assert comment["bus_line_id"] == populated_db.id


def test_fetch_comments_route_pagination(client, populated_db):
    response = client.get(
        "/comments/fetch",
        params={"page": 1, "limit": 2},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_fetch_comments_route_second_page(client, populated_db):
    first_page = client.get(
        "/comments/fetch",
        params={"page": 1, "limit": 2},
    )

    second_page = client.get(
        "/comments/fetch",
        params={"page": 2, "limit": 2},
    )

    first_ids = {c["id"] for c in first_page.json()}
    second_ids = {c["id"] for c in second_page.json()}

    assert len(first_ids) == 2
    assert len(second_ids) == 2
    assert first_ids.isdisjoint(second_ids)


def test_fetch_comments_route_no_results(client):
    response = client.get(
        "/comments/fetch",
        params={"bus_line_id": 9999},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_fetch_comments_route_invalid_page(client, populated_db):
    response = client.get(
        "/comments/fetch",
        params={"page": 0},
    )

    assert response.status_code == 422


def test_fetch_comments_route_invalid_limit(client, populated_db):
    response = client.get(
        "/comments/fetch",
        params={"limit": -1},
    )

    assert response.status_code == 422