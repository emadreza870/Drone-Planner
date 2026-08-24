"""
تست یکپارچه‌سازی کل خط لوله.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import pytest
from shapely.geometry import Polygon, Point

from models.drone import Drone
from models.mission import MissionConfig
from models.schedule import MissionPlan, Shift, DronePlan
from models.waypoint import Waypoint

from geo.projection import wgs84_to_utm, get_utm_crs
from planning.coverage_planner import CoveragePlanner, optimize_angle
from planning.drone_allocator import DroneAllocator
from planning.route_connector import combine_full_route
from planning.battery_checker import check_battery
from planning.shift_scheduler import ShiftScheduler
from geo.measurements import path_length_meters


def make_drones():
    return [
        Drone(
            drone_id="d1",
            max_flight_time_min=30,
            speed_mps=5,
            altitude_m=80,
            reserve_time_min=5,
            takeoff_time_sec=30,
            landing_time_sec=30,
        ),
        Drone(
            drone_id="d2",
            max_flight_time_min=30,
            speed_mps=5,
            altitude_m=80,
            reserve_time_min=5,
            takeoff_time_sec=30,
            landing_time_sec=30,
        ),
    ]


def make_mission_config():
    return MissionConfig(
        track_spacing_m=50,
        shift_duration_min=45,
        target_revisit_interval_min=60,
        default_altitude_m=80,
        default_speed_mps=5,
        reserve_time_min=5,
        takeoff_time_sec=30,
        landing_time_sec=30,
    )


def test_full_pipeline():
    """اجرای کامل خط لوله با یک محدوده مستطیلی کوچک."""
    # محدوده WGS84 (کوچک)
    area_wgs = Polygon([
        (51.0, 35.0),
        (51.01, 35.0),
        (51.01, 35.01),
        (51.0, 35.01),
    ])
    home_point = Point(51.005, 35.005)
    centroid = area_wgs.centroid
    src_crs = get_utm_crs(centroid.x, centroid.y)
    area_utm = wgs84_to_utm(area_wgs, centroid.x, centroid.y)
    home_utm = wgs84_to_utm(home_point, centroid.x, centroid.y)
    home_m = (home_utm.x, home_utm.y)

    drones = make_drones()
    config = make_mission_config()
    spacing = config.track_spacing_m

    # تولید مسیر پوشش
    best_angle, _ = optimize_angle(area_utm, spacing, candidate_angles=[0, 90])
    planner = CoveragePlanner(area_utm, spacing, best_angle)
    coverage_path = planner.generate_coverage_path()
    assert len(coverage_path) > 0

    # تخصیص
    allocator = DroneAllocator(coverage_path, drones, home_m, area_utm)
    allocations = allocator.allocate_by_length()
    assert len(allocations) == len(drones)

    # بررسی باتری برای هر پهپاد
    for drone in drones:
        drone_path = allocations.get(drone.drone_id, [])
        if drone_path:
            full_route = combine_full_route(home_m, drone_path)
            result = check_battery(full_route, drone, home_m)
            # در این محدوده کوچک انتظار داریم قابل انجام باشد
            assert result.can_complete, f"{drone.drone_id} نتوانست مأموریت را کامل کند"

    # برنامه‌ریزی شیفت
    scheduler = ShiftScheduler(
        drones=drones,
        mission_config=config,
        home_m=home_m,
        coverage_path_m=coverage_path,
        allocations=allocations,
    )
    shifts = scheduler.create_shifts()
    assert len(shifts) >= 1

    # ساخت MissionPlan
    mission_plan = MissionPlan(
        mission_id="test_mission",
        created_at="2025-01-01T00:00:00",
        area={"area_m2": area_utm.area},
        summary={"number_of_drones": len(drones), "number_of_shifts": len(shifts)},
        shifts=shifts,
    )
    assert mission_plan.summary["number_of_drones"] == 2
    assert len(mission_plan.shifts) >= 1