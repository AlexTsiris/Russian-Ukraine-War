# -*- coding: utf-8 -*-
"""
Unified model: a Calendar table + date relationships to the facts (people / equipment / territory).
Requires Power BI to be OPEN. Run with the Python312 interpreter (pythonnet + AMO/TOM):
    python create_calendar.py

It:
  * builds Calendar (2022-01-01..2026-12-31): Date, Year, MonthNo, Month (English), YearMonth, MonthStart;
  * adds frontline_history[snapshot_date_dt] = DATEVALUE(snapshot_date)  (the text column stays for Deneb);
  * creates 1:* (single-direction) relationships: Calendar[Date] -> casualties[death_date],
    -> equipment_losses[date], -> frontline_history[snapshot_date_dt].
"""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import (
    Table, Partition, CalculatedPartitionSource, CalculatedColumn, DataType,
    RefreshType, SingleColumnRelationship, RelationshipEndCardinality, CrossFilteringBehavior)

CAL_EXPR = (
    'ADDCOLUMNS ( CALENDAR ( DATE ( 2022, 1, 1 ), DATE ( 2026, 12, 31 ) ), '
    '"Year", YEAR ( [Date] ), '
    '"MonthNo", MONTH ( [Date] ), '
    '"Month", FORMAT ( [Date], "MMM", "en-US" ), '
    '"YearMonth", FORMAT ( [Date], "YYYY-MM" ), '
    '"MonthStart", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ) )'
)

# (many-side table, many-side column)  -> one-side Calendar[Date]
LINKS = [
    ("casualties", "death_date"),
    ("equipment_losses", "date"),
    ("frontline_history", "snapshot_date_dt"),
]


def add_calc_column(tbl, name, expr, dt):
    for c in list(tbl.Columns):
        if c.Name == name:
            tbl.Columns.Remove(c)
    col = CalculatedColumn()
    col.Name = name; col.Expression = expr; col.DataType = dt
    tbl.Columns.Add(col)


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        # --- drop any existing relationships to/from Calendar, then the table itself (rebuild)
        for r in list(model.Relationships):
            try:
                if r.FromTable.Name == "Calendar" or r.ToTable.Name == "Calendar":
                    model.Relationships.Remove(r)
            except Exception:
                pass
        for t in list(model.Tables):
            if t.Name == "Calendar":
                model.Tables.Remove(t)
        cal = Table(); cal.Name = "Calendar"
        part = Partition(); part.Name = "Calendar"
        part.Source = CalculatedPartitionSource(); part.Source.Expression = CAL_EXPR
        cal.Partitions.Add(part)
        model.Tables.Add(cal)

        # --- date column for frontline (the text snapshot_date stays untouched for Deneb)
        fl = s._find_table(model, "frontline_history")
        add_calc_column(fl, "snapshot_date_dt",
                        "DATEVALUE ( frontline_history[snapshot_date] )", DataType.DateTime)

        model.SaveChanges()
        model.RequestRefresh(RefreshType.Calculate)
        model.SaveChanges()

        # --- mark Calendar as the date table
        cal = s._find_table(model, "Calendar")
        cal.DataCategory = "Time"

        # --- relationships
        date_col = cal.Columns["Date"]
        # consider ONLY relationships pointing into Calendar (ignore the hidden auto date tables)
        existing = {(r.FromTable.Name, r.FromColumn.Name) for r in model.Relationships
                    if hasattr(r, "ToTable") and r.ToTable.Name == "Calendar"}
        for tname, cname in LINKS:
            if (tname, cname) in existing:
                print(f"  relationship Calendar -> {tname}[{cname}] already exists — skip"); continue
            try:
                t = s._find_table(model, tname)
                rel = SingleColumnRelationship()
                rel.FromColumn = t.Columns[cname]            # many
                rel.ToColumn = date_col                       # one
                rel.FromCardinality = RelationshipEndCardinality.Many
                rel.ToCardinality = RelationshipEndCardinality.One
                rel.CrossFilteringBehavior = CrossFilteringBehavior.OneDirection
                rel.IsActive = True
                model.Relationships.Add(rel)
                print(f"  + relationship Calendar[Date] -> {tname}[{cname}]")
            except Exception as e:
                print(f"  [!] {tname}[{cname}]: {e}")

        model.SaveChanges()
        model.RequestRefresh(RefreshType.Calculate)   # rebuild the relationship indexes
        model.SaveChanges()
        print("OK: Calendar + relationships created and recalculated. Save the .pbix (Ctrl+S).")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
