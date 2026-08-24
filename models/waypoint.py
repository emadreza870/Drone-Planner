"""
مدل نقطه راه (Waypoint) برای مسیر پرواز.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class WaypointAction(str, Enum):
    """اقدامات ممکن در یک نقطه راه."""
    TAKEOFF = "takeoff"
    TRANSIT = "transit"
    SURVEY = "survey"
    RETURN = "return"
    LANDING = "landing"


class Waypoint(BaseModel):
    """یک نقطه راه در مسیر.

    Attributes:
        latitude: عرض جغرافیایی (WGS84).
        longitude: طول جغرافیایی (WGS84).
        altitude_m: ارتفاع پرواز در این نقطه (متر).
        speed_mps: سرعت پرواز در این نقطه (متر بر ثانیه).
        action: نوع اقدام (takeoff, transit, survey, return, landing).
        sequence: شماره ترتیب نقطه در مسیر (اختیاری).
    """

    latitude: float = Field(..., ge=-90, le=90, description="عرض جغرافیایی")
    longitude: float = Field(..., ge=-180, le=180, description="طول جغرافیایی")
    altitude_m: float = Field(..., ge=0, description="ارتفاع (متر)")
    speed_mps: float = Field(..., gt=0, description="سرعت (متر بر ثانیه)")
    action: WaypointAction = Field(..., description="نوع اقدام")
    sequence: int = Field(default=0, ge=0, description="شماره ترتیب نقطه")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("latitude باید بین -90 و 90 باشد")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("longitude باید بین -180 و 180 باشد")
        return v