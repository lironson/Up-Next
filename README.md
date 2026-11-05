# Up Next · Vancouver

A 3D map for people buying or leasing in Vancouver. Enter an address to see the existing buildings around it as transparent blocks, and the **new buildings over 4 storeys** that have permits nearby, so you can judge what might block a view. Filter by stage and year. The City's protected view cones are shown as an overlay.

**Live site:** https://lironson.github.io/Up-Next/ (after Pages is enabled, see Setup)

## Data

All sources are City of Vancouver Open Data (Opendatasoft API v2.1). A weekly GitHub Action fetches them:

| Layer | Dataset | Notes |
|---|---|---|
| New developments | `issued-building-permits` | Only `typeofwork = New Building`. Storeys are parsed from the description, and only buildings over 4 storeys are kept. Height is estimated as storeys × 3.2 m + 4 m. |
| Development footprints | `property-parcel-polygons` | The permit point is matched to its lot (or the nearest lot within 15 m). Sites over 4,000 m² get an approximate block. |
| Existing buildings | `building-footprints-2009` | LiDAR height above ground (`hgt_agl`), 124k buildings, split into 0.01° grid chunks in `data/buildings/`. |
| View cones | `view-cones` | The City's 24 protected public views. |

**Stages:** the pipeline and UI support Application → Under Review → Approved → Issued → Under Construction → Completed. As of Nov 2026, though, the City publishes **only issued building permits** as open data. Development and rezoning applications live on development.vancouver.ca and rezoning.vancouver.ca, which sit behind a Cloudflare bot challenge, and VanMap's ArcGIS services don't publish them either. The schema report is in `data/_discovery/`. To add a source, write an adapter in `scraper/sources/` that returns `make_record(...)` features, then register it in `scraper/build.py`.

Geocoding uses OpenStreetMap Nominatim, called from the browser on submit only. The basemap is from OpenFreeMap.

## Layout

```
scraper/   Python (stdlib only). Run with: python -m scraper.build [--buildings]
  normalize.py    stage mapping, storey parsing, height estimate, record schema
  build.py        transactional build: stage *.tmp → validate → os.replace
  sources/        one adapter per dataset
web/       static site (no build step). maplibre-gl 5.24.0 and deck.gl 9.4.0 are vendored in web/vendor/
  js/state.js         single store and URL-hash state (shareable links)
  js/layers/index.js  layer registry
  js/effects/index.js effect registry (shadow hook)
  js/sun.js           shadow-analysis interface (stub)
data/      generated output, committed by the Action
```

### Data safety
Each source runs on its own. If one fails, its last good records are kept. All output is staged, then validated: schema, Vancouver bounding box, and no more than a 50% drop in record count (bumping `PARSER_VERSION` allows one deliberate drop). Files are only swapped in once every check passes. If validation fails, the workflow exits non-zero and commits nothing.

## Future: shadow analysis (Jan 1 / Jul 1)
These hooks are already in place:
- `state.datetime` and `state.shadows = { enabled, dateId, hour }` are part of the store.
- `js/sun.js` exports `SHADOW_DATES` (Jan 1 PST, Jul 1 PDT) and `dateAt(dateId, hour)`. The `sunPosition()` stub is for on-screen read-outs.
- `js/effects/index.js` → return `[new deck.LightingEffect({ ambient, sun: new deck._SunLight({ timestamp, _shadow: true }) })]`. Both are present in the vendored deck.gl bundle.
- `js/layers/index.js` has a reserved `ground` slot for a shadow-receiving plane, and every layer factory receives `ctx.shadowsEnabled`.
- `index.html` has a hidden `#time-panel` for the date toggle and hour slider.

## Setup (one-time, repo owner)
1. **Settings → General → Default branch → `main`.** The weekly schedule only runs on the default branch.
2. **Settings → Pages → Source: GitHub Actions.**
3. Actions → *Deploy site* → Run workflow. After that, it redeploys on every push to `main` and after each data refresh.

## Local development
```bash
cd web && python3 -m http.server 8000   # web/data is a symlink to ../data
python3 -m pytest scraper/
```

Heights of proposed buildings are estimates. This map is a guide only and doesn't replace the City's permit records.
