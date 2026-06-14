# -*- coding: utf-8 -*-
"""
Starter analytics over the list of the dead (data/list.csv).
Run it after download_list.py.

Computes basic age statistics and plots an age histogram.
From here you can add any breakdowns you like.
"""

import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "data", "list.csv")
OUT_DIR = os.path.join(HERE, "output")


def main():
    df = pd.read_csv(CSV)
    print(f"Total records: {len(df):,}\n")

    # --- Age ---
    # Drop obvious outliers (typos in the source), keep 14..99
    ages = df["age"].dropna()
    ages = ages[(ages >= 14) & (ages <= 99)]
    print("AGE")
    print(f"  records with age : {len(ages):,}")
    print(f"  mean             : {ages.mean():.1f}")
    print(f"  median           : {ages.median():.0f}")
    print(f"  most frequent    : {ages.mode().iloc[0]:.0f}")
    print()

    # Distribution by age group
    bins = [14, 20, 25, 30, 35, 40, 45, 50, 60, 100]
    labels = ["<20", "20-24", "25-29", "30-34", "35-39",
              "40-44", "45-49", "50-59", "60+"]
    groups = pd.cut(ages, bins=bins, labels=labels, right=False)
    print("BY AGE GROUP")
    grp = groups.value_counts().sort_index()
    for label, cnt in grp.items():
        print(f"  {label:>6}: {cnt:>7,}  ({cnt / len(ages) * 100:4.1f}%)")
    print()

    # --- Most frequent surnames ---
    print("TOP 15 SURNAMES")
    for surname, cnt in df["surname"].value_counts().head(15).items():
        print(f"  {surname:<15} {cnt:>5,}")

    # --- Chart ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(OUT_DIR, exist_ok=True)
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.hist(ages, bins=range(15, 70), color="#bf2928", edgecolor="white")
        ax.set_title("Age distribution of the dead (Mediazona / BBC \"Russia 200\")")
        ax.set_xlabel("Age")
        ax.set_ylabel("Number of dead")
        fig.tight_layout()
        path = os.path.join(OUT_DIR, "age_distribution.png")
        fig.savefig(path, dpi=120)
        print(f"\nChart saved: {path}")
    except ImportError:
        print("\n(matplotlib is not installed — chart skipped. "
              "Install it: pip install matplotlib)")


if __name__ == "__main__":
    main()
