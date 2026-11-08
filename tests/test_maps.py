import asyncio

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.gtfs import GTFS, get_gtfs
from app.services.sptrans import SPTransClient, SPTransError, get_sptrans_client


LINES = [
    {"cl": 1273, "lc": False, "lt": "875A", "sl": 1, "tl": 10,
     "tp": "PERDIZES", "ts": "AEROPORTO"},
    {"cl": 34041, "lc": False, "lt": "875A", "sl": 2, "tl": 10,
     "tp": "PERDIZES", "ts": "AEROPORTO"},
    {"cl": 2000, "lc": False, "lt": "875P", "sl": 1, "tl": 10,
     "tp": "PINHEIROS", "ts": "CENTRO"},
    # SPTrans searches by term, so it may also return lines that only
    # contain the search somewhere else.
    {"cl": 3000, "lc": False, "lt": "1875", "sl": 1, "tl": 10,
     "tp": "A", "ts": "B"},
]

STOPS = [
    {"cp": 1, "np": "PARADA A", "ed": "RUA A", "py": -23.5614, "px": -46.6573},
    {"cp": 2, "np": "PARADA B", "ed": "RUA B", "py": -23.5630, "px": -46.6551},
    {"cp": 3, "np": "PARADA C", "ed": "RUA C", "py": -23.5650, "px": -46.6530},
]


class FakeSPTrans:
    def __init__(self, fail=False):
        self.fail = fail
        self.stops = STOPS
        self.searched = []
        self.stops_for = []

    async def search_lines(self, term):
        if self.fail:
            raise SPTransError("down")
        self.searched.append(term)
        return LINES

    async def fetch_stops(self, line_id):
        self.stops_for.append(line_id)
        return self.stops


def make_client(fake, gtfs=None):
    # By default there is no GTFS, so routes fall back to the stops.
    gtfs = gtfs or GTFS("/nonexistent")
    app.dependency_overrides[get_sptrans_client] = lambda: fake
    app.dependency_overrides[get_gtfs] = lambda: gtfs
    return TestClient(app)


def write_gtfs(folder):
    (folder / "trips.txt").write_text(
        "route_id,service_id,trip_id,trip_headsign,direction_id,shape_id\n"
        "875A-10,USD,875A-10-0,Aeroporto,0,100\n"
        "875A-10,USD,875A-10-1,Perdizes,1,200\n"
    )
    # Points out of order on purpose: shape_pt_sequence defines the order.
    (folder / "shapes.txt").write_text(
        "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\n"
        "200,-23.50,-46.60,2,10\n"
        "100,-23.10,-46.10,1,0\n"
        "200,-23.40,-46.50,1,0\n"
        "200,-23.60,-46.70,3,20\n"
    )
    return GTFS(folder)


def teardown_function():
    app.dependency_overrides.clear()


def test_fetch_bus_lines_matches_code():
    fake = FakeSPTrans()
    response = make_client(fake).get(
        "/maps/fetch_bus_lines", params={"search": "875a"}
    )

    assert response.status_code == 200
    assert response.json() == [
        {"bus_line_code": "875A-10", "direction": 1,
         "origin": "PERDIZES", "destination": "AEROPORTO", "circular": False},
        {"bus_line_code": "875A-10", "direction": 2,
         "origin": "AEROPORTO", "destination": "PERDIZES", "circular": False},
    ]
    assert fake.searched == ["875A"]


def test_fetch_bus_lines_partial_match_in_code():
    response = make_client(FakeSPTrans()).get(
        "/maps/fetch_bus_lines", params={"search": "75"}
    )

    codes = {line["bus_line_code"] for line in response.json()}
    assert codes == {"875A-10", "875P-10", "1875-10"}


def test_fetch_bus_lines_matches_terminal_name():
    response = make_client(FakeSPTrans()).get(
        "/maps/fetch_bus_lines", params={"search": "pinhei"}
    )

    assert [line["bus_line_code"] for line in response.json()] == ["875P-10"]


def test_fetch_bus_lines_no_geometry():
    response = make_client(FakeSPTrans()).get(
        "/maps/fetch_bus_lines", params={"search": "875"}
    )

    for line in response.json():
        assert "features" not in line
        assert "coordinates" not in line


