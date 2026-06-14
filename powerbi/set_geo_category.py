# -*- coding: utf-8 -*-
"""Marks settlements[lat]/[lon] as Latitude/Longitude — for maps."""
import pbi_mcp_server as s

srv, model = s._connect_tom()
t = s._find_table(model, "settlements")
for col in t.Columns:
    if col.Name == "lat":
        col.DataCategory = "Latitude"
        col.SummarizeBy = col.SummarizeBy  # unchanged
    elif col.Name == "lon":
        col.DataCategory = "Longitude"
model.SaveChanges()
print("OK: lat->Latitude, lon->Longitude.")
for col in t.Columns:
    if col.Name in ("lat", "lon", "deaths"):
        print(f"  {col.Name}: dataCategory={col.DataCategory}, summarizeBy={col.SummarizeBy}")
srv.Disconnect()
