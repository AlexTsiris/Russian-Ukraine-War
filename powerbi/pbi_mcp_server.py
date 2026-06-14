# -*- coding: utf-8 -*-
"""
MCP server for the local Power BI Desktop model.

Capabilities:
  * read:  get_model_tables, list_measures, run_dax_query
  * write: create_measure, create_measures (batch), delete_measure
           — via TOM (Tabular Object Model), the same way Tabular Editor does it.

Requires Power BI Desktop to be open (the msmdsrv.exe process).
"""

import json
import os
import logging

from mcp.server.fastmcp import FastMCP
import psutil
import adodbapi

# --- TOM (Tabular Object Model) for writing to the model ---
from pythonnet import load
load("netfx")
import clr

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "lib", "amo", "lib", "net45")
for _dll in ["Microsoft.AnalysisServices.Core.dll",
             "Microsoft.AnalysisServices.Tabular.dll",
             "Microsoft.AnalysisServices.Tabular.Json.dll"]:
    clr.AddReference(os.path.join(_LIB, _dll))
from Microsoft.AnalysisServices.Tabular import Server, Measure  # noqa: E402

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("PowerBI_Local")

DEFAULT_TABLE = "casualties"   # default host table for measures


# ---------------------------------------------------------------- helpers
def get_powerbi_port():
    """Port of the local Analysis Services instance (Power BI Desktop)."""
    for proc in psutil.process_iter(['name', 'pid']):
        if proc.info['name'] == 'msmdsrv.exe':
            try:
                for conn in proc.connections():
                    if conn.status == 'LISTEN':
                        return conn.laddr.port
            except psutil.AccessDenied:
                pass
    return None


def _connect_tom():
    """Returns the TOM (server, model) or (None, None)."""
    port = get_powerbi_port()
    if not port:
        return None, None
    srv = Server()
    srv.Connect(f"localhost:{port}")
    model = srv.Databases[0].Model
    return srv, model


def _find_table(model, name):
    for t in model.Tables:
        if t.Name == name:
            return t
    return None


# ---------------------------------------------------------------- read
@mcp.tool()
def get_model_tables() -> str:
    """Returns the list of user tables in the Power BI model."""
    srv, model = _connect_tom()
    if not model:
        return "Error: Power BI Desktop is not open (msmdsrv.exe not found)."
    try:
        tables = [t.Name for t in model.Tables
                  if not t.Name.startswith(("LocalDateTable_", "DateTableTemplate_"))]
        return "Tables: " + ", ".join(tables)
    finally:
        srv.Disconnect()


@mcp.tool()
def list_measures() -> str:
    """List of all measures in the model: table, name, expression."""
    srv, model = _connect_tom()
    if not model:
        return "Error: Power BI Desktop is not open."
    try:
        out = []
        for t in model.Tables:
            for m in t.Measures:
                out.append(f"[{t.Name}] {m.Name} = {m.Expression}")
        return "\n".join(out) if out else "The model has no measures yet."
    finally:
        srv.Disconnect()


@mcp.tool()
def run_dax_query(dax_query: str) -> str:
    """Runs a DAX/DMV query against the open model and returns the result."""
    port = get_powerbi_port()
    if not port:
        return "Error: Power BI Desktop is not open."
    conn_str = f"Provider=MSOLAP;Data Source=localhost:{port};"
    try:
        conn = adodbapi.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(dax_query)
        columns = [c[0] for c in cursor.description]
        data = cursor.fetchall()
        conn.close()
        result = f"Columns: {columns}\nData:\n"
        for row in data:
            result += f"{list(row)}\n"
        return result
    except Exception as e:
        return f"DAX execution error: {str(e)}"


# ---------------------------------------------------------------- write
def _upsert_measure(table, name, expression, format_string, display_folder,
                    description):
    """Creates or replaces a measure in a TOM table (without SaveChanges)."""
    existing = None
    for m in table.Measures:
        if m.Name == name:
            existing = m
            break
    if existing is not None:
        table.Measures.Remove(existing)
    m = Measure()
    m.Name = name
    m.Expression = expression
    if format_string:
        m.FormatString = format_string
    if display_folder:
        m.DisplayFolder = display_folder
    if description:
        m.Description = description
    table.Measures.Add(m)


@mcp.tool()
def create_measure(name: str, expression: str, table: str = DEFAULT_TABLE,
                   format_string: str = "", display_folder: str = "",
                   description: str = "") -> str:
    """
    Creates (or replaces) a single DAX measure in the Power BI model.
    name — the measure name; expression — DAX (without 'Name ='); table — the host table;
    format_string — e.g. '#,0' or '0.0%'; display_folder — the folder in the Fields pane.
    """
    srv, model = _connect_tom()
    if not model:
        return "Error: Power BI Desktop is not open."
    try:
        t = _find_table(model, table)
        if t is None:
            return f"Error: table '{table}' not found."
        _upsert_measure(t, name, expression, format_string, display_folder,
                        description)
        model.SaveChanges()
        return f"OK: measure '{name}' created in table '{table}'."
    except Exception as e:
        return f"Error creating measure '{name}': {str(e)}"
    finally:
        srv.Disconnect()


@mcp.tool()
def create_measures(measures_json: str, table: str = DEFAULT_TABLE) -> str:
    """
    Creates measures in batch from a JSON array. One SaveChanges for all of them.
    Format: [{"name":"...","expression":"...","format_string":"0.0%",
              "display_folder":"...","description":"..."}, ...]
    'table' — the default host table (can be overridden by a 'table' field).
    """
    srv, model = _connect_tom()
    if not model:
        return "Error: Power BI Desktop is not open."
    try:
        items = json.loads(measures_json)
        done = []
        for it in items:
            tbl_name = it.get("table", table)
            t = _find_table(model, tbl_name)
            if t is None:
                return f"Error: table '{tbl_name}' not found (measure '{it.get('name')}')."
            _upsert_measure(t, it["name"], it["expression"],
                            it.get("format_string", ""),
                            it.get("display_folder", ""),
                            it.get("description", ""))
            done.append(it["name"])
        model.SaveChanges()
        return f"OK: measures created — {len(done)}: " + ", ".join(done)
    except Exception as e:
        return f"Batch-creation error: {str(e)}"
    finally:
        srv.Disconnect()


@mcp.tool()
def delete_measure(name: str) -> str:
    """Deletes a measure by name (searches all tables)."""
    srv, model = _connect_tom()
    if not model:
        return "Error: Power BI Desktop is not open."
    try:
        for t in model.Tables:
            for m in t.Measures:
                if m.Name == name:
                    t.Measures.Remove(m)
                    model.SaveChanges()
                    return f"OK: measure '{name}' deleted from '{t.Name}'."
        return f"Measure '{name}' not found."
    except Exception as e:
        return f"Deletion error: {str(e)}"
    finally:
        srv.Disconnect()


if __name__ == "__main__":
    mcp.run()
