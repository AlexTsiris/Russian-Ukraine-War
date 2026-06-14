# -*- coding: utf-8 -*-
"""
Geography of the dead from the open CDN files of the "Russia 200" project (no API).
Downloads the per-region files regions/<Region>.csv.br and builds:
  * data/settlements.csv  — region, settlement, coordinates, number of dead
  * data/regions_summary.csv — totals by region

These are the authoritative numbers: exactly what the map on 200.zona.media shows.
The r field in the source files = the number of confirmed dead from that settlement.
"""

import csv
import io
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "data")
BASE = "https://s3.zona.media/infographics/g200w/regions"
HEADERS = {"User-Agent": "Mozilla/5.0 (research; casualties analytics)"}

# Full list of regions (the keys from the 200.zona.media app)
REGIONS = [
    "Москва", "Санкт-Петербург", "Республика Адыгея", "Республика Алтай",
    "Алтайский край", "Амурская область", "Архангельская область",
    "Астраханская область", "Республика Башкортостан", "Белгородская область",
    "Брянская область", "Республика Бурятия", "Воронежская область",
    "Владимирская область", "Волгоградская область", "Вологодская область",
    "Республика Дагестан", "Еврейская автономная область", "Забайкальский край",
    "Ивановская область", "Иркутская область", "Республика Ингушетия",
    "Кабардино-Балкарская Республика", "Калининградская область",
    "Республика Калмыкия", "Калужская область", "Камчатский край",
    "Республика Карачаево-Черкесия", "Республика Карелия", "Кемеровская область",
    "Кировская область", "Республика Коми", "Костромская область",
    "Краснодарский край", "Красноярский край", "Курганская область",
    "Курская область", "Ленинградская область", "Липецкая область",
    "Магаданская область", "Республика Марий Эл", "Московская область",
    "Республика Мордовия", "Мурманская область", "Ненецкий автономный округ",
    "Новосибирская область", "Нижегородская область", "Новгородская область",
    "Омская область", "Оренбургская область", "Орловская область",
    "Пензенская область", "Пермский край", "Псковская область",
    "Приморский край", "Ростовская область", "Рязанская область",
    "Самарская область", "Саратовская область", "Сахалинская область",
    "Свердловская область", "Республика Северная Осетия-Алания",
    "Смоленская область", "Ставропольский край", "Тамбовская область",
    "Республика Татарстан", "Тверская область", "Томская область",
    "Тульская область", "Республика Тыва", "Тюменская область",
    "Удмуртская Республика", "Ульяновская область", "Хабаровский край",
    "Республика Хакасия", "Ханты-Мансийский автономный округ - Югра",
    "Челябинская область", "Чеченская Республика", "Чувашская Республика",
    "Чукотский автономный округ", "Республика Саха (Якутия)",
    "Ямало-Ненецкий автономный округ", "Ярославская область", "Байконур",
    "Республика Крым", "Севастополь", "ДНР", "ЛНР",
]


def filename(region):
    """How the app builds the filename: remove brackets, spaces -> '_'."""
    return region.replace("(", "").replace(")", "").replace(" ", "_") + ".csv.br"


def fetch_region(region):
    url = f"{BASE}/{urllib.parse.quote(filename(region))}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    settlements = []     # (region, settlement, lat, lon, count, district)
    region_totals = []   # (region, settlements_count, deaths)
    failed = []

    for i, region in enumerate(REGIONS, 1):
        try:
            text = fetch_region(region)
        except Exception as e:
            failed.append((region, str(e)))
            print(f"  [{i}/{len(REGIONS)}] {region}: ERROR {e}")
            continue

        reader = csv.DictReader(io.StringIO(text))
        total = 0
        n = 0
        for row in reader:
            try:
                cnt = int(row.get("r") or 0)
            except ValueError:
                cnt = 0
            total += cnt
            n += 1
            settlements.append({
                "region": region,
                "settlement": row.get("display_name", ""),
                "lat": row.get("lat", ""),
                "lon": row.get("lon", ""),
                "deaths": cnt,
                "district": row.get("district", ""),
            })
        region_totals.append({
            "region": region, "settlements": n, "deaths": total
        })
        print(f"  [{i}/{len(REGIONS)}] {region}: {n} settlements, {total:,} dead")
        time.sleep(0.2)  # be polite to the CDN

    # save
    with open(os.path.join(OUT_DIR, "settlements.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["region", "settlement", "lat",
                                          "lon", "deaths", "district"])
        w.writeheader()
        w.writerows(settlements)

    region_totals.sort(key=lambda x: x["deaths"], reverse=True)
    with open(os.path.join(OUT_DIR, "regions_summary.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["region", "settlements", "deaths"])
        w.writeheader()
        w.writerows(region_totals)

    grand = sum(r["deaths"] for r in region_totals)
    print(f"\nTotal across {len(region_totals)} regions: {grand:,} dead, "
          f"{len(settlements):,} settlements.")
    print("Top 15 regions:")
    for r in region_totals[:15]:
        print(f"  {r['region']:<40} {r['deaths']:>7,}")
    if failed:
        print(f"\nFailed to download: {[r for r, _ in failed]}")
    print(f"\nFiles: data/settlements.csv, data/regions_summary.csv")


if __name__ == "__main__":
    main()
