# -*- coding: utf-8 -*-
"""
Adds an "Equipment Map" page — a point map of Russian equipment losses (Deneb).
Does NOT touch other pages.

The map (Deneb) draws points straight from the equipment_losses table (lat/lon/status/type),
so no external file is needed. The period slicer (Calendar[YearMonth]) and the type slicer
filter the points. Spec: equipment_map_deneb_spec.json (with a full-Ukraine silhouette).

Fields in the Deneb visual's Values well: equipment_losses[lat], [lon], [status], [type].

Run (with Power BI CLOSED): python add_equipment_map_page.py ; then open the .pbip.
"""
import json
import os

import build_report_pages as B
from build_report_pages import (lit, off, slicer, textbox, divider, header,
                                 ACCENT, WHITE, TEXT, MUTE, FAINT, VC, PAGE_SCHEMA, PAGES_DIR)

PID = "0aa0equipmap00000001"


def placeholder(vid, x, y, w, h, lines):
    para = [{"horizontalTextAlignment": "center",
             "textRuns": [{"value": r["value"], "textStyle": {"fontFamily": "Segoe UI",
                           "fontSize": r["size"], "fontWeight": r.get("weight", "400"),
                           "color": r.get("color", MUTE)}}]} for r in lines]
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": para}}]},
                       "visualContainerObjects": {
                           "title": off(),
                           "background": [{"properties": {"show": lit("true"),
                                          "color": {"solid": {"color": lit("'#161619'")}}, "transparency": lit("0D")}}],
                           "border": [{"properties": {"show": lit("true"),
                                       "color": {"solid": {"color": lit(f"'{FAINT}'")}}, "radius": lit("4D")}}]}}}


VISUALS = header("em", "WHERE THE MACHINES DIED  ·  EACH DOT IS ONE LOSS (PHOTO-CONFIRMED)",
                 "The Geography of Attrition",
                 [{"value": "Every point is a Russian vehicle lost at that spot, coloured by fate. "
                            "Filter by period and type on the left.  ", "size": "12pt", "color": MUTE},
                  {"value": "~61% of losses are geolocated; the rest aren't mapped.",
                   "size": "12pt", "weight": "600", "color": ACCENT}]) + [
    slicer("emsl00000000000001", 40, 178, 220, 230, "Calendar", "YearMonth", "PERIOD"),
    slicer("emsl00000000000002", 40, 418, 220, 232, "equipment_losses", "type", "EQUIPMENT TYPE"),
    placeholder("emmap000000000001", 275, 178, 965, 472,
                [{"value": "📍  EQUIPMENT-LOSS MAP — Deneb", "size": "16pt", "weight": "700", "color": TEXT},
                 {"value": " ", "size": "6pt"},
                 {"value": "Install \"Deneb\", drop it here. Values: equipment_losses lat, lon, status, type.", "size": "11pt"},
                 {"value": "Provider Vega-Lite → paste equipment_map_deneb_spec.json.", "size": "11pt"},
                 {"value": "Points colour by status; period & type slicers filter them.", "size": "10pt", "color": FAINT}]),
    divider("emredline20000001", 40, 168, 1200, 1, FAINT),
    textbox("emfooter00000001", 40, 656, 1200, 30,
            [[{"value": "Source: WarSpotting (ukr.warspotting.net) — visually-confirmed losses with "
                        "geolocation; a conservative lower bound. Point = where the vehicle was hit "
                        "(in Ukraine), not the crew's home region.",
               "size": "9pt", "weight": "400", "color": FAINT}]]),
]


def main():
    page_dir = os.path.join(PAGES_DIR, PID)
    vis_root = os.path.join(page_dir, "visuals")
    os.makedirs(vis_root, exist_ok=True)
    with open(os.path.join(page_dir, "page.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema": PAGE_SCHEMA, "name": PID, "displayName": "Equipment Map",
                   "displayOption": "FitToPage", "height": 720, "width": 1280}, f, indent=2, ensure_ascii=False)
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
    print(f"OK: Equipment Map page added ({len(VISUALS)} visuals). Open the .pbip.")


if __name__ == "__main__":
    main()
