# -*- coding: utf-8 -*-
"""
Download of the named list of the dead from the "Russia 200" project (Mediazona + BBC).
Data source: https://200.zona.media/  (the urls.json file on their CDN).

The script downloads the full list (~225,000 records), parses each slug into
surname / given name / patronymic / age and saves it to data/list.csv.

The data is collected by Mediazona and BBC News Russian from open sources.
When publishing, provide attribution. Use it respectfully.
"""

import csv
import json
import os
import urllib.request

# The project's CDN mirror. The site picks s3.zona.media for Russia and cloudcdn1.org
# for the rest of the world — both serve the same thing.
BASE = "https://s3.zona.media/infographics/g200w"
LIST_URL = f"{BASE}/urls.json.br"   # the server returns already-decompressed JSON

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_CSV = os.path.join(OUT_DIR, "list.csv")
RAW_JSON = os.path.join(OUT_DIR, "urls.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (research; casualties analytics)"}


def download_list():
    """Downloads urls.json and returns the list of slugs."""
    print(f"Downloading list: {LIST_URL}")
    req = urllib.request.Request(LIST_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    slugs = json.loads(raw)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(RAW_JSON, "w", encoding="utf-8") as f:
        json.dump(slugs, f, ensure_ascii=False)
    print(f"Records received: {len(slugs):,}")
    return slugs


def parse_slug(slug):
    """
    'Акимов_Евгений_Евгеньевич_44' -> ('Акимов Евгений Евгеньевич', 'Акимов',
                                        'Евгений', 'Евгеньевич', 44)
    The trailing age is not always present; some surnames are double-barrelled in brackets.
    """
    parts = slug.split("_")
    age = None
    if parts and parts[-1].isdigit():
        age = int(parts[-1])
        parts = parts[:-1]
    full_name = " ".join(parts)
    surname = parts[0] if len(parts) > 0 else ""
    given = parts[1] if len(parts) > 1 else ""
    patronymic = " ".join(parts[2:]) if len(parts) > 2 else ""
    return full_name, surname, given, patronymic, age


def main():
    slugs = download_list()
    rows = []
    for slug in slugs:
        full_name, surname, given, patronymic, age = parse_slug(slug)
        rows.append({
            "slug": slug,                 # useful for /api/case/<slug>
            "full_name": full_name,
            "surname": surname,
            "given_name": given,
            "patronymic": patronymic,
            "age": age,
        })

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["slug", "full_name", "surname",
                           "given_name", "patronymic", "age"]
        )
        writer.writeheader()
        writer.writerows(rows)

    with_age = sum(1 for r in rows if r["age"] is not None)
    print(f"Saved: {OUT_CSV}")
    print(f"  total records : {len(rows):,}")
    print(f"  with age      : {with_age:,}")
    print(f"  without age   : {len(rows) - with_age:,}")


if __name__ == "__main__":
    main()
