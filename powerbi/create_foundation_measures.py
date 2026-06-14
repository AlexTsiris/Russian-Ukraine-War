# -*- coding: utf-8 -*-
"""
Creates the foundation set of DAX measures in the open Power BI model
directly via TOM (uses the helpers from pbi_mcp_server).
Run: python create_foundation_measures.py  (Power BI Desktop must be open)
"""
import pbi_mcp_server as s

MEASURES = [
    # --- 01 Core ---
    dict(name="Total Confirmed Deaths", folder="01 Core", fmt="#,0",
         expr="COUNTROWS ( casualties )",
         desc="Number of confirmed, named deaths (lower bound)."),
    dict(name="Share of Total", folder="01 Core", fmt="0.0%",
         expr="DIVIDE ( [Total Confirmed Deaths], CALCULATE ( [Total Confirmed Deaths], ALL ( casualties ) ) )",
         desc="Share of all confirmed deaths in the current filter context."),
    dict(name="Share 95% CI (+/- pp)", folder="01 Core", fmt="0.0%",
         expr=("VAR p = [Share of Total] "
               "VAR n = CALCULATE ( [Total Confirmed Deaths], ALL ( casualties ) ) "
               "RETURN 1.96 * SQRT ( DIVIDE ( p * ( 1 - p ), n ) )"),
         desc="95% confidence margin (percentage points) for a share."),

    # --- 02 Demographics ---
    dict(name="Deaths with Known Age", folder="02 Demographics", fmt="#,0",
         expr="COUNTROWS ( FILTER ( casualties, NOT ISBLANK ( casualties[age] ) ) )",
         desc="Records that have an age value."),
    dict(name="Average Age", folder="02 Demographics", fmt="0.0",
         expr="AVERAGE ( casualties[age] )", desc="Mean age of the dead."),
    dict(name="Median Age", folder="02 Demographics", fmt="0",
         expr="MEDIAN ( casualties[age] )", desc="Median age of the dead."),
    dict(name="% Aged Under 20", folder="02 Demographics", fmt="0.0%",
         expr="DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[age] < 20 ), [Deaths with Known Age] )",
         desc="Share under 20 among those with known age."),
    dict(name="% Aged 55 and Over", folder="02 Demographics", fmt="0.0%",
         expr="DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[age] >= 55 ), [Deaths with Known Age] )",
         desc="Share aged 55+ among those with known age."),

    # --- 03 Data quality (anti-bias transparency) ---
    dict(name="% Rank Known", folder="03 Data quality", fmt="0.0%",
         expr='DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[rank_category] <> "Unknown" ), [Total Confirmed Deaths] )',
         desc="Share of records where military rank is known."),
    dict(name="% Branch Known", folder="03 Data quality", fmt="0.0%",
         expr='DIVIDE ( CALCULATE ( [Total Confirmed Deaths], casualties[branch_en] <> "No data" ), [Total Confirmed Deaths] )',
         desc="Share of records where service branch is known."),
    dict(name="% with Known Death Date", folder="03 Data quality", fmt="0.0%",
         expr="DIVIDE ( COUNTROWS ( FILTER ( casualties, NOT ISBLANK ( casualties[death_date] ) ) ), [Total Confirmed Deaths] )",
         desc="Share of records with a known date of death."),
]


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Error: Power BI Desktop is not open.")
        return
    try:
        t = s._find_table(model, s.DEFAULT_TABLE)
        for m in MEASURES:
            s._upsert_measure(t, m["name"], m["expr"], m["fmt"],
                              m["folder"], m["desc"])
        model.SaveChanges()
        print("Measures created/updated:", len(MEASURES))
        print("Measures in the casualties table:")
        for mm in t.Measures:
            print("  -", mm.Name)
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
