# -*- coding: utf-8 -*-
"""
Builds the final table data/full.csv from data/cases.jsonl
(which fetch_full.py populates).

Splits the date of death into year/month for convenient time-based analytics.
"""

import json
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(HERE, "data", "all_cases.jsonl")
OUT_CSV = os.path.join(HERE, "data", "full.csv")

COLUMNS = ["slug", "name", "region", "branch", "rank", "age",
           "birth", "death", "death_year", "death_month",
           "location", "source", "uid", "is_new"]


def main():
    rows = []
    skipped = 0
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("_notfound") or rec.get("_error"):
                skipped += 1
                continue

            death = rec.get("death")  # format "dd.mm.yyyy"
            d_year = d_month = None
            if isinstance(death, str) and death.count(".") == 2:
                dd, mm, yyyy = death.split(".")
                if yyyy.isdigit():
                    d_year = int(yyyy)
                if mm.isdigit():
                    d_month = int(mm)

            rows.append({
                "slug": rec.get("slug"),
                "name": rec.get("name"),
                "region": rec.get("regionDisplay") or rec.get("region"),
                "branch": rec.get("type"),            # service branch
                "rank": rec.get("rank"),              # military rank
                "age": rec.get("age"),
                "birth": rec.get("birth"),
                "death": death,
                "death_year": d_year,
                "death_month": d_month,
                "location": rec.get("locationName"),
                "source": rec.get("source"),
                "uid": rec.get("uid"),
                "is_new": rec.get("new"),
            })

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    print(f"Records in the table : {len(df):,}")
    print(f"Skipped (no data / error): {skipped:,}")
    print(f"Saved: {OUT_CSV}\n")
    print("Fill rate of key fields:")
    for col in ["region", "branch", "rank", "age", "death_year", "location"]:
        filled = df[col].notna().sum()
        print(f"  {col:<12}: {filled:>7,} ({filled / len(df) * 100:.0f}%)")


if __name__ == "__main__":
    main()
