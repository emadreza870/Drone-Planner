"""
تست‌های تبدیل سیستم مختصات.
"""

from shapely.geometry import Point, Polygon
from geo.projection import (
    get_utm_epsg,
    get_utm_crs,
    wgs84_to_utm,
    utm_to_wgs84,
)
import math


def test_get_utm_epsg_north():
    """برای طول 51 و عرض 35 باید EPSG:32639 باشد."""
    epsg = get_utm_epsg(longitude=51.0, latitude=35.0)
    assert epsg == 32639


def test_get_utm_epsg_south():
    """برای عرض منفی باید EPSG:327xx باشد."""
    epsg = get_utm_epsg(longitude=151.0, latitude=-33.0)
    assert epsg == 32756  # Sydney area zone 56 south


def test_wgs84_to_utm_and_back_point():
    """تبدیل یک نقطه از WGS84 به UTM و برعکس."""
    point_wgs = Point(51.0, 35.0)  # طول، عرض
    point_utm = wgs84_to_utm(point_wgs)
    # پس از تبدیل، مختصات باید متری باشند و فاصله از مبدأ زیاد نباشد (حدود چند صد کیلومتر)
    assert point_utm.x > 100000
    assert point_utm.y > 100000

    # تبدیل برعکس
    src_crs = get_utm_crs(51.0, 35.0)
    point_back = utm_to_wgs84(point_utm, src_crs)
    # خطای تقریبی
    assert math.isclose(point_back.x, point_wgs.x, abs_tol=1e-6)
    assert math.isclose(point_back.y, point_wgs.y, abs_tol=1e-6)


def test_wgs84_to_utm_polygon():
    """تبدیل یک Polygon و بررسی حفظ مساحت تقریبی."""
    poly_wgs = Polygon([(51.0, 35.0), (51.01, 35.0), (51.01, 35.01), (51.0, 35.01)])
    poly_utm = wgs84_to_utm(poly_wgs)
    # مساحت باید تقریباً برابر باشد (حدود 1km x 1km = 1e6 m^2)
    assert poly_utm.area > 900000  # با خطای کمی
    assert poly_utm.area < 1100000