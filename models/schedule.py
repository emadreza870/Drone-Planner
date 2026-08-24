"""
مدل‌های داده برای برنامه زمانی، شیفت‌ها و خروجی نهایی.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .waypoint import Waypoint
from .drone import Drone


class DronePlan(BaseModel):
    """برنامه پرواز یک پهپاد در یک شیفت.

    Attributes:
        drone_id: شناسه پهپاد.
        status: وضعیت برنامه (planned, in_progress, completed, aborted).
        distance_m: کل مسافت طی شده (متر).
        duration_min: مدت زمان پرواز (دقیقه).
        estimated_battery_remaining_percent: درصد باتری باقی‌مانده تخمینی.
        return_reason: دلیل بازگشت (در صورت بازگشت زودتر).
        waypoints: لیست نقاط راه.
    """

    drone_id: str
    status: str = "planned"
    distance_m: float = 0.0
    duration_min: float = 0.0
    estimated_battery_remaining_percent: float = 0.0
    return_reason: Optional[str] = None
    waypoints: List[Waypoint] = Field(default_factory=list)


class Shift(BaseModel):
    """یک شیفت کاری.

    Attributes:
        shift_id: شناسه شیفت.
        start_time: زمان شروع شیفت.
        end_time: زمان پایان شیفت.
        drones: لیست برنامه‌های پهپادها در این شیفت.
    """

    shift_id: str
    start_time: datetime
    end_time: datetime
    drones: List[DronePlan] = Field(default_factory=list)


class CellStatus(BaseModel):
    """وضعیت پوشش یک سلول از منطقه.

    Attributes:
        cell_id: شناسه سلول.
        polygon: شئ Shapely Polygon سلول.
        priority: اولویت (عدد بزرگ‌تر = اولویت بالاتر).
        last_visit_time: زمان آخرین بازدید.
        next_visit_time: زمان بازدید بعدی.
        responsible_drone: پهپاد مسئول (اختیاری).
        covered: آیا پوشش داده شده است.
    """

    cell_id: str
    polygon: object  # Shapely Polygon
    priority: int = 1
    last_visit_time: Optional[datetime] = None
    next_visit_time: Optional[datetime] = None
    responsible_drone: Optional[str] = None
    covered: bool = False


class MissionPlan(BaseModel):
    """خروجی نهایی برنامه مأموریت.

    Attributes:
        mission_id: شناسه مأموریت.
        created_at: زمان تولید برنامه.
        coordinate_reference_system: سیستم مختصات (مثلاً "WGS84").
        area: اطلاعات مساحت و درصد پوشش.
        summary: خلاصه مأموریت.
        shifts: لیست شیفت‌ها.
        uncovered_segments: بخش‌های پوشش‌داده‌نشده.
        warnings: هشدارها.
    """

    mission_id: str
    created_at: str
    coordinate_reference_system: str = "WGS84"
    area: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)
    shifts: List[Shift] = Field(default_factory=list)
    uncovered_segments: List[dict] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)