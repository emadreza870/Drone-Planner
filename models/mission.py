"""
مدل‌های داده مربوط به پیکربندی مأموریت و دوربین.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CameraConfig(BaseModel):
    """مشخصات دوربین برای محاسبه فاصله خطوط پرواز.

    Attributes:
        fov_deg: زاویه میدان دید دوربین به درجه (مثلاً 60).
        overlap_ratio: درصد هم‌پوشانی بین تصاویر (بین 0 و 1).
    """

    fov_deg: float = Field(..., gt=0, le=180, description="زاویه میدان دید دوربین (درجه)")
    overlap_ratio: float = Field(..., ge=0, lt=1, description="درصد هم‌پوشانی (بین 0 و 1)")

    @field_validator("overlap_ratio")
    @classmethod
    def validate_overlap(cls, v: float) -> float:
        if not 0 <= v < 1:
            raise ValueError("overlap_ratio باید بین 0 و 1 باشد")
        return v


class MissionConfig(BaseModel):
    """پیکربندی کلی مأموریت.

    Attributes:
        track_spacing_m: فاصله بین خطوط پرواز به متر (در صورت نبود دوربین).
        overlap_ratio: درصد هم‌پوشانی مسیرها (در صورت استفاده از دوربین).
        shift_duration_min: مدت هر شیفت به دقیقه.
        target_revisit_interval_min: زمان هدف بازدید مجدد از هر سلول به دقیقه.
        default_altitude_m: ارتفاع پرواز پیش‌فرض به متر.
        default_speed_mps: سرعت پیش‌فرض به متر بر ثانیه.
        reserve_time_min: زمان ذخیره اضطراری پیش‌فرض به دقیقه.
        takeoff_time_sec: زمان برخاست پیش‌فرض به ثانیه.
        landing_time_sec: زمان فرود پیش‌فرض به ثانیه.
        camera: مشخصات دوربین (اختیاری).
    """

    track_spacing_m: Optional[float] = Field(default=None, gt=0, description="فاصله خطوط پرواز (متر)")
    overlap_ratio: float = Field(default=0.2, ge=0, lt=1, description="درصد هم‌پوشانی")
    shift_duration_min: float = Field(..., gt=0, description="مدت هر شیفت (دقیقه)")
    target_revisit_interval_min: float = Field(..., gt=0, description="زمان هدف بازدید مجدد (دقیقه)")
    default_altitude_m: float = Field(..., gt=0, description="ارتفاع پرواز پیش‌فرض (متر)")
    default_speed_mps: float = Field(..., gt=0, description="سرعت پیش‌فرض (متر بر ثانیه)")
    reserve_time_min: float = Field(..., ge=0, description="زمان ذخیره اضطراری پیش‌فرض (دقیقه)")
    takeoff_time_sec: float = Field(..., ge=0, description="زمان برخاست پیش‌فرض (ثانیه)")
    landing_time_sec: float = Field(..., ge=0, description="زمان فرود پیش‌فرض (ثانیه)")
    camera: Optional[CameraConfig] = Field(default=None, description="مشخصات دوربین")

    @field_validator("overlap_ratio")
    @classmethod
    def validate_overlap(cls, v: float) -> float:
        if not 0 <= v < 1:
            raise ValueError("overlap_ratio باید بین 0 و 1 باشد")
        return v

    @model_validator(mode="after")
    def validate_camera_or_spacing(self) -> "MissionConfig":
        """اگر دوربین مشخص نشده است، track_spacing_m باید مقدار داشته باشد."""
        if self.camera is None and self.track_spacing_m is None:
            raise ValueError("اگر دوربین مشخص نشده است، track_spacing_m باید مقدار داشته باشد")
        return self