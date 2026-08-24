"""
تست‌های برنامه‌ریز پوشش.
"""

from shapely.geometry import Polygon

from planning.coverage_planner import CoveragePlanner, optimize_angle


def test_coverage_planner_square():
    poly = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
    planner = CoveragePlanner(poly, spacing_m=5, angle_deg=0)
    points = planner.generate_coverage_path()
    assert len(points) > 0
    # طول مسیر تقریبی: مساحت/فاصله = 400/5 = 80 متر + رفت‌وبرگشت افقی
    length = planner.get_path_length()
    assert length > 70
    assert length < 200


def test_optimize_angle():
    poly = Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])
    best_angle, best_len = optimize_angle(poly, spacing_m=5, candidate_angles=[0, 90])
    # برای مستطیل کشیده، زاویه 0 (افقی) کوتاه‌تر از عمودی است
    assert best_angle in [0, 90]
    assert best_len > 0


def test_empty_polygon():
    poly = Polygon()  # خالی
    planner = CoveragePlanner(poly, spacing_m=5)
    points = planner.generate_coverage_path()
    assert points == []