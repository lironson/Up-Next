"""Property parcels -> footprint lookup for point-only permits."""
from ..geo import GridIndex, outer_rings, ring_area_m2, round_ring
from .ods import export

DATASET = "property-parcel-polygons"
MAX_PARCEL_M2 = 4000  # bigger sites: a parcel overstates tower bulk -> use placeholder


def build_lookup():
    idx = GridIndex()
    for row in export(DATASET, select="geom"):
        for ring in outer_rings(row.get("geom")):
            idx.add(ring, None)

    def footprint_for(lon, lat):
        hit = idx.find(lon, lat)
        if not hit:
            return None, None
        ring = hit[0]
        if ring_area_m2(ring) > MAX_PARCEL_M2:
            return None, "placeholder-large-site"
        return {"type": "Polygon", "coordinates": [round_ring(ring)]}, "parcel"

    return footprint_for