def test_fetch_bus_lines_no_match():
    response = make_client(FakeSPTrans()).get(
        "/maps/fetch_bus_lines", params={"search": "XYZ"}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_fetch_bus_lines_blank_search():
    fake = FakeSPTrans()
    response = make_client(fake).get(
        "/maps/fetch_bus_lines", params={"search": "   "}
    )

    assert response.json() == []
    assert fake.searched == []


def test_fetch_bus_lines_with_full_code_searches_without_suffix():
    fake = FakeSPTrans()
    response = make_client(fake).get(
        "/maps/fetch_bus_lines", params={"search": "875P-10"}
    )

    assert [line["bus_line_code"] for line in response.json()] == ["875P-10"]
    assert fake.searched == ["875P"]


def test_fetch_bus_lines_requires_search():
    response = make_client(FakeSPTrans()).get("/maps/fetch_bus_lines")
    assert response.status_code == 422


def test_fetch_bus_lines_sptrans_error():
    response = make_client(FakeSPTrans(fail=True)).get(
        "/maps/fetch_bus_lines", params={"search": "875"}
    )
    assert response.status_code == 502


def test_fetch_route_returns_geojson():
    fake = FakeSPTrans()
    response = make_client(fake).get(
        "/maps/fetch_route",
        params={"bus_line_code": "875A-10", "direction": 2},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["bus_line_code"] == "875A-10"
    assert data["direction"] == 2
    # Direction 2 of 875A-10 is cl 34041.
    assert fake.stops_for == [34041]

    route, *stops = data["features"]
    assert route["geometry"] == {
        "type": "LineString",
        "coordinates": [[-46.6573, -23.5614], [-46.6551, -23.5630],
                        [-46.6530, -23.5650]],
    }
    assert route["properties"] == {"kind": "route", "source": "stops"}

    assert [stop["properties"]["index"] for stop in stops] == [0, 1, 2]
    assert stops[0]["geometry"] == {
        "type": "Point", "coordinates": [-46.6573, -23.5614],
    }
    assert stops[0]["properties"]["name"] == "PARADA A"
    assert stops[0]["properties"]["kind"] == "stop"


def test_fetch_route_unknown_line():
    response = make_client(FakeSPTrans()).get(
        "/maps/fetch_route",
        params={"bus_line_code": "9999-10", "direction": 1},
    )
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Route not found for bus line 9999-10 in direction 1"
    }


def test_fetch_route_direction_not_found():
    # 875P-10 only exists in direction 1.
    response = make_client(FakeSPTrans()).get(
        "/maps/fetch_route",
        params={"bus_line_code": "875P-10", "direction": 2},
    )
    assert response.status_code == 404


def test_fetch_route_single_stop_has_no_line():
    fake = FakeSPTrans()
    fake.stops = STOPS[:1]
    response = make_client(fake).get(
        "/maps/fetch_route",
        params={"bus_line_code": "875A-10", "direction": 1},
    )

    features = response.json()["features"]
    assert [feature["properties"]["kind"] for feature in features] == ["stop"]


def test_fetch_route_sptrans_error():
    response = make_client(FakeSPTrans(fail=True)).get(
        "/maps/fetch_route",
        params={"bus_line_code": "875A-10", "direction": 1},
    )
    assert response.status_code == 502


def test_fetch_route_invalid_direction():
    response = make_client(FakeSPTrans()).get(
        "/maps/fetch_route",
        params={"bus_line_code": "875A-10", "direction": 3},
    )
    assert response.status_code == 422


def sptrans_with_handler(handler, token="abc"):
    http = httpx.AsyncClient(
        base_url="https://sptrans.test",
        transport=httpx.MockTransport(handler),
    )
    return SPTransClient(token=token, http_client=http)


def test_sptrans_client_logs_in_and_retries_on_401():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/Login/Autenticar":
            assert request.url.params["token"] == "abc"
            return httpx.Response(200, json=True)
        # The first search fails as if the session cookie expired.
        if calls.count("/Linha/Buscar") == 1:
            return httpx.Response(401)
        assert request.url.params["termosBusca"] == "875A"
        return httpx.Response(200, json=LINES)

    client = sptrans_with_handler(handler)
    lines = asyncio.run(client.search_lines("875A"))

    assert lines == LINES
    assert calls == [
        "/Login/Autenticar",
        "/Linha/Buscar",
        "/Login/Autenticar",
        "/Linha/Buscar",
    ]


def test_sptrans_client_without_token():
    client = sptrans_with_handler(lambda request: httpx.Response(200), token="")
    try:
        asyncio.run(client.fetch_stops(1273))
    except SPTransError:
        pass
    else:
        raise AssertionError("expected SPTransError")


def test_sptrans_client_rejected_token():
    client = sptrans_with_handler(lambda request: httpx.Response(200, json=False))
    try:
        asyncio.run(client.search_lines("875A"))
    except SPTransError:
        pass
    else:
        raise AssertionError("expected SPTransError")


def test_sptrans_client_http_error():
    def handler(request):
        if request.url.path == "/Login/Autenticar":
            return httpx.Response(200, json=True)
        return httpx.Response(500)

    client = sptrans_with_handler(handler)
    try:
        asyncio.run(client.fetch_stops(1273))
    except SPTransError:
        pass
    else:
        raise AssertionError("expected SPTransError")


def test_fetch_route_uses_gtfs_shape(tmp_path):
    gtfs = write_gtfs(tmp_path)
    response = make_client(FakeSPTrans(), gtfs).get(
        "/maps/fetch_route",
        params={"bus_line_code": "875a-10", "direction": 2},
    )

    route, *stops = response.json()["features"]
    # Direction 2 is GTFS direction_id 1, which is shape 200.
    assert route["geometry"]["coordinates"] == [
        [-46.50, -23.40], [-46.60, -23.50], [-46.70, -23.60],
    ]
    assert route["properties"] == {"kind": "route", "source": "gtfs"}
    # Stops still come from SPTrans.
    assert [stop["properties"]["index"] for stop in stops] == [0, 1, 2]


def test_fetch_route_falls_back_when_line_not_in_gtfs(tmp_path):
    gtfs = write_gtfs(tmp_path)
    response = make_client(FakeSPTrans(), gtfs).get(
        "/maps/fetch_route",
        params={"bus_line_code": "875P-10", "direction": 1},
    )

    route = response.json()["features"][0]
    assert route["properties"]["source"] == "stops"


def test_gtfs_reads_each_shape_once(tmp_path):
    gtfs = write_gtfs(tmp_path)
    assert gtfs.route_coordinates("875A-10", 1) == [[-46.10, -23.10]]

    # Later calls use the cache, even if the file disappears.
    (tmp_path / "shapes.txt").write_text(
        "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
    )
    assert gtfs.route_coordinates("875A-10", 1) == [[-46.10, -23.10]]
    assert gtfs.route_coordinates("875A-10", 3) is None


def test_gtfs_missing_files(tmp_path):
    assert GTFS(tmp_path).route_coordinates("875A-10", 1) is None


def make_gtfs_zip(files, folder=""):
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for name, content in files.items():
            zip_file.writestr(folder + name, content)
    return buffer.getvalue()


GTFS_ZIP_FILES = {
    "trips.txt": "route_id,service_id,trip_id,trip_headsign,direction_id,shape_id\n"
                 "875A-10,USD,875A-10-0,Aeroporto,0,100\n",
    "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
                  "100,-23.10,-46.10,1\n",
    "stops.txt": "not needed\n",
}


def http_returning(response):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return response

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def test_gtfs_download_extracts_only_needed_files(tmp_path):
    folder = tmp_path / "gtfs"
    http, requests = http_returning(
        httpx.Response(200, content=make_gtfs_zip(GTFS_ZIP_FILES, "gtfs/"))
    )
    gtfs = GTFS(folder, url="https://example.test/gtfs.zip")

    assert gtfs.download_if_missing(http) is True
    assert requests == ["https://example.test/gtfs.zip"]
    assert sorted(path.name for path in folder.iterdir()) == ["shapes.txt", "trips.txt"]
    assert gtfs.route_coordinates("875A-10", 1) == [[-46.10, -23.10]]


def test_gtfs_download_skipped_when_files_exist(tmp_path):
    write_gtfs(tmp_path)
    http, requests = http_returning(httpx.Response(500))
    gtfs = GTFS(tmp_path, url="https://example.test/gtfs.zip")

    assert gtfs.download_if_missing(http) is True
    assert requests == []


def test_gtfs_download_without_url(tmp_path):
    http, requests = http_returning(httpx.Response(500))

    assert GTFS(tmp_path, url=None).download_if_missing(http) is False
    assert requests == []


def test_gtfs_download_http_error(tmp_path):
    http, _ = http_returning(httpx.Response(404))
    gtfs = GTFS(tmp_path / "gtfs", url="https://example.test/gtfs.zip")

    assert gtfs.download_if_missing(http) is False
    assert gtfs.route_coordinates("875A-10", 1) is None


def test_gtfs_download_not_a_zip(tmp_path):
    http, _ = http_returning(httpx.Response(200, content=b"<html>login</html>"))
    gtfs = GTFS(tmp_path / "gtfs", url="https://example.test/gtfs.zip")

    assert gtfs.download_if_missing(http) is False


def test_gtfs_download_zip_without_shapes(tmp_path):
    files = {"trips.txt": GTFS_ZIP_FILES["trips.txt"]}
    http, _ = http_returning(httpx.Response(200, content=make_gtfs_zip(files)))
    gtfs = GTFS(tmp_path / "gtfs", url="https://example.test/gtfs.zip")

    assert gtfs.download_if_missing(http) is False
    assert not (tmp_path / "gtfs" / "trips.txt").exists()
