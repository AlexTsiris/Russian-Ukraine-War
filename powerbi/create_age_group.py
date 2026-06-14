# -*- coding: utf-8 -*-
"""Creates the age_group (buckets) + age_group_sort columns and the sort order."""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import CalculatedColumn, DataType, RefreshType

GROUP = ('VAR a = casualties[age] RETURN SWITCH ( TRUE (), '
         'ISBLANK ( a ), "Unknown", a < 20, "<20", a < 25, "20–24", '
         'a < 30, "25–29", a < 35, "30–34", a < 40, "35–39", a < 45, "40–44", '
         'a < 50, "45–49", a < 55, "50–54", a < 60, "55–59", "60+" )')
SORT = ('VAR a = casualties[age] RETURN SWITCH ( TRUE (), '
        'ISBLANK ( a ), 99, a < 20, 0, a < 25, 1, a < 30, 2, a < 35, 3, '
        'a < 40, 4, a < 45, 5, a < 50, 6, a < 55, 7, a < 60, 8, 9 )')


def add_col(t, name, expr, dtype):
    for c in list(t.Columns):
        if c.Name == name:
            t.Columns.Remove(c)
    col = CalculatedColumn()
    col.Name = name
    col.Expression = expr
    col.DataType = dtype
    t.Columns.Add(col)
    return col


def main():
    srv, model = s._connect_tom()
    cas = s._find_table(model, "casualties")
    add_col(cas, "age_group", GROUP, DataType.String)
    sortcol = add_col(cas, "age_group_sort", SORT, DataType.Int64)
    model.SaveChanges()
    model.RequestRefresh(RefreshType.Calculate)
    model.SaveChanges()
    # sort age_group by age_group_sort
    cas.Columns["age_group"].SortByColumn = sortcol
    model.SaveChanges()
    print("OK: age_group + age_group_sort created, sort order set.")
    srv.Disconnect()


if __name__ == "__main__":
    main()
