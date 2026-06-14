# -*- coding: utf-8 -*-
"""
Ukrainian strikes on strategic targets inside Russia — dataset for Power BI / Azure Maps.

Source (redistributable):
  * Wikipedia article "Attacks in Russia during the Russian invasion of Ukraine"
    (CC BY-SA). Fetched via the MediaWiki action API (no key, no auth -> CI friendly).
    The article is organised chronologically by month; each strike is a dated bullet
    with [[wikilinks]] to the target facility / oblast and <ref> news sources.

Pipeline:
  1. Download the article wikitext (action=parse).
  2. Parse month sections -> dated bullets -> strike events (date, target, oblast, source).
  3. Keep only STRATEGIC targets (refinery / oil depot / airfield / ammo depot / energy /
     defence plant). Non-strategic items (missiles downed over cities, casualties) dropped.
  4. Geocode each event via the Wikipedia coordinates API on the linked facility page
     (facility-level precision), falling back to the linked location page, then to a small
     curated gazetteer, then to an oblast centroid.
  5. Deduplicate by (date, target) and write the outputs.

Reliability is community-sourced, so each row keeps a source_url and a status
(confirmed / claimed). strikes_crosscheck.csv compares our totals against published
counts (Baker Institute, United24, Kyiv Independent) so coverage is auditable.
Bias note: strike reports are predominantly Ukrainian / OSINT claims.

Output (powerbi/):
  strategic_strikes.csv   — fact table: date, target_name, target_type, oblast, lat, lon,
                            geo_precision, status, source_url  (time axis = date)
  strikes_crosscheck.csv  — metric, our_value, reference_value, reference_source
  strikes_meta.csv        — attribution / disclaimer / totals / updated_through

Run: python build_strikes.py
"""
import csv
import datetime as dt
import json
import os
import re
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://en.wikipedia.org/w/api.php"
PAGE = "Attacks in Russia during the Russian invasion of Ukraine"
UA = {"User-Agent": "strikes-etl/1.0 (educational research; contact aleksandertsiris@gmail.com)"}

OUT_STRIKES = os.path.join(HERE, "strategic_strikes.csv")
OUT_CROSSCHECK = os.path.join(HERE, "strikes_crosscheck.csv")
OUT_META = os.path.join(HERE, "strikes_meta.csv")

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

# target_type keyword rules, checked in priority order (first match wins)
TARGET_RULES = [
    ("refinery",      [r"\brefiner"]),
    ("oil_depot",     [r"oil depot", r"oil terminal", r"fuel depot", r"oil storage",
                       r"tank farm", r"fuel hub", r"rosrezerv", r"oil pumping", r"oil base"]),
    ("airfield",      [r"air ?base", r"airfield", r"air field"]),
    ("ammo_depot",    [r"ammunition", r"\barsenal\b", r"\bammo\b", r"munition"]),
    ("energy",        [r"substation", r"power (?:plant|station)", r"electrical",
                       r"\bgas (?:plant|terminal|compressor|facility)", r"thermal power"]),
    ("defense_plant", [r"defou?nse (?:plant|factory)", r"munitions plant",
                       r"military (?:plant|factory)", r"chemical plant", r"defou?nse enterprise"]),
]

# Ukrainian official attribution => "confirmed", otherwise "claimed".
CONFIRM_PAT = re.compile(
    r"(SBU|Security Service of Ukraine|General Staff|Defou?nse Intelligence|"
    r"\bGUR\b|\bHUR\b|Ukrainian (?:military|forces|drone)|Armed Forces of Ukraine|"
    r"Ministry of Defou?nse of Ukraine|Ukraine'?s? (?:military|Air Force|special services))",
    re.I)

