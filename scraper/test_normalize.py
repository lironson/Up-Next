from scraper.normalize import parse_storeys, map_stage, make_record, estimate_height


def test_storey_digits():
    assert parse_storeys("To construct a 21-storey mixed-use building") == 21
    assert parse_storeys("new 6 storey residential") == 6
    assert parse_storeys("a 12 storey tower and a 6-storey podium") == 12


def test_storey_words_and_ranges():
    assert parse_storeys("a six-storey rental building") == 6
    assert parse_storeys("two towers of 28 and 32 storeys") == 32
    assert parse_storeys("towers ranging 18 to 25 storeys") == 25


def test_storey_excludes_parking():
    assert parse_storeys("4 storeys over 3 levels of underground parking") == 4
    assert parse_storeys("three levels of underground parking") is None
    assert parse_storeys("no height info") is None
    assert parse_storeys(None, "") is None


def test_stage_mapping():
    assert map_stage("Issued") == "Issued"
    assert map_stage("Approved") == "Approved"
    assert map_stage("Under Review") == "Under Review"
    assert map_stage("Referred to Public Hearing") == "Under Review"
    assert map_stage("Application received") == "Application"
    assert map_stage("Withdrawn") == "Refused/Withdrawn"
    assert map_stage("Refused") == "Refused/Withdrawn"
    assert map_stage("Completed") == "Completed"
    assert map_stage("") is None


def test_make_record_filters_and_estimates():
    kw = dict(id=1, source="t", address="1 Main St", lon=-123.1, lat=49.28, stage_raw="Issued")
    assert make_record(**kw, storeys=4) is None
    assert make_record(**kw, storeys=None) is None
    r = make_record(**kw, storeys=10, year=2024)
    assert r["properties"]["height_m"] == estimate_height(10)
    assert r["properties"]["height_estimated"] is True
    assert r["geometry"]["type"] == "Point"
    r = make_record(**kw, storeys=10, height_m=33.0)
    assert r["properties"]["height_estimated"] is False


def test_storey_decimals_not_misread():
    assert parse_storeys("To construct a 2.5 storey two-family dwelling") is None or parse_storeys("To construct a 2.5 storey two-family dwelling") < 5
    assert parse_storeys("a 1.5 storey laneway house") in (None, 1)
    assert parse_storeys("a 1 \u00bd storey building") in (None, 1)
    assert parse_storeys("a 12.5 m high, 6-storey building") == 6
