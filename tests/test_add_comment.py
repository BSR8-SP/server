import pytest

from sqlalchemy.exc import IntegrityError

from app.models.comment import Comment
from app.services.comment import add_comment


def test_add_comment(db_session, busline):
    comment = add_comment(
        db_session,
        "Great bus service!",
        busline.id,
    )

    assert comment.id is not None
    assert comment.body == "Great bus service!"
    assert comment.bus_line_id == busline.id


def test_add_comment_default_attributes(db_session, busline):
    comment = add_comment(
        db_session,
        "Nice ride!",
        busline.id,
    )

    assert comment.interactions_positive == 0
    assert comment.interactions_negative == 0


def test_add_comment_persists_to_database(db_session, busline):
    comment = add_comment(
        db_session,
        "Very reliable!",
        busline.id,
    )

    saved_comment = db_session.query(Comment).filter_by(
        id=comment.id
    ).first()

    assert saved_comment is not None
    assert saved_comment.body == "Very reliable!"
    assert saved_comment.bus_line_id == busline.id


def test_add_comment_invalid_busline(db_session):
    with pytest.raises(IntegrityError):
        add_comment(
            db_session,
            "Invalid bus line!",
            9999,
        )

    db_session.rollback()

    assert db_session.query(Comment).count() == 0


def test_add_comment_empty_body(db_session, busline):
    with pytest.raises(IntegrityError):
        add_comment(
            db_session,
            None,
            busline.id,
        )

    db_session.rollback()

    assert db_session.query(Comment).count() == 0


def test_busline_relationship(db_session, busline):
    comment = add_comment(
        db_session,
        "Good service!",
        busline.id,
    )

    assert comment.busline.id == busline.id
    assert comment.busline.bus_line_code == "123"
    assert comment in busline.comments