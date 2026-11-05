"""Issued building permits (stage = Issued) for new buildings > 4 storeys."""
from ..normalize import make_record, parse_storeys
from .ods import export, record_url

DATASET = "issued-building-permits"
SOURCE = "City of Vancouver - Issued Building Permits"


def _list(v):
    return ", ".join(v) if isinstance(v, list) else (v or None)


def fetch():
    return export(DATASET, where='typeofwork="New Building"', select=",".join([
        "permitnumber", "issuedate", "issueyear", "address", "projectdescription",
        "typeofwork", "permitcategory", "propertyuse", "specificusecategory",
        "projectvalue", "geo_point_2d"]))


def to_records(rows, footprint_for=None):
    out = []
    for r in rows:
        storeys = parse_storeys(r.get("projectdescription"), r.get("permitcategory"))
        pt = r.get("geo_point_2d") or {}
        lon, lat = pt.get("lon"), pt.get("lat")
        geom, fp_src = (footprint_for(lon, lat) if footprint_for and lon is not None else (None, None))
        rec = make_record(
            id=r.get("permitnumber"), source=SOURCE, address=r.get("address"),
            lon=lon, lat=lat, stage_raw="Issued", stage="Issued",
            stage_date=r.get("issuedate"),
            year=r.get("issueyear") or (r.get("issuedate") or "")[:4] or None,
            storeys=storeys, geometry=geom,
            use=_list(r.get("specificusecategory")) or _list(r.get("propertyuse")),
            description=r.get("projectdescription"),
            url=record_url(DATASET, r.get("permitnumber")),
        )
        if rec:
            rec["properties"]["footprint_source"] = fp_src or "placeholder"
            rec["properties"]["project_value"] = r.get("projectvalue")
            out.append(rec)
    return out
