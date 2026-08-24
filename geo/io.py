"""
خواندن و استخراج داده‌های جغرافیایی از فایل‌های GeoJSON.
"""

import json
from pathlib import Path
from typing import List

from shapely.geometry import Polygon, MultiPolygon, shape


def read_geojson(file_path: str) -> dict:
    """
    خواندن یک فایل GeoJSON و بازگرداندن محتوای JSON.

    Args:
        file_path: مسیر فایل.

    Returns:
        dict: دیکشنری حاوی داده‌های GeoJSON.

    Raises:
        FileNotFoundError: اگر فایل وجود نداشته باشد.
        json.JSONDecodeError: اگر فایل معتبر نباشد.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"فایل GeoJSON یافت نشد: {file_path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _extract_polygon_from_geometry(geometry: dict) -> Polygon:
    """
    تبدیل geometry از GeoJSON به شئ Polygon.
    اگر geometry از نوع MultiPolygon باشد، بزرگ‌ترین Polygon را برمی‌گرداند.

    Args:
        geometry: دیکشنری geometry استاندارد GeoJSON.

    Returns:
        Polygon: چندضلعی استخراج‌شده.

    Raises:
        ValueError: اگر geometry نوع Polygon یا MultiPolygon نباشد.
    """
    geom_type = geometry.get("type")
    if geom_type == "Polygon":
        return shape(geometry)
    elif geom_type == "MultiPolygon":
        multi = shape(geometry)
        # انتخاب بزرگ‌ترین چندضلعی
        largest = max(multi.geoms, key=lambda p: p.area)
        return largest
    else:
        raise ValueError(f"نوع geometry باید Polygon یا MultiPolygon باشد، اما {geom_type} دریافت شد.")


def read_area_polygon(file_path: str) -> Polygon:
    """
    خواندن یک فایل GeoJSON که شامل محدوده مجاز است.
    انتظار می‌رود فایل شامل یک FeatureCollection با حداقل یک Feature باشد.
    اولین Feature (یا Feature با بیشترین مساحت) به عنوان محدوده مجاز در نظر گرفته می‌شود.

    Args:
        file_path: مسیر فایل GeoJSON.

    Returns:
        Polygon: چندضلعی محدوده مجاز.
    """
    data = read_geojson(file_path)

    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        if not features:
            raise ValueError("هیچ Feature در GeoJSON یافت نشد.")
        # اگر چند Feature باشد، یکی با بیشترین مساحت را انتخاب کن
        polygons = []
        for feat in features:
            geom = feat.get("geometry")
            if geom is not None:
                try:
                    polygons.append(_extract_polygon_from_geometry(geom))
                except ValueError:
                    continue
        if not polygons:
            raise ValueError("هیچ Polygon یا MultiPolygon در FeatureCollection یافت نشد.")
        return max(polygons, key=lambda p: p.area)
    elif data.get("type") == "Feature":
        geom = data.get("geometry")
        if geom is None:
            raise ValueError("Feature هندسه ندارد.")
        return _extract_polygon_from_geometry(geom)
    elif data.get("type") == "Polygon":
        return _extract_polygon_from_geometry(data)
    else:
        raise ValueError("ساختار GeoJSON پشتیبانی نمی‌شود. از FeatureCollection، Feature یا Polygon استفاده کنید.")


def read_no_fly_zones(file_path: str) -> List[Polygon]:
    """
    خواندن فایل GeoJSON شامل مناطق ممنوعه.
    هر Feature با geometry از نوع Polygon یا MultiPolygon به عنوان یک منطقه ممنوعه در نظر گرفته می‌شود.

    Args:
        file_path: مسیر فایل GeoJSON.

    Returns:
        List[Polygon]: لیست چندضلعی‌های مناطق ممنوعه.
    """
    data = read_geojson(file_path)
    zones = []
    if data.get("type") == "FeatureCollection":
        for feat in data.get("features", []):
            geom = feat.get("geometry")
            if geom is not None:
                try:
                    poly = _extract_polygon_from_geometry(geom)
                    zones.append(poly)
                except ValueError:
                    continue
    elif data.get("type") == "Feature":
        geom = data.get("geometry")
        if geom is not None:
            zones.append(_extract_polygon_from_geometry(geom))
    elif data.get("type") == "Polygon":
        zones.append(_extract_polygon_from_geometry(data))
    else:
        raise ValueError("ساختار GeoJSON پشتیبانی نمی‌شود.")
    return zones