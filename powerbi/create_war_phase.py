# -*- coding: utf-8 -*-
"""war_phase + war_phase_sort: the war phase by month of death (for colouring the timeline)."""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import CalculatedColumn, DataType, RefreshType

PHASE = ('VAR d = casualties[death_month_start] RETURN SWITCH ( TRUE (), '
         'ISBLANK ( d ), "Unknown date", '
         'd < DATE ( 2022, 4, 1 ), "1 · Invasion & Kyiv (Feb–Mar 2022)", '
         'd < DATE ( 2022, 9, 1 ), "2 · Donbas offensive (Apr–Aug 2022)", '
         'd < DATE ( 2022, 11, 1 ), "3 · UA counter-offensives + mobilization (Sep–Oct 2022)", '
         'd < DATE ( 2023, 6, 1 ), "4 · Bakhmut (Nov 2022–May 2023)", '
         'd < DATE ( 2023, 10, 1 ), "5 · UA summer counter-offensive (Jun–Sep 2023)", '
         'd < DATE ( 2024, 3, 1 ), "6 · Avdiivka (Oct 2023–Feb 2024)", '
         'd < DATE ( 2025, 1, 1 ), "7 · Pokrovsk & attrition (2024)", '
         '"8 · Attrition (2025– )" )')
SORT = ('VAR d = casualties[death_month_start] RETURN SWITCH ( TRUE (), '
        'ISBLANK ( d ), 99, '
        'd < DATE ( 2022, 4, 1 ), 1, d < DATE ( 2022, 9, 1 ), 2, '
        'd < DATE ( 2022, 11, 1 ), 3, d < DATE ( 2023, 6, 1 ), 4, '
        'd < DATE ( 2023, 10, 1 ), 5, d < DATE ( 2024, 3, 1 ), 6, '
        'd < DATE ( 2025, 1, 1 ), 7, 8 )')


def add(t, name, expr, dt):
    for c in list(t.Columns):
        if c.Name == name:
            t.Columns.Remove(c)
    col = CalculatedColumn(); col.Name = name; col.Expression = expr; col.DataType = dt
    t.Columns.Add(col); return col


srv, model = s._connect_tom()
cas = s._find_table(model, "casualties")
add(cas, "war_phase", PHASE, DataType.String)
sortcol = add(cas, "war_phase_sort", SORT, DataType.Int64)
model.SaveChanges()
model.RequestRefresh(RefreshType.Calculate)
model.SaveChanges()
cas.Columns["war_phase"].SortByColumn = sortcol
model.SaveChanges()
print("OK: war_phase + war_phase_sort created, sort order set.")
srv.Disconnect()
