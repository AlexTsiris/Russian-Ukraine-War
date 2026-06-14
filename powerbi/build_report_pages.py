# -*- coding: utf-8 -*-
"""
Generates the dashboard pages (PBIR): Overview, Timeline, Remembrance.
Editorial dark style, with a red thread (top strip) running across every page.
Power BI Desktop must be CLOSED; afterwards, reopen the .pbip.
"""
import json
import os
import shutil

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "powerbi_analyse.Report", "definition")
PAGES_DIR = os.path.join(REPORT, "pages")
VC = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

ACCENT = "#D04949"
WHITE = "#FFFFFF"
TEXT = "#ECE6E6"
MUTE = "#A89B9C"
FAINT = "#6E5F60"


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def off():
    return [{"properties": {"show": lit("false")}}]


def m_field(e, p):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": e}}, "Property": p}}


def c_field(e, p):
    return {"Column": {"Expression": {"SourceRef": {"Entity": e}}, "Property": p}}


def textbox(vid, x, y, w, h, paragraphs, align="left"):
    para = [{"horizontalTextAlignment": align,
             "textRuns": [{"value": r["value"],
                           "textStyle": {"fontFamily": r.get("font", "Segoe UI"),
                                         "fontSize": r["size"],
                                         "fontWeight": r.get("weight", "400"),
                                         "color": r.get("color", TEXT)}}
                          for r in runs]} for runs in paragraphs]
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": para}}]},
                       "visualContainerObjects": {"title": off(), "background": off(),
                                                  "border": off(), "dropShadow": off()}}}


def divider(vid, x, y, w, h, color):
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": [
                           {"textRuns": [{"value": "", "textStyle": {"fontSize": "1pt"}}]}]}}]},
                       "visualContainerObjects": {
                           "title": off(), "border": off(), "dropShadow": off(),
                           "background": [{"properties": {"show": lit("true"),
                                          "color": {"solid": {"color": lit(f"'{color}'")}},
                                          "transparency": lit("0D")}}]}}}


def card(vid, x, y, w, h, entity, measure, title=None, value_color=None,
         full_number=False, callout_size=None):
    v = {"$schema": VC, "name": vid,
         "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
         "visual": {"visualType": "cardVisual",
                    "query": {"queryState": {"Data": {"projections": [{
                        "field": m_field(entity, measure),
                        "queryRef": f"{entity}.{measure}",
                        "nativeQueryRef": measure}]}}},
                    "drillFilterOtherVisuals": True}}
    if title:
        v["visual"]["visualContainerObjects"] = {"title": [{"properties": {
            "show": lit("true"), "text": lit(f"'{title}'"),
            "fontColor": {"solid": {"color": lit("'#D6CFD0'")}},
            "fontSize": lit("11D")}}]}
    else:
        v["visual"]["visualContainerObjects"] = {"title": off()}
    props = {}
    if value_color:
        props["color"] = {"solid": {"color": lit(f"'{value_color}'")}}
    if full_number:
        props["displayUnits"] = lit("1D")
    if callout_size:
        props["fontSize"] = lit(f"{callout_size}D")
    if props:
        v["visual"]["objects"] = {"calloutValue": [{"properties": props}]}
    return v


def chart(vid, x, y, w, h, ce, cc, ve, vm, title, topn=None,
          vtype="barChart", sort_by="measure", direction="Descending"):
    sort_field = m_field(ve, vm) if sort_by == "measure" else c_field(ce, cc)
    v = {"$schema": VC, "name": vid,
         "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
         "visual": {"visualType": vtype,
                    "query": {"queryState": {
                        "Category": {"projections": [{"field": c_field(ce, cc),
                                     "queryRef": f"{ce}.{cc}", "nativeQueryRef": cc}]},
                        "Y": {"projections": [{"field": m_field(ve, vm),
                              "queryRef": f"{ve}.{vm}", "nativeQueryRef": vm}]}},
                        "sortDefinition": {"sort": [{"field": sort_field,
                                           "direction": direction}],
                                           "isDefaultSort": True}},
                    "drillFilterOtherVisuals": True,
                    "objects": {"labels": [{"properties": {"show": lit("true")}}]},
                    "visualContainerObjects": {"title": [{"properties": {
                        "show": lit("true"), "text": lit(f"'{title}'"),
                        "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}},
                        "fontSize": lit("12D")}}]}}}
    if topn:
        v["filterConfig"] = {"filters": [{
            "name": vid[:10] + "topn",
            "field": c_field(ce, cc),
            "type": "VisualTopN",
            "filter": {"Version": 2,
                       "From": [{"Name": "t", "Entity": ce, "Type": 0}],
                       "Where": [{"Condition": {"VisualTopN": {"ItemCount": topn}},
                                  "Target": [{"Column": {
                                      "Expression": {"SourceRef": {"Source": "t"}},
                                      "Property": cc}}]}]}}]}
    return v


