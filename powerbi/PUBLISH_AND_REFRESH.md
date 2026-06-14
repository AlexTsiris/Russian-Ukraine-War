# Publishing & Auto-Refresh (Variant 1 — Web connector)

This is the one place that ties the whole automation together: load every table from
**raw GitHub URLs**, set a **scheduled refresh** in the Power BI Service, and **publish
to web** so the public always sees current data.

> Why the Web connector and not a local CSV import? Local-file import needs a gateway to
> refresh in the cloud, and legacy CSV import is being deprecated (after 2026-07-31).
> Loading from a public URL is **gateway-less** — the Service refreshes it on a schedule
> by itself.

Repo: <https://github.com/AlexTsiris/Russian-Ukraine-War> · branch `main`.
Raw URL pattern:
`https://raw.githubusercontent.com/AlexTsiris/Russian-Ukraine-War/main/powerbi/<file>`

---

## Step 1 — Push the project to GitHub

```bash
cd "<this project folder>"
git init
git add .
git commit -m "Open-source war analytics dashboard"
git branch -M main
git remote add origin https://github.com/AlexTsiris/Russian-Ukraine-War.git
git push -u origin main
```

`.gitignore` keeps the large raw files, the `.pbix`, and `powerbi/lib/` out; the small
published tables under `powerbi/` are committed and become the data feed.

## Step 2 — Re-point each table to its Web URL (Power BI Desktop)

For every table below: **Transform data → select the query → Source step (gear) →** if it
was a local file, replace the source with **Web** and paste the raw URL. (Or **Get Data →
Web → paste URL** for a fresh query, then rename it to the exact table name.)

| Power BI table | Raw URL (append to the pattern above) |
|----------------|----------------------------------------|
| `casualties` | `powerbi/casualties.csv` |
| `regions` | `powerbi/regions.csv` |
| `settlements` | `powerbi/settlements.csv` |
| `equipment_losses` | `powerbi/equipment_losses.csv` |
| `equipment_by_type` | `powerbi/equipment_by_type.csv` |
| `equipment_by_month` | `powerbi/equipment_by_month.csv` |
| `equipment_crosscheck` | `powerbi/equipment_crosscheck.csv` |
| `equipment_meta` | `powerbi/equipment_meta.csv` |
| `frontline_history` | `powerbi/frontline_history.csv` |
| `frontline_meta` | `powerbi/frontline_meta.csv` |

Example full URL:
`https://raw.githubusercontent.com/AlexTsiris/Russian-Ukraine-War/main/powerbi/casualties.csv`

Notes:
- Keep column types as set (Power Query may re-detect — verify `death_date` stays Date and
  `lat`/`lon` stay Decimal). The model relationships (Calendar, etc.) are rebuilt by
  `create_calendar.py`; re-run it after the model loads if relationships drop.
- The **Deneb maps** read GeoJSON directly by URL, not as a table. In each Deneb spec set
  the URL to
  `https://raw.githubusercontent.com/AlexTsiris/Russian-Ukraine-War/main/powerbi/frontline.geojson`
  (see `FRONTLINE_SETUP.md`). The inline spec needs no URL.

## Step 3 — Publish & schedule refresh (Power BI Service)

1. **Publish:** Desktop → **Home → Publish** → pick a workspace.
2. In the Service: **workspace → the semantic model → Settings → Data source credentials.**
   Each Web source: **Authentication = Anonymous**, **Privacy = Public**. Sign in if asked.
3. **Scheduled refresh:** same Settings page → **Refresh → On** → add a daily time
   (e.g. 06:00, after the frontline Action's 04:30 UTC commit). No gateway is required for
   public Web URLs.
4. **Publish to web:** **report → File → Embed report → Publish to web (public)** → copy the
   public link / embed code for LinkedIn.

> Publish-to-web makes the report **fully public** — only use it with data meant to be
> public (which this is). It refreshes from the cached dataset, so the scheduled refresh in
> step 3 is what keeps the public view current.

## How "current" each piece stays

| Piece | Mechanism | Latency |
|-------|-----------|---------|
| Frontline map (Deneb) | reads `frontline.geojson` by URL on render | live (daily commit) |
| `frontline_history` / equipment / casualty tables | Web connector + scheduled refresh | daily |
| `frontline.geojson` itself | GitHub Action `frontline_autoupdate/` | daily 04:30 UTC |

Casualty/equipment table freshness depends on re-running the local ETL and pushing
(those sources aren't auto-scraped here). To automate them too, replicate the
`frontline_autoupdate/` GitHub Action pattern for `build_equipment.py` and the casualty
scripts.
