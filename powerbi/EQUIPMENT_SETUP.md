# Equipment losses — data, setup & the unified data model

Visually-confirmed Russian equipment losses, cross-checked across two independent trackers.

## Sources & credibility (must be shown on the page)
- **WarSpotting** (ukr.warspotting.net) — photo/video-confirmed losses with date, type, status, oblast, coordinates. Full history pulled from the open MIT mirror `lazar-bit/automated-warspotting-scraper` (its Action scrapes the public API daily; the public API itself only returns the latest ~100 records + aggregate counts).
- **Oryx** (oryxspioenkop.com) — the most-cited independent visually-confirmed tracker; per-type totals from the machine-readable mirror `scarnecchia/oryx_data`. Used as an **independent cross-check**.
- Both are **strictly visual confirmation → a conservative lower bound.** Government claims (either side) are **excluded** by design.

## Cross-check (the trust story)
Two independently-compiled photo-confirmed counts agree within ~2 %:

| Category | WarSpotting | Oryx |
|---|---|---|
| All types | 23,036 | 22,558 |
| Tanks | 4,029 | 4,103 |
| Armoured vehicles | 13,363 | 13,154 |

(Finer categories use different taxonomies, so only clean equivalents are compared.)

## What was built
- `build_equipment.py` — ETL (stdlib only, no deps). Outputs:
  - `equipment_losses.csv` — fact: `date, type, status, model, oblast, lat, lon` (23k rows, 2022-02-24 → present).
  - `equipment_by_month.csv` — `month, total, destroyed` (for the trend, Sum-friendly).
  - `equipment_by_type.csv` — `type, destroyed, damaged, abandoned, captured, total`.
  - `equipment_crosscheck.csv` — `category, warspotting, oryx`.
  - `equipment_meta.csv` — attribution + totals + `updated_through`.
- **Page "Equipment"** is pre-built (`add_equipment_page.py`): cards (WarSpotting total, Oryx cross-check, destroyed), losses-by-type bar, WarSpotting-vs-Oryx cross-check bar, losses-per-month trend, attribution. Does **not** touch other pages.
- **Auto-update:** added to `frontline_autoupdate/` (the daily GitHub Action now builds equipment too).

## Load the tables (open the `.pbip`, names must match exactly)
Get Data → Text/CSV for each: `equipment_meta`, `equipment_by_type`, `equipment_crosscheck`, `equipment_by_month` (keep `month` as **Text**), `equipment_losses` (keep `date` as **Date**). Until loaded, the Equipment page shows field errors.

## The unified data model — relationships (the project's core idea)
The honest way to join all our datasets is **TIME**. Build one shared **Calendar** dimension and relate the fact tables to it by date:

```
            Calendar[Date]
          /      |        \
 casualties   equipment    frontline_history
 [death_date] [date]       [snapshot_date]
   PEOPLE      MACHINES      TERRITORY
```

Then one date slicer / timeline drives people + machines + territory together — three independent sources, one picture.

⚠️ **Do not** link geography across datasets: a casualty's region = home region in Russia; an equipment loss location = where the vehicle was hit in Ukraine. Different meaning → a false relationship. Time is the only valid shared axis.

Creating the `Calendar` table + relationships needs Power BI **open** (done via the Power BI MCP / TOM). Steps:
1. Add a `Calendar` table (CALENDAR/CALENDARAUTO).
2. Relationships: `Calendar[Date]` → `equipment_losses[date]`, → `casualties[death_date]`, → `frontline_history[snapshot_date]` (single-direction, 1-to-many).
3. Use `Calendar[Date]`/`Calendar[Year-Month]` on shared timelines and slicers.
