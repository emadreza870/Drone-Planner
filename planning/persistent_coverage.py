"""
مدیریت پوشش سلولی و بازدید مجدد.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import math

from shapely.geometry import Polygon, Point
from shapely.geometry.base import BaseGeometry
from models.schedule import CellStatus
import logging

logger = logging.getLogger(__name__)


class PersistentCoverage:
    """سیستم پوشش مستمر مبتنی بر سلول‌های جغرافیایی."""

    def __init__(
        self,
        area_polygon: Polygon,
        cell_size_m: float,
    ):
        """
        Args:
            area_polygon: محدوده مجاز (سیستم متری).
            cell_size_m: اندازه هر سلول مربعی (متر).
        """
        self.area_polygon = area_polygon
        self.cell_size_m = cell_size_m
        self.cells: List[CellStatus] = []
        self._create_cells()

    def _create_cells(self) -> None:
        """تقسیم محدوده به سلول‌های مربعی و ساخت CellStatus."""
        bounds = self.area_polygon.bounds
        minx, miny, maxx, maxy = bounds
        width = maxx - minx
        height = maxy - miny

        # تعداد سلول‌ها در هر جهت
        n_cols = max(1, math.ceil(width / self.cell_size_m))
        n_rows = max(1, math.ceil(height / self.cell_size_m))

        for row in range(n_rows):
            for col in range(n_cols):
                x0 = minx + col * self.cell_size_m
                y0 = miny + row * self.cell_size_m
                x1 = min(x0 + self.cell_size_m, maxx)
                y1 = min(y0 + self.cell_size_m, maxy)
                cell_poly = Polygon([
                    (x0, y0), (x1, y0), (x1, y1), (x0, y1)
                ])
                # فقط سلول‌هایی که با محدوده مجاز تقاطع دارند
                if cell_poly.intersects(self.area_polygon):
                    # برش سلول با محدوده مجاز برای دقت بهتر
                    clipped = cell_poly.intersection(self.area_polygon)
                    if not clipped.is_empty:
                        cell_id = f"cell_{row:03d}_{col:03d}"
                        self.cells.append(CellStatus(
                            cell_id=cell_id,
                            polygon=clipped,
                            priority=1,
                            last_visit_time=None,
                            next_visit_time=None,
                            responsible_drone=None,
                            covered=False,
                        ))

    def update_visits(
        self,
        waypoints_m: List[Tuple[float, float]],
        drone_id: str,
        visit_time: datetime,
    ) -> None:
        """
        به‌روزرسانی زمان آخرین بازدید سلول‌هایی که نقاط مسیر در آن‌ها قرار دارند.

        Args:
            waypoints_m: نقاط مسیر (x, y) متری.
            drone_id: شناسه پهپاد.
            visit_time: زمان بازدید (مثلاً زمان شروع شیفت).
        """
        for cell in self.cells:
            # بررسی می‌کنیم آیا حداقل یک نقطه از مسیر داخل سلول است
            for point in waypoints_m:
                pt = Point(point[0], point[1])
                if cell.polygon.contains(pt) or cell.polygon.touches(pt):
                    cell.last_visit_time = visit_time
                    cell.responsible_drone = drone_id
                    cell.covered = True
                    break

    def get_overdue_cells(
        self,
        current_time: datetime,
        target_revisit_interval_min: float,
    ) -> List[CellStatus]:
        """
        شناسایی سلول‌هایی که زمان بازدید مجدد آن‌ها گذشته است.

        Args:
            current_time: زمان فعلی.
            target_revisit_interval_min: بازه هدف بازدید مجدد (دقیقه).

        Returns:
            List[CellStatus]: سلول‌های عقب‌افتاده.
        """
        overdue = []
        for cell in self.cells:
            if cell.last_visit_time is None:
                overdue.append(cell)
            else:
                elapsed = (current_time - cell.last_visit_time).total_seconds() / 60.0
                if elapsed > target_revisit_interval_min:
                    overdue.append(cell)
        return overdue

    def get_max_revisit_interval(self, current_time: datetime) -> float:
        """
        بیشترین زمان سپری‌شده از آخرین بازدید در بین همه سلول‌ها (دقیقه).

        Args:
            current_time: زمان فعلی.

        Returns:
            float: حداکثر بازه بازدید (دقیقه). اگر سلولی هرگز بازدید نشده باشد، None برگردانده می‌شود.
        """
        intervals = []
        for cell in self.cells:
            if cell.last_visit_time is not None:
                elapsed = (current_time - cell.last_visit_time).total_seconds() / 60.0
                intervals.append(elapsed)
        if not intervals:
            return float('inf')  # هیچ بازدیدی ثبت نشده است
        return max(intervals)

    def get_uncovered_cells(self) -> List[CellStatus]:
        """سلول‌هایی که هرگز بازدید نشده‌اند."""
        return [cell for cell in self.cells if cell.last_visit_time is None]