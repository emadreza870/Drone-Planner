"""
تولید خروجی GeoJSON از مسیرها و مناطق.
"""

import json
from typing import List, Tuple, Dict, Any, Optional
from shapely.geometry import mapping, LineString, Point, Polygon


def _convert_coords_to_lists(geom: Dict) -> Dict:
    """
    تبدیل همه مختصات داخل geometry از tuple به list برای سازگاری با استاندارد GeoJSON.
    """
    if "coordinates" in geom:
        def convert(obj):
            if isinstance(obj, tuple):
                return [convert(item) for item in obj]
            elif isinstance(obj, list):
                return [convert(item) for item in obj]
            else:
                return obj
        geom["coordinates"] = convert(geom["coordinates"])
    return geom


def polygon_to_geojson(polygon: Polygon, properties: Optional[Dict] = None) -> Dict:
    """تبدیل Shapely Polygon به Feature GeoJSON."""
    geom = mapping(polygon)
    geom = _convert_coords_to_lists(geom)
    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": geom,
    }


def points_to_geojson_line(
    points_wgs84: List[Tuple[float, float]],
    properties: Optional[Dict] = None,
) -> Dict:
    """
    تبدیل لیست نقاط (lat, lon) به Feature از نوع LineString.
    ورودی باید (lat, lon) باشد و در خروجی مختصات به صورت [lon, lat] خواهد بود.
    """
    line = LineString([(lon, lat) for lat, lon in points_wgs84])
    geom = mapping(line)
    geom = _convert_coords_to_lists(geom)
    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": geom,
    }


def create_feature_collection(features: List[Dict]) -> Dict:
    """ساخت FeatureCollection از لیست Featureها."""
    return {
        "type": "FeatureCollection",
        "features": features,
    }