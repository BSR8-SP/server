from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.gtfs import GTFS, get_gtfs
from app.services.sptrans import SPTransClient, get_sptrans_client
from app.services.maps import fetch_bus_lines, fetch_route
from app.services.section_locator import DEFAULT_MAX_DISTANCE_M, locate_bus_section

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


@router.get("/locate_section")
async def locate_section_by_position(
    bus_line_code: str = Query(min_length=1),
    direction: int = Query(ge=1, le=2),
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    max_distance_m: float = Query(default=DEFAULT_MAX_DISTANCE_M, gt=0),
    sptrans: SPTransClient = Depends(get_sptrans_client),
    gtfs: GTFS = Depends(get_gtfs),
):
    """Section (pair of consecutive stops) of the line where the person is."""
    return await locate_bus_section(
        bus_line_code,
        direction,
        latitude,
        longitude,
        sptrans,
        gtfs,
        max_distance_m=max_distance_m,
    )
