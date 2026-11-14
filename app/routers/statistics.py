from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.statistics import BusLineStatisticsSpecification, RatingMapElement
from app.services import statistics as statistics_service
from app.services.sptrans import SPTransClient, get_sptrans_client
from app.services.gtfs import get_gtfs
from datetime import date, time

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
)

@router.post("/bus-line")
def get_statistics(spec: BusLineStatisticsSpecification, 
                   db: Session = Depends(get_db)):
    
    return statistics_service.get_bus_line_statistics(spec, db)


@router.get(
    "/map",
    response_model=list[RatingMapElement],
)
async def get_ratings_for_map(
    db: Session = Depends(get_db),
    sptrans_client : SPTransClient = Depends(get_sptrans_client),
):
    return await statistics_service.get_all_ratings_for_map(db, sptrans_client)
