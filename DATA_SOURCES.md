# Data Sources & Attribution

This project combines **three independent, verifiable data sources**. The guiding
principle is simple: *several independent sources → cross-verification → one
unbiased count.* Every figure is a **verified lower bound**, never an estimate of
the "true total," and the provenance of each number is stated on the dashboard.

All data is redistributed here for **educational, non-commercial research** only,
**with attribution**, under each source's own terms. None of the source projects
endorse this analysis.

---

## 1. Human cost — Mediazona & BBC News Russian ("Russia 200")

- **What:** Named, individually source-verified Russian military deaths in the war
  against Ukraine (obituaries, regional media, official statements, cemetery records).
- **Where:** <https://200.zona.media/>
- **Used for:** `casualties.csv`, `regions.csv`, `settlements.csv`.
- **How obtained:** the public list (`urls.json`) and per-record API
  (`/api/case/<slug>`) on the project's CDN; regional settlement counts from the
  open per-region CDN files. See `download_list.py`, `fetch_all.py`, `geo_regions.py`.
- **Nature of the figure:** a **confirmed, named lower bound** (~225,000), well below
  independent statistical estimates of *total* losses (~350,000). It is **not** the
  total number of Russian dead.
- **Attribution:** Data © **Mediazona & BBC News Russian** ("Russia 200").
- **Terms:** Educational / public-interest use with attribution. Names are retained
  because they are already public and verifiable; the subject matter concerns real
  human deaths and is presented with corresponding care.

## 2. Frontline / occupied territory — DeepStateMap.live

- **What:** Russian-occupied territory of Ukraine over time (monthly snapshots).
- **Where:** <https://deepstatemap.live/>  (Ukrainian OSINT; memorandum with Ukraine's MoD).
- **Used for:** `frontline_history.csv`, `frontline.geojson`, `frontline_meta.csv`,
  the Deneb occupation map.
- **How obtained:** historical snapshots (2022-04 … 2024-06) via the still-open
  per-id endpoint `/api/history/<id>/geojson` (id list recovered from the Wayback
  Machine); recent months (2024-07 … today) from the open GPL mirror
  [`cyterat/deepstate-map-data`](https://github.com/cyterat/deepstate-map-data).
  See `powerbi/build_frontline.py`.
- **Nature of the figure:** Ukrainian OSINT; Russian sources are not included;
  accuracy is not guaranteed; a ~2–3 day delay. Cross-checked against the mirror
  (areas agree to ~0.3%).
- **Attribution:** Russian-occupied territory data © **DeepStateMap.live**.
- **Terms:** Educational / **non-commercial** use **with mandatory attribution**.
  The API is **not** redistributed to third parties. Commercial use requires written
  permission from DeepState. *(A courtesy notice to the DeepState team is recommended.)*

## 3. Equipment losses — WarSpotting + Oryx

- **What:** Visually-confirmed Russian equipment losses (photo/video only).
- **Where:** WarSpotting <https://ukr.warspotting.net/> · Oryx <https://www.oryxspioenkop.com/>
- **Used for:** `equipment_losses.csv`, `equipment_by_type.csv`,
  `equipment_by_month.csv`, `equipment_crosscheck.csv`, `equipment_meta.csv`,
  the Deneb equipment-loss map.
- **How obtained:** WarSpotting full history from the open MIT scrape mirror
  [`lazar-bit/automated-warspotting-scraper`](https://github.com/lazar-bit/automated-warspotting-scraper)
  (the public API returns only the last ~100 records); Oryx per-type totals from the
  machine-readable mirror [`scarnecchia/oryx_data`](https://github.com/scarnecchia/oryx_data),
  used as an **independent cross-check**. See `powerbi/build_equipment.py`.
- **Nature of the figure:** strictly visual confirmation ⇒ a conservative **lower
  bound**. Government claims (Russian or Ukrainian MoD) are **excluded**. The two
  trackers agree to within ~2%.
- **Attribution:** **WarSpotting** (ukr.warspotting.net) and **Oryx** (oryxspioenkop.com).
- **Terms:** Educational / non-commercial use with attribution. *(A courtesy notice
  to WarSpotting is recommended.)*

---

## Cross-verification summary

| Domain | Primary source | Independent check | Agreement |
|--------|----------------|-------------------|-----------|
| Equipment | WarSpotting | Oryx | ~2% |
| Frontline | own ETL (DeepState API) | `cyterat` GPL mirror | ~0.3% |
| Casualties (shares) | full named list | random sample (n=10,000, fixed seed) | <±1% |

See [`powerbi/METHODOLOGY_AND_LIMITATIONS.md`](powerbi/METHODOLOGY_AND_LIMITATIONS.md)
for the full methodology, the bias table, and how each limitation is handled.
