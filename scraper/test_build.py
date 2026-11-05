from scraper.build import validate_developments
from scraper.normalize import make_record
from scraper.sources import building_permits
from scraper.geo import point_in_ring, ring_area_m2, GridIndex


def _rec(i, **kw):
    base = dict(id=i, source="t", address="x", lon=-123.1, lat=49.28, stage_raw="Issued", storeys=8, year=2024)
    base.update(kw)
    return make_record(**base)


def test_validate_ok_and_drop_guard():
    feats = [_rec(i) for i in range(10)]
    assert validate_developments(feats, 10) == []
    assert any("dropped" in e for e in validate_developments(feats[:4], 10))


def test_validate_bbox():
    assert validate_developments([_rec(1, lon=-122.0)], 0)


def test_building_permit_adapter():
    rows = [
        {"permitnumber": "BP-1", "issuedate": "2024-03-01", "issueyear": "2024", "address": "1 Main St",
         "projectdescription": "New Building - to construct a 21-storey residential tower",
         "specificusecategory": ["Multiple Dwelling"], "geo_point_2d": {"lon": -123.12, "lat": 49.28}},
        {"permitnumber": "BP-2", "issuedate": "2024-03-01", "issueyear": "2024", "address": "2 Main St",
         "projectdescription": "New Building - single family dwelling with basement",
         "geo_point_2d": {"lon": -123.12, "lat": 49.28}},
    ]
    sq = [[-123.121, 49.279], [-123.119, 49.279], [-123.119, 49.281], [-123.121, 49.281], [-123.121, 49.279]]
    recs = building_permits.to_records(rows, lambda lon, lat: ({"type": "Polygon", "coordinates": [sq]}, "parcel"))
    assert len(recs) == 1
    p = recs[0]["properties"]
    assert (p["storeys"], p["stage"], p["year"], p["footprint_source"]) == (21, "Issued", 2024, "parcel")
    assert recs[0]["geometry"]["type"] == "Polygon"


def test_geo():
    sq = [[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]
    assert point_in_ring(0.0005, 0.0005, sq) and not point_in_ring(0.002, 0.0005, sq)
    assert 10000 < ring_area_m2(sq) < 13000
    g = GridIndex(); g.add(sq, "a")
    assert g.find(0.0005, 0.0005)[1] == "a" and g.find(0.5, 0.5) is None
