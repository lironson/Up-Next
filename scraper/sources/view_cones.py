"""City-protected public view cones (overlay)."""
from .ods import export

DATASET = "view-cones"


def fetch_geojson():
    rows = export(DATASET)
    feats = []
    for r in rows:
        g = r.get("geom") or {}
        geom = g.get("geometry") if g.get("type") == "Feature" else g
        if not geom:
            continue
        feats.append({"type": "Feature", "geometry": geom, "properties": {
            "view_number": r.get("view_number"), "name": r.get("view_cone_name"),
            "description": r.get("description"), "url": r.get("url")}})
    feats.sort(key=lambda f: str(f["properties"]["view_number"]))
    return {"type": "FeatureCollection", "features": feats}
