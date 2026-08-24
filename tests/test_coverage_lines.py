"""
تست‌های تولید خطوط موازی و مرتب‌سازی.
"""

import math
from shapely.geometry import Polygon, LineString

from geo.coverage_lines import (
    generate_parallel_lines,
    get_intersections_with_polygon,
    order_segments_boustrophedon,
    create_waypoints_from_segments,
)


def test_generate_parallel_lines():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    lines = generate_parallel_lines(poly, spacing_m=2, angle_deg=0)
    # برای مربع 10x10 با فاصله 2، حدود 5 خط داخل محدوده باید باشد
    assert len(lines) >= 5
    # خطوط باید افقی باشند (y ثابت)
    for line in lines:
        y = line.coords[0][1]
        assert abs(line.coords[0][1] - line.coords[-1][1]) < 1e-9


def test_intersections_with_polygon():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    lines = generate_parallel_lines(poly, spacing_m=5, angle_deg=0)
    segments = get_intersections_with_polygon(poly, lines)
    # باید 3 خط (در y=2.5، 5، 7.5) داشته باشیم
    assert len(segments) == 3
    # طول هر قطعه باید 10 باشد
    for seg in segments:
        assert abs(seg.length - 10.0) < 1e-9


def test_order_segments_boustrophedon():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    lines = generate_parallel_lines(poly, spacing_m=5, angle_deg=0)
    segments = get_intersections_with_polygon(poly, lines)
    ordered = order_segments_boustrophedon(segments)
    # باید 3 قطعه مرتب شده باشند
    assert len(ordered) == 3
    # جهت قطعات باید معکوس متناوب باشد (بررسی y مرکزها)
    centers_y = [seg.centroid.y for seg in ordered]
    # مراکز باید صعودی یا نزولی باشند
    assert centers_y == sorted(centers_y) or centers_y == sorted(centers_y, reverse=True)


def test_create_waypoints_from_segments():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    lines = generate_parallel_lines(poly, spacing_m=5, angle_deg=0)
    segments = get_intersections_with_polygon(poly, lines)
    ordered = order_segments_boustrophedon(segments)
    points = create_waypoints_from_segments(ordered)
    # تعداد نقاط باید حداقل 4 باشد (3 قطعه * 2 - 2 اتصال)
    assert len(points) >= 4