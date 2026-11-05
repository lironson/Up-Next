"""Build all site data transactionally.

    python -m scraper.build [--buildings]   # --buildings forces footprint chunk rebuild

Each source runs on its own; a failing source keeps its last-good records. Everything is
staged to *.tmp, validated as a whole, and only then moved into place. Any validation
failure exits 1 and leaves data/ untouched (so the workflow commits nothing).
"""
import json
import os
import shutil
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone

from .io_utils import commit, in_vancouver, read_json, rollback, write_json_atomic
from .normalize import PARSER_VERSION, SCHEMA_VERSION, STAGES, MIN_STOREYS
from .sources import building_permits, footprints, parcels, view_cones

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DEV = os.path.join(ROOT, "developments.geojson")
META = os.path.join(ROOT, "meta.json")
CONES = os.path.join(ROOT, "view_cones.geojson")
BLD = os.path.join(ROOT, "buildings")
REQUIRED = ("id", "source", "address", "lat", "lon", "stage", "storeys", "height_m", "year")
MIN_RATIO = 0.5  # new count must be >= 50% of previous (guards against partial outages)


def log(*a):
    print(*a, flush=True)


def build_developments(prev_features):
    """Run every development source. Returns (features, per-source status)."""
    status = {}
    feats = []
    try:
        footprint_for = parcels.build_lookup()
        status["parcels"] = "ok"
    except Exception as e:
        footprint_for = None
        status["parcels"] = f"failed: {e}"
        log("parcels failed, using placeholders:", e)

    sources = [(building_permits.SOURCE, lambda: building_permits.to_records(
        building_permits.fetch(), footprint_for))]
    for name, run in sources:
        try:
            recs = run()
            status[name] = f"ok ({len(recs)})"
        except Exception:
            traceback.print_exc()
            recs = [f for f in prev_features if f["properties"].get("source") == name]
            status[name] = f"failed; kept {len(recs)} previous"
        feats.extend(recs)
    # de-duplicate on (source, id), keep latest stage_date
    best = {}
    for f in feats:
        k = (f["properties"]["source"], f["properties"]["id"])
        if k not in best or (f["properties"].get("stage_date") or "") > (best[k]["properties"].get("stage_date") or ""):
            best[k] = f
    out = sorted(best.values(), key=lambda f: (f["properties"]["source"], f["properties"]["id"]))
    return out, status


def validate_developments(feats, prev_count):
    errs = []
    if not feats:
        errs.append("no development records")
    if prev_count and len(feats) < prev_count * MIN_RATIO:
        errs.append(f"record count dropped {prev_count} -> {len(feats)}")
    for f in feats:
        p = f["properties"]
        missing = [k for k in REQUIRED if k not in p]
        if missing:
            errs.append(f"{p.get('id')}: missing {missing}")
        elif p["stage"] not in STAGES:
            errs.append(f"{p['id']}: bad stage {p['stage']}")
        elif not in_vancouver(p["lon"], p["lat"]):
            errs.append(f"{p['id']}: outside Vancouver {p['lon']},{p['lat']}")
        elif p["storeys"] < MIN_STOREYS:
            errs.append(f"{p['id']}: storeys {p['storeys']}")
        if len(errs) > 20:
            break
    return errs


def stage_buildings(force):
    """Stage footprint chunks into data/buildings.tmp/. Returns (tmpdir|None, stats)."""
    idx = read_json(os.path.join(BLD, "index.json"))
    if idx and not force:
        return None, {"skipped": True, "buildings": idx.get("buildings"), "chunks": len(idx["chunks"])}
    chunks, stats = footprints.build_chunks()
    prev = (idx or {}).get("buildings") or 0
    if stats["buildings"] < 50000 or (prev and stats["buildings"] < prev * MIN_RATIO):
        raise ValueError(f"footprint validation failed: {stats}")
    tmp = BLD + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for k, v in chunks.items():
        with open(os.path.join(tmp, f"{k}.json"), "w") as f:
            json.dump(v, f, separators=(",", ":"))
    with open(os.path.join(tmp, "index.json"), "w") as f:
        json.dump({"cell": footprints.CELL, "chunks": sorted(chunks), "buildings": stats["buildings"],
                   "source": footprints.SOURCE}, f, indent=1)
    return tmp, stats


def main(argv):
    force_buildings = "--buildings" in argv or not os.path.exists(os.path.join(BLD, "index.json"))
    prev = read_json(DEV, {"features": []})
    prev_feats = prev.get("features", [])
    staged, bld_tmp = [], None
    try:
        feats, status = build_developments(prev_feats)
        prev_meta = read_json(META, {}) or {}
        rules_changed = prev_meta.get("parser_version") != PARSER_VERSION
        errs = validate_developments(feats, 0 if rules_changed else len(prev_feats))
        if errs:
            raise ValueError("development validation failed:\n  " + "\n  ".join(errs[:20]))
        staged.append(write_json_atomic(DEV, {"type": "FeatureCollection", "features": feats}, compact=True))

        try:
            cones = view_cones.fetch_geojson()
            if not cones["features"]:
                raise ValueError("no view cones")
            staged.append(write_json_atomic(CONES, cones, compact=True))
            status["view_cones"] = f"ok ({len(cones['features'])})"
        except Exception as e:
            status["view_cones"] = f"failed; kept previous ({e})"

        bld_tmp, bstats = stage_buildings(force_buildings)
        status["buildings"] = bstats

        props = [f["properties"] for f in feats]
        meta = {
            "schema_version": SCHEMA_VERSION,
            "parser_version": PARSER_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "min_storeys": MIN_STOREYS,
            "count": len(feats),
            "by_stage": dict(Counter(p["stage"] for p in props)),
            "by_year": dict(sorted(Counter(str(p["year"]) for p in props).items())),
            "by_source": dict(Counter(p["source"] for p in props)),
            "footprints": dict(Counter(p.get("footprint_source") for p in props)),
            "sources": status,
        }
        # meta changes every run (timestamp); only stage it when data actually changed
        data_changed = (json.dumps(feats, sort_keys=True) != json.dumps(prev_feats, sort_keys=True)) or bld_tmp or rules_changed
        if data_changed or not os.path.exists(META):
            staged.append(write_json_atomic(META, meta))
    except Exception:
        rollback(staged)
        if bld_tmp:
            shutil.rmtree(bld_tmp, ignore_errors=True)
        traceback.print_exc()
        return 1

    # --- commit: everything validated ---
    if bld_tmp:
        old = BLD + ".old"
        shutil.rmtree(old, ignore_errors=True)
        if os.path.exists(BLD):
            os.replace(BLD, old)
        os.replace(bld_tmp, BLD)
        shutil.rmtree(old, ignore_errors=True)
    commit(staged)
    log(json.dumps({k: meta[k] for k in ("count", "by_stage", "footprints", "sources")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
