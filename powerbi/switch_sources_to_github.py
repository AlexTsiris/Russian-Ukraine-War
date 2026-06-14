# -*- coding: utf-8 -*-
"""
Repoint every local-file table source to the GitHub raw URL, so the Power BI Service can
do a gateway-less scheduled refresh (matching the already-web strategic_strikes table).
Requires Power BI OPEN. Run with Python312:  python switch_sources_to_github.py

For each partition it ONLY swaps  File.Contents("C:\\...\\powerbi\\X.csv")  ->
Web.Contents("https://raw.githubusercontent.com/AlexTsiris/Russian-Ukraine-War/main/powerbi/X.csv")
keeping the per-table Columns/types/steps identical. DATATABLE (conflict_context) and the
DAX Calendar table have no file source and are left untouched. No refresh is forced here —
refresh in Power BI Desktop (Anonymous creds for raw.githubusercontent.com) then Ctrl+S.
"""
import re
import pbi_mcp_server as s

RAW = "https://raw.githubusercontent.com/AlexTsiris/Russian-Ukraine-War/main/powerbi/"
PAT = re.compile(r'File\.Contents\("[^"]*powerbi[\\/]([^"\\/]+\.csv)"\)')


def main():
    srv, model = s._connect_tom()
    if not model:
        print("Power BI is not open"); return
    try:
        changed = []
        for t in model.Tables:
            for p in t.Partitions:
                src = p.Source
                if not hasattr(src, "Expression") or not src.Expression:
                    continue
                expr = src.Expression
                if "File.Contents(" not in expr:
                    continue
                new = PAT.sub(lambda m: f'Web.Contents("{RAW}{m.group(1)}")', expr)
                if new != expr:
                    src.Expression = new
                    fname = PAT.search(expr)
                    changed.append((t.Name, fname.group(1) if fname else "?"))
        model.SaveChanges()
        print(f"Repointed {len(changed)} tables to GitHub raw:")
        for tname, fname in changed:
            print(f"  {tname:22s} -> {fname}")
        print("\nNext: in Power BI Desktop click Refresh (Anonymous if prompted), then Ctrl+S.")
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    main()
