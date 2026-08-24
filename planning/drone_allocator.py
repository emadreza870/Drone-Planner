"""
الگوریتم‌های تخصیص مسیر به چند پهپاد.
"""

from typing import List, Tuple, Dict, Optional
import math

from shapely.geometry import Polygon
from geo.measurements import distance_between_points, path_length_meters
from models.drone import Drone
import logging

logger = logging.getLogger(__name__)


class DroneAllocator:
    """تقسیم مسیر پوشش بین چند پهپاد با روش‌های مختلف."""

    def __init__(
        self,
        waypoints: List[Tuple[float, float]],
        drones: List[Drone],
        home_m: Tuple[float, float],
        area_polygon: Optional[Polygon] = None,
    ):
        """
        Args:
            waypoints: نقاط مسیر کامل مأموریت (متر).
            drones: لیست پهپادهای موجود.
            home_m: مختصات آشیانه (x, y) برای روش سلولی.
            area_polygon: محدوده مجاز (برای سلول‌بندی)؛ اختیاری.
        """
        if not waypoints:
            raise ValueError("waypoints نمی‌تواند خالی باشد.")
        if not drones:
            raise ValueError("حداقل یک پهپاد لازم است.")
        self.waypoints = waypoints
        self.drones = drones
        self.home_m = home_m
        self.area_polygon = area_polygon
        self.n_drones = len(drones)

    def allocate_by_length(self) -> Dict[str, List[Tuple[float, float]]]:
        """
        تقسیم مسیر به بخش‌های با طول تقریباً مساوی بین پهپادها.

        Returns:
            Dict[str, List[Tuple[float, float]]]: نگاشت drone_id به لیست نقاط مأموریت.
        """
        total_length = path_length_meters(self.waypoints)
        if total_length <= 0:
            logger.warning("طول مسیر صفر است؛ تقسیم معنی‌دار نیست.")
            return {drone.drone_id: [] for drone in self.drones}

        target_length = total_length / self.n_drones
        allocations = {drone.drone_id: [] for drone in self.drones}

        current_drone_idx = 0
        current_segment_length = 0.0
        current_segment_start = self.waypoints[0]
        current_segment_points = [current_segment_start]

        for i in range(1, len(self.waypoints)):
            segment = distance_between_points(self.waypoints[i - 1], self.waypoints[i])
            # اگر افزودن این قطعه باعث عبور از target شود و پهپاد بعدی موجود باشد
            if current_segment_length + segment > target_length and current_drone_idx < self.n_drones - 1:
                # اتمام بخش فعلی
                # نقطه فعلی (waypoints[i-1]) آخرین نقطه بخش است
                allocations[self.drones[current_drone_idx].drone_id] = current_segment_points
                # شروع بخش جدید
                current_drone_idx += 1
                current_segment_length = 0.0
                current_segment_start = self.waypoints[i - 1]
                current_segment_points = [current_segment_start]
                # ادامه از همین نقطه (اتصال بین بخش‌ها)
                # مهم: نقطه مشترک بین دو بخش تکرار می‌شود تا هر بخش نقطه شروع و پایان خود را داشته باشد

            # افزودن نقطه بعدی
            current_segment_points.append(self.waypoints[i])
            current_segment_length += segment

        # افزودن بخش آخر
        allocations[self.drones[current_drone_idx].drone_id] = current_segment_points

        # پهپادهای بعدی (اگر تعداد پهپادها بیشتر از بخش‌های ایجادشده باشد) خالی می‌مانند
        for idx in range(current_drone_idx + 1, self.n_drones):
            drone_id = self.drones[idx].drone_id
            allocations[drone_id] = []

        return allocations

    def allocate_by_grid(self, n_cells_per_side: Optional[int] = None) -> Dict[str, List[Tuple[float, float]]]:
        """
        تقسیم محدوده به سلول‌های مربعی و تخصیص هر سلول به پهپاد بر اساس نزدیکی به آشیانه.
        برای سادگی، سلول‌ها را به ترتیب از نزدیک‌ترین به آشیانه تا دورترین مرتب می‌کنیم
        و به پهپادها به صورت گردشی اختصاص می‌دهیم.

        Args:
            n_cells_per_side: تعداد سلول در هر بعد (مثلاً 3 یعنی 9 سلول).
                اگر None باشد، به صورت خودکار بر اساس تعداد پهپادها محاسبه می‌شود.

        Returns:
            Dict[str, List[Tuple[float, float]]]: نگاشت drone_id به لیست نقاط مأموریت.
        """
        if self.area_polygon is None:
            # اگر محدوده داده نشده، bounding box نقاط مسیر را می‌گیریم
            minx = min(p[0] for p in self.waypoints)
            maxx = max(p[0] for p in self.waypoints)
            miny = min(p[1] for p in self.waypoints)
            maxy = max(p[1] for p in self.waypoints)
            bounds = (minx, miny, maxx, maxy)
        else:
            bounds = self.area_polygon.bounds

        if n_cells_per_side is None:
            # تعداد سلول‌ها حدوداً برابر تعداد پهپادها
            n_cells_per_side = max(1, math.ceil(math.sqrt(self.n_drones)))

        minx, miny, maxx, maxy = bounds
        width = maxx - minx
        height = maxy - miny
        if width <= 0 or height <= 0:
            raise ValueError("ابعاد محدوده صفر است؛ نمی‌توان سلول‌بندی کرد.")

        cell_width = width / n_cells_per_side
        cell_height = height / n_cells_per_side

        # ساخت سلول‌ها: هر سلول شامل لیست نقاط داخل آن
        cell_points = {}  # (row, col) -> list of point indices
        for idx, point in enumerate(self.waypoints):
            col = int((point[0] - minx) // cell_width)
            row = int((point[1] - miny) // cell_height)
            # محدود کردن اندیس به حداکثر
            col = min(col, n_cells_per_side - 1)
            row = min(row, n_cells_per_side - 1)
            cell = (row, col)
            if cell not in cell_points:
                cell_points[cell] = []
            cell_points[cell].append(idx)

        if not cell_points:
            logger.warning("هیچ نقطه‌ای در سلول‌ها قرار نگرفت.")
            return {drone.drone_id: [] for drone in self.drones}

        # محاسبه مرکز هر سلول و فاصله تا آشیانه
        cell_distances = []
        for (row, col), indices in cell_points.items():
            center_x = minx + (col + 0.5) * cell_width
            center_y = miny + (row + 0.5) * cell_height
            dist = distance_between_points((center_x, center_y), self.home_m)
            cell_distances.append((dist, (row, col), indices))

        # مرتب‌سازی سلول‌ها بر اساس فاصله (نزدیک‌ترین اول)
        cell_distances.sort(key=lambda x: x[0])

        # تخصیص گردشی به پهپادها
        allocations = {drone.drone_id: [] for drone in self.drones}
        drone_order = [drone.drone_id for drone in self.drones]
        drone_counter = 0
        for _, _, indices in cell_distances:
            drone_id = drone_order[drone_counter % self.n_drones]
            # افزودن نقاط با حفظ ترتیب اصلی مسیر
            for idx in sorted(indices):
                allocations[drone_id].append(self.waypoints[idx])
            drone_counter += 1

        return allocations