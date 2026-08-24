"""
بررسی محدودیت باتری و بازگشت پیشگیرانه.
"""

from typing import List, Tuple, Optional

from models.drone import Drone
from planning.mission_metrics import calculate_mission_metrics
from geo.measurements import distance_between_points


class BatteryCheckResult:
    """نتیجه بررسی باتری برای یک مأموریت."""
    def __init__(
        self,
        can_complete: bool,
        total_distance_m: float,
        total_duration_min: float,
        battery_remaining_percent: float,
        return_point_index: Optional[int] = None,
        return_reason: Optional[str] = None,
    ):
        self.can_complete = can_complete
        self.total_distance_m = total_distance_m
        self.total_duration_min = total_duration_min
        self.battery_remaining_percent = battery_remaining_percent
        self.return_point_index = return_point_index
        self.return_reason = return_reason


def check_battery(
    waypoints_m: List[Tuple[float, float]],
    drone: Drone,
    home_position_m: Tuple[float, float],
) -> BatteryCheckResult:
    """
    بررسی امکان‌پذیری مأموریت از نظر باتری و تعیین نقطه بازگشت در صورت نیاز.

    Args:
        waypoints_m: نقاط مسیر کامل شامل رفت از آشیانه، مأموریت و برگشت به آشیانه (x, y).
        drone: مشخصات پهپاد.
        home_position_m: مختصات آشیانه در سیستم متری.

    Returns:
        BatteryCheckResult: نتیجه بررسی.
    """
    if not waypoints_m:
        return BatteryCheckResult(False, 0.0, 0.0, 100.0, None, "empty_path")

    total_distance, total_duration_min = calculate_mission_metrics(waypoints_m, drone)

    # درصد باتری باقی‌مانده (بر اساس زمان کل پرواز بدون ذخیره)
    battery_remaining_percent = max(0.0, 100.0 * (1.0 - total_duration_min / drone.max_flight_time_min))

    # زمان مجاز پرواز با در نظر گرفتن ذخیره اضطراری
    allowed_flight_time = drone.max_flight_time_min - drone.reserve_time_min

    # اگر کل مسیر با ذخیره قابل انجام است
    if total_duration_min <= allowed_flight_time:
        return BatteryCheckResult(
            can_complete=True,
            total_distance_m=total_distance,
            total_duration_min=total_duration_min,
            battery_remaining_percent=battery_remaining_percent,
            return_point_index=None,
            return_reason=None,
        )

    # در غیر این صورت، شبیه‌سازی برای یافتن نقطه بازگشت
    elapsed_time_min = drone.takeoff_time_sec / 60.0
    # اگر حتی برخاست هم ممکن نباشد (نادر)
    if elapsed_time_min > allowed_flight_time:
        return BatteryCheckResult(
            can_complete=False,
            total_distance_m=0.0,
            total_duration_min=elapsed_time_min,
            battery_remaining_percent=max(0.0, 100.0 * (1.0 - elapsed_time_min / drone.max_flight_time_min)),
            return_point_index=0,
            return_reason="takeoff_not_possible",
        )

    # پیمایش نقاط مسیر
    distance_covered = 0.0
    current_pos = waypoints_m[0]
    early_return_triggered = False

    for i in range(1, len(waypoints_m)):
        next_pos = waypoints_m[i]
        segment_dist = distance_between_points(current_pos, next_pos)
        segment_time = segment_dist / drone.speed_mps / 60.0

        # حرکت به نقطه بعدی
        distance_covered += segment_dist
        elapsed_time_min += segment_time

        # بررسی امکان بازگشت از این نقطه
        dist_to_home = distance_between_points(next_pos, home_position_m)
        return_time_min = dist_to_home / drone.speed_mps / 60.0
        landing_time_min = drone.landing_time_sec / 60.0
        required_time = elapsed_time_min + return_time_min + landing_time_min + drone.reserve_time_min

        if required_time > drone.max_flight_time_min:
            # باید از نقطه قبلی (current_pos) بازگردد
            return_index = i - 1
            distance_until_return = distance_covered - segment_dist
            elapsed_until_return = elapsed_time_min - segment_time
            battery_remaining_percent = max(0.0, 100.0 * (1.0 - elapsed_until_return / drone.max_flight_time_min))
            early_return_triggered = True
            return BatteryCheckResult(
                can_complete=False,
                total_distance_m=distance_until_return,
                total_duration_min=elapsed_until_return,
                battery_remaining_percent=battery_remaining_percent,
                return_point_index=return_index,
                return_reason="low_battery_early_return",
            )

        current_pos = next_pos

    # اگر به اینجا برسیم، یعنی کل مسیر پیموده شده ولی زمان کل از allowed بیشتر بوده است
    # (یعنی ذخیره اضطراری مصرف شده است)
    return BatteryCheckResult(
        can_complete=False,
        total_distance_m=total_distance,
        total_duration_min=total_duration_min,
        battery_remaining_percent=battery_remaining_percent,
        return_point_index=None,
        return_reason="reserve_time_violated",
    )