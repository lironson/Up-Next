"""Schema discovery for City of Vancouver open data (runs in GitHub Actions).

Writes data/_discovery/: catalog.json (matching datasets) and one <dataset_id>.json
per dataset (field list + 3 sample records, geometry truncated), plus probes.json
for the non-ODS City sites. Stdlib only.
"""
import json
import os
import sys
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
    catalog = {}
    for term in TERMS:
        q = urllib.parse.urlencode({"where": f'search("{term}")', "limit": 100,
                                    "select": "dataset_id,metas.default.title,metas.default.records_count,metas.default.modified"})
        try:
            for d in get(f"{BASE}/catalog/datasets?{q}").get("results", []):
                catalog[d["dataset_id"]] = d
        except Exception as e:  # keep going; record the failure
            catalog[f"_error_{term}"] = str(e)
    with open(os.path.join(OUT, "catalog.json"), "w") as f:
        json.dump(catalog, f, indent=1, sort_keys=True)

    for ds in sorted(k for k in catalog if not k.startswith("_error")):
        info = {}
        try:
            meta = get(f"{BASE}/catalog/datasets/{ds}")
            info["fields"] = [{k: fl.get(k) for k in ("name", "type", "label")}
                              for fl in meta.get("fields", [])]
            info["records_count"] = meta.get("metas", {}).get("default", {}).get("records_count")
            recs = get(f"{BASE}/catalog/datasets/{ds}/records?limit=3")
            info["samples"] = truncate(recs.get("results", []))
            info["total_count"] = recs.get("total_count")
        except Exception as e:
            info["error"] = str(e)
        with open(os.path.join(OUT, f"{ds}.json"), "w") as f:
            json.dump(info, f, indent=1)

    probes = {}
    for url in ["https://rezoning.vancouver.ca/", "https://rezoning.vancouver.ca/applications/",
                "https://development.vancouver.ca/", "https://development.vancouver.ca/applications"]:
        try:
            status, body = get(url, raw=True)
            probes[url] = {"status": status, "head": body[:4000]}
        except Exception as e:
            probes[url] = {"error": str(e)}
    with open(os.path.join(OUT, "probes.json"), "w") as f:
        json.dump(probes, f, indent=1)
    print(f"datasets: {len([k for k in catalog if not k.startswith('_error')])}")


if __name__ == "__main__":
    sys.exit(main())
