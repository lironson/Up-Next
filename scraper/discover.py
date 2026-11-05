"""Schema discovery for City of Vancouver open data (runs in GitHub Actions).

Writes data/_discovery/: catalog.json (matching datasets) and one <dataset_id>.json
per dataset (field list + 3 sample records, geometry truncated), plus probes.json
for the non-ODS City sites. Stdlib only.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://opendata.vancouver.ca/api/explore/v2.1"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "_discovery")
UA = {"User-Agent": "up-next-discovery/1.0 (+https://github.com/lironson/up-next)"}
TERMS = ["permit", "development", "footprint", "building", "height", "rezoning",
         "address", "view", "parcel", "zoning", "massing", "storey"]


def get(url, raw=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        return (r.status, body.decode("utf-8", "replace")) if raw else json.loads(body)


def truncate(v, depth=0):
    if isinstance(v, dict):
        if "coordinates" in v or v.get("type") in ("Feature", "Polygon", "MultiPolygon", "Point"):
            return {"type": v.get("type"), "_truncated": True,
                    "sample": json.dumps(v)[:200]}
        return {k: truncate(x, depth + 1) for k, x in v.items()}
    if isinstance(v, list):
        return [truncate(x, depth + 1) for x in v[:5]]
    if isinstance(v, str) and len(v) > 400:
        return v[:400] + "..."
    return v


def main():
    os.makedirs(OUT, exist_ok=True)
    catalog, errors, offset = {}, [], 0
    while True:
        try:
            page = get(f"{BASE}/catalog/datasets?limit=100&offset={offset}")
        except urllib.error.HTTPError as e:
            errors.append(f"offset {offset}: {e.code} {e.read()[:500]!r}")
            break
        for d in page.get("results", []):
            m = d.get("metas", {}).get("default", {})
            catalog[d["dataset_id"]] = {
                "title": m.get("title"), "records_count": m.get("records_count"),
                "modified": m.get("modified"), "keyword": m.get("keyword"),
                "fields": [f.get("name") for f in d.get("fields", [])],
            }
        offset += 100
        if offset >= page.get("total_count", 0) or not page.get("results"):
            break
    with open(os.path.join(OUT, "catalog.json"), "w") as f:
        json.dump({"errors": errors, "datasets": catalog}, f, indent=1, sort_keys=True)

    def relevant(ds, info):
        hay = " ".join([ds, str(info.get("title")), str(info.get("keyword"))]).lower()
        return any(t in hay for t in TERMS)

    for ds in sorted(k for k, v in catalog.items() if relevant(k, v)):
        info = {"title": catalog[ds]["title"]}
        try:
            meta = get(f"{BASE}/catalog/datasets/{ds}")
            info["fields"] = [{k: fl.get(k) for k in ("name", "type", "label")}
                              for fl in meta.get("fields", [])]
            recs = get(f"{BASE}/catalog/datasets/{ds}/records?limit=3")
            info["samples"] = truncate(recs.get("results", []))
            info["total_count"] = recs.get("total_count")
        except urllib.error.HTTPError as e:
            info["error"] = f"{e.code} {e.read()[:500]!r}"
        except Exception as e:
            info["error"] = str(e)
        with open(os.path.join(OUT, f"{ds}.json"), "w") as f:
            json.dump(info, f, indent=1)

    probes = {}
    honest_ua = {"User-Agent": "Mozilla/5.0 (compatible; up-next/1.0; +https://github.com/lironson/up-next)"}
    for url in ["https://development.vancouver.ca/", "https://rezoning.vancouver.ca/"]:
        try:
            req = urllib.request.Request(url, headers=honest_ua)
            with urllib.request.urlopen(req, timeout=30) as r:
                probes[url] = {"status": r.status, "head": r.read(6000).decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            probes[url] = {"status": e.code, "body": e.read(800).decode("utf-8", "replace"),
                           "server": e.headers.get("server"), "headers": dict(e.headers)}
        except Exception as e:
            probes[url] = {"error": str(e)}

    # Official City ArcGIS REST directories (VanMap). Walk one folder level, list layer names.
    arc = {}
    for root in ["https://maps.vancouver.ca/server/rest/services",
                 "https://maps.vancouver.ca/arcgis/rest/services",
                 "https://gis.vancouver.ca/arcgis/rest/services",
                 "https://maps.vancouver.ca/gis/rest/services"]:
        try:
            top = get(root + "?f=json")
        except Exception as e:
            arc[root] = {"error": str(e)}
            continue
        entry = {"folders": top.get("folders"), "services": top.get("services"), "layers": {}}
        svcs = [(root, s_) for s_ in top.get("services", [])]
        for folder in (top.get("folders") or [])[:40]:
            try:
                sub = get(f"{root}/{folder}?f=json")
                svcs += [(root, s_) for s_ in sub.get("services", [])]
            except Exception as e:
                entry["layers"][folder] = str(e)
        for base, sv in svcs[:200]:
            if sv.get("type") not in ("MapServer", "FeatureServer"):
                continue
            url = f"{base}/{sv['name']}/{sv['type']}"
            try:
                info = get(url + "?f=json")
                entry["layers"][url] = [(l.get("id"), l.get("name")) for l in info.get("layers", [])]
            except Exception as e:
                entry["layers"][url] = str(e)
        arc[root] = entry
    probes["arcgis"] = arc

    # Targeted layer inspection: fields, counts, samples, distinct values of type-ish fields.
    layers = {}
    lp = "https://maps.vancouver.ca/server/rest/services/VanMapViewer/Licenses_and_Permits/MapServer"
    try:
        lp_layers = [f"{lp}/{l_['id']}" for l_ in get(lp + "/layers?f=json").get("layers", [])
                     if l_.get("type") == "Feature Layer"]
    except Exception as e:
        lp_layers, layers["_lp_error"] = [], str(e)
    for url in lp_layers:
        li = {}
        try:
            meta = get(url + "?f=json")
            li["name"] = meta.get("name")
            li["fields"] = [(f_.get("name"), f_.get("type"), f_.get("alias")) for f_ in meta.get("fields") or []]
            li["maxRecordCount"] = meta.get("maxRecordCount")
            li["count"] = get(url + "/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
            li["samples"] = [ft.get("attributes") for ft in get(
                url + "/query?where=1%3D1&outFields=*&resultRecordCount=5&returnGeometry=false&f=json"
            ).get("features", [])]
            for f_ in li["fields"]:
                n = (f_[0] or "").lower()
                if f_[1] == "esriFieldTypeString" and any(w in n for w in ("type", "status", "categ", "class", "work", "stage")):
                    q = urllib.parse.urlencode({"where": "1=1", "outFields": f_[0], "returnDistinctValues": "true",
                                                "returnGeometry": "false", "f": "json"})
                    vals = get(f"{url}/query?{q}").get("features", [])
                    li.setdefault("distinct", {})[f_[0]] = [v["attributes"].get(f_[0]) for v in vals][:80]
        except urllib.error.HTTPError as e:
            li["error"] = f"{e.code} {e.read(300)!r}"
        except Exception as e:
            li["error"] = str(e)
        layers[url] = li
    with open(os.path.join(OUT, "arcgis_layers.json"), "w") as f:
        json.dump(layers, f, indent=1, default=str)
    with open(os.path.join(OUT, "probes.json"), "w") as f:
        json.dump(probes, f, indent=1)
    print(f"datasets: {len(catalog)} errors: {errors}")


if __name__ == "__main__":
    sys.exit(main())
