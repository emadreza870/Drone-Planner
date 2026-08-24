"""
تولید خروجی JSON ساخت‌یافته از برنامه مأموریت.
"""

import json
from typing import Dict, Any, List
from models.schedule import MissionPlan, Shift, DronePlan
from models.waypoint import Waypoint


def mission_plan_to_dict(plan: MissionPlan) -> Dict:
    """
    تبدیل MissionPlan به دیکشنری قابل JSON.

    Args:
        plan: شئ MissionPlan.

    Returns:
        dict: خروجی JSON.
    """
    shifts = []
    for shift in plan.shifts:
        shift_dict = {
            "shift_id": shift.shift_id,
            "start_time": shift.start_time.isoformat(),
            "end_time": shift.end_time.isoformat(),
            "drones": [],
        }
        for drone_plan in shift.drones:
            drone_dict = {
                "drone_id": drone_plan.drone_id,
                "status": drone_plan.status,
                "distance_m": drone_plan.distance_m,
                "duration_min": drone_plan.duration_min,
                "estimated_battery_remaining_percent": drone_plan.estimated_battery_remaining_percent,
                "return_reason": drone_plan.return_reason,
                "waypoints": [
                    {
                        "latitude": wp.latitude,
                        "longitude": wp.longitude,
                        "altitude_m": wp.altitude_m,
                        "speed_mps": wp.speed_mps,
                        "action": wp.action.value if hasattr(wp.action, 'value') else str(wp.action),
                        "sequence": wp.sequence,
                    }
                    for wp in drone_plan.waypoints
                ],
            }
            shift_dict["drones"].append(drone_dict)
        shifts.append(shift_dict)

    return {
        "mission_id": plan.mission_id,
        "created_at": plan.created_at,
        "coordinate_reference_system": plan.coordinate_reference_system,
        "area": plan.area,
        "summary": plan.summary,
        "shifts": shifts,
        "uncovered_segments": plan.uncovered_segments,
        "warnings": plan.warnings,
    }


def save_mission_plan_json(plan: MissionPlan, file_path: str) -> None:
    """ذخیره MissionPlan به عنوان فایل JSON."""
    data = mission_plan_to_dict(plan)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)