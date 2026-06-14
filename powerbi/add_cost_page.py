# -*- coding: utf-8 -*-
"""
Adds a "Price of Advance" page — the cross-source cost metric (confirmed Russian
losses per net km2 of territory taken). Does NOT touch other pages. Reuses the
styling from build_report_pages.py.

Depends on the measures created by create_cost_metrics.py (folder "07 Cost of
Advance" in the casualties table): Lives per km2 Captured, Equipment per km2
Captured, Territory Captured (km2), Equipment Losses (Confirmed),
km2 per 1,000 Confirmed Dead — plus the existing Total Confirmed Deaths.

The period control must be a date-RANGE slicer (Between) on Calendar[Date]:
the territory measure is end-minus-start, so a single date gives zero. After
running, switch the PERIOD slicer to "Between" style (see the reminder print).

Run (with Power BI CLOSED): python add_cost_page.py ; then open the .pbip.
"""
import json
import os

import build_report_pages as B   # reuse the helpers and styling
from build_report_pages import (lit, off, card, slicer, textbox, divider,
                                 header, ACCENT, WHITE, TEXT, MUTE, FAINT,
                                 VC, PAGE_SCHEMA, PAGES_DIR)

PID = "0ab0priceadvance0001"
ENTITY = "casualties"   # host table where the cost measures live


def boxed_note(vid, x, y, w, h, lines):
    """A dark bordered box with the honesty caption (left-aligned paragraphs)."""
    para = [{"horizontalTextAlignment": "left",
             "textRuns": [{"value": r["value"],
                           "textStyle": {"fontFamily": "Segoe UI", "fontSize": r["size"],
                                         "fontWeight": r.get("weight", "400"),
                                         "color": r.get("color", MUTE)}} for r in runs]}
            for runs in lines]
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


VISUALS = header("pa", "THE PRICE OF ADVANCE  ·  LOSSES PER KM² OF GROUND TAKEN",
                 "What One Kilometre Costs",
                 [{"value": "Confirmed Russian losses set against the NET territory gained over "
                            "the period in view. Set a date range to compare phases.  ",
                   "size": "12pt", "color": MUTE},
                  {"value": "An illustrative ratio — confirmed lower bounds, not a causal price tag.",
                   "size": "12pt", "weight": "600", "color": ACCENT}]) + [
    slicer("paslicer000000001", 40, 190, 240, 290, "Calendar", "Date", "PERIOD (SET A RANGE)"),

    # --- headline ratios
    card("palives0000000001", 300, 190, 300, 150, ENTITY, "Lives per km2 Captured",
         "CONFIRMED DEAD PER KM² TAKEN", ACCENT, callout_size=32),
    card("paequip0000000001", 620, 190, 300, 150, ENTITY, "Equipment per km2 Captured",
         "EQUIPMENT LOST PER KM² TAKEN", ACCENT, callout_size=32),
    card("paterr00000000001", 940, 190, 300, 150, ENTITY, "Territory Captured (km2)",
         "NET TERRITORY GAINED (KM²)", TEXT, full_number=True, callout_size=32),

    # --- supporting context
    card("padeaths000000001", 300, 360, 300, 120, ENTITY, "Total Confirmed Deaths",
         "CONFIRMED DEAD (IN PERIOD)", MUTE, full_number=True),
    card("paeqloss000000001", 620, 360, 300, 120, ENTITY, "Equipment Losses (Confirmed)",
         "EQUIPMENT LOST (IN PERIOD)", MUTE, full_number=True),
    card("painv000000000001", 940, 360, 300, 120, ENTITY, "km2 per 1,000 Confirmed Dead",
         "KM² PER 1,000 DEAD", MUTE),

    boxed_note("panote00000000001", 300, 500, 940, 130, [
        [{"value": "⚠  Preliminary — identification is ongoing.  ", "size": "11pt",
          "weight": "700", "color": ACCENT},
         {"value": "The casualty count in the model is still being collected (a fraction of the "
                   "~225,000 confirmed names) and is skewed toward earlier deaths, so these ratios "
                   "are understated and will rise as the data completes.", "size": "11pt", "color": TEXT}],
        [{"value": " ", "size": "4pt"}],
        [{"value": "Method:  ", "size": "10pt", "weight": "700", "color": MUTE},
         {"value": "confirmed losses ÷ net change in Russian-occupied area over the selected period. "
                   "Territory is complete (DeepStateMap); casualties and equipment are individually / "
                   "visually confirmed lower bounds. Not all losses are \"for territory\" — this is an "
                   "illustrative ratio, not a causal cost.", "size": "10pt", "color": MUTE}],
    ]),

    divider("paredline20000001", 40, 168, 1200, 1, FAINT),
    textbox("pafooter00000001", 40, 656, 1200, 30,
            [[{"value": "Sources: Mediazona/BBC \"Russia 200\" (named dead) · WarSpotting (equipment) · "
                        "DeepStateMap.live (territory).  ·  Confirmed lower bounds; net territory = "
                        "end minus start of the period.",
               "size": "9pt", "weight": "400", "color": FAINT}]]),
]


def main():
    page_dir = os.path.join(PAGES_DIR, PID)
    vis_root = os.path.join(page_dir, "visuals")
    os.makedirs(vis_root, exist_ok=True)
    with open(os.path.join(page_dir, "page.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema": PAGE_SCHEMA, "name": PID, "displayName": "Price of Advance",
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
    print(f"OK: Price of Advance page added ({len(VISUALS)} visuals). Open the .pbip.")
    print("Reminder: select the PERIOD slicer -> Format -> Slicer settings -> Options -> "
          "Style = 'Between' (a date-range slider). A single date gives 0 net territory.")


if __name__ == "__main__":
    main()
