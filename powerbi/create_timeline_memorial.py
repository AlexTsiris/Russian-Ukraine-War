# -*- coding: utf-8 -*-
"""
Adds to the model:
  * a calculated column death_month_start (the 1st day of the month of death) — the timeline axis;
  * peak-month measures (Deadliest Month / Peak Month Deaths);
  * "person of the day" measures for the memorial page (deterministic from TODAY(), changes once a day).
Then recalculates the model.
"""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import CalculatedColumn, DataType, RefreshType

MEASURES = [
    ("Peak Month Deaths", "04 Timeline", "#,0",
     "VAR t = ADDCOLUMNS ( FILTER ( ALL ( casualties[death_month_start] ), "
     "NOT ISBLANK ( casualties[death_month_start] ) ), \"@n\", "
     "CALCULATE ( COUNTROWS ( casualties ) ) ) RETURN MAXX ( t, [@n] )",
     "Confirmed deaths in the deadliest month."),
    ("Deadliest Month", "04 Timeline", "",
     "VAR t = ADDCOLUMNS ( FILTER ( ALL ( casualties[death_month_start] ), "
     "NOT ISBLANK ( casualties[death_month_start] ) ), \"@n\", "
     "CALCULATE ( COUNTROWS ( casualties ) ) ) "
     "VAR mx = MAXX ( t, [@n] ) "
     "VAR d = MINX ( FILTER ( t, [@n] = mx ), casualties[death_month_start] ) "
     "RETURN FORMAT ( d, \"MMMM yyyy\", \"en-US\" )",
     "Name of the deadliest month."),
    ("Remembered Index", "05 Memorial", "0",
     "VAR n = COUNTROWS ( ALL ( casualties ) ) "
     "RETURN MOD ( DATEDIFF ( DATE ( 2022, 2, 24 ), TODAY (), DAY ) * 9973, n ) + 1",
     "Deterministic daily index (changes once per day)."),
    ("Remembered Name", "05 Memorial", "",
     "VAR idx = [Remembered Index] "
     "VAR sel = TOPN ( 1, TOPN ( idx, ALL ( casualties ), casualties[uid], ASC ), "
     "casualties[uid], DESC ) RETURN MAXX ( sel, casualties[name_ru] )",
     "Name (RU) of today's remembered person."),
    ("Remembered Details", "05 Memorial", "",
     "VAR idx = [Remembered Index] "
     "VAR sel = TOPN ( 1, TOPN ( idx, ALL ( casualties ), casualties[uid], ASC ), "
     "casualties[uid], DESC ) "
     "VAR nm = MAXX ( sel, casualties[name_en] ) "
     "VAR age = MAXX ( sel, casualties[age] ) "
     "VAR reg = MAXX ( sel, casualties[region_en] ) "
     "VAR br = MAXX ( sel, casualties[branch_en] ) "
     "VAR dd = MAXX ( sel, casualties[death_date] ) "
     "RETURN nm "
     "& IF ( NOT ISBLANK ( age ), \"  ·  aged \" & age ) "
     "& IF ( NOT ISBLANK ( reg ), \"  ·  \" & reg ) "
     "& IF ( NOT ISBLANK ( br ) && br <> \"No data\", \"  ·  \" & br ) "
     "& IF ( NOT ISBLANK ( dd ), \"  ·  died \" & FORMAT ( dd, \"d MMMM yyyy\", \"en-US\" ) )",
     "Details line of today's remembered person."),
    ("Remembered Source", "05 Memorial", "",
     "VAR idx = [Remembered Index] "
     "VAR sel = TOPN ( 1, TOPN ( idx, ALL ( casualties ), casualties[uid], ASC ), "
     "casualties[uid], DESC ) "
     "RETURN \"Source: \" & MAXX ( sel, casualties[source_url] )",
     "Verification source of today's remembered person."),
]


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        cas = s._find_table(model, "casualties")

        # month-of-death column
        for c in list(cas.Columns):
            if c.Name == "death_month_start":
                cas.Columns.Remove(c)
        col = CalculatedColumn()
        col.Name = "death_month_start"
        col.Expression = ("IF ( NOT ISBLANK ( casualties[death_date] ), "
                          "DATE ( YEAR ( casualties[death_date] ), "
                          "MONTH ( casualties[death_date] ), 1 ) )")
        col.DataType = DataType.DateTime
        col.FormatString = "MMM yyyy"
        cas.Columns.Add(col)

        for name, folder, fmt, expr, desc in MEASURES:
            s._upsert_measure(cas, name, expr, fmt, folder, desc)

        model.SaveChanges()
        model.RequestRefresh(RefreshType.Calculate)
        model.SaveChanges()
        print("OK: column death_month_start + 6 measures created, model recalculated.")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
