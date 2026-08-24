"""
تست‌های واحد برای مدل‌های داده.
"""

import pytest
from pydantic import ValidationError
from shapely.geometry import Polygon

from models.drone import Drone, DroneStatus
from models.mission import MissionConfig, CameraConfig
from models.waypoint import Waypoint, WaypointAction
from models.area import Area


def test_drone_valid():
    drone = Drone(
        drone_id="drone_01",
        max_flight_time_min=35,
        speed_mps=8,
        altitude_m=80,
        reserve_time_min=5,
        takeoff_time_sec=30,
        landing_time_sec=30,
        status="available"
    )
    assert drone.drone_id == "drone_01"
    assert drone.status == DroneStatus.AVAILABLE


def test_drone_invalid_speed():
    with pytest.raises(ValidationError):
        Drone(
            drone_id="drone_02",
            max_flight_time_min=35,
            speed_mps=0,  # سرعت صفر مجاز نیست
            altitude_m=80,
            reserve_time_min=5,
            takeoff_time_sec=30,
            landing_time_sec=30,
        )


def test_drone_reserve_less_than_max():
    with pytest.raises(ValidationError):
        Drone(
            drone_id="drone_03",
            max_flight_time_min=10,
            speed_mps=8,
            altitude_m=80,
            reserve_time_min=10,  # برابر با حداکثر زمان پرواز
            takeoff_time_sec=30,
            landing_time_sec=30,
        )


def test_mission_config_with_camera():
    config = MissionConfig(
        shift_duration_min=45,
        target_revisit_interval_min=60,
        default_altitude_m=80,
        default_speed_mps=8,
        reserve_time_min=5,
        takeoff_time_sec=30,
        landing_time_sec=30,
        camera=CameraConfig(fov_deg=60, overlap_ratio=0.2)
    )
    assert config.track_spacing_m is None  # دوربین وجود دارد


def test_mission_config_without_camera_requires_track_spacing():
    with pytest.raises(ValidationError):
        MissionConfig(
            shift_duration_min=45,
            target_revisit_interval_min=60,
            default_altitude_m=80,
            default_speed_mps=8,
            reserve_time_min=5,
            takeoff_time_sec=30,
            landing_time_sec=30,
        )


def test_waypoint_valid():
    wp = Waypoint(
        latitude=35.123,
        longitude=51.456,
        altitude_m=80,
        speed_mps=8,
        action="survey",
        sequence=1
    )
    assert wp.action == WaypointAction.SURVEY


def test_waypoint_invalid_latitude():
    with pytest.raises(ValidationError):
        Waypoint(
            latitude=95.0,
            longitude=51.456,
            altitude_m=80,
            speed_mps=8,
            action="survey"
        )


def test_area_calculation():
    polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    area = Area(polygon=polygon, no_fly_zones=[])
    assert area.area_m2 == 100 * 100
    assert area.effective_area_m2 == 100 * 100

    # با یک منطقه ممنوعه
    nfz = Polygon([(40, 40), (60, 40), (60, 60), (40, 60)])
    area2 = Area(polygon=polygon, no_fly_zones=[nfz])
    assert area2.effective_area_m2 == 100 * 100 - 20 * 20