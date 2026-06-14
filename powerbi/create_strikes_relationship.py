# -*- coding: utf-8 -*-
"""
Relate the strategic_strikes fact table to the shared Calendar by date.
Requires Power BI to be OPEN. Run with the Python312 interpreter (pythonnet + AMO/TOM):
    python create_strikes_relationship.py

Creates a 1:* single-direction relationship Calendar[Date] -> strategic_strikes[date].
Geography (lat/lon/oblast) is intentionally NOT related to anything: a strike location is
where it was hit in Russia, unrelated to casualty home regions. Time is the only shared axis.
"""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import (
    RefreshType, SingleColumnRelationship, RelationshipEndCardinality, CrossFilteringBehavior)

MANY_TABLE = "strategic_strikes"
MANY_COL = "date"


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
        rel.FromColumn = t.Columns[MANY_COL]          # many
        rel.ToColumn = date_col                        # one
        rel.FromCardinality = RelationshipEndCardinality.Many
        rel.ToCardinality = RelationshipEndCardinality.One
        rel.CrossFilteringBehavior = CrossFilteringBehavior.OneDirection
        rel.IsActive = True
        model.Relationships.Add(rel)
        print(f"  + relationship Calendar[Date] -> {MANY_TABLE}[{MANY_COL}]")

        model.SaveChanges()
        model.RequestRefresh(RefreshType.Calculate)   # rebuild the relationship indexes
        model.SaveChanges()
        print("OK: relationship created and recalculated. Save the .pbix (Ctrl+S).")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