def agg_field(e, p, fn=0):  # fn=0 => Sum
    return {"Aggregation": {"Expression": {"Column": {
        "Expression": {"SourceRef": {"Entity": e}}, "Property": p}}, "Function": fn}}


def geomap(vid, x, y, w, h, e, loc, lat, lon, size, title):
    # Map: ONLY Lat/Long + Size (Location cannot be combined with Lat/Long).
    # The settlement name goes into the Tooltips well.
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "map",
                       "query": {"queryState": {
                           "Y": {"projections": [{"field": c_field(e, lat),
                                 "queryRef": f"{e}.{lat}", "nativeQueryRef": lat}]},
                           "X": {"projections": [{"field": c_field(e, lon),
                                 "queryRef": f"{e}.{lon}", "nativeQueryRef": lon}]},
                           "Size": {"projections": [{"field": agg_field(e, size, 0),
                                    "queryRef": f"Sum({e}.{size})", "nativeQueryRef": size}]},
                           "Tooltips": {"projections": [{"field": c_field(e, loc),
                                        "queryRef": f"{e}.{loc}", "nativeQueryRef": loc}]}}},
                       "drillFilterOtherVisuals": True,
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}},
                           "fontSize": lit("12D")}}]}}}


def slicer(vid, x, y, w, h, e, col, title):
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": "slicer",
                       "query": {"queryState": {"Values": {"projections": [{
                           "field": c_field(e, col),
                           "queryRef": f"{e}.{col}", "nativeQueryRef": col}]}}},
                       "drillFilterOtherVisuals": True,
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}},
                           "fontSize": lit("11D")}}]}}}


def stacked(vid, x, y, w, h, ce, cat, se, ser, ve, vm, title,
            vtype="hundredPercentStackedColumnChart", sort_cat=True):
    sort_field = c_field(ce, cat) if sort_cat else m_field(ve, vm)
    direction = "Ascending" if sort_cat else "Descending"
    return {"$schema": VC, "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h},
            "visual": {"visualType": vtype,
                       "query": {"queryState": {
                           "Category": {"projections": [{"field": c_field(ce, cat),
                                        "queryRef": f"{ce}.{cat}", "nativeQueryRef": cat}]},
                           "Series": {"projections": [{"field": c_field(se, ser),
                                      "queryRef": f"{se}.{ser}", "nativeQueryRef": ser}]},
                           "Y": {"projections": [{"field": m_field(ve, vm),
                                 "queryRef": f"{ve}.{vm}", "nativeQueryRef": vm}]}},
                           "sortDefinition": {"sort": [{"field": sort_field,
                                              "direction": direction}],
                                              "isDefaultSort": True}},
                       "drillFilterOtherVisuals": True,
                       "visualContainerObjects": {"title": [{"properties": {
                           "show": lit("true"), "text": lit(f"'{title}'"),
                           "fontColor": {"solid": {"color": lit(f"'{TEXT}'")}},
                           "fontSize": lit("12D")}}]}}}


def header(pid_prefix, kicker, title, standfirst_runs):
    """Standard page header: red thread + kicker + title + standfirst + rule line."""
    return [
        divider(pid_prefix + "strip000000", 0, 0, 1280, 4, ACCENT),
        textbox(pid_prefix + "kicker00000", 40, 20, 1200, 26,
                [[{"value": kicker, "size": "10pt", "weight": "700", "color": ACCENT}]]),
        textbox(pid_prefix + "title000000", 40, 48, 1140, 64,
                [[{"value": title, "size": "32pt", "weight": "700", "color": WHITE}]]),
        textbox(pid_prefix + "stand000000", 40, 112, 1140, 44, [standfirst_runs]),
        divider(pid_prefix + "redline0000", 40, 160, 150, 3, ACCENT),
    ]


