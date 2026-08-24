"""
تست‌های تخصیص مسیر به چند پهپاد.
"""

import math
import pytest
from shapely.geometry import Polygon

from models.drone import Drone
from planning.drone_allocator import DroneAllocator
from geo.measurements import path_length_meters


def make_drone(drone_id, max_flight_time_min=30, speed_mps=5):
    return Drone(
        drone_id=drone_id,
        max_flight_time_min=max_flight_time_min,
        speed_mps=speed_mps,
        altitude_m=80,
        reserve_time_min=5,
        takeoff_time_sec=30,
        landing_time_sec=30,
        status="available",
    )


def test_allocate_by_length_two_drones():
    # مسیر خطی از (0,0) تا (100,0)
    waypoints = [(i * 10, 0) for i in range(11)]  # 11 نقطه
    drones = [make_drone("d1"), make_drone("d2")]
    home = (0, 0)
    allocator = DroneAllocator(waypoints, drones, home)
    allocations = allocator.allocate_by_length()

    # هر دو پهپاد باید مسیر داشته باشند
    assert len(allocations["d1"]) > 0
    assert len(allocations["d2"]) > 0
    # مجموع طول‌ها باید تقریباً برابر با طول کل باشد (با خطای کم)
    total_allocated = sum(path_length_meters(allocations[d]) for d in allocations)
    assert total_allocated == pytest.approx(path_length_meters(waypoints), abs=1e-6)
    # طول هر بخش باید حدود نصف باشد
    assert path_length_meters(allocations["d1"]) == pytest.approx(50, abs=20)
    assert path_length_meters(allocations["d2"]) == pytest.approx(50, abs=20)


def test_allocate_by_length_three_drones():
    waypoints = [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0)]
    drones = [make_drone("d1"), make_drone("d2"), make_drone("d3")]
    home = (0, 0)
    allocator = DroneAllocator(waypoints, drones, home)
    allocations = allocator.allocate_by_length()
    # هر سه پهپاد باید مسیر داشته باشند (حداقل یک نقطه)
    assert all(len(allocations[d]) >= 2 for d in allocations)
    # مجموع طول‌ها برابر طول کل
    assert sum(path_length_meters(allocations[d]) for d in allocations) == pytest.approx(
        path_length_meters(waypoints), abs=1e-6)


def test_allocate_by_grid_basic():
    # محدوده مستطیلی 20x20 با شبکه نقاط
    polygon = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
    # نقاط روی شبکه 5x5
    waypoints = []
    for y in range(0, 21, 5):
        for x in range(0, 21, 5):
            waypoints.append((x, y))
    drones = [make_drone("d1"), make_drone("d2")]
    home = (0, 0)
    allocator = DroneAllocator(waypoints, drones, home, area_polygon=polygon)
    allocations = allocator.allocate_by_grid(n_cells_per_side=2)
    # هر دو پهپاد باید نقاطی دریافت کنند
    assert len(allocations["d1"]) > 0
    assert len(allocations["d2"]) > 0
    # تعداد کل نقاط تخصیص‌یافته باید برابر تعداد نقاط اصلی باشد
    total_points = sum(len(allocations[d]) for d in allocations)
    assert total_points == len(waypoints)


def test_allocate_by_grid_no_polygon():
    # بدون area_polygon
    waypoints = [(0, 0), (5, 5), (10, 10), (15, 15)]
    drones = [make_drone("d1")]
    home = (0, 0)
    allocator = DroneAllocator(waypoints, drones, home)
    allocations = allocator.allocate_by_grid(n_cells_per_side=2)
    assert len(allocations["d1"]) == len(waypoints)