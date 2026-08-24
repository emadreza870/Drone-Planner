"""
تولید خطوط موازی برای پوشش منطقه و مرتب‌سازی رفت‌وبرگشتی.
"""

import math
from typing import List, Tuple

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import logging

logger = logging.getLogger(__name__)


def generate_parallel_lines(
    polygon: Polygon,
    spacing_m: float,
    angle_deg: float = 0.0,
) -> List[LineString]:
    """
    تولید خطوط موازی با فاصله مشخص که کل Polygon را پوشش می‌دهند.
    خطوط به‌صورت بی‌نهایت طولانی هستند و بعداً تقاطع گرفته می‌شود.

    Args:
        polygon: چندضلعی مجاز (در سیستم متری).
        spacing_m: فاصله بین خطوط (متر).
        angle_deg: زاویه خطوط نسبت به شمال (درجه). 0 یعنی خطوط افقی (شرقی-غربی).

    Returns:
        List[LineString]: لیست خطوط موازی.
    """
    if spacing_m <= 0:
        raise ValueError("فاصله خطوط باید مثبت باشد.")

    # تبدیل زاویه به رادیان (زاویه نسبت به محور x)
    angle_rad = math.radians(angle_deg)
    direction = np.array([math.cos(angle_rad), math.sin(angle_rad)])

    # محاسبه حدود polygon
    minx, miny, maxx, maxy = polygon.bounds
    # قطر bounding box برای اطمینان از پوشش کامل
    diag = math.hypot(maxx - minx, maxy - miny)

    # بردار عمود بر جهت خطوط (برای فاصله‌گذاری)
    normal = np.array([-math.sin(angle_rad), math.cos(angle_rad)])

    # نقطه مرجع (مرکز bounding box)
    center = np.array([(minx + maxx) / 2, (miny + maxy) / 2])

    # تعیین تعداد خطوط لازم: فاصله حداکثر از مرکز تا لبه polygon در جهت normal
    # تقریباً diag/2 کافی است. سپس خطوط در دو طرف مرکز.
    half_range = diag / 2
    n_lines = math.ceil(half_range / spacing_m) + 1

    lines = []
    for i in range(-n_lines, n_lines + 1):
        offset = i * spacing_m
        # نقطه روی خط: مرکز + offset * normal
        point_on_line = center + offset * normal
        # خط بی‌نهایت از دو طرف
        p1 = point_on_line - direction * diag  # دیاگ کافی است
        p2 = point_on_line + direction * diag
        lines.append(LineString([p1, p2]))

    return lines


def get_intersections_with_polygon(
    polygon: Polygon,
    lines: List[LineString],
) -> List[LineString]:
    """
    محاسبه تقاطع هر خط با محدوده و حذف قطعات خالی.

    Args:
        polygon: محدوده مجاز.
        lines: خطوط موازی.

    Returns:
        List[LineString]: قطعات داخل محدوده.
    """
    segments = []
    for line in lines:
        inter = line.intersection(polygon)
        if inter.is_empty:
            continue
        if isinstance(inter, LineString):
            if inter.length > 1e-6:
                segments.append(inter)
        elif hasattr(inter, 'geoms'):  # MultiLineString یا GeometryCollection
            for geom in inter.geoms:
                if isinstance(geom, LineString) and geom.length > 1e-6:
                    segments.append(geom)
    return segments


def order_segments_boustrophedon(segments: List[LineString]) -> List[LineString]:
    """
    مرتب‌سازی قطعات به‌صورت رفت‌وبرگشتی (Boustrophedon).
    ابتدا قطعات را بر اساس مختصات مرکزشان در جهت عمود بر خطوط مرتب می‌کنیم،
    سپس در هر ردیف جهت حرکت را معکوس می‌کنیم.

    Args:
        segments: قطعات تقاطع‌یافته.

    Returns:
        List[LineString]: قطعات مرتب‌شده.
    """
    if not segments:
        return []

    # جهت خطوط را از روی اولین قطعه تخمین بزنید
    # فرض می‌کنیم خطوط تقریباً موازی هستند؛ برای مرتب‌سازی کافی است.
    # مختصات centroid قطعات را بگیرید.
    centroids = [seg.centroid for seg in segments]

    # تعیین محور مرتب‌سازی: عمود بر جهت اصلی خطوط.
    # جهت اصلی خطوط = تفاضل دو نقطه انتهایی قطعه اول
    first_seg = segments[0]
    dx = first_seg.coords[-1][0] - first_seg.coords[0][0]
    dy = first_seg.coords[-1][1] - first_seg.coords[0][1]
    # زاویه خط
    angle = math.atan2(dy, dx)
    # بردار نرمال
    normal_angle = angle + math.pi / 2
    normal = np.array([math.cos(normal_angle), math.sin(normal_angle)])

    # پروجکشن مرکزها روی normal
    projections = [np.dot([c.x, c.y], normal) for c in centroids]
    # مرتب‌سازی بر اساس پروجکشن
    idx_sorted = sorted(range(len(segments)), key=lambda i: projections[i])

    ordered = []
    flip = False
    # گروه‌بندی بر اساس مقادیر نزدیک (خطوط هم‌فاز)
    # در این نسخه ساده، فقط بر اساس مرتب‌سازی پروجکشن کار می‌کنیم و جهت را معکوس می‌کنیم.
    for i in idx_sorted:
        seg = segments[i]
        if flip:
            # معکوس کردن جهت قطعه
            seg = LineString(list(seg.coords)[::-1])
        ordered.append(seg)
        flip = not flip

    return ordered


def create_waypoints_from_segments(segments: List[LineString]) -> List[Tuple[float, float]]:
    """
    تبدیل قطعات به دنباله نقاط راه (مختصات x,y متری).
    برای هر قطعه، دو انتها را اضافه می‌کنیم و بین قطعات، نقطه اتصال را تکراری نمی‌کنیم.

    Args:
        segments: قطعات مرتب‌شده.

    Returns:
        List[Tuple[float, float]]: لیست نقاط (x, y).
    """
    points = []
    for i, seg in enumerate(segments):
        coords = list(seg.coords)
        if i == 0:
            points.extend(coords)
        else:
            # از انتهای قطعه قبلی به ابتدای این قطعه می‌رویم
            # برای سادگی، ابتدا و انتهای این قطعه را اضافه می‌کنیم (نقطه اول قبلاً وجود دارد)
            # اگر نقطه اول قطعه با آخرین نقطه قبلی یکی باشد، تکراری نمی‌شود
            if len(points) > 0 and (abs(points[-1][0] - coords[0][0]) < 1e-9 and abs(points[-1][1] - coords[0][1]) < 1e-9):
                # نقطه اول تکراری است، فقط انتهای قطعه را اضافه کن
                points.append(coords[-1])
            else:
                points.extend(coords)
    return points