"""Source-independent normalization: stages, storeys, heights, records."""
import re

SCHEMA_VERSION = 1
# Bump when parsing/filter rules change: the next build may then legitimately shrink
# by more than the drop guard allows (see build.py).
PARSER_VERSION = 2
STAGES = ["Application", "Under Review", "Approved", "Issued",
          "Under Construction", "Completed", "Refused/Withdrawn"]
MIN_STOREYS = 5  # product focus: buildings > 4 storeys
STOREY_M, GROUND_EXTRA_M = 3.2, 4.0

# Ordered: first match wins. Patterns run on the lower-cased raw status.
_STAGE_RULES = [
    (r"refus|reject|withdr|cancel|abandon|expired|denied|closed - not", "Refused/Withdrawn"),
    (r"complet|occup|final", "Completed"),
    (r"construct|in progress|underway|started", "Under Construction"),
    (r"issued|permit issued", "Issued"),
    (r"approv|enact|adopted|prior[- ]to|conditional|ready to issue", "Approved"),
    (r"review|referr|hearing|public|circulat|process|evaluat|pending|open", "Under Review"),
    (r"appl|submit|received|intake|new|enquir|inquir", "Application"),
]

_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
_WORDS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60})
_NUM = r"(?<![\d.,/])(\d{1,3}(?![.,/]\d)|" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r")"
_STOREY_RE = re.compile(_NUM + r"(?:\s*\(\d{1,3}\))?\s*[- ]?\s*(?:storey|story|stories|storeys|floors?|levels?)\b", re.I)
_RANGE_RE = re.compile(r"(?<![\d.,/])(\d{1,3})\s*(?:-|to|and)\s*(\d{1,3})\s*[- ]?\s*(?:storey|story|stories|storeys)", re.I)
_EXCLUDE_CONTEXT = re.compile(r"(underground|below grade|parking|basement|sub-?surface|podium)\s*$", re.I)


def map_stage(raw):
    s = (raw or "").strip().lower()
    for pat, stage in _STAGE_RULES:
        if re.search(pat, s):
            return stage
    return None


def _num(tok):
    tok = tok.lower()
    return int(tok) if tok.isdigit() else _WORDS.get(tok)


def parse_storeys(*texts):
    """Max above-grade storey count mentioned in any text, else None.

    Skips counts directly preceded by 'underground'/'parking'... and implausible values.
    """
    best = None
    for text in texts:
        if not text:
            continue
        t = str(text)
        for m in _RANGE_RE.finditer(t):
            v = max(int(m.group(1)), int(m.group(2)))
            if 1 <= v <= 120:
                best = max(best or 0, v)
        for m in _STOREY_RE.finditer(t):
            after = t[m.end():m.end() + 25].lower()
            if re.match(r"\s*(of\s+)?(underground|below|parking|basement)", after):
                continue
            if _EXCLUDE_CONTEXT.search(t[max(0, m.start() - 25):m.start()]):
                continue
            v = _num(m.group(1))
            if v and 1 <= v <= 120:
                best = max(best or 0, v)
    return best


def estimate_height(storeys):
    return round(storeys * STOREY_M + GROUND_EXTRA_M, 1)


def make_record(*, id, source, address, lon, lat, stage_raw, stage=None, year=None,
                stage_date=None, storeys=None, height_m=None, geometry=None,
                use=None, description=None, url=None):
    """Build a normalized GeoJSON Feature, or None if it fails product filters."""
    stage = stage or map_stage(stage_raw)
    if stage is None or storeys is None or storeys < MIN_STOREYS:
        return None
    if lon is None or lat is None:
        return None
    est = height_m is None
    if est:
        height_m = estimate_height(storeys)
    geom = geometry or {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]}
    return {
        "type": "Feature",
        "geometry": geom,
        "properties": {
            "id": str(id), "source": source, "address": (address or "").strip(),
            "lat": round(lat, 6), "lon": round(lon, 6),
            "stage": stage, "stage_raw": stage_raw, "stage_date": stage_date,
            "year": int(year) if year else None,
            "storeys": int(storeys), "height_m": float(height_m), "height_estimated": est,
            "use": use, "description": (description or "")[:600] or None, "url": url,
        },
    }
