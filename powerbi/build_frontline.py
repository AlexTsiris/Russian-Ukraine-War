# -*- coding: utf-8 -*-
"""
Builds the front-line dataset for Power BI (the "Frontline" page + time slider).
FULL history: April 2022 -> today, one snapshot per month.

Source: DeepStateMap.live (Ukrainian OSINT, memorandum with Ukraine's MoD).
Two parts are stitched together:
  * 2022-04 .. 2024-06 — historical snapshots: the list of snapshot ids comes from
    the Wayback Machine copy of the /api/history endpoint (the live list is now behind
    auth), and each snapshot's geometry is pulled from the still-open per-id endpoint
    https://deepstatemap.live/api/history/<id>/geojson. Cached on disk.
  * 2024-07 .. today — from the open GPL mirror github.com/cyterat/deepstate-map-data
    (the consolidated deepstate-map-data.geojson.gz, already occupied territory only).

From each raw snapshot we keep ONLY the real occupied territory of Ukraine: the status
in `name` contains "occupied"/"cadr"/"calr" AND the centroid is inside Ukraine's bbox
(this drops DeepState's satirical polygons — "Occupied East Prussia/Karelia/Kuril/
Abkhazia" etc.). The method was cross-checked against the mirror (areas agree to ~0.3%).
Geometry is simplified (~0.5 km) into a compact WKT for Power BI.

LICENSE NOTE: the data is from DeepStateMap.live; educational / non-commercial use
WITH MANDATORY ATTRIBUTION (see frontline_meta.csv and the dashboard page). The API is
not redistributed to third parties. Commercial use needs written permission from DeepState.

Output (powerbi/):
  frontline_history.csv  — snapshot_date, occupied_km2, wkt  (monthly, ~46 rows)
  frontline_meta.csv     — attribution / disclaimer + date of the latest snapshot

Run:           python build_frontline.py
Fresh data:    python build_frontline.py --refresh   (re-download mirror + Wayback)
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import math
import os
import time
import urllib.request

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import force_2d, set_precision, wkt as shapely_wkt

HERE = os.path.dirname(os.path.abspath(__file__))
GZ = os.path.join(HERE, "ds_hist.geojson.gz")
WB = os.path.join(HERE, "wb_hist.json")
CACHE = os.path.join(HERE, "frontline_cache_hist.csv")
OUT_HIST = os.path.join(HERE, "frontline_history.csv")
OUT_META = os.path.join(HERE, "frontline_meta.csv")
OUT_GEOJSON = os.path.join(HERE, "frontline.geojson")

RAW_GZ = "https://raw.githubusercontent.com/cyterat/deepstate-map-data/main/deepstate-map-data.geojson.gz"
DATA_API = "https://api.github.com/repos/cyterat/deepstate-map-data/contents/data"
WB_HIST = "http://web.archive.org/web/20241113232159id_/https://deepstatemap.live/api/history"
PERID = "https://deepstatemap.live/api/history/%d/geojson"

SOURCE = ("Source: DeepStateMap.live (attribution required). Ukrainian OSINT; "
          "Russian sources not included; accuracy not guaranteed; ~2-3 day delay.")
SIMPLIFY_DEG = 0.005      # ~0.5 km: high-detail outline (Deneb loads the file over a URL)
EARTH_R = 6371.0088       # km, mean Earth radius
MIN_COMPLETE_KM2 = 80000  # completeness threshold for a snapshot (see the filter in main)
HIST_UNTIL = "2024-06"    # up to and including this month is the historical part (API)
UA_BBOX = (22, 44, 41, 53)
UA = {"User-Agent": "frontline-etl"}


def get_json(url, timeout=120):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout))


def download(url, dest):
    print(f"  download {url} ...")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())


def _ring_area_km2(coords):
    """Geodesic area of one ring (spherical formula, more accurate than an equirectangular one)."""
    s = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i][0], coords[i][1]
        x2, y2 = coords[i + 1][0], coords[i + 1][1]
        s += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    return abs(s * EARTH_R * EARTH_R / 2.0)


def area_km2(g):
    polys = g.geoms if g.geom_type == "MultiPolygon" else [g]
    total = 0.0
    for p in polys:
        total += _ring_area_km2(list(p.exterior.coords))
        for h in p.interiors:                       # subtract holes (liberated enclaves)
            total -= _ring_area_km2(list(h.coords))
    return total


def occupied_union(gj):
    """From a raw DeepState GeoJSON -> a single MultiPolygon of the real occupied Ukraine."""
    polys = []
    for f in gj["features"]:
        if f["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            continue
        nm = (f["properties"].get("name") or "").lower()
        if not ("occupied" in nm or "cadr" in nm or "calr" in nm):
            continue
        g = force_2d(shape(f["geometry"]))
        c = g.centroid
        if UA_BBOX[0] <= c.x <= UA_BBOX[2] and UA_BBOX[1] <= c.y <= UA_BBOX[3]:
            polys.append(g if g.is_valid else g.buffer(0))
    return unary_union(polys) if polys else None


def compact_wkt(geom):
    geom = geom.simplify(SIMPLIFY_DEG, preserve_topology=True)
    geom = set_precision(geom, 0.0001)
    return None if geom.is_empty else (geom.wkt, round(area_km2(geom)))


def month_key(d):  # 'YYYY-MM'
    return d[:7]


# ---------------------------------------------------------------- historical (API via Wayback ids)
def build_historical(refresh):
    if refresh or not os.path.exists(WB):
        download(WB_HIST, WB)
    snaps = json.load(open(WB, encoding="utf-8"))
    # the last id in each month (end of month), only up to HIST_UNTIL
    by_month = {}
    for s in snaps:
        d = dt.datetime.fromtimestamp(s["id"], dt.UTC).strftime("%Y-%m-%d")
        if month_key(d) <= HIST_UNTIL:
            cur = by_month.get(month_key(d))
            if cur is None or s["id"] > cur[1]:
                by_month[month_key(d)] = (d, s["id"])
    want = sorted(by_month.values())  # [(date, id), ...]

    cache = {}
    if os.path.exists(CACHE):
        for r in csv.DictReader(open(CACHE, encoding="utf-8")):
            cache[r["snapshot_date"]] = (r["snapshot_date"], int(r["occupied_km2"]), r["wkt"])

    rows = []
    for date, sid in want:
        if date in cache:
            rows.append(cache[date]); continue
        try:
            gj = get_json(PERID % sid, timeout=60)
            u = occupied_union(gj)
            cw = compact_wkt(u) if u else None
            if cw:
                rows.append((date, cw[1], cw[0]))
                print(f"  [api] {date}  ~{cw[1]:,} km2")
            time.sleep(0.5)  # be gentle with the API
        except Exception as e:
            print(f"  [api] {date} FAILED: {e}")
    # update the cache
    allrows = {r[0]: r for r in list(cache.values()) + rows}
    with open(CACHE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["snapshot_date", "occupied_km2", "wkt"])
        for r in sorted(allrows.values()):
            w.writerow(r)
    return [allrows[k] for k in sorted(allrows) if month_key(k) <= HIST_UNTIL]


# ---------------------------------------------------------------- recent (mirror)
def build_recent(refresh):
    if refresh or not os.path.exists(GZ):
        download(RAW_GZ, GZ)
    with gzip.open(GZ, "rt", encoding="utf-8") as f:
        feats = json.load(f)["features"]
    items = get_json(DATA_API)
    import re
    fdates = sorted(re.search(r"(\d{8})", x["name"]).group(1) for x in items if re.search(r"\d{8}\.geojson$", x["name"]))
    fdates = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in fdates]
    if len(fdates) != len(feats):
        raise SystemExit("mirror: dates/features mismatch — run --refresh")
    last_idx = {}
    for i, d in enumerate(fdates):
        if month_key(d) > HIST_UNTIL:
            last_idx[month_key(d)] = i
    if fdates:
        last_idx[month_key(fdates[-1])] = len(fdates) - 1  # the most recent date
    rows = []
    for i in sorted(last_idx.values()):
        cw = compact_wkt(force_2d(shape(feats[i]["geometry"])))
        if cw:
            rows.append((fdates[i], cw[1], cw[0]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    print("Historical part (2022-04 .. %s via DeepState API + Wayback ids):" % HIST_UNTIL)
    hist = build_historical(args.refresh)
    print("Recent part (>%s via cyterat mirror):" % HIST_UNTIL)
    recent = build_recent(args.refresh)

    merged = {r[0]: r for r in hist}
    merged.update({r[0]: r for r in recent})
    rows = [merged[k] for k in sorted(merged)]

    # Completeness filter: early DeepState snapshots (before ~Sep 2022) only drew
    # active-front annotations without fully filling Crimea/Donbas, so their area is
    # implausibly small. Drop incomplete snapshots (< 80,000 sq.km).
    dropped = [r[0] for r in rows if r[1] < MIN_COMPLETE_KM2]
    rows = [r for r in rows if r[1] >= MIN_COMPLETE_KM2]
    if dropped:
        print(f"  (dropped incomplete early snapshots: {dropped[0]}..{dropped[-1]}, "
              f"{len(dropped)} of them — DeepState has no full control fill before Sep 2022)")

    with open(OUT_HIST, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["snapshot_date", "occupied_km2", "wkt"])
        for r in rows:
            w.writerow(r)
    with open(OUT_META, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["attribution", "url", "updated_through"])
        w.writerow([SOURCE, "https://deepstatemap.live", rows[-1][0]])

    # GeoJSON with every month (for Deneb): one feature per date
    features = [{"type": "Feature",
                 "properties": {"date": d, "occupied_km2": a},
                 "geometry": mapping(shapely_wkt.loads(wkt))}
                for d, a, wkt in rows]
    fc = {"type": "FeatureCollection",
          "attribution": SOURCE,
          "features": features}
    with open(OUT_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))

    maxlen = max(len(r[2]) for r in rows)
    print(f"\nOK: {len(rows)} monthly snapshots  {rows[0][0]} -> {rows[-1][0]}")
    print(f"    occupied: {rows[0][1]:,} -> {rows[-1][1]:,} sq.km")
    print(f"    max WKT length: {maxlen:,} chars")
    print(f"    geojson size: {os.path.getsize(OUT_GEOJSON)//1024:,} KB")
    print(f"    -> {OUT_HIST}\n    -> {OUT_META}\n    -> {OUT_GEOJSON}")


if __name__ == "__main__":
    main()
