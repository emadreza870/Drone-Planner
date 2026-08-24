"""
الگوریتم برنامه‌ریزی پوشش رفت‌وبرگشتی.
"""

from typing import List, Tuple, Optional

from shapely.geometry import Polygon, LineString

from geo.coverage_lines import (
    generate_parallel_lines,
    get_intersections_with_polygon,
    order_segments_boustrophedon,
    create_waypoints_from_segments,
)
from geo.measurements import path_length_meters

import logging

logger = logging.getLogger(__name__)


class CoveragePlanner:
    """برنامه‌ریز مسیر پوشش با الگوریتم Boustrophedon."""

    def __init__(
        self,
        polygon: Polygon,
        spacing_m: float,
        angle_deg: float = 0.0,
    ):
        """
        Args:
            polygon: محدوده مجاز (سیستم متری).
            spacing_m: فاصله بین خطوط پوشش.
            angle_deg: زاویه خطوط (درجه).
        """
        if spacing_m <= 0:
            raise ValueError("spacing_m باید مثبت باشد.")
        self.polygon = polygon
        self.spacing_m = spacing_m
        self.angle_deg = angle_deg

    def generate_coverage_path(self) -> List[Tuple[float, float]]:
        if self.polygon.is_empty:
           return []
        """
        تولید مسیر کامل پوشش به صورت نقاط متری.

        Returns:
            List[Tuple[float, float]]: نقاط مسیر (x, y).
        """
        lines = generate_parallel_lines(self.polygon, self.spacing_m, self.angle_deg)
        segments = get_intersections_with_polygon(self.polygon, lines)
        if not segments:
            logger.warning("هیچ قطعه‌ای با محدوده تقاطع ندارد.")
            return []
        ordered = order_segments_boustrophedon(segments)
        points = create_waypoints_from_segments(ordered)
        return points

    def get_path_length(self) -> float:
        """محاسبه طول کل مسیر پوشش (متر)."""
        points = self.generate_coverage_path()
        return path_length_meters(points)


def optimize_angle(
    polygon: Polygon,
    spacing_m: float,
    candidate_angles: List[float] = [0, 30, 45, 60, 90, 120, 135, 150],
) -> Tuple[float, float]:
    """
    پیدا کردن بهترین زاویه پوشش از بین کاندیدها بر اساس کوتاه‌ترین طول مسیر.

    Args:
        polygon: محدوده مجاز.
        spacing_m: فاصله خطوط.
        candidate_angles: زوایای مورد بررسی (درجه).

    Returns:
        Tuple[float, float]: (بهترین زاویه، طول مسیر متناظر).
    """
    best_angle = candidate_angles[0]
    best_length = float('inf')
    for angle in candidate_angles:
        planner = CoveragePlanner(polygon, spacing_m, angle)
        length = planner.get_path_length()
        if length < best_length:
            best_length = length
            best_angle = angle
    return best_angle, best_length