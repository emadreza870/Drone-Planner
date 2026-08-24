"""
نمایش مسیرها روی نقشه با Folium.
"""

import folium
from typing import List, Tuple, Optional
import json


def create_map(
    center: Tuple[float, float],
    zoom_start: int = 12,
) -> folium.Map:
    """
    ایجاد نقشه Folium با مرکز مشخص.

    Args:
        center: (lat, lon) مرکز نقشه.
        zoom_start: سطح زوم.

    Returns:
        folium.Map: شئ نقشه.
    """
    return folium.Map(location=center, zoom_start=zoom_start)


def add_polygon_to_map(
    m: folium.Map,
    polygon_geojson: dict,
    color: str = "blue",
    fill_color: str = "blue",
    weight: int = 2,
    fill_opacity: float = 0.1,
) -> None:
    """افزودن Polygon به نقشه."""
    folium.GeoJson(
        polygon_geojson,
        style_function=lambda x, color=color, fill_color=fill_color, weight=weight, fill_opacity=fill_opacity: {
            "color": color,
            "fillColor": fill_color,
            "weight": weight,
            "fillOpacity": fill_opacity,
        }
    ).add_to(m)


def add_marker(
    m: folium.Map,
    lat: float,
    lon: float,
    popup_text: str = "",
    icon_color: str = "red",
) -> None:
    """افزودن مارکر به نقشه."""
    folium.Marker(
        [lat, lon],
        popup=popup_text,
        icon=folium.Icon(color=icon_color),
    ).add_to(m)


def add_route_to_map(
    m: folium.Map,
    points_wgs84: List[Tuple[float, float]],  # (lat, lon)
    color: str = "green",
    weight: int = 3,
    opacity: float = 0.8,
) -> None:
    """افزودن مسیر به نقشه."""
    if not points_wgs84:
        return
    folium.PolyLine(
        points_wgs84,
        color=color,
        weight=weight,
        opacity=opacity,
    ).add_to(m)