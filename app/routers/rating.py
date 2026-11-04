from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.rating import OnTheRunRatingCreate, LateRatingCreate
from app.services import rating as rating_service

router = APIRouter(
    prefix="/ratings",
    tags=["Ratings"],
)

@router.post("/on-the-run")
def create_on_the_run_rating(
    rating_data: OnTheRunRatingCreate,
    db: Session = Depends(get_db),
):
    return rating_service.add_on_the_run_rating(
        db,
        rating_data,
    )

@router.post("/late")
def create_late_rating(
    rating_data: LateRatingCreate,
    db: Session = Depends(get_db),
):
    return rating_service.add_late_rating(db, rating_data)