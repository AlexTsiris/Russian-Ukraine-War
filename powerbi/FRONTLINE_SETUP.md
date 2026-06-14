# Frontline map (territorial control) — data, setup & licensing

A time-sliding map of Russian-occupied territory of Ukraine for the dashboard.

## What was built
- `build_frontline.py` — ETL. Produces:
  - `frontline_history.csv` — `snapshot_date, occupied_km2, wkt` — **46 monthly snapshots, 2022-09-30 → today**. One dissolved `MULTIPOLYGON` of occupied territory per date, geometry simplified to ~0.5 km (max WKT ≈ 22 KB). `occupied_km2` is a true **geodesic** area (spherical formula), not a flat approximation.
  - `frontline_meta.csv` — attribution + disclaimer + "updated through" date (one row, for the on-map caption).
  - `frontline.geojson` — same 46 snapshots as a single FeatureCollection (each feature: `date`, `occupied_km2` + geometry), ~400 KB — this is what the **Deneb** map reads.
  - `frontline_deneb_spec.json` — ready-to-paste Vega-Lite spec for the Deneb visual (replace `<<GEOJSON_URL>>`).
- **Two data sources, merged** (same extraction + validated to match within ~0.3 %):
  - **2022-09 .. 2024-06** — historical: snapshot ids recovered from the Wayback Machine archive of DeepState's `/api/history` list (the live list is now auth-gated), then each month's geometry pulled from the still-open per-id endpoint `…/api/history/<id>/geojson`. Cached in `frontline_cache_hist.csv`.
  - **2024-07 .. today** — from the open GPL mirror `github.com/cyterat/deepstate-map-data`.
- Occupied territory is extracted as: polygons whose status contains `occupied`/`cadr`/`calr` **and** whose centroid is inside Ukraine's bbox — this drops DeepState's satirical polygons ("Occupied East Prussia / Karelia / Kuril / Abkhazia" …).
- Sanity check / realism: ≈115k km² (autumn 2022) → dip after the Kherson withdrawal → slow rise to ≈117k (2024–2026). Latest ≈ **116,600 km² ≈ 19.3 % of Ukraine** — within published estimates.
- **Auto-update:** `frontline_autoupdate/` is a ready-to-push GitHub Actions pipeline that rebuilds the data daily and commits it; the Deneb map (reading the raw URL) then refreshes with no manual step. See `frontline_autoupdate/README.md`.
- Cache/temp files in `powerbi/` (regenerable, can be git-ignored): `ds_hist.geojson.gz`, `wb_hist.json`, `frontline_cache_hist.csv`.

## Source & credibility (must be shown on the page)
- **DeepStateMap.live** — Ukrainian OSINT project; memorandum with Ukraine's MoD (2024); cited by BBC, NYT, Kyiv Independent.
- Pulled from the open GPL-3.0 mirror `github.com/cyterat/deepstate-map-data` (daily snapshots + consolidated file) — **not** from DeepState's API directly.
- ⚠️ **Bias to disclose:** Russian sources are deliberately excluded; this is a Ukrainian-sourced assessment. Accuracy is not guaranteed by the source. Updates have an intentional 2–3 day delay.

## Licensing — how we stay compliant
DeepState's license (deepstatemap.live/license-en.html):
- ❌ Redistributing/proxying their **API** to third parties — we don't; we consume a static dataset.
- ❌ Creating "identical objects" / a competing live map — we don't; we show an attributed context layer.
- ✅ Commercial/non-commercial use of **content with attribution** (text reference, logo, or link) — we comply.
- **Required on the dashboard page:** visible text "Source: DeepStateMap.live" + link `https://deepstatemap.live` (already in `frontline_meta.csv`).
- This project is **educational / non-commercial**. Before any commercial use, email DeepState for written approval (their license requires it for commercial API use).

## The page is pre-built
`add_frontline_page.py` already created the **"Frontline"** page in the report (slicer, occupied-km² card, area-over-time trend, attribution, and a marked box for the Deneb map). Run it with Power BI **closed**, then open the `.pbip`. It does **not** touch the other pages. You still need the three manual steps below (load data, install Deneb, host GeoJSON) — until `frontline_history` is loaded the page shows field errors.

## Power BI assembly — Deneb (free, certified, no license)
The original free Icon Map was removed from AppSource (Mar 2025) and Icon Map **Pro** needs a paid/expiring license. We use **Deneb** (free, MIT, Microsoft-certified, publishable). It renders the polygon from an external GeoJSON and is filtered by a normal Power BI slicer.

