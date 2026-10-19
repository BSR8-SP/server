from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models.user import User
from app.models.busline import BusLine
from app.models.rating import Rating, LateRating, OnTheRunRating
from app.models.comment import Comment


def populate_db() -> None:
    init_db()

    with SessionLocal() as db:
        users_by_name = {}
        for name in ["Alice", "Bob", "Charlie"]:
            user = db.scalar(select(User).where(User.name == name))
            if user is None:
                user = User(name=name)
                db.add(user)
                db.flush()
            users_by_name[name] = user

        buslines_by_code = {}
        for code in ["6250", "875A", "M12"]:
            busline = db.scalar(
                select(BusLine).where(BusLine.busline_code == code)
            )
            if busline is None:
                busline = BusLine(busline_code=code)
                db.add(busline)
                db.flush()
            buslines_by_code[code] = busline

        # Seed ratings once.
        if db.scalar(select(Rating.id).limit(1)) is None:
            db.add_all([
                LateRating(
                    user=users_by_name["Alice"],
                    busline=buslines_by_code["6250"],
                    section_start=1,
                    section_end=5,
                    crowdedness=4,
                    is_exception_day=False,
                    perceived_safety=4,
                    infrastructure=3,
                    traffic_quality=2,
                    travel_time_minutes=35,
                    infrastructure_questions_response={
                        "sidewalk_condition": 3,
                        "lighting": 4,
                    },
                    perceived_safety_questions_response={
                        "felt_safe": True,
                        "lighting": 4,
                    },
                ),
                OnTheRunRating(
                    user=users_by_name["Bob"],
                    busline=buslines_by_code["875A"],
                    section_start=2,
                    section_end=6,
                    crowdedness=5,
                    is_exception_day=False,
                ),
                Rating(
                    user=None,
                    busline=buslines_by_code["M12"],
                    section_start=1,
                    section_end=3,
                    crowdedness=2,
                    is_exception_day=True,
                ),
            ])

        sample_comments = [
            ("Alice", "The bus was crowded this morning."),
            ("Bob", "Traffic was lighter than usual."),
            ("Charlie", "The stop needs better lighting."),
        ]

        for name, body in sample_comments:
            comment = db.scalar(
                select(Comment).where(Comment.body == body)
            )
            if comment is None:
                db.add(Comment(user=users_by_name[name], body=body))

        db.commit()

    print("Database populated successfully.")


if __name__ == "__main__":
    populate_db()