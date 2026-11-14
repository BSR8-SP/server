from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.gtfs import GTFS, get_gtfs
from app.services.sptrans import SPTransClient, get_sptrans_client
from app.services.maps import fetch_bus_lines, fetch_route

router = APIRouter(
    prefix="/maps",
    tags=["maps"],
)

@router.get("/fetch_bus_lines")
async def fetch_bus_lines_by_name(
    search: str = Query(min_length=1),
    sptrans: SPTransClient = Depends(get_sptrans_client),
):
    return await fetch_bus_lines(search, sptrans)


@router.get("/fetch_route")
async def fetch_route_geometry(
    bus_line_code: str = Query(min_length=1),
    direction: int = Query(ge=1, le=2),
    sptrans: SPTransClient = Depends(get_sptrans_client),
    gtfs: GTFS = Depends(get_gtfs),
):
    return await fetch_route(bus_line_code, direction, sptrans, gtfs)