**1. Host the GeoJSON at a public URL.** Deneb fetches geometry by URL. Put `frontline.geojson` on GitHub (a repo or a **Gist**) and copy its **raw** URL, e.g. `https://raw.githubusercontent.com/<you>/<repo>/main/frontline.geojson` (raw GitHub serves permissive CORS, works in the Service). Re-upload this file whenever you refresh the data.

**2. Load the tables (open the `.pbip`).** Get Data → Text/CSV → `frontline_history.csv` — set **`snapshot_date` = Text** (important: keep it text "YYYY-MM-DD" so it matches the GeoJSON key; do **not** let it auto-convert to Date). Load `frontline_meta.csv` too.

**3. Install Deneb.** Visualizations → **Get more visuals** → **"Deneb"** (by Daniel Marsh-Patrick). Add it to the page.

**4. Bind data & paste spec.**
   - Drag **`frontline_history[snapshot_date]`** into the Deneb **Values** well.
   - Open Deneb editor → set **Provider = Vega-Lite** → paste the contents of `frontline_deneb_spec.json`.
   - Replace both `<<GEOJSON_URL>>` placeholders with your raw URL from step 1.
   - If Deneb blocks the fetch: in Deneb settings turn on the option to **allow external/remote data URIs**.

**5. Time slider.** Add a **Slicer** on `frontline_history[snapshot_date]` (set to **Single select**). Stepping it redraws the front for that month — Deneb reacts to the slicer automatically.
   - For auto-play, install the **"Play Axis (Dynamic Slicer)"** custom visual and bind it to `snapshot_date`.

**6. Attribution caption (required).** A text box or Card showing `frontline_meta[attribution]` + the link — keep it visible.

**7. Optional companion.** A line chart of `occupied_km2` over `snapshot_date` ("occupied area over time").

### ⚠️ Important: keep the slicer on one date
With no selection the slicer passes all 46 dates → Deneb draws every month in red at once. Default the slicer to a single date / Single-select so exactly one month renders. (The faint grey layer in the spec is the all-months envelope; it only stabilises the zoom.)

### Quick win — no hosting (recommended to see it working now)
Use **`frontline_deneb_spec_inline.json`** (generated by `make_deneb_inline.py`, ~290 KB, geometry embedded). Steps:
1. Load `frontline_history.csv` (snapshot_date = **Text**) — needed so the slicer can drive the map.
2. Get more visuals → **Deneb** → drop it on the map box on the Frontline page.
3. Put `frontline_history[snapshot_date]` into Deneb's **Values**.
4. Deneb editor → Provider **Vega-Lite** → paste the whole `frontline_deneb_spec_inline.json`.
5. Set the date slicer to a single date → the front for that month appears; move it to animate.

This is self-contained (no URL, no GitHub). The trade-off: it doesn't auto-update — re-run `make_deneb_inline.py` and re-paste when you refresh data. For hands-off auto-update, switch to the hosted URL spec (`frontline_deneb_spec.json`) + `frontline_autoupdate/`.

## Refresh ("update on Refresh")
- Re-run `python build_frontline.py --refresh` → re-downloads the latest archive (updated daily ~03:00 UTC) and rebuilds the CSVs **and `frontline.geojson`**. Then: re-upload `frontline.geojson` to the same URL, and **Refresh** in Power BI for the tables. (Deneb re-reads the URL on render.)
- Fully in-app option: **Get Data → Python script** and paste the ETL, so Power BI's Refresh runs it directly. Note: Python-in-Power-Query needs Python configured locally, and in the Power BI **Service** it requires a **personal data gateway** (Python isn't supported by the standard gateway). For a portfolio report, the simplest reliable path is: run the script, then Refresh.

## Known limitation
- Series starts **2022-09**. DeepState's earlier open GeoJSON (Feb–Aug 2022) drew only active-front annotations, **not** a full filled control area (Crimea + Donbas weren't rendered as polygons), so a complete monthly total isn't reconstructable before ~Sept 2022. Snapshots whose area is implausibly small (< 80,000 km²) are dropped automatically by the ETL. The dramatic spring-2022 surge and the autumn-2022 Kharkiv/Kherson losses are therefore only partially captured (the series opens just after, at the ~112k peak).
