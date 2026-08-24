"""
تست‌های نمایش نقشه (بررسی اینکه بدون خطا اجرا می‌شود).
"""

import folium
from visualization.map_view import create_map, add_marker, add_route_to_map


def test_create_map():
    m = create_map(center=(35.0, 51.0), zoom_start=12)
    assert isinstance(m, folium.Map)


def test_add_marker():
    m = create_map(center=(35.0, 51.0))
    add_marker(m, 35.0, 51.0, popup_text="Test", icon_color="red")
    # می‌توانیم بررسی کنیم که مارکر اضافه شده است (چون folium مستقیماً لیست ندارد، فقط اجرای بدون خطا کافی است)
    assert True


def test_add_route_to_map():
    m = create_map(center=(35.0, 51.0))
    points = [(35.0, 51.0), (35.001, 51.001)]
    add_route_to_map(m, points, color="green")
    assert True