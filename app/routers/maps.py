from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.gtfs import GTFS, get_gtfs
from app.services.sptrans import SPTransClient, SPTransError, get_sptrans_client

router = APIRouter(
    prefix="/maps",
    tags=["maps"],
)


def line_code(line: dict) -> str:
    # The code shown on the bus sign, e.g. "875A-10".
    return f"{line['lt']}-{line['tl']}"


def origin_and_destination(line: dict) -> tuple[str, str]:
    # Direction 1 goes from the main terminal (tp) to the secondary one (ts).
    if line["sl"] == 1:
        return line["tp"], line["ts"]
    return line["ts"], line["tp"]


async def search_lines(sptrans: SPTransClient, term: str) -> list[dict]:
    try:
        return await sptrans.search_lines(term)
    except SPTransError as error:
        raise HTTPException(status_code=502, detail=str(error))


@router.get("/fetch_bus_lines")
async def fetch_bus_lines(
    search: str = Query(min_length=1),
    sptrans: SPTransClient = Depends(get_sptrans_client),
):
    search = search.strip().upper()
    if not search:
        return []

    # SPTrans does not know the "-10" suffix of "875A-10", so we only send
    # what comes before it. SPTrans matches loosely, so we filter again here.
    lines = await search_lines(sptrans, search.split("-")[0] or search)

    bus_lines = []
    for line in lines:
        code = line_code(line)
        origin, destination = origin_and_destination(line)

        # A line matches when the search is a substring of any of its
        # searchable fields: the code or the terminal names.
        searchable = (code, origin, destination)
        if not any(search in field.upper() for field in searchable):
            continue

        bus_lines.append({
            "bus_line_code": code,
            "direction": line["sl"],
            "origin": origin,
            "destination": destination,
            "circular": line["lc"],
        })

    bus_lines.sort(key=lambda line: (line["bus_line_code"], line["direction"]))
    return bus_lines


@router.get("/fetch_route")
async def fetch_route(
    bus_line_code: str = Query(min_length=1),
    direction: int = Query(ge=1, le=2),
    sptrans: SPTransClient = Depends(get_sptrans_client),
    gtfs: GTFS = Depends(get_gtfs),
):
    code = bus_line_code.strip().upper()

    # Translate bus_line_code + direction into the SPTrans line id (cl).
    lines = await search_lines(sptrans, code.split("-")[0])
    line = next(
        (
            line for line in lines
            if line_code(line).upper() == code
            and line["sl"] == direction
        ),
        None,
    )
    if line is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Route not found for bus line {code} "
                f"in direction {direction}"
            ),
        )

    try:
        stops = await sptrans.fetch_stops(line["cl"])
    except SPTransError as error:
        raise HTTPException(status_code=502, detail=str(error))

    # Prefer the street geometry from the GTFS shapes.txt. Without it, fall
    # back to straight lines between the stops.
    coordinates = gtfs.route_coordinates(code, direction)
    source = "gtfs"
    if coordinates is None:
        # GeoJSON uses [longitude, latitude]; SPTrans px is longitude, py latitude.
        coordinates = [[stop["px"], stop["py"]] for stop in stops]
        source = "stops"

    features = []
    if len(coordinates) >= 2:
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coordinates},
            "properties": {"kind": "route", "source": source},
        })

    # The stop index is what defines a section (section_start/section_end).
    for index, stop in enumerate(stops):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [stop["px"], stop["py"]]},
            "properties": {
                "kind": "stop",
                "index": index,
                "stop_code": stop["cp"],
                "name": stop["np"],
                "address": stop.get("ed"),
            },
        })

    return {
        "type": "FeatureCollection",
        "bus_line_code": code,
        "direction": direction,
        "features": features,
    }
