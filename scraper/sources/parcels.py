"""Property parcels -> footprint lookup for point-only permits."""
from ..geo import GridIndex, nearest, outer_rings, ring_area_m2, round_ring
from .ods import export

DATASET = "property-parcel-polygons"
MAX_PARCEL_M2 = 4000  # bigger sites: a parcel overstates tower bulk -> use placeholder
SNAP_M = 15          # permit points often sit on the street frontage just outside the lot


def build_lookup():
    idx = GridIndex()
    for row in export(DATASET, select="geom"):
        for ring in outer_rings(row.get("geom")):
            idx.add(ring, None)

    def footprint_for(lon, lat):
        hit = idx.find(lon, lat)
        if hit:
            ring, src = hit[0], "parcel"
        else:
            near = nearest(idx, lon, lat, SNAP_M)
            if not near:
                return None, None
            ring, src = near[1], "parcel-nearest"
        if ring_area_m2(ring) > MAX_PARCEL_M2:
            return None, "placeholder-large-site"
        return {"type": "Polygon", "coordinates": [round_ring(ring)]}, src

    return footprint_for
