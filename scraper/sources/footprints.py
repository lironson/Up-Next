"""Existing buildings: 2009 LiDAR footprints with height above ground -> grid chunks."""
import math
from collections import defaultdict

from ..geo import outer_rings, round_ring
from .ods import export

DATASET = "building-footprints-2009"
SOURCE = "City of Vancouver - Building Footprints 2009 (LiDAR heights)"
CELL = 0.01
MIN_HEIGHT_M = 2.0


def build_chunks():
    """Returns ({key: {"b": [[h, ring], ...]}}, stats)."""
    chunks = defaultdict(list)
    n = 0
    for row in export(DATASET, select="bldgid,hgt_agl,maxht_m,geom,geo_point_2d"):
        h = row.get("hgt_agl") or row.get("maxht_m")
        pt = row.get("geo_point_2d") or {}
        if not h or h < MIN_HEIGHT_M or pt.get("lon") is None:
            continue
        key = f"{math.floor(pt['lon'] / CELL)}_{math.floor(pt['lat'] / CELL)}"
        for ring in outer_rings(row.get("geom")):
            chunks[key].append([round(float(h), 1), round_ring(ring)])
            n += 1
    for v in chunks.values():
        v.sort(key=lambda b: (b[1][0][0], b[1][0][1], b[0]))  # deterministic -> no git churn
    return {k: {"b": v} for k, v in chunks.items()}, {"buildings": n, "chunks": len(chunks)}
