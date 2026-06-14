# Strategic strikes — data, model & metrics

Ukrainian strikes on strategic targets **inside Russia** (refineries, oil depots, air bases,
ammunition depots, energy/defence facilities) — for a map on Azure + counting metrics.

## Source & credibility (must be shown on the page)
- **Wikipedia — "Attacks in Russia during the Russian invasion of Ukraine"** (CC BY-SA).
  Fetched via the MediaWiki API (no key, CI-friendly). Each strike is a dated entry with
  wikilinks to the target / oblast and `<ref>` news sources, so every row keeps a `source_url`.
- **Coordinates** come from each facility's own Wikipedia page, then from a curated
  gazetteer of ~50 known Russian strategic facilities (refineries / air bases / terminals).
  Points are **never** placed from arbitrary city mentions → no misplacement.
- **Bias / completeness (be honest on the page):** strike reports are predominantly
  Ukrainian / OSINT claims — the `status` field marks **confirmed vs claimed**. The
  Wikipedia article is a curated *highlights* list, so the dataset is a **verified lower
  bound**, like the equipment "visually-confirmed" count. `strikes_crosscheck.csv` shows
  our totals against published counts (Baker Institute, United24, Kyiv Independent) so the
  gap is auditable, not hidden.

## What was built
- `build_strikes.py` — ETL (stdlib only, no deps). Outputs (powerbi/):
  - `strategic_strikes.csv` — fact: `date, target_name, target_type, oblast, lat, lon, geo_precision, status, source_url`.
  - `strikes_crosscheck.csv` — `metric, our_value, reference_value, reference_source`.
  - `strikes_meta.csv` — attribution / disclaimer / totals / `updated_through`.
- **Auto-update:** added to `frontline_autoupdate/` — the daily GitHub Action (04:30 UTC)
  now also runs `build_strikes.py` and commits the three CSVs. No GDELT, no key, no secrets.

## Load the table (open the `.pbip`; the name must match exactly)
Get Data → Text/CSV → `strategic_strikes`. Set data types:
- `date` → **Date** (this is what links to Calendar)
- `lat`, `lon` → **Decimal number**
- `target_type`, `status`, `oblast`, `geo_precision` → **Text**
- `source_url` → Text (tooltip only)

## Map on Azure (no Deneb)
Use the native **Azure Maps** visual: drag `lat` → Latitude, `lon` → Longitude,
`target_type` → Legend (bubble colour), `target_name` → Tooltip, slice by `Calendar`.
Only rows with coordinates render; the metrics below still count every strike.

## Model — relationship (time is the only honest shared axis)
Single relationship, single-direction, 1-to-many:
```
Calendar[Date]  →  strategic_strikes[date]
```
⚠️ **Do not** link `lat`/`lon`/`oblast` to any other table — a strike location is *where it
was hit in Russia*, a casualty's region is *home region*: different meaning → false join.
Needs Power BI **open** (done via the Power BI MCP / TOM, same as the other tables).

## Metrics (DAX measures — display folder `05 Strikes`)
Measures, not calculated columns (nothing materialises → the model stays light):

```DAX
Total Strikes        = COUNTROWS ( strategic_strikes )
Confirmed Strikes    = CALCULATE ( [Total Strikes], strategic_strikes[status] = "confirmed" )
Claimed Strikes      = CALCULATE ( [Total Strikes], strategic_strikes[status] = "claimed" )
% Confirmed          = DIVIDE ( [Confirmed Strikes], [Total Strikes] )

Refinery Strikes     = CALCULATE ( [Total Strikes], strategic_strikes[target_type] = "refinery" )
Airfield Strikes     = CALCULATE ( [Total Strikes], strategic_strikes[target_type] = "airfield" )
Oil Depot Strikes    = CALCULATE ( [Total Strikes], strategic_strikes[target_type] = "oil_depot" )
Energy Strikes       = CALCULATE ( [Total Strikes], strategic_strikes[target_type] = "energy" )
Ammo Depot Strikes   = CALCULATE ( [Total Strikes], strategic_strikes[target_type] = "ammo_depot" )

Distinct Refineries Hit =
    CALCULATE ( DISTINCTCOUNT ( strategic_strikes[target_name] ),
                strategic_strikes[target_type] = "refinery" )

Mapped Strikes       = CALCULATE ( [Total Strikes], NOT ( ISBLANK ( strategic_strikes[lat] ) ) )

Last Strike Date     = MAX ( strategic_strikes[date] )
Days Since Last Strike = DATEDIFF ( [Last Strike Date], TODAY (), DAY )

Strikes Cumulative =
    CALCULATE ( [Total Strikes],
                FILTER ( ALL ( 'Calendar' ), 'Calendar'[Date] <= MAX ( 'Calendar'[Date] ) ) )

Strikes MoM % =
    VAR Cur  = [Total Strikes]
    VAR Prev = CALCULATE ( [Total Strikes], DATEADD ( 'Calendar'[Date], -1, MONTH ) )
    RETURN DIVIDE ( Cur - Prev, Prev )
```
`Strikes Cumulative` / `Strikes MoM %` require the Calendar relationship above.

## Performance ("won't lag")
- The table is tiny (~hundreds of rows) → negligible vs `casualties`/`equipment_losses`.
- Low-cardinality text (`target_type`, `status`, `oblast`) compresses well in VertiPaq.
- Counting via measures, not calc columns; one single-direction relationship; no bi-di.
- The map draws only a few hundred points (unlike 14k equipment points) → smooth.
- Biggest model-wide lever is still `casualties` cardinality (hide/keep-as-is the slug/name
  text columns), not this table.
</content>
</invoke>
