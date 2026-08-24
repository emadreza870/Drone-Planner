"""
تست‌های زمان‌بندی شیفت‌ها.
"""

from datetime import datetime
import pytest

from models.drone import Drone
from models.mission import MissionConfig
from models.schedule import Shift
from planning.shift_scheduler import ShiftScheduler


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


def make_config(shift_duration_min=20):
    return MissionConfig(
        track_spacing_m=10,
        shift_duration_min=shift_duration_min,
        target_revisit_interval_min=60,
        default_altitude_m=80,
        default_speed_mps=5,
        reserve_time_min=5,
        takeoff_time_sec=30,
        landing_time_sec=30,
    )


def test_single_shift_fits():
    # مسیر کوتاه که در یک شیفت جا می‌شود
    drones = [make_drone("d1", max_flight_time_min=30, speed_mps=10)]
    config = make_config(shift_duration_min=30)
    home = (0, 0)
    path = [(0, 0), (100, 0), (200, 0)]
    alloc = {"d1": path}
    scheduler = ShiftScheduler(drones, config, home, path, alloc)
    shifts = scheduler.create_shifts(start_time=datetime(2025, 1, 1, 8, 0, 0))
    assert len(shifts) == 1
    assert shifts[0].shift_id == "shift_01"
    assert len(shifts[0].drones) == 1
    assert shifts[0].drones[0].drone_id == "d1"


def test_two_shifts_for_long_path():
    # مسیر طولانی که در یک شیفت جا نمی‌شود
    drones = [make_drone("d1", max_flight_time_min=60, speed_mps=0.5)]
    config = make_config(shift_duration_min=10)
    home = (0, 0)
    path = [(0, 0), (100, 0), (200, 0), (300, 0), (400, 0)]
    scheduler = ShiftScheduler(drones, config, home, path, {"d1": path})
    shifts = scheduler.create_shifts(start_time=datetime(2025, 1, 1, 8, 0, 0))
    assert len(shifts) >= 2
    # اولین شیفت باید قسمتی از مسیر را پوشش دهد
    assert len(shifts[0].drones) == 1
    assert shifts[0].drones[0].distance_m > 0
    # در شیفت دوم ادامه مسیر انجام می‌شود
    assert len(shifts[-1].drones) == 1


def test_multiple_drones_parallel():
    # چند پهپاد هم‌زمان در یک شیفت
    drones = [make_drone("d1"), make_drone("d2")]
    config = make_config(shift_duration_min=20)
    home = (0, 0)
    path = [(0, 0), (50, 0), (100, 0), (150, 0), (200, 0)]
    alloc = {
        "d1": [(0, 0), (50, 0), (100, 0)],
        "d2": [(100, 0), (150, 0), (200, 0)],
    }
    scheduler = ShiftScheduler(drones, config, home, path, alloc)
    shifts = scheduler.create_shifts(start_time=datetime(2025, 1, 1, 8, 0, 0))
    assert len(shifts) >= 1
    # در شیفت اول باید هر دو پهپاد حضور داشته باشند
    shift1_drones = [dp.drone_id for dp in shifts[0].drones]
    assert "d1" in shift1_drones
    assert "d2" in shift1_drones