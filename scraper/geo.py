"""Tiny geometry helpers (no shapely): point-in-polygon, area, grid index."""
import math
from collections import defaultdict


def outer_rings(geom):
    """GeoJSON geometry (or Feature) -> list of outer rings."""
    if not geom:
        return []
    if geom.get("type") == "Feature":
        geom = geom.get("geometry") or {}
    t, c = geom.get("type"), geom.get("coordinates")
    if t == "Polygon":
        return [c[0]]
    if t == "MultiPolygon":
        return [p[0] for p in c]
    return []


def point_in_ring(lon, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi:
            inside = not inside
        j = i
    return inside


def ring_area_m2(ring):
    if len(ring) < 3:
        return 0.0
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    kx, ky = 111320 * math.cos(lat0), 110540
    a = 0.0
    for i in range(len(ring) - 1):
        a += (ring[i][0] * kx) * (ring[i + 1][1] * ky) - (ring[i + 1][0] * kx) * (ring[i][1] * ky)
    return abs(a) / 2


def round_ring(ring, nd=6):
    out = [[round(p[0], nd), round(p[1], nd)] for p in ring]
    return [p for i, p in enumerate(out) if i == 0 or p != out[i - 1]]


class GridIndex:
    """Bucket rings by bbox into a lon/lat grid for fast point lookups."""

    def __init__(self, cell=0.002):
        self.cell = cell
        self.cells = defaultdict(list)

    def add(self, ring, payload):
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        c = self.cell
        for gx in range(math.floor(min(xs) / c), math.floor(max(xs) / c) + 1):
            for gy in range(math.floor(min(ys) / c), math.floor(max(ys) / c) + 1):
                self.cells[(gx, gy)].append((ring, payload))

    def find(self, lon, lat):
        for ring, payload in self.cells.get((math.floor(lon / self.cell), math.floor(lat / self.cell)), []):
            if point_in_ring(lon, lat, ring):
                return ring, payload
        return None
