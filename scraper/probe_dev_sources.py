"""Temporary probe (runs in Actions): structure of Council meeting docs + Wikipedia tower list.
Writes data/_discovery/council.json and data/_discovery/wikipedia.json. Stdlib only."""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "_discovery")
UA = {"User-Agent": "up-next-probe/1.0 (+https://github.com/lironson/up-next)"}
HREF = re.compile(r'href\s*=\s*["\']([^"\'#]+)', re.I)


def fetch(url, n=None):
    time.sleep(1)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
            return {"status": r.status, "url": r.geturl(), "body": body if n is None else body[:n]}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "url": url, "server": e.headers.get("server"),
                "body": e.read(600).decode("utf-8", "replace")}
    except Exception as e:
        return {"status": None, "url": url, "error": str(e)}


def links(page):
    base = page.get("url") or ""
    return sorted({urllib.parse.urljoin(base, h) for h in HREF.findall(page.get("body") or "")})


def text(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def council():
    res = {}
    roots = ["https://council.vancouver.ca/", "https://pub-vancouver.escribemeetings.com/",
             "https://vancouver.ca/your-government/council-meetings.aspx"]
    pattern = re.compile(r"phea|public.?hearing|agenda|minutes|/20\d{6}/|meeting|calendar|20(2[0-6])", re.I)
    for root in roots:
        p = fetch(root)
        ls = links(p)
        entry = {"status": p.get("status"), "server": p.get("server"), "error": p.get("error"),
                 "n_links": len(ls), "interesting_links": [l for l in ls if pattern.search(l)][:150],
                 "head_text": text(p.get("body") or "")[:2500]}
        # second level: follow up to 8 index-like links on the same host
        host = urllib.parse.urlparse(root).netloc
        second = {}
        for l in [l for l in entry["interesting_links"] if urllib.parse.urlparse(l).netloc == host][:8]:
            q = fetch(l)
            ql = links(q)
            second[l] = {"status": q.get("status"),
                         "links": [x for x in ql if re.search(r"phea|public.?hearing|/20\d{6}/|rr\d|referral|rezon", x, re.I)][:120]}
        entry["second_level"] = second
        res[root] = entry
    # pick one public hearing agenda and one minutes doc if found anywhere
    allk = [x for r in res.values() for s in r.get("second_level", {}).values() for x in s.get("links", [])]
    allk += [x for r in res.values() for x in r.get("interesting_links", [])]
    for kind, rx in [("sample_agenda", r"phea.*ag|public.?hearing.*agenda"), ("sample_minutes", r"phea.*min|public.?hearing.*minutes")]:
        cand = sorted({x for x in allk if re.search(rx, x, re.I)}, reverse=True)
        res[kind + "_candidates"] = cand[:20]
        if cand:
            p = fetch(cand[0])
            res[kind] = {"url": cand[0], "status": p.get("status"), "text": text(p.get("body") or "")[:15000],
                         "links": links(p)[:120], "raw_html_head": (p.get("body") or "")[:6000]}
    return res


def wikipedia():
    api = "https://en.wikipedia.org/w/api.php"
    page = "List_of_tallest_buildings_in_Vancouver"
    res = {}
    s = fetch(f"{api}?action=parse&page={page}&prop=sections&format=json&formatversion=2")
    try:
        secs = json.loads(s["body"])["parse"]["sections"]
    except Exception as e:
        return {"error": str(e), "raw": s}
    res["sections"] = [(x["index"], x["line"], x["level"]) for x in secs]
    for idx, line, _ in res["sections"]:
        if re.search(r"construct|approv|propos|planned|tallest", line, re.I):
            p = fetch(f"{api}?action=parse&page={page}&prop=text|links&section={idx}&format=json&formatversion=2")
            try:
                j = json.loads(p["body"])["parse"]
                res[f"section_{idx}_{line}"] = {"html": j["text"][:60000], "links": [l["title"] for l in j.get("links", [])][:200]}
            except Exception as e:
                res[f"section_{idx}_{line}"] = {"error": str(e)}
    # coordinates support check on a few linked titles
    titles = []
    for k, v in res.items():
        if k.startswith("section_") and isinstance(v, dict):
            titles += v.get("links", [])[:10]
    if titles:
        q = urllib.parse.urlencode({"action": "query", "prop": "coordinates", "titles": "|".join(titles[:20]),
                                    "format": "json", "formatversion": "2"})
        c = fetch(f"{api}?{q}")
        res["coordinates_sample"] = c.get("body", "")[:4000]
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("wikipedia", wikipedia), ("council", council)]:
        try:
            data = fn()
        except Exception as e:
            data = {"fatal": str(e)}
        with open(os.path.join(OUT, f"{name}.json"), "w") as f:
            json.dump(data, f, indent=1)
        print(name, "done")


if __name__ == "__main__":
    main()
