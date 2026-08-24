"""
مدل‌های داده مربوط به منطقه عملیات.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from shapely.geometry import Polygon


class Area(BaseModel):
    """منطقه عملیات شامل Polygon مجاز و مناطق ممنوعه.

    Attributes:
        polygon: چندضلعی مجاز (شئ Shapely Polygon).
        no_fly_zones: لیست چندضلعی‌های ممنوعه (اختیاری).
        area_m2: مساحت کل منطقه مجاز به متر مربع (محاسبه می‌شود).
        effective_area_m2: مساحت مؤثر پس از کسر مناطق ممنوعه (محاسبه می‌شود).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    polygon: Polygon = Field(..., description="چندضلعی مجاز")
    no_fly_zones: List[Polygon] = Field(default_factory=list, description="مناطق ممنوعه")
    area_m2: Optional[float] = Field(default=None, description="مساحت کل (متر مربع)")
    effective_area_m2: Optional[float] = Field(default=None, description="مساحت مؤثر (متر مربع)")

    def __init__(self, **data):
        super().__init__(**data)
        # محاسبه مساحت‌ها
        self.area_m2 = self.polygon.area
        effective = self.polygon
        for nfz in self.no_fly_zones:
            effective = effective.difference(nfz)
        self.effective_area_m2 = effective.area