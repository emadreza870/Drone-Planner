"""
تست‌های ماژول‌های خروجی.
"""

import json
from shapely.geometry import Polygon, Point
from exporters.geojson_exporter import polygon_to_geojson, points_to_geojson_line, create_feature_collection
from exporters.json_exporter import mission_plan_to_dict
from models.schedule import MissionPlan, Shift, DronePlan
from models.waypoint import Waypoint
from datetime import datetime


def test_polygon_to_geojson():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    feature = polygon_to_geojson(poly, properties={"type": "area"})
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["type"] == "area"


def test_points_to_geojson_line():
    pts = [(35.0, 51.0), (35.1, 51.1)]
    feature = points_to_geojson_line(pts, properties={"type": "route"})
    assert feature["geometry"]["type"] == "LineString"
    # مختصات در GeoJSON باید [lon, lat] باشد
    assert feature["geometry"]["coordinates"][0] == [51.0, 35.0]


def test_mission_plan_to_dict():
    plan = MissionPlan(
        mission_id="test_001",
        created_at="2025-01-01T00:00:00",
    )
    data = mission_plan_to_dict(plan)
    assert data["mission_id"] == "test_001"
    assert "shifts" in data