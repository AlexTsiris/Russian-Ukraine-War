# -*- coding: utf-8 -*-
"""
Model audit fixes (round 1), applied live via TOM. Power BI Desktop must be OPEN.
Run with the Python312 interpreter:  python fix_model_v1.py

Fixes:
  #2  conflict_context: hardcoded Ukraine deaths 225,019 -> 0 (the page uses the LIVE
      measure for Ukraine, so the static count must not overstate the current data).
  #3  'Deaths per Day' made filter-aware: denominator = span of death dates in the
      current context (was a fixed DATEDIFF to TODAY, which broke under a date filter).
  #5  Calendar[Month] sorted by MonthNo (was alphabetical if used on an axis).
  #6  frontline_history[occupied_km2] default aggregation -> none (prevents an
      accidental sum of all months when shown without a single-date filter).
"""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import RefreshType, AggregateFunction

CONFLICT_DATATABLE = (
    'DATATABLE ( "Conflict", STRING, "Deaths", INTEGER, "SortOrder", INTEGER, '
    '"Side", STRING, { '
    '{ "Russia in Ukraine (confirmed)", 0, 1, "Russia / USSR" }, '
    '{ "US in Vietnam", 58220, 2, "United States" }, '
    '{ "USSR in Afghanistan", 14453, 3, "Russia / USSR" }, '
    '{ "US in Iraq + Afghanistan", 7073, 4, "United States" }, '
    '{ "Russia in Chechnya II", 6000, 5, "Russia / USSR" }, '
    '{ "Russia in Chechnya I", 5500, 6, "Russia / USSR" } '
    '} )'
)

DEATHS_PER_DAY = (
    "VAR d1 = MIN ( casualties[death_date] ) "
    "VAR d2 = MAX ( casualties[death_date] ) "
    "VAR days = DATEDIFF ( d1, d2, DAY ) + 1 "
    "RETURN DIVIDE ( [Total Confirmed Deaths], days )"
)


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        done = []

        # #3 Deaths per Day -> filter-aware
        cas = s._find_table(model, "casualties")
        cas.Measures["Deaths per Day"].Expression = DEATHS_PER_DAY
        done.append("#3 Deaths per Day rewritten")

        # #5 Calendar[Month] sort by MonthNo
        cal = s._find_table(model, "Calendar")
        cal.Columns["Month"].SortByColumn = cal.Columns["MonthNo"]
        done.append("#5 Calendar[Month] sorted by MonthNo")

        # #6 occupied_km2 default aggregation -> none
        # (NB: 'None' is a Python keyword, so fetch the .NET enum member via getattr)
        fl = s._find_table(model, "frontline_history")
        fl.Columns["occupied_km2"].SummarizeBy = getattr(AggregateFunction, "None")
        done.append("#6 occupied_km2 summarizeBy = none")

        # #2 conflict_context: Ukraine 225,019 -> 0
        cc = s._find_table(model, "conflict_context")
        part = next(iter(cc.Partitions))   # collection is keyed by name, not index
        part.Source.Expression = CONFLICT_DATATABLE
        done.append("#2 conflict_context Ukraine -> 0 (Live used on page)")

        model.SaveChanges()
        model.RequestRefresh(RefreshType.Calculate)   # recompute the calc table + sort
        model.SaveChanges()

        print("OK: applied", len(done), "fixes:")
        for d in done:
            print("   -", d)
        print("Now press Ctrl+S in Power BI to persist to disk.")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
