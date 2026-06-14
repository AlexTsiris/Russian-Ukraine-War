# Methodology & Data Limitations

*Russian military fatalities in the war against Ukraine — an open-source statistical, demographic, and military-strategic study.*

**Data source:** Mediazona & BBC News Russian — "Russia 200" named casualty list (200.zona.media), compiled from public, verifiable sources (obituaries, regional media, official statements, cemetery records).
**Extraction date:** 2026-06-12 · **Analysis by:** [author].

---

## 1. What this dataset is — and is not

- **IS:** individually identified, source-verified Russian military deaths (name-by-name).
- **IS NOT:** the total number of Russian military deaths.

This is a **verified lower bound**. Independent statistical estimates of *total* Russian losses (Mediazona/Meduza, via excess-mortality and probate modelling) are **substantially higher** (~350,000 vs. the ~225,000 confirmed by name). **Every figure in this dashboard refers to *confirmed, named* deaths unless explicitly stated.**

## 2. Sources of bias and how they are handled

| # | Bias | Why it matters | Mitigation in this study |
|---|------|----------------|--------------------------|
| 1 | **Confirmation lag** | The most recent months are undercounted; identification continues for months–years after death. Apparent recent declines may be artefacts. | The most recent ~6 months are flagged **"provisional — identification ongoing"** and excluded from trend conclusions. |
| 2 | **Non-random missing fields** | `rank` is known for ~33% of records; `branch` is "No data" for ~16%. Computing shares on known-only over-represents officers/known categories. | An explicit **"Unknown"** category is always shown; shares are reported against a stated denominator. |
| 3 | **Reporting visibility** | Rural areas and ethnic republics publicise deaths more than large, anonymous cities. "Major cities barely affected" is partly a coverage effect. | Coverage effects are stated; no causal claims. Per-capita figures interpreted with caution. |
| 4 | **"The dead ≠ those serving"** | The age/branch profile of the *dead* is not the demographic of the *force*. | All statements are framed strictly as "among confirmed dead," never "in the army." |
| 5 | **Per-capita denominator** | Outdated population data distorts per-capita burden. | Latest official population figures used; source and year cited. |

## 3. Statistical principles

- Proportions are reported **with 95% confidence intervals**, not as bare percentages.
- Both **absolute counts and relative shares** are shown.
- **"Unknown"** is never silently dropped.
- Source and extraction date appear on every page.
- **No causal or predictive claims** beyond what the data supports.

## 4. Representativeness note

Category proportions (branch, rank, year) are validated against a **random sample (n = 10,000, fixed seed)** drawn from the full named list, giving margins of error below ±1%. Geography (region, settlement) uses the **complete** authoritative settlement-level counts published by the project.

## 5. Attribution

Data © **Mediazona & BBC News Russian** ("Russia 200"). This is an independent analysis; it is not endorsed by the data authors. Use is for research and public-interest journalism. The subject matter concerns real human deaths and is presented with corresponding care.
