# -*- coding: utf-8 -*-
"""
Fix the 'Deaths per Day' measure: use the DATED death count in the numerator so it matches
the denominator (the dated span), instead of Total Confirmed Deaths (which includes ~21k
rows without a death date and inflated the rate). Surgical expression-only edit via TOM
(format string / display folder / description preserved). Requires Power BI OPEN. Python312.
"""
import pbi_mcp_server as s

NAME = "Deaths per Day"
NEW_EXPR = (
    "VAR d1 = MIN ( casualties[death_date] ) "
    "VAR d2 = MAX ( casualties[death_date] ) "
    "VAR days = DATEDIFF ( d1, d2, DAY ) + 1 "
    "VAR dated = COUNTROWS ( FILTER ( casualties, NOT ISBLANK ( casualties[death_date] ) ) ) "
    "RETURN DIVIDE ( dated, days )"
)


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        target = None
        for t in model.Tables:
            for m in t.Measures:
                if m.Name == NAME:
                    target = m; break
            if target:
                break
        if not target:
            print(f"Measure '{NAME}' not found"); return
        print(f"  old: {target.Expression}")
        target.Expression = NEW_EXPR
        model.SaveChanges()
        print(f"  new: {NEW_EXPR}")
        print("OK: 'Deaths per Day' now uses dated deaths in the numerator. Ctrl+S to persist.")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
