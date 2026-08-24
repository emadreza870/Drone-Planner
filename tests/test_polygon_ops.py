"""
تست‌های اعتبارسنجی و عملیات چندضلعی.
"""

import pytest
from shapely.geometry import Polygon

from geo.polygon_ops import validate_polygon, repair_polygon, subtract_no_fly_zones


def test_validate_valid_polygon():
    poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
    assert validate_polygon(poly) is True


def test_validate_invalid_polygon():
    # خودتقاطع (bow-tie)
    poly = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])
    assert validate_polygon(poly) is False


def test_repair_invalid_polygon():
    poly = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])
    repaired = repair_polygon(poly)
    assert repaired.is_valid


def test_subtract_no_fly_zones():
    area = Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])
    nfz = Polygon([(4, 4), (4, 6), (6, 6), (6, 4)])
    result = subtract_no_fly_zones(area, [nfz])
    # مساحت باید 100 - 4 = 96 باشد
    assert result.area == 96.0
    # باید داخل محدوده بماند
    assert result.within(area)