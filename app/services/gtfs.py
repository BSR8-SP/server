import csv
import logging
import os
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path

import httpx


# Folder with the SPTrans GTFS files (trips.txt and shapes.txt).
# The files are large and are not committed; see the README.
GTFS_DIR = os.getenv("GTFS_DIR", "data/gtfs")

# Optional direct link to the GTFS .zip, used when the files are missing.
# SPTrans only offers the .zip after a login on its website, so the group
# hosts a copy (e.g. a GitHub release) and points this variable to it.
GTFS_URL = os.getenv("GTFS_URL")

GTFS_FILES = ("trips.txt", "shapes.txt")

logger = logging.getLogger(__name__)


class GTFS:
    """Reads route shapes from the SPTrans GTFS.

    trips.txt maps a route (e.g. "875A-10") and a direction to a shape_id,
    and shapes.txt has the points of each shape, which follow the streets.
    """

    def __init__(self, folder: str | Path = GTFS_DIR, url: str | None = GTFS_URL):
        self.folder = Path(folder)
        self.url = url
        self.shape_ids: dict[tuple[str, int], str] | None = None
        # Each shape is read once and then kept in memory.
        self.read_shape = lru_cache(maxsize=256)(self.read_shape)

    def available(self) -> bool:
        return all((self.folder / name).exists() for name in GTFS_FILES)

    def download_if_missing(self, http_client: httpx.Client | None = None) -> bool:
        """Downloads the GTFS .zip from GTFS_URL when the files are missing.

        Only trips.txt and shapes.txt are extracted. Returns True when the
        files are available afterwards. A failed download is only logged,
        so the server still starts and routes fall back to the stops.
        """
        if self.available():
            return True
        if not self.url:
            return False

        http = http_client or httpx.Client(follow_redirects=True, timeout=300)
        try:
            with tempfile.TemporaryFile() as archive:
                with http.stream("GET", self.url) as response:
                    response.raise_for_status()
                    for chunk in response.iter_bytes():
                        archive.write(chunk)

                self.extract(archive)
        except (httpx.HTTPError, zipfile.BadZipFile, KeyError) as error:
            logger.warning("Could not download the GTFS from %s: %s", self.url, error)
            return False
        finally:
            if http_client is None:
                http.close()

        logger.info("GTFS downloaded to %s", self.folder)
        return True

    def extract(self, archive) -> None:
        with zipfile.ZipFile(archive) as zip_file:
            # The files may be inside a folder in the .zip.
            members = {Path(name).name: name for name in zip_file.namelist()}
            missing = [name for name in GTFS_FILES if name not in members]
            if missing:
                raise KeyError(f"{', '.join(missing)} not in the .zip")

            self.folder.mkdir(parents=True, exist_ok=True)
            for name in GTFS_FILES:
                with zip_file.open(members[name]) as source, open(
                    self.folder / name, "wb"
                ) as target:
                    while chunk := source.read(1024 * 1024):
                        target.write(chunk)

    def load_shape_ids(self) -> dict[tuple[str, int], str]:
        if self.shape_ids is None:
            self.shape_ids = {}
            with open(self.folder / "trips.txt", newline="", encoding="utf-8-sig") as file:
                for trip in csv.DictReader(file):
                    # GTFS direction_id is 0 or 1; SPTrans sl is 1 or 2.
                    key = (trip["route_id"].upper(), int(trip["direction_id"]) + 1)
                    self.shape_ids.setdefault(key, trip["shape_id"])
        return self.shape_ids

    def read_shape(self, shape_id: str) -> list[list[float]]:
        points = []
        with open(self.folder / "shapes.txt", newline="", encoding="utf-8-sig") as file:
            for point in csv.DictReader(file):
                if point["shape_id"] == shape_id:
                    points.append((
                        int(point["shape_pt_sequence"]),
                        float(point["shape_pt_lon"]),
                        float(point["shape_pt_lat"]),
                    ))
        points.sort()
        # GeoJSON order: [longitude, latitude].
        return [[lon, lat] for _, lon, lat in points]

    def route_coordinates(
        self, bus_line_code: str, direction: int
    ) -> list[list[float]] | None:
        """Street geometry of a line, or None when the GTFS does not have it."""
        if not self.available():
            return None

        shape_id = self.load_shape_ids().get((bus_line_code.upper(), direction))
        if shape_id is None:
            return None

        return self.read_shape(shape_id) or None


gtfs = GTFS()


def get_gtfs() -> GTFS:
    return gtfs
