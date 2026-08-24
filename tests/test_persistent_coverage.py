"""
تست‌های پوشش مستمر و سلول‌بندی.
"""

from datetime import datetime, timedelta
import pytest

from shapely.geometry import Polygon
from planning.persistent_coverage import PersistentCoverage


def test_create_cells():
    area = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
    pc = PersistentCoverage(area, cell_size_m=10)
    # انتظار 4 سلول (2x2)
    assert len(pc.cells) == 4


def test_update_visits():
    area = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
    pc = PersistentCoverage(area, cell_size_m=10)
    visit_time = datetime(2025, 1, 1, 8, 0, 0)
    # مسیر بازدید از سلول پایین-چپ
    waypoints = [(1, 1), (2, 2)]
    pc.update_visits(waypoints, drone_id="d1", visit_time=visit_time)
    # سلول‌های بازدید شده باید last_visit_time داشته باشند
    visited = [c for c in pc.cells if c.last_visit_time is not None]
    assert len(visited) >= 1
    # سلول‌های دیگر بازدید نشده‌اند
    unvisited = pc.get_uncovered_cells()
    assert len(unvisited) == 3  # 4-1


def test_overdue_cells():
    area = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
    pc = PersistentCoverage(area, cell_size_m=10)
    now = datetime(2025, 1, 1, 10, 0, 0)
    # فقط یک سلول را بازدید می‌کنیم
    pc.update_visits([(1, 1)], "d1", visit_time=now - timedelta(minutes=30))
    # بازه هدف 15 دقیقه
    overdue = pc.get_overdue_cells(now, target_revisit_interval_min=15)
    # سلول بازدید شده بیش از 15 دقیقه پیش بازدید شده است، بنابراین باید در لیست باشد
    assert any(c.last_visit_time is not None for c in overdue)
    # سلول‌های بازدید نشده هم باید در لیست باشند
    assert any(c.last_visit_time is None for c in overdue)
    # تعداد کل سلول‌های عقب‌افتاده باید 4 باشد (همه سلول‌ها)
    assert len(overdue) == 4


def test_max_revisit_interval():
    area = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
    pc = PersistentCoverage(area, cell_size_m=10)
    now = datetime(2025, 1, 1, 10, 0, 0)
    pc.update_visits([(1, 1)], "d1", visit_time=now - timedelta(minutes=10))
    # ماکزیمم بازه = 10 دقیقه (اگر سلول‌های دیگر None باشند، None را نادیده می‌گیریم)
    max_interval = pc.get_max_revisit_interval(now)
    assert max_interval == 10.0