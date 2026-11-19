"""Finds the section of a bus route where a person (inside the bus) is.

A section is the stretch between two consecutive stops of one line
direction, identified by the stop indices used in ratings
(section_start, section_end), e.g. (2, 3).

The idea: turn the route into a ruler, where every point of the route is
"X meters from the start of the line". Put the stops and the person on
that ruler, then see between which two stops the person fell.

Step by step:

1. Fetch the data (locate_bus_section): the SPTrans line id (cl) for the
   code and direction, its stops in route order, and the GTFS shape. When
   there is no GTFS, the route is the stops joined by straight lines.

2. Build the ruler (Route.__init__): convert each (lat, lon) point to
   meters on a flat plane (to_xy; over the size of a city the Earth can be
   treated as flat), then add up the segment lengths. `cumulative[i]` is
   how many meters of route come before point i, e.g. [0, 120, 340, ...].

3. Project a point onto one segment (project_on_segment): for a point P
   and a segment A -> B, find the closest point of the segment to P. `t`
   says where it is (0 = at A, 1 = at B, 0.5 = halfway). From it:
   - distance_to_route_m: distance from P to that closest point;
   - distance_along_m: cumulative[A] + t * segment length, i.e. the
     position of P on the ruler.

4. Put the stops on the ruler (project_stops), always moving forward
   from the previous stop, e.g. [0, 480, 1020, 1700, ...].

5. Put the person on the ruler (project): try every segment and keep the
   closest one, e.g. 1250 m along the route and 12 m away from it.

6. Find the section (locate_section): the last stop at or before the
   person (stop 2 at 1020 m), so the section is (2, 3). Also:
   - progress = (1250 - 1020) / (1700 - 1020) = 0.34, the fraction of the
     section already travelled, measured along the streets;
   - position: before the first stop, between stops or after the last.

7. Build the response: stop indices and names, bus_line_id in the format
   used by the rating routes, distance to the route and on_route.
"""

import math
from dataclasses import dataclass

from fastapi import HTTPException

from app.services.gtfs import GTFS
from app.services.sptrans import SPTransClient, SPTransError


EARTH_RADIUS_M = 6_371_000

# Some routes pass near the same stop twice (e.g. circular lines that go
# down and back up the same avenue). For each stop we look only at the
# route after the previous stop, and among the passes that are at most
# this many meters farther than the closest one, we take the first (the
# lowest segment number). This keeps the stops in route order.
STOP_MATCH_TOLERANCE_M = 50

# Default distance from the route above which the person is considered
# to not be on this line.
DEFAULT_MAX_DISTANCE_M = 200


@dataclass
class Projection:
    distance_along_m: float  # from the start of the route
    distance_to_route_m: float  # from the point to the route
    segment: int  # index of the route segment the point falls on


@dataclass
class SectionMatch:
    section_start: int
    section_end: int
    # "between_stops", "before_first_stop" or "after_last_stop".
    position: str
    # 0 at the start stop, 1 at the end stop.
    progress: float
    distance_to_route_m: float
    distance_along_route_m: float


class Route:
    """A route polyline with helpers to project points onto it.

    Points are (latitude, longitude). They are converted once to meters
    on a plane tangent to the route, which keeps the math simple.
    """

    def __init__(self, points: list[tuple[float, float]]):
        if len(points) < 2:
            raise ValueError("A route needs at least two points")

        self.ref_lat = math.radians(sum(lat for lat, _ in points) / len(points))
        self.xy = [self.to_xy(lat, lon) for lat, lon in points]

        # Distance along the route at the start of each point.
        self.cumulative = [0.0]
        for (x1, y1), (x2, y2) in zip(self.xy, self.xy[1:]):
            self.cumulative.append(self.cumulative[-1] + math.hypot(x2 - x1, y2 - y1))

    @property
    def length_m(self) -> float:
        return self.cumulative[-1]

    def to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        x = math.radians(lon) * math.cos(self.ref_lat) * EARTH_RADIUS_M
        y = math.radians(lat) * EARTH_RADIUS_M
        return x, y

    def project_on_segment(self, x: float, y: float, segment: int) -> Projection:
        (x1, y1), (x2, y2) = self.xy[segment], self.xy[segment + 1]
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy
        raw_t = ((x - x1) * dx + (y - y1) * dy) / length_sq if length_sq > 0 else 0.0
        t = max(0.0, min(1.0, raw_t))
        px, py = x1 + t * dx, y1 + t * dy

        # Before the start or past the end of the route, the distance along
        # it goes below 0 or above its length, so callers can tell.
        along_t = t
        if (segment == 0 and raw_t < 0) or (segment == len(self.xy) - 2 and raw_t > 1):
            along_t = raw_t

        return Projection(
            distance_along_m=self.cumulative[segment] + along_t * math.sqrt(length_sq),
            distance_to_route_m=math.hypot(x - px, y - py),
            segment=segment,
        )

    def projections(self, lat: float, lon: float, first_segment: int = 0):
        x, y = self.to_xy(lat, lon)
        return [
            self.project_on_segment(x, y, segment)
            for segment in range(first_segment, len(self.xy) - 1)
        ]

    def project(self, lat: float, lon: float) -> Projection:
        """Closest point of the route (the first one on a tie)."""
        return min(
            self.projections(lat, lon),
            key=lambda projection: projection.distance_to_route_m,
        )

    def project_stops(self, stops: list[tuple[float, float]]) -> list[float]:
        """Distance along the route of each stop, never going backwards."""
        positions = []
        segment = 0
        last = -math.inf
        for lat, lon in stops:
            candidates = [
                projection for projection in self.projections(lat, lon, segment)
                if projection.distance_along_m >= last
            ]
            if not candidates:
                # Only reachable when a stop falls behind the previous one
                # on the last segment; keep the order.
                positions.append(last)
                continue

            closest = min(c.distance_to_route_m for c in candidates)
            chosen = next(
                c for c in candidates
                if c.distance_to_route_m <= closest + STOP_MATCH_TOLERANCE_M
            )
            positions.append(chosen.distance_along_m)
            segment = chosen.segment
            last = chosen.distance_along_m
        return positions


