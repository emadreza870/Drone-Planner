"""
زمان‌بندی شیفت‌ها و تخصیص پهپادها در هر شیفت.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging

from models.drone import Drone
from models.schedule import Shift, DronePlan
from models.mission import MissionConfig
from planning.mission_metrics import calculate_mission_metrics
from planning.route_connector import combine_full_route
from geo.measurements import path_length_meters

logger = logging.getLogger(__name__)


class ShiftScheduler:
    """برنامه‌ریز شیفت‌های کاری برای مأموریت چندپهپادی."""

    def __init__(
        self,
        drones: List[Drone],
        mission_config: MissionConfig,
        home_m: Tuple[float, float],
        coverage_path_m: List[Tuple[float, float]],
        allocations: Optional[Dict[str, List[Tuple[float, float]]]] = None,
    ):
        """
        Args:
            drones: لیست پهپادهای موجود.
            mission_config: پیکربندی مأموریت (شامل shift_duration_min).
            home_m: مختصات آشیانه (x, y) متری.
            coverage_path_m: مسیر کامل پوشش (نقاط متری).
            allocations: تخصیص اولیه مسیر به پهپادها (اختیاری).
                         اگر None باشد، کل مسیر به اولین پهپاد داده می‌شود.
        """
        self.drones = drones
        self.mission_config = mission_config
        self.home_m = home_m
        self.coverage_path_m = coverage_path_m
        self.allocations = allocations if allocations is not None else {
            drones[0].drone_id: coverage_path_m
        }
        self.shift_duration_min = mission_config.shift_duration_min

    def _split_path_for_shift(
        self,
        path_m: List[Tuple[float, float]],
        drone: Drone,
        max_mission_time_min: float,
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        تقسیم یک مسیر به دو بخش: بخشی که در زمان مجاز شیفت انجام می‌شود و باقی‌مانده.

        Args:
            path_m: مسیر مأموریت (بدون رفت و برگشت به آشیانه).
            drone: پهپاد مربوطه.
            max_mission_time_min: حداکثر زمان مجاز برای بخش اول (دقیقه).

        Returns:
            Tuple[List, List]: (بخش اول، بخش باقی‌مانده)
        """
        if not path_m or len(path_m) < 2:
            return path_m, []

        # زمان برخاست و فرود را جدا حساب می‌کنیم
        takeoff_landing_time_min = (drone.takeoff_time_sec + drone.landing_time_sec) / 60.0
        available_flight_time = max_mission_time_min - takeoff_landing_time_min
        if available_flight_time <= 0:
            # حتی برخاست و فرود هم ممکن نیست
            return [], path_m

        # پیمایش نقاط مسیر و محاسبه زمان تجمعی
        cumulative_time = 0.0
        last_included_index = 0  # آخرین نقطه‌ای که شامل می‌شود
        for i in range(1, len(path_m)):
            dist = ((path_m[i][0] - path_m[i-1][0])**2 + (path_m[i][1] - path_m[i-1][1])**2) ** 0.5
            seg_time = dist / drone.speed_mps / 60.0
            if cumulative_time + seg_time > available_flight_time:
                # این قطعه کامل جا نمی‌شود؛ توقف در نقطه قبلی
                break
            cumulative_time += seg_time
            last_included_index = i

        # بخش اول شامل نقاط از 0 تا last_included_index
        first_part = path_m[:last_included_index + 1]
        # بخش دوم از نقطه‌ای که توقف کرده‌ایم تا انتها (با احتساب نقطه مشترک)
        second_part = path_m[last_included_index:] if last_included_index < len(path_m) - 1 else []

        # اگر بخش اول فقط یک نقطه باشد، عملاً مأموریتی انجام نشده است
        if len(first_part) < 2:
            return [], path_m

        return first_part, second_part

    def create_shifts(
        self,
        start_time: Optional[datetime] = None,
    ) -> List[Shift]:
        """
        تولید لیست شیفت‌ها با برنامه هر پهپاد.

        Args:
            start_time: زمان شروع اولین شیفت (پیش‌فرض: اکنون).

        Returns:
            List[Shift]: لیست شیفت‌ها.
        """
        if start_time is None:
            start_time = datetime.now()

        shifts: List[Shift] = []
        current_time = start_time

        # نگاشت از drone_id به مسیر باقی‌مانده
        remaining_paths = {
            drone.drone_id: self.allocations.get(drone.drone_id, [])
            for drone in self.drones
        }

        shift_counter = 1
        while any(len(path) >= 2 for path in remaining_paths.values()):
            shift_drones: List[DronePlan] = []
            shift_end_time = current_time + timedelta(minutes=self.shift_duration_min)

            for drone in self.drones:
                drone_id = drone.drone_id
                path = remaining_paths.get(drone_id, [])
                if len(path) < 2:
                    # این پهپاد کاری ندارد
                    continue

                # مسیر کامل شامل رفت و برگشت به آشیانه
                full_route = combine_full_route(self.home_m, path)
                total_dist, total_dur = calculate_mission_metrics(full_route, drone)

                if total_dur <= self.shift_duration_min:
                    # کل مسیر باقی‌مانده در این شیفت انجام می‌شود
                    planned_path = path
                    remaining_paths[drone_id] = []  # تمام شد
                else:
                    # باید تقسیم شود
                    first_part, second_part = self._split_path_for_shift(
                        path, drone, self.shift_duration_min
                    )
                    planned_path = first_part
                    remaining_paths[drone_id] = second_part

                if len(planned_path) < 2:
                    continue

                # ساخت DronePlan
                full_route_planned = combine_full_route(self.home_m, planned_path)
                dist, dur = calculate_mission_metrics(full_route_planned, drone)
                drone_plan = DronePlan(
                    drone_id=drone_id,
                    status="planned",
                    distance_m=dist,
                    duration_min=dur,
                    estimated_battery_remaining_percent=max(
                        0.0, 100.0 * (1.0 - dur / drone.max_flight_time_min)
                    ),
                    return_reason=None,
                    waypoints=[],  # در این مرحله نقاط راه را با مختصات WGS84 پر نمی‌کنیم
                )
                shift_drones.append(drone_plan)

            if not shift_drones:
                # پیشرفت نکردیم، جلوگیری از حلقه بی‌نهایت
                logger.warning("هیچ پهپادی در این شیفت برنامه‌ریزی نشد.")
                break

            shift = Shift(
                shift_id=f"shift_{shift_counter:02d}",
                start_time=current_time,
                end_time=shift_end_time,
                drones=shift_drones,
            )
            shifts.append(shift)
            shift_counter += 1
            current_time = shift_end_time

        return shifts