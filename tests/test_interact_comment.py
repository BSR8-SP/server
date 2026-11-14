from fastapi.testclient import TestClient

from app.database.session import get_db
from app.services import comment as comment_service

def test_interact_positive(client, populated_db):
    response = client.post(
        "/comments/interact",
        params={
            "comment_id": 1,
            "interaction_type": "positive",
        },
    )

    assert response.status_code == 200
    assert response.json()["interactions_positive"] == 1


def test_interact_negative(client, populated_db):
    response = client.post(
        "/comments/interact",
        params={
            "comment_id": 1,
            "interaction_type": "negative",
        },
    )

    assert response.status_code == 200
    assert response.json()["interactions_negative"] == 1


def test_interact_nonexistent_comment(client):
    response = client.post(
        "/comments/interact",
        params={
            "comment_id": 9999,
            "interaction_type": "positive",
        },
    )

    assert response.status_code == 404


def test_interact_invalid_type(client, populated_db):
    response = client.post(
        "/comments/interact",
        params={
            "comment_id": 1,
            "interaction_type": "neutral",
        },
    )

    assert response.status_code == 422