# -*- coding: utf-8 -*-
"""Creates the calculated table conflict_context for the In Context page."""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import (
    Table, Partition, CalculatedPartitionSource, RefreshType)

DAX = (
    'DATATABLE ( "Conflict", STRING, "Deaths", INTEGER, "SortOrder", INTEGER, '
    '"Side", STRING, { '
    '{ "Russia in Ukraine (confirmed)", 225019, 1, "Russia / USSR" }, '
    '{ "US in Vietnam", 58220, 2, "United States" }, '
    '{ "USSR in Afghanistan", 14453, 3, "Russia / USSR" }, '
    '{ "US in Iraq + Afghanistan", 7073, 4, "United States" }, '
    '{ "Russia in Chechnya II", 6000, 5, "Russia / USSR" }, '
    '{ "Russia in Chechnya I", 5500, 6, "Russia / USSR" } '
    '} )'
)


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        for t in list(model.Tables):
            if t.Name == "conflict_context":
                model.Tables.Remove(t)
        t = Table()
        t.Name = "conflict_context"
        p = Partition()
        p.Name = "conflict_context"
        src = CalculatedPartitionSource()
        src.Expression = DAX
        p.Source = src
        t.Partitions.Add(p)
        model.Tables.Add(t)
        model.SaveChanges()
        model.RequestRefresh(RefreshType.Full)
        model.SaveChanges()
        # measure for the bar chart
        s._upsert_measure(t, "Conflict Deaths", "SUM ( conflict_context[Deaths] )",
                          "#,0", "06 Context",
                          "Military deaths per conflict (officials' own counts; Ukraine = confirmed floor).")
        model.SaveChanges()
        print("OK: conflict_context table + Conflict Deaths measure created.")
        print("columns:", [c.Name for c in t.Columns])
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
