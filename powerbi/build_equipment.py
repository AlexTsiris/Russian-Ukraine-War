# -*- coding: utf-8 -*-
"""
Russian equipment-loss dataset for Power BI — VISUALLY CONFIRMED ONLY (photo/video).
Two independent sources; cross-checking them = confidence in a single count.

Sources:
  * WarSpotting (ukr.warspotting.net) — photo-confirmed losses with date/type/status/
    oblast/coordinates. The full history comes from the open MIT scrape mirror
    lazar-bit/automated-warspotting-scraper (its GitHub Action pulls the public API daily;
    the public API itself returns only the last ~100 records + aggregate counters).
  * Oryx (oryxspioenkop.com) — the most-cited independent tracker; per-type totals are
    taken from the machine-readable mirror scarnecchia/oryx_data. Used as an INDEPENDENT
    CROSS-CHECK.

Both are strictly visual confirmation => a conservative LOWER bound. Claims by either
government (Russian/Ukrainian MoD) are NOT included. Attribution is mandatory (see
equipment_meta.csv).

Output (powerbi/):
  equipment_losses.csv     — fact table: date, type, status, model, oblast, lat, lon (time/geo axes)
  equipment_by_type.csv    — type, destroyed, damaged, abandoned, captured, total
  equipment_crosscheck.csv — category, warspotting, oryx  (cross-check of the two sources)
  equipment_meta.csv       — attribution / disclaimer / totals / updated_through

Run: python build_equipment.py
"""
import csv
import io
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WS_CSV = "https://raw.githubusercontent.com/lazar-bit/automated-warspotting-scraper/main/warspotting_losses.csv"
ORYX_API = "https://api.github.com/repos/scarnecchia/oryx_data/contents/totals_by_type.csv"
UA = {"User-Agent": "equipment-etl"}

OUT_LOSSES = os.path.join(HERE, "equipment_losses.csv")
OUT_BYMONTH = os.path.join(HERE, "equipment_by_month.csv")
OUT_BYTYPE = os.path.join(HERE, "equipment_by_type.csv")
OUT_CROSS = os.path.join(HERE, "equipment_crosscheck.csv")
OUT_META = os.path.join(HERE, "equipment_meta.csv")

ATTRIB = ("Visually-confirmed losses only (photo/video). Sources: WarSpotting "
          "(ukr.warspotting.net) & Oryx (oryxspioenkop.com). A conservative lower bound; "
          "claims by either government are excluded.")

# Cross-check only on clearly comparable categories (the source taxonomies differ), so we
# take the grand total + the large armour categories where the mapping is unambiguous.
# (label, [WarSpotting types], Oryx equipment_type substring)
CROSSCHECK = [
    ("Tanks", ["Tanks"], "Tanks"),
    ("Armoured vehicles", ["Tanks", "Infantry fighting vehicles", "Infantry mobility vehicles"],
     "Armoured Combat Vehicles"),
]


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read()


def load_warspotting():
    rows = list(csv.DictReader(io.StringIO(fetch(WS_CSV).decode("utf-8"))))
    rows = [r for r in rows if (r.get("lost_by") or "").strip() == "Russia" and r.get("date")]
    return rows


def load_oryx():
    meta = json.loads(fetch(ORYX_API).decode("utf-8"))
    data = fetch(meta["download_url"]).decode("utf-8")
    out = {}
    for r in csv.DictReader(io.StringIO(data)):
        if (r.get("country") or "").strip() != "Russia":
            continue
        et = (r.get("equipment_type") or "").strip()
        # descriptive summary rows: keep only the "Armoured Combat Vehicles" one we need
        if " - " in et or "of which" in et.lower():
            if "Armoured Combat Vehicles" in et:
                et = "Armoured Combat Vehicles"
            else:
                continue
        try:
            out[et] = {k: int(r[k] or 0) for k in
                       ("destroyed", "abandoned", "captured", "damaged", "type_total")}
        except ValueError:
            continue
    return out


def main():
    print("WarSpotting (granular history) ...")
    ws = load_warspotting()
    print("Oryx (totals by type) ...")
    oryx = load_oryx()

    # --- fact table: equipment losses
    with open(OUT_LOSSES, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "type", "status", "model", "oblast", "lat", "lon"])
        for r in ws:
            w.writerow([r["date"], r["type"], r["status"], r.get("model", ""),
                        r.get("nearest_location", ""), r.get("latitude", ""), r.get("longitude", "")])

    # --- monthly aggregate (for the trend; Sum-friendly)
    by_month = {}
    for r in ws:
        m = r["date"][:7]
        d = by_month.setdefault(m, {"total": 0, "destroyed": 0})
        d["total"] += 1
        if r["status"] == "Destroyed":
            d["destroyed"] += 1
    with open(OUT_BYMONTH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "total", "destroyed"])
        for m in sorted(by_month):
            w.writerow([m, by_month[m]["total"], by_month[m]["destroyed"]])

    # --- by type (statuses from the WarSpotting granular records)
    STAT = ["Destroyed", "Damaged", "Abandoned", "Captured"]
    by_type = {}
    for r in ws:
        d = by_type.setdefault(r["type"], {s: 0 for s in STAT})
        if r["status"] in d:
            d[r["status"]] += 1
    with open(OUT_BYTYPE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "destroyed", "damaged", "abandoned", "captured", "total"])
        for t, d in sorted(by_type.items(), key=lambda x: -sum(x[1].values())):
            w.writerow([t, d["Destroyed"], d["Damaged"], d["Abandoned"], d["Captured"], sum(d.values())])

    # --- cross-check WarSpotting vs Oryx
    def ws_count(types):
        return sum(1 for r in ws if r["type"] in types)

    def oryx_count(substr):
        for et, v in oryx.items():
            if substr.lower() in et.lower() and "all types" not in et.lower():
                return v["type_total"]
        return None

    ws_total = len(ws)
    oryx_total = oryx.get("All Types", {}).get("type_total")
    rows_cc = [("Total (all types)", ws_total, oryx_total)]
    for label, wtypes, osub in CROSSCHECK:
        rows_cc.append((label, ws_count(wtypes), oryx_count(osub)))
    with open(OUT_CROSS, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "warspotting", "oryx"])
        for row in rows_cc:
            w.writerow(row)

    # --- meta
    dates = sorted(r["date"] for r in ws)
    destroyed = sum(1 for r in ws if r["status"] == "Destroyed")
    with open(OUT_META, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["attribution", "warspotting_total", "oryx_total", "destroyed", "updated_through"])
        w.writerow([ATTRIB, ws_total, oryx_total, destroyed, dates[-1]])

    print(f"\nOK: WarSpotting {ws_total:,} (destroyed {destroyed:,})  vs  Oryx {oryx_total:,}"
          f"  -> agree within {abs(ws_total-oryx_total)/oryx_total*100:.1f}%")
    print(f"   history {dates[0]} -> {dates[-1]}  |  {len(by_type)} types")
    print(f"   -> {OUT_LOSSES}\n   -> {OUT_BYTYPE}\n   -> {OUT_CROSS}\n   -> {OUT_META}")


if __name__ == "__main__":
    main()
