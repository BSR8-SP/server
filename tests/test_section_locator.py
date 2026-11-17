import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.gtfs import GTFS, get_gtfs
from app.services.section_locator import (
    Route,
    locate_bus_section,
    locate_section,
)
from app.services.sptrans import SPTransError, get_sptrans_client


LAT = -23.56

# Four stops going east along one street (about 500 m, 500 m and 1 km apart).
STOPS = [(LAT, -46.660), (LAT, -46.655), (LAT, -46.650), (LAT, -46.640)]


def sptrans_stops(points):
    return [
        {"cp": 100 + i, "np": f"PARADA {i}", "ed": "RUA", "py": lat, "px": lon}
        for i, (lat, lon) in enumerate(points)
    ]


LINES = [
    {"cl": 1, "lc": False, "lt": "875A", "sl": 1, "tl": 10,
     "tp": "PERDIZES", "ts": "AEROPORTO"},
    {"cl": 2, "lc": False, "lt": "875A", "sl": 2, "tl": 10,
     "tp": "PERDIZES", "ts": "AEROPORTO"},
    {"cl": 3, "lc": False, "lt": "1875", "sl": 1, "tl": 10,
     "tp": "A", "ts": "B"},
]


class FakeSPTrans:
    def __init__(self, stops_by_line=None, fail=False):
        self.fail = fail
        self.stops_by_line = stops_by_line or {
            # Direction 1 goes east on LAT; direction 2 comes back west on
            # a parallel street about 330 m to the north.
            1: sptrans_stops(STOPS),
            2: sptrans_stops([(LAT + 0.003, lon) for _, lon in reversed(STOPS)]),
            3: sptrans_stops(STOPS),
        }
        self.stops_for = []

    async def search_lines(self, term):
        if self.fail:
            raise SPTransError("down")
        return LINES

    async def fetch_stops(self, line_id):
        self.stops_for.append(line_id)
        return self.stops_by_line[line_id]


def no_gtfs():
    return GTFS("/nonexistent")


def run(coroutine):
    return asyncio.run(coroutine)


def teardown_function():
    app.dependency_overrides.clear()


# --- locate_section (pure geometry) ---------------------------------------

def test_point_between_first_two_stops():
    match = locate_section(LAT, -46.6575, STOPS)
    assert (match.section_start, match.section_end) == (0, 1)
    assert match.position == "between_stops"
    assert match.progress == pytest.approx(0.5, abs=0.01)
    assert match.distance_to_route_m < 1


def test_point_in_last_section():
    match = locate_section(LAT, -46.642, STOPS)
    assert (match.section_start, match.section_end) == (2, 3)
    assert match.progress == pytest.approx(0.8, abs=0.01)


def test_point_off_the_street_reports_distance():
    # About 111 m north of the street.
    match = locate_section(LAT + 0.001, -46.652, STOPS)
    assert (match.section_start, match.section_end) == (1, 2)
    assert match.distance_to_route_m == pytest.approx(111, abs=2)


def test_point_exactly_on_a_stop_starts_the_next_section():
    match = locate_section(*STOPS[1], STOPS)
    assert (match.section_start, match.section_end) == (1, 2)
    assert match.progress == 0


def test_point_before_first_and_after_last_stop():
    before = locate_section(LAT, -46.670, STOPS)
    assert (before.section_start, before.position) == (0, "before_first_stop")
    assert before.progress == 0

    after = locate_section(LAT, -46.630, STOPS)
    assert (after.section_end, after.position) == (3, "after_last_stop")
    assert after.progress == 1


def test_route_geometry_is_used_instead_of_straight_lines():
    # Stops at three corners of a square; the bus goes around it.
    a, b, c = (LAT, -46.660), (LAT + 0.01, -46.660), (LAT + 0.01, -46.650)
    # On the second street (b -> c).
    point = (LAT + 0.0099, -46.652)
    assert locate_section(*point, [a, b, c], route=[a, b, c]).section_start == 1

    # The bus makes a detour from a to c: east, north, then west. A point on
    # the detour is far from the straight line a -> c but on the route.
    detour = [a, (LAT, -46.640), (LAT + 0.01, -46.640), c, b]
    stops = [a, c, b]
    match = locate_section(LAT + 0.005, -46.640, stops, route=detour)
    # On the detour street, which is between a and c along the route.
    assert (match.section_start, match.section_end) == (0, 1)
    assert match.distance_to_route_m < 1


def test_loop_keeps_stops_in_route_order():
    # Circular line: goes east, north, west, and back south to the start.
    a = (LAT, -46.660)
    b = (LAT, -46.650)
    c = (LAT + 0.01, -46.650)
    d = (LAT + 0.01, -46.660)
    loop = [a, b, c, d, a]
    stops = [a, b, c, d, a]

    route = Route(loop)
    positions = route.project_stops(stops)
    assert positions == sorted(positions)
    assert positions[-1] == pytest.approx(route.length_m)

    # Going down the last street, back to the first stop.
    match = locate_section(LAT + 0.004, -46.660, stops, route=loop)
    assert (match.section_start, match.section_end) == (3, 4)


