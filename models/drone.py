"""
مدل‌های داده مربوط به پهپاد.

این ماژول شامل کلاس Drone و وضعیت‌های مجاز آن است.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class DroneStatus(str, Enum):
    """وضعیت‌های ممکن برای یک پهپاد."""
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    CHARGING = "charging"
    IN_MISSION = "in_mission"


class Drone(BaseModel):
    """مشخصات کامل یک پهپاد.

    Attributes:
        drone_id: شناسه یکتای پهپاد (مثلاً drone_01).
        max_flight_time_min: حداکثر زمان پرواز مفید به دقیقه.
        speed_mps: سرعت پرواز به متر بر ثانیه.
        altitude_m: ارتفاع پرواز پیش‌فرض به متر.
        reserve_time_min: زمان ذخیره اضطراری برای بازگشت به دقیقه.
        takeoff_time_sec: زمان لازم برای برخاستن به ثانیه.
        landing_time_sec: زمان لازم برای فرود به ثانیه.
        status: وضعیت اولیه پهپاد.
    """

    drone_id: str = Field(..., min_length=1, description="شناسه یکتای پهپاد")
    max_flight_time_min: float = Field(..., gt=0, description="حداکثر زمان پرواز مفید (دقیقه)")
    speed_mps: float = Field(..., gt=0, description="سرعت پرواز (متر بر ثانیه)")
    altitude_m: float = Field(..., gt=0, description="ارتفاع پرواز (متر)")
    reserve_time_min: float = Field(..., ge=0, description="زمان ذخیره اضطراری (دقیقه)")
    takeoff_time_sec: float = Field(..., ge=0, description="زمان برخاست (ثانیه)")
    landing_time_sec: float = Field(..., ge=0, description="زمان فرود (ثانیه)")
    status: DroneStatus = Field(default=DroneStatus.AVAILABLE, description="وضعیت پهپاد")

    @field_validator("drone_id")
    @classmethod
    def validate_drone_id(cls, v: str) -> str:
        """شناسه نباید خالی یا فقط شامل فاصله باشد."""
        if not v.strip():
            raise ValueError("drone_id نمی‌تواند خالی باشد")
        return v.strip()

    @field_validator("reserve_time_min", "takeoff_time_sec", "landing_time_sec")
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("مقادیر زمان نمی‌توانند منفی باشند")
        return v

    @field_validator("reserve_time_min")
    @classmethod
    def validate_reserve_less_than_max(cls, v: float, info) -> float:
        """زمان ذخیره نباید از زمان پرواز مفید بیشتر باشد."""
        max_flight = info.data.get("max_flight_time_min")
        if max_flight is not None and v >= max_flight:
            raise ValueError("زمان ذخیره باید کمتر از حداکثر زمان پرواز مفید باشد")
        return v