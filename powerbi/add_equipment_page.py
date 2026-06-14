# -*- coding: utf-8 -*-
"""
Adds an "Equipment" page (visually-confirmed Russian equipment losses) to the PBIR.
Does NOT touch other pages. Reuses the styling from build_report_pages.py.

Model tables (load as Text/CSV with exactly these names):
  equipment_meta(warspotting_total, oryx_total, destroyed, attribution, updated_through)
  equipment_by_type(type, destroyed, damaged, abandoned, captured, total)
  equipment_crosscheck(category, warspotting, oryx)
  equipment_by_month(month [Text], total, destroyed)
  equipment_losses(date, type, status, model, oblast, lat, lon)  -- for the Calendar relationship

Run (with Power BI CLOSED): python add_equipment_page.py ; then open the .pbip.
"""
import json
import os

import build_report_pages as B
from build_report_pages import (lit, off, c_field, agg_field, textbox, divider,
                                 header, ACCENT, WHITE, TEXT, MUTE, FAINT, VC, PAGE_SCHEMA, PAGES_DIR)

PID = "0a99equipment0000001"


def card_agg(vid, x, y, w, h, entity, col, title, color, units=True, size=28):
    proj = {"field": agg_field(entity, col, 0), "queryRef": f"Sum({entity}.{col})", "nativeQueryRef": col}
    props = {"color": {"solid": {"color": lit(f"'{color}'")}}}
    if units:
        props["displayUnits"] = lit("1D")
    if size:
        props["fontSize"] = lit(f"{size}D")
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "cardVisual",
                       "query": {"queryState": {"Data": {"projections": [proj]}}},
                       "drillFilterOtherVisuals": True,
                       "objects": {"calloutValue": [{"properties": props}]},
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit("'#D6CFD0'")}},
                           "fontSize": lit("11D")}}]}}}


def bar(vid, x, y, w, h, entity, cat, vcol, title):
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "barChart",
                       "query": {"queryState": {
                           "Category": {"projections": [{"field": c_field(entity, cat),
                                        "queryRef": f"{entity}.{cat}", "nativeQueryRef": cat}]},
                           "Y": {"projections": [{"field": agg_field(entity, vcol, 0),
                                 "queryRef": f"Sum({entity}.{vcol})", "nativeQueryRef": vcol}]}},
                           "sortDefinition": {"sort": [{"field": agg_field(entity, vcol, 0),
                                              "direction": "Descending"}], "isDefaultSort": True}},
                       "drillFilterOtherVisuals": True,
                       "objects": {"labels": [{"properties": {"show": lit("true")}}]},
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}}, "fontSize": lit("12D")}}]}}}


def clustered2(vid, x, y, w, h, entity, cat, c1, c2, title):
    yproj = [{"field": agg_field(entity, c, 0), "queryRef": f"Sum({entity}.{c})", "nativeQueryRef": c}
             for c in (c1, c2)]
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "clusteredBarChart",
                       "query": {"queryState": {
                           "Category": {"projections": [{"field": c_field(entity, cat),
                                        "queryRef": f"{entity}.{cat}", "nativeQueryRef": cat}]},
                           "Y": {"projections": yproj}}},
                       "drillFilterOtherVisuals": True,
                       "objects": {"labels": [{"properties": {"show": lit("true")}}]},
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}}, "fontSize": lit("11D")}}]}}}


def trend(vid, x, y, w, h, entity, cat, vcol, title):
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "lineChart",
                       "query": {"queryState": {
                           "Category": {"projections": [{"field": c_field(entity, cat),
                                        "queryRef": f"{entity}.{cat}", "nativeQueryRef": cat}]},
                           "Y": {"projections": [{"field": agg_field(entity, vcol, 0),
                                 "queryRef": f"Sum({entity}.{vcol})", "nativeQueryRef": vcol}]}},
                           "sortDefinition": {"sort": [{"field": c_field(entity, cat),
                                              "direction": "Ascending"}], "isDefaultSort": True}},
                       "drillFilterOtherVisuals": True,
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}}, "fontSize": lit("11D")}}]}}}


VISUALS = header("eq", "THE MACHINES  ·  VISUALLY-CONFIRMED RUSSIAN EQUIPMENT LOSSES",
                 "Counted Only When Photographed",
                 [{"value": "Every vehicle here is backed by a photo or video. Two independent "
                            "trackers — WarSpotting and Oryx — are cross-checked.  ",
                   "size": "12pt", "color": MUTE},
                  {"value": "A verified floor, not the true total.",
                   "size": "12pt", "weight": "600", "color": ACCENT}]) + [
    card_agg("eqcard00000000001", 40, 176, 380, 104, "equipment_meta", "warspotting_total",
             "CONFIRMED LOSSES — WARSPOTTING", ACCENT),
    card_agg("eqcard00000000002", 440, 176, 380, 104, "equipment_meta", "oryx_total",
             "INDEPENDENT COUNT — ORYX (CROSS-CHECK)", TEXT),
    card_agg("eqcard00000000003", 840, 176, 400, 104, "equipment_meta", "destroyed",
             "OF WHICH DESTROYED", ACCENT),
    bar("eqbar000000000001", 40, 300, 595, 348, "equipment_by_type", "type", "total",
        "Confirmed losses by equipment type"),
    clustered2("eqcross0000000001", 655, 300, 585, 165, "equipment_crosscheck", "category",
               "warspotting", "oryx", "Two independent counts agree (WarSpotting vs Oryx)"),
    trend("eqtrend0000000001", 655, 479, 585, 169, "equipment_by_month", "month", "total",
          "Confirmed losses per month"),
    divider("eqredline20000001", 40, 168, 1200, 1, FAINT),
    textbox("eqfooter00000001", 40, 656, 1200, 30,
            [[{"value": "Sources: WarSpotting (ukr.warspotting.net) & Oryx (oryxspioenkop.com) — "
                        "visually-confirmed losses only (photo/video); a conservative lower bound. "
                        "Government claims excluded.  ·  History from 24 Feb 2022.",
               "size": "9pt", "weight": "400", "color": FAINT}]]),
]


def main():
    page_dir = os.path.join(PAGES_DIR, PID)
    vis_root = os.path.join(page_dir, "visuals")
    os.makedirs(vis_root, exist_ok=True)
    with open(os.path.join(page_dir, "page.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema": PAGE_SCHEMA, "name": PID, "displayName": "Equipment",
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
    print(f"OK: Equipment page added ({len(VISUALS)} visuals). Open the .pbip.")
    print("Load the equipment_* tables (see the file header). Date relationship — set up separately via Calendar.")


if __name__ == "__main__":
    main()
