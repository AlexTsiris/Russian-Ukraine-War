# -*- coding: utf-8 -*-
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import RefreshType

srv, model = s._connect_tom()
reg = s._find_table(model, "regions")
s._upsert_measure(reg, "Regional Deaths (Confirmed)",
                  "SUM ( regions[total_deaths_full] )", "#,0", "04 Geography",
                  "Authoritative confirmed deaths by home region (full geography).")
model.SaveChanges()
print("OK: measure Regional Deaths (Confirmed) created.")
srv.Disconnect()
