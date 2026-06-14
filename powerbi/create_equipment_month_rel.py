# -*- coding: utf-8 -*-
"""
Relate equipment_by_month[month] to the shared Calendar so the monthly equipment trend
follows the global time slicer (equipment_losses is already related; this pre-aggregated
table was standalone).  Requires Power BI OPEN. Run with Python312.

equipment_by_month[month] holds month-start dates; Calendar[Date] (unique, daily) covers
them all -> clean many-to-one, single direction (Calendar filters equipment_by_month).
"""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import (
    RefreshType, SingleColumnRelationship, RelationshipEndCardinality, CrossFilteringBehavior)

MANY_TABLE, MANY_COL = "equipment_by_month", "month"


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        cal = s._find_table(model, "Calendar")
        date_col = cal.Columns["Date"]
        existing = {(r.FromTable.Name, r.FromColumn.Name) for r in model.Relationships
                    if hasattr(r, "ToTable") and r.ToTable.Name == "Calendar"}
        if (MANY_TABLE, MANY_COL) in existing:
            print(f"  relationship Calendar[Date] -> {MANY_TABLE}[{MANY_COL}] already exists — skip")
            return
        t = s._find_table(model, MANY_TABLE)
        rel = SingleColumnRelationship()
        rel.FromColumn = t.Columns[MANY_COL]
        rel.ToColumn = date_col
        rel.FromCardinality = RelationshipEndCardinality.Many
        rel.ToCardinality = RelationshipEndCardinality.One
        rel.CrossFilteringBehavior = CrossFilteringBehavior.OneDirection
        rel.IsActive = True
        model.Relationships.Add(rel)
        model.SaveChanges()
        model.RequestRefresh(RefreshType.Calculate)
        model.SaveChanges()
        print(f"OK: Calendar[Date] -> {MANY_TABLE}[{MANY_COL}] created. Save the .pbix (Ctrl+S).")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
