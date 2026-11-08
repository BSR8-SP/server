import pytest

from sqlalchemy.exc import IntegrityError

from app.models.comment import Comment
from app.services.comment import add_comment


def test_add_comment(db_session, bus_line):
    comment = add_comment(
        db_session,
        "Great bus service!",
        bus_line.id,
    )

    assert comment.id is not None
    assert comment.body == "Great bus service!"
    assert comment.bus_line_id == bus_line.id


def test_add_comment_default_attributes(db_session, bus_line):
    comment = add_comment(
        db_session,
        "Nice ride!",
        bus_line.id,
    )

    assert comment.interactions_positive == 0
    assert comment.interactions_negative == 0


def test_add_comment_persists_to_database(db_session, bus_line):
    comment = add_comment(
        db_session,
        "Very reliable!",
        bus_line.id,
    )

    saved_comment = db_session.query(Comment).filter_by(
        id=comment.id
    ).first()

    assert saved_comment is not None
    assert saved_comment.body == "Very reliable!"
    assert saved_comment.bus_line_id == bus_line.id


def test_add_comment_invalid_bus_line(db_session):
    with pytest.raises(IntegrityError):
        add_comment(
            db_session,
            "Invalid bus line!",
            "9999",
        )

    db_session.rollback()

    assert db_session.query(Comment).count() == 0


def test_add_comment_empty_body(db_session, bus_line):
    with pytest.raises(IntegrityError):
        add_comment(
            db_session,
            None,
            bus_line.id,
        )

    db_session.rollback()

    assert db_session.query(Comment).count() == 0


def test_bus_line_relationship(db_session, bus_line):
    comment = add_comment(
        db_session,
        "Good service!",
        bus_line.id,
    )

    assert comment.bus_line.id == bus_line.id
    assert comment.bus_line.bus_line_code == "123"
    assert comment in bus_line.comments