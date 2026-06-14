# -*- coding: utf-8 -*-
"""
Adds a "Frontline" page to the report (PBIR) — the occupation map (Deneb) + a territory
counter + a date slicer. Does NOT touch other pages (unlike build_report_pages.py, which
regenerates everything). Reuses the styling from there.

Model dependencies (load as Text/CSV with exactly these names):
  table `frontline_history`: snapshot_date (Text), occupied_km2 (Whole number), wkt (Text)

The map visual itself is the custom Deneb visual (installed from AppSource); the user drops
it onto the marked box and pastes frontline_deneb_spec.json. The rest (slicer, card, trend,
header, attribution) is built by this script.

Run (with Power BI CLOSED): python add_frontline_page.py ; then open the .pbip.
"""
import json
import os

import build_report_pages as B   # reuse the helpers and styling
from build_report_pages import (lit, off, c_field, agg_field, textbox, divider,
                                 slicer, header, ACCENT, WHITE, TEXT, MUTE, FAINT,
                                 VC, PAGE_SCHEMA, PAGES_DIR)

PID = "0a88frontline0000001"
ENTITY = "frontline_history"


def placeholder(vid, x, y, w, h, lines):
    """A dark bordered box with centered text — the placeholder for the Deneb visual."""
    para = [{"horizontalTextAlignment": "center",
             "textRuns": [{"value": r["value"],
                           "textStyle": {"fontFamily": "Segoe UI", "fontSize": r["size"],
                                         "fontWeight": r.get("weight", "400"),
                                         "color": r.get("color", MUTE)}}]} for r in lines]
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": para}}]},
                       "visualContainerObjects": {
                           "title": off(),
                           "background": [{"properties": {"show": lit("true"),
                                          "color": {"solid": {"color": lit("'#161619'")}},
                                          "transparency": lit("0D")}}],
                           "border": [{"properties": {"show": lit("true"),
                                       "color": {"solid": {"color": lit(f"'{FAINT}'")}},
                                       "radius": lit("4D")}}]}}}


def card_agg(vid, x, y, w, h, col, title, color, units=False, size=None):
    proj = {"field": agg_field(ENTITY, col, 0),
            "queryRef": f"Sum({ENTITY}.{col})", "nativeQueryRef": col}
    v = {"$schema": VC, "name": vid,
         "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
         "visual": {"visualType": "cardVisual",
                    "query": {"queryState": {"Data": {"projections": [proj]}}},
                    "drillFilterOtherVisuals": True,
                    "visualContainerObjects": {"title": [{"properties": {
                        "show": lit("true"), "text": lit(f"'{title}'"),
                        "fontColor": {"solid": {"color": lit("'#D6CFD0'")}},
                        "fontSize": lit("11D")}}]}}}
    props = {"color": {"solid": {"color": lit(f"'{color}'")}}}
    if units:
        props["displayUnits"] = lit("1D")
    if size:
        props["fontSize"] = lit(f"{size}D")
    v["visual"]["objects"] = {"calloutValue": [{"properties": props}]}
    return v


def trend_line(vid, x, y, w, h, cat, col, title):
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "lineChart",
                       "query": {"queryState": {
                           "Category": {"projections": [{"field": c_field(ENTITY, cat),
                                        "queryRef": f"{ENTITY}.{cat}", "nativeQueryRef": cat}]},
                           "Y": {"projections": [{"field": agg_field(ENTITY, col, 0),
                                 "queryRef": f"Sum({ENTITY}.{col})", "nativeQueryRef": col}]}},
                           "sortDefinition": {"sort": [{"field": c_field(ENTITY, cat),
                                              "direction": "Ascending"}], "isDefaultSort": True}},
                       "drillFilterOtherVisuals": True,
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}},
                           "fontSize": lit("11D")}}]}}}


def attribution(vid, x, y, w, h, runs):
    return textbox(vid, x, y, w, h, [runs])


VISUALS = header("fl", "THE SHIFTING FRONT  ·  TERRITORIAL CONTROL OVER TIME",
                 "How the Front Has Moved",
                 [{"value": "Russian-occupied territory of Ukraine, month by month. "
                            "Drag the date slicer to watch the front shift.  ",
                   "size": "12pt", "color": MUTE},
                  {"value": "A different dataset from the casualty count — shown for context.",
                   "size": "12pt", "weight": "600", "color": ACCENT}]) + [
    slicer("flslicer00000000001", 40, 178, 220, 472, ENTITY, "snapshot_date", "SNAPSHOT DATE"),
    placeholder("flmap000000000001", 275, 178, 675, 472,
                [{"value": "🗺  OCCUPATION MAP — Deneb", "size": "16pt", "weight": "700", "color": TEXT},
                 {"value": " ", "size": "6pt"},
                 {"value": "Install the free \"Deneb\" visual, drop it on this box,", "size": "11pt"},
                 {"value": "paste frontline_deneb_spec.json and set your GeoJSON URL.", "size": "11pt"},
                 {"value": "Geometry field: frontline_history[wkt] is published via the URL.", "size": "10pt", "color": FAINT}]),
    card_agg("flcard00000000001", 965, 178, 275, 132, "occupied_km2",
             "OCCUPIED TERRITORY — SELECTED DATE (SQ KM)", ACCENT, units=True, size=30),
    textbox("flnote00000000001", 965, 322, 275, 80,
            [[{"value": "Ukraine total ≈ 603,548 sq km.", "size": "11pt", "color": MUTE}],
             [{"value": "Latest occupied ≈ 116,600 (~19.3%).", "size": "11pt", "weight": "600", "color": TEXT}]]),
    trend_line("fltrend0000000001", 965, 408, 275, 242, "snapshot_date", "occupied_km2",
               "OCCUPIED AREA OVER TIME (SQ KM)"),
    divider("flredline20000001", 40, 168, 1200, 1, FAINT),
    attribution("flfooter00000001", 40, 656, 1200, 30,
                [{"value": "Source: DeepStateMap.live — Russian-occupied territory of Ukraine "
                           "(Ukrainian OSINT; Russian sources not included; accuracy not guaranteed; "
                           "~2–3 day delay).  ·  Monthly snapshots, Sep 2022 – present.",
                  "size": "9pt", "weight": "400", "color": FAINT}]),
]


def main():
    page_dir = os.path.join(PAGES_DIR, PID)
    vis_root = os.path.join(page_dir, "visuals")
    os.makedirs(vis_root, exist_ok=True)
    with open(os.path.join(page_dir, "page.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema": PAGE_SCHEMA, "name": PID, "displayName": "Frontline",
                   "displayOption": "FitToPage", "height": 720, "width": 1280},
                  f, indent=2, ensure_ascii=False)
    for v in VISUALS:
        vdir = os.path.join(vis_root, v["name"])
        os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(vdir, "visual.json"), "w", encoding="utf-8") as f:
            json.dump(v, f, indent=2, ensure_ascii=False)

    pj = os.path.join(PAGES_DIR, "pages.json")
    meta = json.load(open(pj, encoding="utf-8"))
    if PID not in meta["pageOrder"]:
        meta["pageOrder"].append(PID)
    json.dump(meta, open(pj, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"OK: Frontline page added ({len(VISUALS)} visuals). Open the .pbip.")
    print("Reminder: load frontline_history.csv (snapshot_date=Text) and drop Deneb onto the map box.")


if __name__ == "__main__":
    main()
