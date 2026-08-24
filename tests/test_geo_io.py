"""
تست‌های مربوط به خواندن GeoJSON و استخراج Polygon.
"""

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from geo.io import read_area_polygon, read_no_fly_zones, read_geojson


def test_read_geojson_simple(tmp_path):
    """خواندن یک فایل GeoJSON ساده."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                }
            }
        ]
    }
    file = tmp_path / "area.geojson"
    file.write_text(json.dumps(geojson), encoding='utf-8')
    data = read_geojson(str(file))
    assert data["type"] == "FeatureCollection"


def test_read_area_polygon_valid(tmp_path):
    """استخراج Polygon از FeatureCollection."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]]
                }
            }
        ]
    }
    file = tmp_path / "area.geojson"
    file.write_text(json.dumps(geojson), encoding='utf-8')
    poly = read_area_polygon(str(file))
    assert isinstance(poly, Polygon)
    assert poly.area == 4.0  # مساحت 2x2


def test_read_area_polygon_invalid_type(tmp_path):
    """خواندن فایلی که geometry آن Polygon نیست باید خطا بدهد."""
    geojson = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Point",
            "coordinates": [0, 0]
        }
    }
    file = tmp_path / "invalid.geojson"
    file.write_text(json.dumps(geojson), encoding='utf-8')
    with pytest.raises(ValueError):
        read_area_polygon(str(file))


def test_read_no_fly_zones(tmp_path):
    """خواندن مناطق ممنوعه از GeoJSON."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.5, 0.5], [0.5, 1.5], [1.5, 1.5], [1.5, 0.5], [0.5, 0.5]]]
                }
            }
        ]
    }
    file = tmp_path / "nfz.geojson"
    file.write_text(json.dumps(geojson), encoding='utf-8')
    zones = read_no_fly_zones(str(file))
    assert len(zones) == 1
    assert isinstance(zones[0], Polygon)