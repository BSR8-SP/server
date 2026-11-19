from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.rating import OnTheRunRatingCreate, LateRatingCreate
from app.services import rating as rating_service
from app.services.gtfs import GTFS, get_gtfs
from app.services.sptrans import SPTransClient, get_sptrans_client

router = APIRouter(
    prefix="/ratings",
    tags=["Ratings"],
)

@router.post("/on-the-run")
async def create_on_the_run_rating(
    rating_data: OnTheRunRatingCreate,
    db: Session = Depends(get_db),
    sptrans: SPTransClient = Depends(get_sptrans_client),
    gtfs: GTFS = Depends(get_gtfs)
):
    return await rating_service.add_on_the_run_rating(
        db,
        rating_data,
        sptrans=sptrans,
        gtfs=gtfs
    )

@router.post("/late")
def create_late_rating(
    rating_data: LateRatingCreate,
    db: Session = Depends(get_db),
):
    return rating_service.add_late_rating(db, rating_data)