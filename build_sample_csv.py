# -*- coding: utf-8 -*-
"""
Builds data/sample.csv from data/sample_cases.jsonl and immediately prints the shares
by service branch, rank and year of death (that is the point of the sample).
"""

import json
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(HERE, "data", "sample_cases.jsonl")
OUT = os.path.join(HERE, "data", "sample.csv")


def main():
    rows = []
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("_notfound") or rec.get("_error"):
                continue
            death = rec.get("death")
            year = None
            if isinstance(death, str) and "." in death:
                tail = death.split(".")[-1]
                if tail.isdigit() and len(tail) == 4:
                    year = int(tail)
            elif isinstance(death, str) and death.isdigit() and len(death) == 4:
                year = int(death)
            rows.append({
                "name": rec.get("name"),
                "region": rec.get("regionDisplay") or rec.get("region"),
                "branch": rec.get("type"),
                "rank": rec.get("rank"),
                "age": rec.get("age"),
                "death": death,
                "death_year": year,
                "location": rec.get("locationName"),
                "slug": rec.get("slug"),
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Sample: {len(df):,} records -> {OUT}\n")

    def show(col, title, top=None):
        vc = df[col].value_counts(dropna=True)
        if top:
            vc = vc.head(top)
        print(title)
        for k, v in vc.items():
            print(f"  {str(k):<28} {v:>6,}  ({v / len(df) * 100:4.1f}%)")
        print()

    show("branch", "SERVICE BRANCH (shares):", top=15)
    show("death_year", "YEAR OF DEATH (shares):")
    show("rank", "RANK (top 12):", top=12)


if __name__ == "__main__":
    main()