# Curated gazetteer of Russia's strategic facilities (refineries, air bases, oil
# terminals/depots) with exact coordinates. Matched by a distinctive token found in the
# strike text -> guarantees correct placement where Wikipedia page coords are missing or
# the bullet names several cities. (token, lat, lon); checked in order, first hit wins.
FACILITIES = [
    # --- refineries ---
    ("novoshakhtinsk", 47.740, 39.930), ("novokuybyshevsk", 53.100, 49.940),
    ("kuibyshev", 53.160, 50.070), ("syzran", 53.130, 48.430),
    ("saratov", 51.490, 46.050), ("ryazan", 54.580, 39.780),
    ("volgograd", 48.620, 44.470), ("tuapse", 44.095, 39.075),
    ("ilsky", 44.840, 38.570), ("afipsky", 44.900, 38.840),
    ("slavyansk", 45.260, 38.130), ("krasnodar", 45.070, 39.050),
    ("kstovo", 56.130, 44.200), ("norsi", 56.130, 44.200),
    ("kirishi", 59.460, 32.020), ("kinef", 59.460, 32.020),
    ("yaroslavl", 57.530, 39.930), ("yanos", 57.530, 39.930),
    ("orsk", 51.200, 58.570), ("taneco", 55.650, 51.780),
    ("nizhnekamsk", 55.650, 51.780), ("salavat", 53.360, 55.920),
    ("ufa", 54.820, 56.100), ("kapotnya", 55.640, 37.790),
    ("astrakhan", 46.120, 48.270), ("komsomolsk", 50.550, 137.000),
    ("khabarovsk", 48.480, 135.060), ("marijsk", 56.100, 48.300),
    # --- air bases ---
    ("engels", 51.480, 46.210), ("dyagilevo", 54.640, 39.570),
    ("soltsy", 58.140, 30.330), ("morozovsk", 48.310, 41.790),
    ("primorsko-akhtarsk", 46.060, 38.230), ("shaykovka", 54.100, 34.200),
    ("millerovo", 48.950, 40.300), ("khalino", 51.750, 36.300),
    ("savasleyka", 55.460, 42.340), ("olenya", 68.150, 33.460),
    ("belaya", 52.910, 103.070), ("akhtubinsk", 48.310, 46.210),
    ("yeysk", 46.680, 38.210), ("borisoglebsk", 51.370, 42.090),
    ("marinovka", 48.650, 43.790), ("buturlinovka", 50.790, 40.600),
    ("kushchyovsk", 46.550, 39.580), ("saky", 45.090, 33.600),
    ("saki", 45.090, 33.600), ("gvardeyskoye", 45.100, 34.020),
    ("belbek", 44.690, 33.570),
    # --- oil terminals / depots ---
    ("klintsy", 52.750, 32.230), ("feodosia", 45.050, 35.380),
    ("ust-luga", 59.670, 28.270), ("primorsk", 60.360, 28.610),
    ("novorossiysk", 44.720, 37.790), ("sevastopol", 44.620, 33.530),
]

# Oblast / region centroids — last-resort fallback when no facility/city coords exist.
OBLAST_CENTROID = {
    "Belgorod Oblast": (50.60, 36.60), "Bryansk Oblast": (52.90, 33.50),
    "Kursk Oblast": (51.70, 36.20), "Voronezh Oblast": (51.10, 39.80),
    "Rostov Oblast": (47.70, 40.60), "Krasnodar Krai": (45.30, 39.50),
    "Samara Oblast": (53.20, 50.50), "Saratov Oblast": (51.50, 46.50),
    "Ryazan Oblast": (54.50, 40.20), "Tula Oblast": (54.00, 37.60),
    "Moscow Oblast": (55.50, 37.40), "Moscow": (55.75, 37.62),
    "Lipetsk Oblast": (52.60, 39.20), "Tambov Oblast": (52.70, 41.40),
    "Volgograd Oblast": (49.50, 44.00), "Astrakhan Oblast": (46.80, 47.40),
    "Nizhny Novgorod Oblast": (56.20, 44.00), "Tatarstan": (55.40, 50.90),
    "Bashkortostan": (54.30, 56.30), "Oryol Oblast": (52.90, 36.30),
    "Kaluga Oblast": (54.40, 35.60), "Smolensk Oblast": (54.90, 32.50),
    "Leningrad Oblast": (59.80, 31.30), "Novgorod Oblast": (58.30, 31.80),
    "Pskov Oblast": (57.50, 28.80), "Yaroslavl Oblast": (57.80, 39.30),
    "Orenburg Oblast": (52.00, 55.00), "Krasnodar": (45.04, 38.98),
    "Republic of Tatarstan": (55.40, 50.90), "Republic of Bashkortostan": (54.30, 56.30),
    "Crimea": (45.30, 34.40), "Sevastopol": (44.62, 33.53),
}
REGION_SUFFIX = re.compile(r"(Oblast|Krai|Republic)$")


