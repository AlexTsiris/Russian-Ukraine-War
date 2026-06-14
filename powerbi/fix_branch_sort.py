# -*- coding: utf-8 -*-
"""Breaks the dependency cycle: branch_group_sort is computed directly from branch_en."""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import RefreshType

NEW = ('SWITCH ( casualties[branch_en], "Volunteers (contract)", 0, '
       '"Convicts (prison recruits)", 1, "Mobilized", 2, '
       '"Motorized rifle troops", 3, "Airborne (VDV)", 4, '
       '"PMC (Wagner etc.)", 5, "No data", 7, 6 )')

srv, model = s._connect_tom()
cas = s._find_table(model, "casualties")
cas.Columns["branch_group_sort"].Expression = NEW
model.SaveChanges()
model.RequestRefresh(RefreshType.Calculate)
model.SaveChanges()
print("OK: branch_group_sort recomputed from branch_en, cycle broken.")
srv.Disconnect()
