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


def dist_to_ring_m(lon, lat, ring):
    """Distance (m) from point to the ring boundary, local equirectangular projection."""
    kx, ky = 111320 * math.cos(math.radians(lat)), 110540
    best = float("inf")
    for i in range(len(ring) - 1):
        ax, ay = (ring[i][0] - lon) * kx, (ring[i][1] - lat) * ky
        bx, by = (ring[i + 1][0] - lon) * kx, (ring[i + 1][1] - lat) * ky
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def nearest(index, lon, lat, max_m):
    """Nearest ring in a GridIndex within max_m (checks the 3x3 neighbouring cells)."""
    c = index.cell
    gx, gy = math.floor(lon / c), math.floor(lat / c)
    best, seen = None, set()
    for x in (gx - 1, gx, gx + 1):
        for y in (gy - 1, gy, gy + 1):
            for ring, payload in index.cells.get((x, y), []):
                if id(ring) in seen:
                    continue
                seen.add(id(ring))
                d = dist_to_ring_m(lon, lat, ring)
                if d <= max_m and (best is None or d < best[0]):
                    best = (d, ring, payload)
    return best
