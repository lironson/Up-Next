"""Minimal City of Vancouver Opendatasoft (v2.1) client. Stdlib only."""
import json
import time
import urllib.parse
import urllib.request

BASE = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets"
UA = {"User-Agent": "up-next-scraper/1.0 (+https://github.com/lironson/up-next)"}


def export(dataset, fmt="json", retries=3, **params):
    """Full dataset export (no 10k paging limit). Returns parsed JSON."""
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{BASE}/{dataset}/exports/{fmt}" + (f"?{q}" if q else "")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def record_url(dataset, query):
    return f"https://opendata.vancouver.ca/explore/dataset/{dataset}/table/?q={urllib.parse.quote(str(query))}"