def locate_section(
    latitude: float,
    longitude: float,
    stops: list[tuple[float, float]],
    route: list[tuple[float, float]] | None = None,
) -> SectionMatch:
    """Section (pair of consecutive stop indices) where a point is.

    stops: (latitude, longitude) of each stop, in route order.
    route: (latitude, longitude) of the route geometry, e.g. the GTFS
    shape. Without it, straight lines between the stops are used.

    Before the first stop the answer is the first section, and after the
    last stop it is the last section; `position` tells these cases apart.
    """
    if len(stops) < 2:
        raise ValueError("A line needs at least two stops to have a section")

    polyline = Route(route if route and len(route) >= 2 else stops)
    stop_positions = polyline.project_stops(stops)
    person = polyline.project(latitude, longitude)
    along = person.distance_along_m

    # Last stop at or before the person.
    index = 0
    for i, stop_position in enumerate(stop_positions[:-1]):
        if stop_position <= along:
            index = i

    if along < stop_positions[0]:
        position = "before_first_stop"
    elif along > stop_positions[-1]:
        position = "after_last_stop"
    else:
        position = "between_stops"

    start, end = stop_positions[index], stop_positions[index + 1]
    progress = (along - start) / (end - start) if end > start else 0.0

    return SectionMatch(
        section_start=index,
        section_end=index + 1,
        position=position,
        progress=round(max(0.0, min(1.0, progress)), 3),
        distance_to_route_m=round(person.distance_to_route_m, 1),
        distance_along_route_m=round(along, 1),
    )


async def locate_bus_section(
    bus_line_code: str,
    direction: int,
    latitude: float,
    longitude: float,
    sptrans: SPTransClient,
    gtfs: GTFS,
    max_distance_m: float = DEFAULT_MAX_DISTANCE_M,
) -> dict:
    """Section of a bus line direction where a person is.

    bus_line_code and direction follow fetch_route: "875A-10" and the
    SPTrans direction 1 or 2.
    """
    code = bus_line_code.strip().upper()
    not_found = HTTPException(
        status_code=404,
        detail=f"Route not found for bus line {code} in direction {direction}",
    )

    try:
        lines = await sptrans.search_lines(code.split("-")[0])
    except SPTransError as error:
        raise HTTPException(status_code=502, detail=str(error))

    line = next(
        (
            line for line in lines
            if f"{line['lt']}-{line['tl']}".upper() == code
            and line["sl"] == direction
        ),
        None,
    )
    if line is None:
        raise not_found

    try:
        raw_stops = await sptrans.fetch_stops(line["cl"])
    except SPTransError as error:
        raise HTTPException(status_code=502, detail=str(error))

    # SPTrans: py is latitude, px is longitude.
    stops = [(float(stop["py"]), float(stop["px"])) for stop in raw_stops]
    if len(stops) < 2:
        raise not_found

    # GTFS shapes are [longitude, latitude].
    shape = gtfs.route_coordinates(code, direction)
    route = [(lat, lon) for lon, lat in shape] if shape else None

    match = locate_section(latitude, longitude, stops, route)
    start_stop = raw_stops[match.section_start]
    end_stop = raw_stops[match.section_end]
    return {
        "bus_line_code": code,
        "direction": direction,
        # Same format as BusLine.id, ready for the rating routes.
        "bus_line_id": f"{code}.{direction - 1}",
        "section_start": match.section_start,
        "section_end": match.section_end,
        "start_stop": {"stop_code": start_stop["cp"], "name": start_stop["np"]},
        "end_stop": {"stop_code": end_stop["cp"], "name": end_stop["np"]},
        "position": match.position,
        "progress": match.progress,
        "distance_to_route_m": match.distance_to_route_m,
        "distance_along_route_m": match.distance_along_route_m,
        "route_source": "gtfs" if route else "stops",
        "on_route": match.distance_to_route_m <= max_distance_m,
    }
