# -*- coding: utf-8 -*-
"""
Migrate the casualties table to the slim 5-column schema and reload the FULL 225k data.
Requires Power BI OPEN. Run with Python312 (pythonnet + AMO/TOM):  python migrate_casualties_slim.py

The model was loaded from the old wide (19-col, partial 76k) CSV; build_powerbi.py now exports
only the 5 columns the report actually uses. Verified: no visual and no measure references the
14 dropped base columns (names/uid/source_url/cities/birth_date/death_year/death_month/*_ru).
Calculated columns (age_group, war_phase, branch_group, death_month_start, *_sort) derive from
age / branch_en / death_date and are preserved.

Steps: rewrite the Power Query (5 typed columns) -> drop the 14 unused base columns ->
Full refresh (reloads 225k from the local slim CSV) -> recalc.
"""
import pbi_mcp_server as s
from Microsoft.AnalysisServices.Tabular import RefreshType

NEW_M = r'''let
    Source = Csv.Document(File.Contents("C:\Users\aleks\OneDrive\Desktop\моя учеба\мой проект\powerbi\casualties.csv"),[Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"region_en", type text}, {"branch_en", type text}, {"rank_category", type text}, {"age", Int64.Type}, {"death_date", type date}}),
    #"Replaced Errors" = Table.ReplaceErrorValues(#"Changed Type", {{"death_date", null}})
in
    #"Replaced Errors"'''

DROP = ["uid", "name_en", "name_ru", "region_ru", "branch_ru", "rank_en", "rank_ru",
        "birth_date", "death_year", "death_month", "death_month_name",
        "city_en", "city_ru", "source_url"]


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        t = s._find_table(model, "casualties")

        for p in t.Partitions:
            if hasattr(p.Source, "Expression"):
                p.Source.Expression = NEW_M
                print(f"  partition '{p.Name}': Power Query rewritten to 5 columns")

        dropped = []
        for name in DROP:
            for c in list(t.Columns):
                if c.Name == name:
                    t.Columns.Remove(c)
                    dropped.append(name)
        print(f"  dropped {len(dropped)} unused columns: {', '.join(dropped)}")

        model.SaveChanges()
        model.RequestRefresh(RefreshType.Full)   # reload 225k from the slim CSV
        model.SaveChanges()
        print("OK: casualties migrated to slim schema + full data reloaded. Save the .pbix (Ctrl+S).")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
