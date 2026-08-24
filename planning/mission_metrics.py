"""
محاسبات پایه مسافت و زمان مأموریت.
"""

from typing import List, Tuple

from models.drone import Drone
from geo.measurements import path_length_meters


def calculate_mission_metrics(
    waypoints_m: List[Tuple[float, float]],
    drone: Drone,
) -> Tuple[float, float]:
    """
    محاسبه مسافت کل و مدت زمان پرواز (بدون در نظر گرفتن بازگشت زودرس).

    Args:
        waypoints_m: نقاط مسیر به ترتیب (x, y متری).
        drone: شیء پهپاد.

    Returns:
        Tuple[float, float]: (total_distance_m, total_duration_min)
    """
    total_distance = path_length_meters(waypoints_m)
    flight_time_sec = total_distance / drone.speed_mps
    total_time_sec = flight_time_sec + drone.takeoff_time_sec + drone.landing_time_sec
    total_duration_min = total_time_sec / 60.0
    return total_distance, total_duration_min