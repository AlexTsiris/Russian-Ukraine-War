# Russia–Ukraine War — Open-Source Analytics Dashboard

An independent, **non-partisan** Power BI dashboard that combines **three independent,
verifiable data sources** to tell the human and material story of Russia's war against
Ukraine. The guiding principle:

> **Several independent sources → cross-verification → one unbiased count.**

Every number shown is a **verified lower bound** — confirmed, named, or photo-confirmed
— never an unverifiable estimate. Honesty over impact: "Unknown" is shown explicitly,
recent months are flagged as provisional, and the source of every figure is stated.

> ⚠️ This is an educational / portfolio project. It is not endorsed by any of the data
> sources. The subject matter concerns real human deaths and is presented with care.

---

## What's inside

| Page | Question it answers | Source |
|------|---------------------|--------|
| **Overview / Demographics / Timeline / Geography / In Context / Force Composition** | Who Russia's confirmed war dead were, when and where they died, and how the toll compares to past wars | Mediazona & BBC "Russia 200" |
| **Frontline** | How Russian-occupied territory of Ukraine has shifted, month by month (with a date slider) | DeepStateMap.live |
| **Equipment** + **Equipment Map** | Visually-confirmed Russian equipment losses, by type and over time, mapped to where they were hit | WarSpotting + Oryx |
| **Strategic Strikes** | Ukrainian strikes on strategic targets inside Russia (refineries, air bases, depots), mapped over time | Wikipedia (CC BY-SA) |

Maps use the free **Deneb** custom visual (Vega-Lite) for the frontline/equipment, and the
native **Azure Maps** visual for strategic strikes. Cross-source checks: equipment
WarSpotting vs Oryx agree to ~2%; the frontline ETL vs the GPL mirror agree to ~0.3%;
casualty category shares are validated against a fixed-seed random sample (±<1%); strike
counts are cross-checked against published tallies (`powerbi/strikes_crosscheck.csv`).

## Repository layout

```
.
├── .github/workflows/update.yml   # Daily GitHub Action: rebuilds all public tables
├── *.py                      # Casualty-data collection & prep (root)
│   ├── download_list.py       #   1. download the named list
│   ├── fetch_all.py           #   2. fetch each record (resumable, polite)
│   ├── build_powerbi.py       #   3. build the English Power BI tables
│   ├── geo_regions.py         #   regional / settlement geography
│   └── analyze.py, sample_api.py, ...
├── powerbi/
│   ├── *.csv, *.geojson, *.json   # Published tables that feed the dashboard
│   ├── build_frontline.py / build_equipment.py    # Frontline & equipment ETL
│   ├── build_strikes.py            # Strategic-strikes ETL (Wikipedia)
│   ├── build_casualties_geo.py     # Casualties geography ETL (Mediazona CDN)
│   ├── build_report_pages.py / add_*_page.py      # Report page generators (PBIR)
│   ├── create_*.py / pbi_mcp_server.py            # Model build via TOM
│   ├── wb_hist.json, frontline_cache_hist.csv     # Frontline history caches (Action reads these)
│   └── *_SETUP.md, METHODOLOGY_AND_LIMITATIONS.md, DAX_MEASURES.md
├── DATA_SOURCES.md            # Full attribution & terms for every source
├── LICENSE                    # MIT (code only — not the data)
└── README.md
```

The **published data tables** under `powerbi/` are committed so the public dashboard can
read them. The daily GitHub Action (`.github/workflows/update.yml`) runs the four cloud-safe
ETL scripts and commits the refreshed tables back to `powerbi/`. Large raw/intermediate files
and binaries are **not** committed — see [`.gitignore`](.gitignore). Rebuild from the scripts (below).

## Rebuilding the data

```bash
pip install requests pandas shapely        # core deps
# 1) Casualties
python download_list.py                     # -> data/urls.json, data/list.csv
python fetch_all.py                         # -> data/all_cases.jsonl (resumable)
python geo_regions.py                       # -> data/settlements.csv, regions_summary.csv
python build_powerbi.py                     # -> powerbi/casualties.csv, regions.csv, settlements.csv
# 2) Frontline, equipment, strikes & casualties geography (all cloud-safe, run by the Action)
python powerbi/build_frontline.py           # -> powerbi/frontline_*.csv, frontline.geojson
python powerbi/build_equipment.py           # -> powerbi/equipment_*.csv
python powerbi/build_strikes.py             # -> powerbi/strategic_strikes.csv, strikes_*.csv
python powerbi/build_casualties_geo.py      # -> powerbi/regions.csv, settlements.csv
```

Then open `powerbi/powerbi_analyse.pbip` in Power BI Desktop. The model-build helpers
(`powerbi/create_*.py`, `pbi_mcp_server.py`) talk to a **running** Power BI Desktop via
TOM and require the Microsoft AMO/TOM client libraries in `powerbi/lib/` (not committed —
install locally).

## Keeping the public dashboard current (automation)

- **The daily Action** ([`.github/workflows/update.yml`](.github/workflows/update.yml)) runs
  at 04:30 UTC, rebuilds frontline + equipment + strikes + casualties geography, and commits
  the refreshed tables back to `powerbi/`.
- **Maps (Deneb / Azure Maps):** read `frontline.geojson` / coordinates by URL on every
  render — update with **no Power BI refresh** once the Action commits.
- **Tables (CSV):** loaded into Power BI via **Get Data → Web** from the raw GitHub URLs,
  with a **scheduled refresh** in the Power BI Service, then **publish to web**. See
  [`powerbi/PUBLISH_AND_REFRESH.md`](powerbi/PUBLISH_AND_REFRESH.md),
  [`powerbi/FRONTLINE_SETUP.md`](powerbi/FRONTLINE_SETUP.md),
  [`powerbi/EQUIPMENT_SETUP.md`](powerbi/EQUIPMENT_SETUP.md) and
  [`powerbi/STRIKES_SETUP.md`](powerbi/STRIKES_SETUP.md).

## Sources & methodology

- **Attribution and terms for every source:** [`DATA_SOURCES.md`](DATA_SOURCES.md)
- **Methodology, bias handling, statistical principles:**
  [`powerbi/METHODOLOGY_AND_LIMITATIONS.md`](powerbi/METHODOLOGY_AND_LIMITATIONS.md)

Data © Mediazona & BBC News Russian, DeepStateMap.live, WarSpotting, and Oryx —
redistributed for educational, non-commercial research with attribution. Code is MIT.
