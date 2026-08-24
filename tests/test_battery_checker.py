"""
تست‌های بررسی باتری و بازگشت پیشگیرانه.
"""

import math
import pytest
from models.drone import Drone
from planning.battery_checker import check_battery
from planning.mission_metrics import calculate_mission_metrics


def make_drone(
    max_flight_time_min=30,
    speed_mps=5,
    reserve_time_min=5,
    takeoff_time_sec=30,
    landing_time_sec=30,
):
    return Drone(
        drone_id="test",
        max_flight_time_min=max_flight_time_min,
        speed_mps=speed_mps,
        altitude_m=80,
        reserve_time_min=reserve_time_min,
        takeoff_time_sec=takeoff_time_sec,
        landing_time_sec=landing_time_sec,
        status="available",
    )


def test_calculate_metrics():
    drone = make_drone(speed_mps=10)
    waypoints = [(0, 0), (100, 0), (0, 0)]
    dist, dur = calculate_mission_metrics(waypoints, drone)
    assert dist == 200.0
    # پرواز: 200/10=20 ثانیه + برخاست 30 + فرود 30 = 80 ثانیه = 1.333 دقیقه
    expected_dur = (20 + 60) / 60.0
    assert math.isclose(dur, expected_dur, rel_tol=1e-6)


def test_mission_feasible():
    drone = make_drone(max_flight_time_min=10, speed_mps=10, reserve_time_min=1)
    home = (0, 0)
    waypoints = [home, (100, 0), (0, 0), home]  # مسافت 200 متر
    result = check_battery(waypoints, drone, home)
    assert result.can_complete is True
    assert result.return_point_index is None
    assert result.battery_remaining_percent > 50


def test_mission_not_feasible_short_battery():
    drone = make_drone(max_flight_time_min=2, speed_mps=5, reserve_time_min=0.5)
    home = (0, 0)
    waypoints = [home, (500, 0), home]  # مسافت 1000 متر
    result = check_battery(waypoints, drone, home)
    assert result.can_complete is False
    assert result.return_reason is not None


def test_early_return_point():
    drone = make_drone(
        max_flight_time_min=3,
        speed_mps=1,
        reserve_time_min=0.5,
        takeoff_time_sec=10,
        landing_time_sec=10,
    )
    home = (0, 0)
    waypoints = [home, (10, 0), (200, 0), home]
    result = check_battery(waypoints, drone, home)
    assert result.can_complete is False
    assert result.return_point_index is not None
    assert result.return_point_index < len(waypoints) - 1