def footer(pid_prefix):
    return textbox(pid_prefix + "footer00000", 40, 664, 1200, 30,
                   [[{"value": "Source: Mediazona & BBC News Russian — \"Russia 200\"  ·  "
                              "Confirmed, named deaths (a lower bound)  ·  Extracted 2026-06-12",
                      "size": "9pt", "weight": "400", "color": FAINT}]])


# ============================================================ OVERVIEW
PG_OVERVIEW = {
    "id": "0a11ee220verview0001", "display": "Overview",
    "visuals": header("ov", "THE HUMAN COST  ·  MEDIAZONA × BBC OPEN-SOURCE COUNT",
                      "Russia's Confirmed War Dead",
                      [{"value": "Named, source-verified Russian military deaths in the war "
                                 "against Ukraine. A verified lower bound — not total losses.  ",
                        "size": "12pt", "color": MUTE},
                       {"value": "Independent estimates put total losses at ≈350,000.",
                        "size": "12pt", "weight": "600", "color": ACCENT}]) + [
        card("ovcard0000000000001", 40, 176, 290, 104, "casualties",
             "Total Confirmed Deaths", "CONFIRMED DEATHS — NAMED", ACCENT, full_number=True),
        card("ovcard0000000000002", 350, 176, 290, 104, "casualties",
             "Median Age", "MEDIAN AGE AT DEATH"),
        card("ovcard0000000000003", 660, 176, 290, 104, "casualties",
             "% Rank Known", "MILITARY RANK KNOWN"),
        card("ovcard0000000000004", 970, 176, 290, 104, "casualties",
             "% Branch Known", "SERVICE BRANCH KNOWN"),
        chart("ovbar00000000000001", 40, 296, 595, 340, "casualties", "branch_en",
              "casualties", "Total Confirmed Deaths",
              "Confirmed deaths by service branch — top 10", topn=10),
        chart("ovbar00000000000002", 655, 296, 605, 340, "regions", "region_en",
              "regions", "Deaths per 100k (Confirmed)",
              "Deaths per 100,000 residents — 12 hardest-hit regions", topn=12),
        textbox("ovscale00000000001", 40, 640, 1220, 24,
                [[{"value": "The confirmed dead alone outnumber the entire population of "
                            "Veliky Novgorod — a regional capital of 222,000 people.",
                   "size": "11pt", "weight": "600", "color": TEXT}]]),
        footer("ov"),
    ]}

# ============================================================ TIMELINE
PG_TIMELINE = {
    "id": "0a22timeline00000001", "display": "Timeline",
    "visuals": header("tl", "THE RHYTHM OF WAR  ·  MONTHLY CONFIRMED DEATHS",
                      "When They Died",
                      [{"value": "Monthly confirmed deaths trace the war's phases. ",
                        "size": "12pt", "color": MUTE},
                       {"value": "Recent months look lower because identification takes "
                                 "months — not because losses fell.",
                        "size": "12pt", "weight": "600", "color": ACCENT}]) + [
        card("tlcard0000000000001", 40, 176, 400, 104, "casualties",
             "Deadliest Month", "DEADLIEST MONTH", callout_size=26),
        card("tlcard0000000000002", 460, 176, 400, 104, "casualties",
             "Peak Month Deaths", "CONFIRMED DEATHS THAT MONTH", ACCENT, full_number=True),
        card("tlcard0000000000003", 880, 176, 380, 104, "casualties",
             "% with Known Death Date", "DEATH DATE KNOWN"),
        stacked("tlcol00000000000001", 40, 296, 1220, 366, "casualties", "death_month_start",
                "casualties", "war_phase", "casualties", "Total Confirmed Deaths",
                "Confirmed deaths per month — coloured by phase of the war",
                vtype="columnChart", sort_cat=True),
        footer("tl"),
    ]}

# ============================================================ REMEMBRANCE
PG_REMEMBER = {
    "id": "0a33remember00000001", "display": "Remembrance",
    "visuals": header("rm", "IN MEMORIAM  ·  A DIFFERENT NAME EVERY DAY",
                      "Behind Every Number, a Person",
                      [{"value": "Selected automatically from the verified list; the name "
                                 "changes once a day. Every record links to a public source.",
                        "size": "12pt", "color": MUTE}]) + [
        card("rmname0000000000001", 140, 200, 1000, 170, "casualties",
             "Remembered Name", "TODAY WE REMEMBER", WHITE),
        card("rmdetail00000000001", 140, 390, 1000, 90, "casualties",
             "Remembered Details", None, TEXT, callout_size=16),
        card("rmsource00000000001", 140, 490, 1000, 70, "casualties",
             "Remembered Source", None, FAINT, callout_size=11),
        textbox("rmclosing000000001", 140, 580, 1000, 50,
                [[{"value": "One of more than 200,000 named and verified. "
                            "Behind each entry — a family, a funeral, a hometown.",
                   "size": "12pt", "weight": "600", "color": ACCENT}]], align="center"),
        footer("rm"),
    ]}

