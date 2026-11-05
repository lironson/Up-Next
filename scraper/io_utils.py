"""Transactional file output: write tmp -> validate -> os.replace."""
import json
import os

VAN_BBOX = (-123.30, 49.18, -123.00, 49.33)  # lon/lat bounds incl. margin


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json_atomic(path, obj, compact=False):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        if compact:
            json.dump(obj, f, separators=(",", ":"))
        else:
            json.dump(obj, f, indent=1)
    return tmp


def commit(tmps):
    """Rename all staged tmp files into place (only after every validation passed)."""
    for tmp in tmps:
        os.replace(tmp, tmp[:-4])


def rollback(tmps):
    for tmp in tmps:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass


def in_vancouver(lon, lat):
    w, s, e, n = VAN_BBOX
    return lon is not None and lat is not None and w <= lon <= e and s <= lat <= n
