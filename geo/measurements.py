"""
توابع محاسبات فاصله و طول مسیر.
"""

from typing import List, Tuple

import math


def distance_between_points(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    فاصله اقلیدسی بین دو نقطه (متر).

    Args:
        p1: (x1, y1)
        p2: (x2, y2)

    Returns:
        float: فاصله به متر.
    """
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def path_length_meters(points: List[Tuple[float, float]]) -> float:
    """
    طول کل مسیر از دنباله نقاط (متر).

    Args:
        points: لیست نقاط (x, y).

    Returns:
        float: طول کل مسیر.
    """
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i in range(len(points) - 1):
        total += distance_between_points(points[i], points[i + 1])
    return total