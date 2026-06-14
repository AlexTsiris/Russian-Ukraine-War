# -*- coding: utf-8 -*-
"""
Builds a SELF-CONTAINED Deneb spec (geometry embedded inline) so the map works without
hosting the GeoJSON anywhere. You only need to paste it into Deneb.
Geometry is simplified more aggressively (for a compact paste). The slicer on snapshot_date
works the same way (lookup against the Power BI dataset). For auto-updating, use the
URL version (frontline_deneb_spec.json) + frontline_autoupdate/.

Run:    python make_deneb_inline.py
Output: frontline_deneb_spec_inline.json
"""
import json
import os

from shapely.geometry import shape, mapping
from shapely import set_precision

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "frontline.geojson")
UKRAINE = os.path.join(HERE, "ukraine_outline.json")
OUT = os.path.join(HERE, "frontline_deneb_spec_inline.json")
SIMPLIFY = 0.025   # ~2.5 km: compact for inline use, not noticeable on an overview map

SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"


def main():
    fc = json.load(open(SRC, encoding="utf-8"))
    feats = []
    for f in fc["features"]:
        g = shape(f["geometry"]).simplify(SIMPLIFY, preserve_topology=True)
        g = set_precision(g, 0.001)            # ~110 m rounding -> shorter
        feats.append({"type": "Feature", "properties": f["properties"],
                      "geometry": mapping(g)})

    ukraine = json.load(open(UKRAINE, encoding="utf-8"))
    ukraine["properties"] = {"kind": "ukraine"}
    for f in feats:
        f["properties"]["kind"] = "occupied"

    # ONE layer (Ukraine + occupied together): the projection auto-fits to the whole set =>
    # the full country, and both are guaranteed to share one coordinate system (no mismatch).
    spec = {
        "$schema": SCHEMA,
        "description": "Occupied territory of Ukraine over time on a full-country silhouette "
                       "(single layer => shared projection). Date from Power BI slicer "
                       "(text snapshot_date). Source: DeepStateMap.live.",
        "width": "container", "height": "container", "background": "transparent",
        "config": {"view": {"stroke": None}, "font": "Segoe UI"},
        "datasets": {"features": [ukraine] + feats},
        "projection": {"type": "mercator"},
        "layer": [
            {"data": {"name": "features"},
             "transform": [
                 {"lookup": "properties.date",
                  "from": {"data": {"name": "dataset"}, "key": "snapshot_date",
                           "fields": ["snapshot_date"]}, "as": "sel"},
                 {"filter": "datum.properties.kind == 'ukraine' || isValid(datum.sel)"}],
             "mark": {"type": "geoshape", "strokeWidth": 0.6},
             "encoding": {
                 "color": {"field": "properties.kind", "type": "nominal",
                           "scale": {"domain": ["ukraine", "occupied"],
                                     "range": ["#2A2A30", "#D04949"]},
                           "legend": None},
                 "fillOpacity": {"condition": {"test": "datum.properties.kind == 'ukraine'",
                                               "value": 0.5}, "value": 0.82},
                 "stroke": {"field": "properties.kind", "type": "nominal",
                            "scale": {"domain": ["ukraine", "occupied"],
                                      "range": ["#6E5F60", "#7A1F1F"]},
                            "legend": None},
                 "tooltip": [
                     {"field": "properties.date", "type": "nominal", "title": "Date"},
                     {"field": "properties.occupied_km2", "type": "quantitative",
                      "title": "Occupied (sq.km)", "format": ",.0f"}]}}
        ]
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK -> {OUT}  ({os.path.getsize(OUT)//1024:,} KB, {len(feats)} months)")


if __name__ == "__main__":
    main()