# ============================================================ GEOGRAPHY
PG_GEOGRAPHY = {
    "id": "0a44geography00000001", "display": "Geography",
    "visuals": header("gg", "WHERE THEY CAME FROM  ·  HOME REGION, NOT BIRTHPLACE",
                      "The Geography of Loss",
                      [{"value": "Each point is a town or village that lost someone — mapped by "
                                 "home settlement (where the soldier was from / is commemorated), "
                                 "not literal birthplace.  ", "size": "12pt", "color": MUTE},
                       {"value": "The war is fought disproportionately by the rural provinces.",
                        "size": "12pt", "weight": "600", "color": ACCENT}]) + [
        geomap("ggmap00000000000001", 40, 176, 770, 478, "settlements",
               "settlement_en", "lat", "lon", "deaths",
               "Confirmed deaths by home settlement"),
        chart("ggbar00000000000001", 830, 176, 410, 478, "regions", "region_en",
              "regions", "Regional Deaths (Confirmed)",
              "Home regions — top 12 by confirmed deaths", topn=12),
        footer("gg"),
    ]}

# ============================================================ IN CONTEXT
def big_stat(vid, x, y, w, big, label):
    return textbox(vid, x, y, w, 104, [
        [{"value": big, "size": "30pt", "weight": "700", "color": ACCENT}],
        [{"value": label, "size": "11pt", "weight": "400", "color": MUTE}]])


PG_CONTEXT = {
    "id": "0a55context000000001", "display": "In Context",
    "visuals": header("ic", "A 21ST-CENTURY WAR AT 20TH-CENTURY SCALE",
                      "In Context",
                      [{"value": "Even counted only by name, Russia's losses already exceed every "
                                 "Soviet and Russian war since 1945 — combined.  ",
                        "size": "12pt", "color": MUTE},
                       {"value": "And the confirmed total is only a floor.",
                        "size": "12pt", "weight": "600", "color": ACCENT}]) + [
        card("icstat00000000001", 40, 176, 390, 104, "casualties",
             "Ratio vs Afghan War", "× THE SOVIET–AFGHAN WAR (1979–1989)", ACCENT),
        card("icstat00000000002", 440, 176, 390, 104, "casualties",
             "Ratio vs Post-1945 Wars", "× ALL POST-1945 RUSSIAN WARS, COMBINED", ACCENT),
        card("icstat00000000003", 840, 176, 400, 104, "casualties",
             "Death Frequency", "FREQUENCY OF A CONFIRMED DEATH", ACCENT),
        chart("icbar00000000000001", 40, 300, 1220, 320, "conflict_context",
              "Conflict", "conflict_context", "Conflict Deaths Live",
              "Military deaths: this war vs. other modern conflicts (officials' own counts)"),
        textbox("icnote00000000001", 40, 628, 1220, 30,
                [[{"value": "Sources: USSR/Russia & US DoD official counts (Afghanistan 14,453 · "
                            "Chechnya I ~5,500 · Chechnya II ~6,000 · Vietnam 58,220 · US Iraq+Afghanistan 7,073)  ·  "
                            "Ukraine = Mediazona/BBC confirmed names (a floor).",
                   "size": "9pt", "weight": "400", "color": FAINT}]]),
    ]}

