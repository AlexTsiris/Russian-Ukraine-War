# DAX Measures — Foundation set

Paste each into Power BI: **Modeling → New Measure**. Put them in the `Measures` table.
All measures validated live against the model. Names are dashboard-ready (English).

> ⚠️ **Before publishing any time-based visual:** refresh the model with the **complete**
> 225k dataset. The currently loaded subset is ordered by date-added and is biased
> toward 2022–2023 deaths — temporal analysis on it is **not valid**.

---

## 1. Core counts

```DAX
Total Confirmed Deaths = COUNTROWS ( casualties )
```

```DAX
Share of Total =
DIVIDE ( [Total Confirmed Deaths], CALCULATE ( [Total Confirmed Deaths], ALL ( casualties ) ) )
```

```DAX
Share 95% CI (± pp) =
VAR p = [Share of Total]
VAR n = CALCULATE ( [Total Confirmed Deaths], ALL ( casualties ) )
RETURN 1.96 * SQRT ( DIVIDE ( p * ( 1 - p ), n ) )
```
*Use as a ± error value on share charts. Reports the 95% confidence margin in percentage points.*

---

## 2. Demographics (age)

```DAX
Deaths with Known Age = COUNTROWS ( FILTER ( casualties, NOT ISBLANK ( casualties[age] ) ) )
```

```DAX
Average Age = AVERAGE ( casualties[age] )
```

```DAX
Median Age = MEDIAN ( casualties[age] )
```

```DAX
% Aged Under 20 =
DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[age] < 20 ), [Deaths with Known Age] )
```

```DAX
% Aged 55 and Over =
DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[age] >= 55 ), [Deaths with Known Age] )
```

---

## 3. Data transparency (anti-bias — show these on every relevant page)

```DAX
% Rank Known =
DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[rank_category] <> "Unknown" ), [Total Confirmed Deaths] )
```

```DAX
% Branch Known =
DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[branch_en] <> "No data" ), [Total Confirmed Deaths] )
```

```DAX
% with Known Death Date =
DIVIDE ( COUNTROWS ( FILTER ( casualties, NOT ISBLANK ( casualties[death_date] ) ) ), [Total Confirmed Deaths] )
```
*These let the audience see how complete each field is. Never compute a share on
"known only" without displaying the corresponding "% Known".*

---

## 4. Recency-lag guard (for the timeline page — use after full refresh)

Add a **calculated column** on `casualties`:

```DAX
Death Period Status =
VAR LatestDeath = CALCULATE ( MAX ( casualties[death_date] ), ALL ( casualties ) )
RETURN
IF (
    NOT ISBLANK ( casualties[death_date] ) && casualties[death_date] > EDATE ( LatestDeath, -6 ),
    "Provisional (identification ongoing)",
    "Confirmed period"
)
```
*On the timeline, colour/annotate the last 6 months as "Provisional" so the audience
does not read the inevitable recent dip as a real decline.*

---

## 5. Reference figure (text card, not a measure)

> **Confirmed (named) deaths in this dataset are a lower bound.**
> Statistical estimates of *total* Russian losses are roughly **1.5× higher**
> (Mediazona/Meduza). Always label visuals "confirmed, named deaths".
