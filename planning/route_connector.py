"""
اتصال مسیر رفت و برگشت به آشیانه.
"""

from typing import List, Tuple

from geo.measurements import path_length_meters


def connect_home_to_start(
    home: Tuple[float, float],
    start_point: Tuple[float, float],
) -> List[Tuple[float, float]]:
    """
    تولید مسیر از آشیانه تا نقطه شروع (خط مستقیم).

    Args:
        home: مختصات آشیانه (x, y) متری.
        start_point: نقطه شروع مأموریت.

    Returns:
        List[Tuple[float, float]]: مسیر رفت.
    """
    return [home, start_point]


def connect_end_to_home(
    end_point: Tuple[float, float],
    home: Tuple[float, float],
) -> List[Tuple[float, float]]:
    """
    تولید مسیر برگشت از انتهای مأموریت به آشیانه.

    Args:
        end_point: نقطه پایان مأموریت.
        home: مختصات آشیانه.

    Returns:
        List[Tuple[float, float]]: مسیر برگشت.
    """
    return [end_point, home]


def combine_full_route(
    home: Tuple[float, float],
    mission_points: List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """
    ترکیب مسیر رفت، مأموریت و برگشت به صورت یک دنباله نقاط.

    Args:
        home: مختصات آشیانه.
        mission_points: نقاط مسیر مأموریت.

    Returns:
        List[Tuple[float, float]]: مسیر کامل.
    """
    if not mission_points:
        return [home]  # فقط آشیانه
    full = [home] + mission_points + [home]
    return full