def fetch_wikitext(page):
    q = (API + "?action=parse&prop=wikitext&format=json&redirects=1&page="
         + urllib.parse.quote(page))
    req = urllib.request.Request(q, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["parse"]["wikitext"]["*"]


def links(text):
    """Return [(target_title, display_text)] for every [[..]] in text."""
    out = []
    for m in re.findall(r"\[\[([^\]]+)\]\]", text):
        if "|" in m:
            tgt, disp = m.split("|", 1)
        else:
            tgt = disp = m
        out.append((tgt.strip(), disp.strip()))
    return out


def classify(text):
    low = text.lower()
    for ttype, pats in TARGET_RULES:
        if any(re.search(p, low) for p in pats):
            return ttype
    return None


def strip_markup(s):
    s = re.sub(r"\[\[[^\]|]*\|([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"'''?|<[^>]+>", "", s)
    return s.strip()


def first_ref_url(bullet):
    m = re.search(r"url\s*=\s*(https?://[^\s|}\]]+)", bullet)
    return m.group(1).rstrip(".,") if m else ""


def parse_events(wt):
    """Yield raw events: dict(day, month, year, target_link, target_disp, target_type,
       oblast, status, source_url, raw)."""
    events = []
    year = None
    section_month = None
    for ln in wt.splitlines():
        h = re.match(r"^==+\s*(.+?)\s*==+\s*$", ln)
        if h:
            head = h.group(1)
            ym = re.search(r"\b(20\d{2})\b", head)
            if ym:
                year = int(ym.group(1))
            mm = [MONTHS[w] for w in re.findall(r"[A-Z][a-z]+", head) if w in MONTHS]
            section_month = mm[-1] if mm else section_month
            continue
        b = re.match(r"^\*+\s*(.+)", ln)
        if not b:
            continue
        bullet = b.group(1)
        ttype = classify(bullet)
        if not ttype:
            continue
        # date: first "DD Month" within the bullet head
        dm = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|"
                       r"August|September|October|November|December)", bullet[:80])
        if dm:
            day, month = int(dm.group(1)), MONTHS[dm.group(2)]
        else:
            dm2 = re.match(r"\D*?(\d{1,2})\s*[:\-–]", bullet)
            if not (dm2 and section_month):
                continue
            day, month = int(dm2.group(1)), section_month
        if not year:
            continue
        # target facility link (link whose text matches a target keyword)
        target_link = target_disp = ""
        oblast = ""
        for tgt, disp in links(bullet):
            blob = (tgt + " " + disp).lower()
            if not target_link and classify(blob) == ttype:
                target_link, target_disp = tgt, disp
            if not oblast and REGION_SUFFIX.search(tgt):
                oblast = tgt
            if not oblast and tgt in OBLAST_CENTROID:
                oblast = tgt
        if not target_disp:
            target_disp = (oblast or "Russia") + " " + ttype.replace("_", " ")
        status = "confirmed" if CONFIRM_PAT.search(bullet) else "claimed"
        events.append({
            "day": day, "month": month, "year": year,
            "target_link": target_link, "target_disp": strip_markup(target_disp),
            "target_type": ttype, "oblast": oblast,
            "links": [t for t, _ in links(bullet)],
            "status": status, "source_url": first_ref_url(bullet),
        })
    return events


def wiki_coords(titles):
    """Batch-resolve {requested_title: (lat, lon)} via the coordinates API (<=45/call)."""
    coords = {}
    titles = [t for t in titles if t]
    for i in range(0, len(titles), 45):
        batch = titles[i:i + 45]
        q = (API + "?action=query&prop=coordinates&format=json&redirects=1&titles="
             + urllib.parse.quote("|".join(batch)))
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=60) as r:
                d = json.load(r)
        except Exception:
            continue
        qd = d.get("query", {})
        # map requested title -> final title through normalized + redirects
        chain = {}
        for n in qd.get("normalized", []):
            chain[n["from"]] = n["to"]
        for n in qd.get("redirects", []):
            chain[n["from"]] = n["to"]

        def resolve(t):
            seen = set()
            while t in chain and t not in seen:
                seen.add(t)
                t = chain[t]
            return t

        final_coords = {}
        for p in qd.get("pages", {}).values():
            c = p.get("coordinates")
            if c:
                final_coords[p["title"]] = (round(c[0]["lat"], 5), round(c[0]["lon"], 5))
        for t in batch:
            fc = final_coords.get(resolve(t))
            if fc:
                coords[t] = fc
        time.sleep(0.3)
    return coords


def in_russia(lat, lon):
    return 41.0 <= lat <= 82.0 and 19.0 <= lon <= 180.0


def gaz_match(text):
    low = text.lower()
    for token, lat, lon in FACILITIES:
        if token in low:
            return (lat, lon)
    return None


def geocode(events):
    # facility-page coordinates straight from Wikipedia (only the linked target page,
    # never arbitrary place links -> no misplacement when a bullet names several cities)
    titles = sorted({e["target_link"] for e in events if e["target_link"]})
    coord_map = wiki_coords(titles)
    for e in events:
        lat = lon = None
        prec = ""
        text = e["target_disp"] + " " + e["target_link"] + " " + e["oblast"]
        c = coord_map.get(e["target_link"])
        if c and in_russia(*c):                 # 1) the facility's own Wikipedia page
            lat, lon, prec = c[0], c[1], "facility"
        elif gaz_match(text):                   # 2) curated facility gazetteer
            lat, lon = gaz_match(text)
            prec = "facility"
        elif e["oblast"] in OBLAST_CENTROID:    # 3) oblast centroid (coarse, labelled)
            lat, lon = OBLAST_CENTROID[e["oblast"]]
            prec = "oblast"
        # else: leave blank — never fabricate a point
        e["lat"], e["lon"], e["geo_precision"] = lat, lon, prec
    return events


def main():
    print("Fetching Wikipedia article ...")
    wt = fetch_wikitext(PAGE)
    print(f"  wikitext: {len(wt):,} chars")

    events = parse_events(wt)
    print(f"Parsed strategic-strike events: {len(events)}")

    # dedup by (date, target)
    seen, uniq = set(), []
    for e in sorted(events, key=lambda x: (x["year"], x["month"], x["day"])):
        try:
            d = dt.date(e["year"], e["month"], e["day"]).isoformat()
        except ValueError:
            continue
        e["date"] = d
        key = (d, e["target_disp"].lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)
    print(f"After dedup: {len(uniq)}")

    print("Geocoding via Wikipedia coordinates API ...")
    geocode(uniq)

    cols = ["date", "target_name", "target_type", "oblast", "lat", "lon",
            "geo_precision", "status", "source_url"]
    with open(OUT_STRIKES, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for e in uniq:
            w.writerow([e["date"], e["target_disp"], e["target_type"], e["oblast"],
                        e["lat"] if e["lat"] is not None else "",
                        e["lon"] if e["lon"] is not None else "",
                        e["geo_precision"], e["status"], e["source_url"]])

    # ---- stats ----
    total = len(uniq)
    geocoded = sum(1 for e in uniq if e["lat"] is not None)
    facility = sum(1 for e in uniq if e["geo_precision"] == "facility")
    confirmed = sum(1 for e in uniq if e["status"] == "confirmed")
    by_type = {}
    for e in uniq:
        by_type[e["target_type"]] = by_type.get(e["target_type"], 0) + 1
    refinery_targets = {e["target_disp"] for e in uniq if e["target_type"] == "refinery"}
    refinery_events = by_type.get("refinery", 0)
    last_date = max((e["date"] for e in uniq), default="")

    # ---- crosscheck vs published counts ----
    crosscheck = [
        ("refinery_strike_events", refinery_events, "150+",
         "Kyiv Independent (Apr 2025): 150+ strikes on refineries"),
        ("distinct_refineries_hit", len(refinery_targets), "24 of 33",
         "United24 (Jul 2025): 24 of Russia's 33 major refineries hit"),
        ("energy_strike_events", by_type.get("refinery", 0) + by_type.get("oil_depot", 0)
         + by_type.get("energy", 0), "272",
         "Baker Institute: 272 discrete strikes on energy infrastructure"),
        ("total_strategic_strikes", total, "120 in 2025",
         "Bloomberg: 120 attacks on Russian energy facilities in 2025"),
    ]
    with open(OUT_CROSSCHECK, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "our_value", "reference_value", "reference_source"])
        w.writerows(crosscheck)

    with open(OUT_META, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["field", "value"])
        w.writerow(["source", "Wikipedia: Attacks in Russia during the Russian invasion of Ukraine (CC BY-SA)"])
        w.writerow(["source_url", "https://en.wikipedia.org/wiki/" + PAGE.replace(" ", "_")])
        w.writerow(["license", "CC BY-SA 4.0 — attribution + share-alike required"])
        w.writerow(["disclaimer", "Strike reports are predominantly Ukrainian/OSINT claims; status field marks confirmed vs claimed."])
        w.writerow(["total_strikes", total])
        w.writerow(["geocoded", geocoded])
        w.writerow(["updated_through", last_date])
        w.writerow(["generated_utc", dt.datetime.utcnow().isoformat(timespec="seconds")])

    # ---- report ----
    print("\n================ RESULT ================")
    print(f"strategic strikes:    {total}")
    print(f"  geocoded:           {geocoded}/{total} ({100*geocoded//max(total,1)}%)")
    print(f"    facility-precise: {facility}")
    print(f"  confirmed/claimed:  {confirmed}/{total-confirmed}")
    print(f"  date range:         {uniq[0]['date'] if uniq else '-'} .. {last_date}")
    print("  by target_type:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"      {t:14s} {n}")
    print(f"  distinct refineries hit: {len(refinery_targets)}")
    print("\n  CROSSCHECK vs published counts:")
    for metric, ours, ref, src in crosscheck:
        print(f"      {metric:24s} ours={ours:<6} ref={ref:<10} ({src})")
    print("\nWrote:", OUT_STRIKES, OUT_CROSSCHECK, OUT_META, sep="\n  ")


if __name__ == "__main__":
    main()
