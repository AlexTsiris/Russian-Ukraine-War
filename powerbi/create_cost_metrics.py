# -*- coding: utf-8 -*-
"""
"Cost of advance" measures — how much one square kilometre of captured territory
costs the Russian army, in confirmed people and equipment. Cross-source metric
(Mediazona casualties × WarSpotting equipment × DeepStateMap territory).

All measures are CONTEXT-AWARE: with no date filter they cover the full available
window; with a date slicer / Play Axis they recompute for the selected period
(this is the honest way to read them — see the caveats in the dashboard caption).

Territory is NET change (area at the last snapshot in view minus the first). When
Russia lost ground in the window (net <= 0) the ratios return BLANK on purpose,
because "cost per km2 captured" is meaningless then.

Run with Power BI Desktop OPEN, using the Python312 interpreter (pythonnet + TOM):
    python create_cost_metrics.py
"""
import pbi_mcp_server as s

FOLDER = "07 Cost of Advance"

MEASURES = [
    ("Equipment Losses (Confirmed)", "#,0", FOLDER,
     "COUNTROWS ( equipment_losses )",
     "Visually-confirmed Russian equipment losses in context (WarSpotting; a lower bound)."),

    ("Territory Captured (km2)", "#,0", FOLDER,
     "VAR MinD = MIN ( frontline_history[snapshot_date_dt] ) "
     "VAR MaxD = MAX ( frontline_history[snapshot_date_dt] ) "
     "VAR StartKm = CALCULATE ( SUM ( frontline_history[occupied_km2] ), "
     "frontline_history[snapshot_date_dt] = MinD ) "
     "VAR EndKm = CALCULATE ( SUM ( frontline_history[occupied_km2] ), "
     "frontline_history[snapshot_date_dt] = MaxD ) "
     "RETURN EndKm - StartKm",
     "Net change in Russian-occupied area between the first and last snapshot in view "
     "(km2). Negative = Russia lost ground."),

    ("Lives per km2 Captured", "#,0.0", FOLDER,
     "VAR Terr = [Territory Captured (km2)] "
     "RETURN IF ( Terr > 0, DIVIDE ( [Total Confirmed Deaths], Terr ) )",
     "Confirmed Russian dead per net km2 gained in view. Illustrative lower bound — "
     "not all deaths are for territory; real toll is higher than confirmed names."),

    ("Equipment per km2 Captured", "#,0.0", FOLDER,
     "VAR Terr = [Territory Captured (km2)] "
     "RETURN IF ( Terr > 0, DIVIDE ( [Equipment Losses (Confirmed)], Terr ) )",
     "Confirmed equipment lost per net km2 gained in view. Illustrative lower bound."),

    # Inverse framing — often more intuitive ("how little ground that many lives bought").
    ("km2 per 1,000 Confirmed Dead", "#,0.00", FOLDER,
     "VAR Terr = [Territory Captured (km2)] "
     "RETURN IF ( Terr > 0, DIVIDE ( Terr, [Total Confirmed Deaths] ) * 1000 )",
     "Net km2 gained for every 1,000 confirmed Russian dead in view. Illustrative."),
]


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        cas = s._find_table(model, s.DEFAULT_TABLE)  # host table: casualties (measures are global)
        for name, fmt, folder, expr, desc in MEASURES:
            s._upsert_measure(cas, name, expr, fmt, folder, desc)
        model.SaveChanges()
        print(f"OK: {len(MEASURES)} cost-of-advance measures created in folder '{FOLDER}'.")
        print("Pair them with a date slicer / Play Axis. Save the .pbix (Ctrl+S).")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
