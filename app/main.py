"""
نقطه ورود CLI برای اجرای سناریو یا بررسی نصب.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from models.drone import Drone
from models.mission import MissionConfig
from models.waypoint import Waypoint


def main():
    print("Drone Planner - Phase 1")
    print("1) اجرای سناریوی نمونه")
    print("2) بررسی نصب ماژول‌ها")
    choice = input("انتخاب کنید (1/2): ").strip()
    if choice == "1":
        from examples.run_scenario import main as run_scenario
        run_scenario()
    else:
        print("Checking imports...")
        drone = Drone(
            drone_id="test_drone",
            max_flight_time_min=30,
            speed_mps=10,
            altitude_m=100,
            reserve_time_min=5,
            takeoff_time_sec=30,
            landing_time_sec=30,
        )
        print(f"Created drone: {drone.drone_id}")
        print("Models imported successfully.")


if __name__ == "__main__":
    main()