import csv
import os
from functools import lru_cache
from pathlib import Path


# Folder with the SPTrans GTFS files (trips.txt and shapes.txt).
# The files are large and are not committed; see the README.
GTFS_DIR = os.getenv("GTFS_DIR", "data/gtfs")


class GTFS:
    """Reads route shapes from the SPTrans GTFS.

    trips.txt maps a route (e.g. "875A-10") and a direction to a shape_id,
    and shapes.txt has the points of each shape, which follow the streets.
    """

    def __init__(self, folder: str | Path = GTFS_DIR):
        self.folder = Path(folder)
        self.shape_ids: dict[tuple[str, int], str] | None = None
        # Each shape is read once and then kept in memory.
        self.read_shape = lru_cache(maxsize=256)(self.read_shape)

    def available(self) -> bool:
        return (self.folder / "trips.txt").exists() and (
            self.folder / "shapes.txt"
        ).exists()

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