def test_needs_two_stops():
    with pytest.raises(ValueError):
        locate_section(LAT, -46.66, STOPS[:1])


# --- locate_bus_section (SPTrans + GTFS) ----------------------------------

def test_returns_section_and_stops():
    fake = FakeSPTrans()
    result = run(locate_bus_section(" 875a-10 ", 1, LAT, -46.652, fake, no_gtfs()))

    assert result["direction"] == 1
    assert result["bus_line_id"] == "875A-10.0"
    assert (result["section_start"], result["section_end"]) == (1, 2)
    assert result["start_stop"] == {"stop_code": 101, "name": "PARADA 1"}
    assert result["end_stop"] == {"stop_code": 102, "name": "PARADA 2"}
    assert result["on_route"] is True
    assert result["route_source"] == "stops"
    # Line 1875 also came back from the search, but must be ignored.
    assert fake.stops_for == [1]


def test_return_direction():
    result = run(locate_bus_section("875A-10", 2, LAT + 0.003, -46.652, FakeSPTrans(), no_gtfs()))
    assert result["bus_line_id"] == "875A-10.1"
    # Going west, -46.652 is between the 2nd (-46.650) and 3rd (-46.655) stops.
    assert (result["section_start"], result["section_end"]) == (1, 2)
    assert result["on_route"] is True


def test_far_from_route_is_flagged():
    # On the street of direction 1, about 330 m from the return street.
    result = run(locate_bus_section("875A-10", 2, LAT, -46.652, FakeSPTrans(), no_gtfs()))
    assert result["on_route"] is False
    result = run(locate_bus_section(
        "875A-10", 2, LAT, -46.652, FakeSPTrans(), no_gtfs(), max_distance_m=500
    ))
    assert result["on_route"] is True


def test_uses_gtfs_shape(tmp_path):
    (tmp_path / "trips.txt").write_text(
        "route_id,service_id,trip_id,trip_headsign,direction_id,shape_id\n"
        "875A-10,USD,875A-10-0,Aeroporto,0,100\n"
    )
    (tmp_path / "shapes.txt").write_text(
        "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\n"
        f"100,{LAT},-46.660,1,0\n"
        f"100,{LAT},-46.640,2,0\n"
    )
    result = run(locate_bus_section("875A-10", 1, LAT, -46.645, FakeSPTrans(), GTFS(tmp_path)))
    assert result["route_source"] == "gtfs"
    assert (result["section_start"], result["section_end"]) == (2, 3)


def test_unknown_line_or_direction_is_404():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        run(locate_bus_section("9999-10", 1, LAT, -46.65, FakeSPTrans(), no_gtfs()))
    assert error.value.status_code == 404

    # A direction without enough stops is skipped.
    fake = FakeSPTrans({1: sptrans_stops(STOPS[:1]), 2: [], 3: []})
    with pytest.raises(HTTPException) as error:
        run(locate_bus_section("875A-10", 1, LAT, -46.65, fake, no_gtfs()))
    assert error.value.status_code == 404
    assert error.value.detail == "Route not found for bus line 875A-10 in direction 1"


# --- endpoint --------------------------------------------------------------

def make_client(fake):
    app.dependency_overrides[get_sptrans_client] = lambda: fake
    app.dependency_overrides[get_gtfs] = no_gtfs
    return TestClient(app)


def test_endpoint_returns_section():
    response = make_client(FakeSPTrans()).get(
        "/maps/locate_section",
        params={"bus_line_code": "875A-10", "direction": 1, "latitude": LAT, "longitude": -46.6575},
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["section_start"], body["section_end"]) == (0, 1)
    assert body["direction"] == 1


def test_endpoint_validation_and_errors():
    client = make_client(FakeSPTrans())
    params = {"bus_line_code": "875A-10", "direction": 1, "latitude": LAT, "longitude": -46.65}

    assert client.get("/maps/locate_section", params={**params, "direction": 3}).status_code == 422
    assert client.get("/maps/locate_section", params={**params, "latitude": 100}).status_code == 422
    assert client.get("/maps/locate_section", params={"bus_line_code": "875A-10"}).status_code == 422
    without_direction = {k: v for k, v in params.items() if k != "direction"}
    assert client.get("/maps/locate_section", params=without_direction).status_code == 422
    assert client.get("/maps/locate_section", params={**params, "bus_line_code": "1-10"}).status_code == 404

    response = make_client(FakeSPTrans(fail=True)).get("/maps/locate_section", params=params)
    assert response.status_code == 502


def test_stops_outside_the_shape_keep_their_order():
    # The GTFS shape starts after the first stop and ends before the last.
    shape = [(LAT, -46.658), (LAT, -46.645)]
    match = locate_section(LAT, -46.659, STOPS, route=shape)
    assert (match.section_start, match.section_end) == (0, 1)
    assert match.position == "between_stops"

    match = locate_section(LAT, -46.641, STOPS, route=shape)
    assert (match.section_start, match.section_end) == (2, 3)