# ============================================================ DEMOGRAPHICS
PG_DEMOGRAPHICS = {
    "id": "0a66agedist000000001", "display": "Demographics",
    "visuals": header("dm", "WHO THEY WERE  ·  THE AGE OF THE DEAD",
                      "Not a War of Teenagers",
                      [{"value": "The median man killed is in his mid-30s. More die aged 55+ than "
                                 "under 20 — conscripts are not sent, so this is a war of contract "
                                 "and mobilized men.  ", "size": "12pt", "color": MUTE},
                       {"value": "The dead are not who the stereotype expects.",
                        "size": "12pt", "weight": "600", "color": ACCENT}]) + [
        card("dmcard0000000000001", 40, 176, 290, 104, "casualties",
             "Median Age", "MEDIAN AGE AT DEATH"),
        card("dmcard0000000000002", 350, 176, 290, 104, "casualties",
             "Average Age", "AVERAGE AGE"),
        card("dmcard0000000000003", 660, 176, 290, 104, "casualties",
             "% Aged Under 20", "AGED UNDER 20"),
        card("dmcard0000000000004", 970, 176, 290, 104, "casualties",
             "% Aged 55 and Over", "AGED 55 AND OVER"),
        chart("dmhist0000000000001", 40, 300, 1220, 326, "casualties", "age_group",
              "casualties", "Total Confirmed Deaths",
              "Confirmed deaths by age group", vtype="columnChart",
              sort_by="category", direction="Ascending"),
        textbox("dmnote00000000001", 40, 632, 1220, 26,
                [[{"value": "Age is known for ~96% of records. \"Unknown\" shown for honesty. "
                            "Conscripts (18–19, not legally deployable) are almost absent.",
                   "size": "9pt", "weight": "400", "color": FAINT}]]),
    ]}

# ============================================================ FORCE COMPOSITION
PG_FORCE = {
    "id": "0a77force0000000001", "display": "Force Composition",
    "visuals": header("fc", "WHO RUSSIA THREW IN — AND WHEN",
                      "The Changing Face of the Force",
                      [{"value": "The mix of who dies maps the war's phases: elite airborne first, "
                                 "then prison recruits (the Wagner wave), then the mobilized and "
                                 "contract volunteers.  ", "size": "12pt", "color": MUTE},
                       {"value": "Use the filters on the left to explore.",
                        "size": "12pt", "weight": "600", "color": ACCENT}]) + [
        slicer("fcsl00000000000001", 40, 178, 230, 150, "casualties", "region_en", "REGION"),
        slicer("fcsl00000000000002", 40, 338, 230, 150, "casualties", "age_group", "AGE GROUP"),
        slicer("fcsl00000000000003", 40, 498, 230, 158, "casualties", "rank_category", "RANK"),
        stacked("fcstack00000000001", 290, 178, 970, 478, "casualties", "death_year",
                "casualties", "branch_group", "casualties", "Total Confirmed Deaths",
                "Share of confirmed deaths by service branch, by year of death"),
        footer("fc"),
    ]}

PAGES = [PG_OVERVIEW, PG_DEMOGRAPHICS, PG_FORCE, PG_TIMELINE, PG_GEOGRAPHY, PG_CONTEXT]


def main():
    for pg in PAGES:
        page_dir = os.path.join(PAGES_DIR, pg["id"])
        vis_root = os.path.join(page_dir, "visuals")
        if os.path.isdir(vis_root):
            shutil.rmtree(vis_root)
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, "page.json"), "w", encoding="utf-8") as f:
            json.dump({"$schema": PAGE_SCHEMA, "name": pg["id"],
                       "displayName": pg["display"], "displayOption": "FitToPage",
                       "height": 720, "width": 1280}, f, indent=2, ensure_ascii=False)
        for v in pg["visuals"]:
            vdir = os.path.join(vis_root, v["name"])
            os.makedirs(vdir, exist_ok=True)
            with open(os.path.join(vdir, "visual.json"), "w", encoding="utf-8") as f:
                json.dump(v, f, indent=2, ensure_ascii=False)
        print(f"  {pg['display']}: {len(pg['visuals'])} visuals")

    keep_ids = {pg["id"] for pg in PAGES}
    # remove stale pages from disk (e.g. Remembrance)
    for d in os.listdir(PAGES_DIR):
        full = os.path.join(PAGES_DIR, d)
        if os.path.isdir(full) and d not in keep_ids:
            shutil.rmtree(full)
            print(f"  removed stale page: {d}")
    pj = os.path.join(PAGES_DIR, "pages.json")
    meta = json.load(open(pj, encoding="utf-8"))
    meta["pageOrder"] = [pg["id"] for pg in PAGES]   # exactly our pages
    meta["activePageName"] = PG_OVERVIEW["id"]
    json.dump(meta, open(pj, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("OK: pages written and registered.")


if __name__ == "__main__":
    main()
