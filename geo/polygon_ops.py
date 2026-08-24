"""
عملیات اعتبارسنجی و اصلاح چندضلعی‌ها.
"""

from typing import List

from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import explain_validity
import logging

logger = logging.getLogger(__name__)


def validate_polygon(polygon: Polygon) -> bool:
    """
    بررسی اعتبار یک Polygon.

    Args:
        polygon: شئ Polygon.

    Returns:
        bool: True اگر معتبر باشد، در غیر این صورت False.
    """
    if polygon.is_empty:
        logger.warning("Polygon خالی است.")
        return False
    if not polygon.is_valid:
        logger.warning(f"Polygon نامعتبر است: {explain_validity(polygon)}")
        return False
    return True


def repair_polygon(polygon: Polygon) -> Polygon:
    """
    تلاش برای اصلاح Polygon نامعتبر با استفاده از buffer(0).
    اگر نتیجه MultiPolygon باشد، بزرگ‌ترین Polygon را برمی‌گرداند.

    Args:
        polygon: شئ Polygon احتمالی نامعتبر.

    Returns:
        Polygon: چندضلعی اصلاح‌شده.
    """
    if not polygon.is_valid:
        repaired = polygon.buffer(0)
        if repaired.is_empty:
            raise ValueError("Polygon پس از اصلاح خالی است.")
        if isinstance(repaired, MultiPolygon):
            # انتخاب بزرگ‌ترین زیرچندضلعی
            repaired = max(repaired.geoms, key=lambda p: p.area)
        if not isinstance(repaired, Polygon):
            # در موارد نادر ممکن است نتیجه از نوع GeometryCollection باشد؛
            # سعی می‌کنیم از convex hull استفاده کنیم (برای فاز اول قابل قبول است)
            repaired = repaired.convex_hull
            if not isinstance(repaired, Polygon):
                raise ValueError("نمی‌توان Polygon را به صورت خودکار اصلاح کرد.")
        polygon = repaired   # این خط اضافه شد
        logger.info("Polygon اصلاح شد.")
    return polygon

def subtract_no_fly_zones(polygon: Polygon, no_fly_zones: List[Polygon]) -> Polygon:
    """
    حذف مناطق ممنوعه از محدوده مجاز.

    Args:
        polygon: محدوده مجاز.
        no_fly_zones: لیست مناطق ممنوعه.

    Returns:
        Polygon: محدوده مجاز پس از حذف مناطق ممنوعه.
        اگر نتیجه MultiPolygon باشد، بزرگ‌ترین Polygon را برمی‌گرداند.
    """
    current = polygon
    for nfz in no_fly_zones:
        current = current.difference(nfz)
    if current.is_empty:
        raise ValueError("محدوده مجاز پس از حذف مناطق ممنوعه خالی است.")
    if isinstance(current, MultiPolygon):
        current = max(current.geoms, key=lambda p: p.area)
    if not isinstance(current, Polygon):
        current = current.convex_hull
    return current