"""Geo helpers for farm boundary area."""
from __future__ import annotations

import math
from typing import Any


def polygon_area_ha(boundary: list[Any]) -> float:
    """Approximate polygon area in hectares from [{lat,lng}, ...] or [[lat,lng], ...]."""
    if not boundary or len(boundary) < 3:
        return 0.0
    pts = []
    for p in boundary:
        if isinstance(p, dict):
            pts.append((float(p["lat"]), float(p["lng"])))
        else:
            pts.append((float(p[0]), float(p[1])))
    lat0 = sum(p[0] for p in pts) / len(pts)
    cos_lat = math.cos(math.radians(lat0))
    m_per_deg_lat = 111320.0
    m_per_deg_lng = 111320.0 * cos_lat
    area = 0.0
    for i in range(len(pts)):
        lat1, lng1 = pts[i]
        lat2, lng2 = pts[(i + 1) % len(pts)]
        x1, y1 = lng1 * m_per_deg_lng, lat1 * m_per_deg_lat
        x2, y2 = lng2 * m_per_deg_lng, lat2 * m_per_deg_lat
        area += x1 * y2 - x2 * y1
    return abs(area / 2.0) / 10000.0
