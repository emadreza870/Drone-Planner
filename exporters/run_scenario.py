"""
اجرای یک سناریوی کامل از برنامه‌ریزی مأموریت.

این اسکریپت یک محدوده نمونه تولید می‌کند، مسیر پوشش را برنامه‌ریزی کرده،
بین پهپادها تقسیم می‌کند و خروجی‌های JSON و نقشه HTML تولید می‌کند.
"""

import sys
from pathlib import Path

# افزودن ریشه پروژه به sys.path
sys.path.append(str(Path(__file__).parent.parent))

import json
import math
from datetime import datetime

from shapely.geometry import Polygon, Point
import folium

from models.drone import Drone, DroneStatus
from models.mission import MissionConfig, CameraConfig
from models.waypoint import Waypoint, WaypointAction
from models.schedule import MissionPlan, Shift, DronePlan, CellStatus

from geo.io import read_area_polygon
from geo.projection import wgs84_to_utm, utm_to_wgs84, get_utm_crs, transform_geometry
from geo.polygon_ops import validate_polygon, repair_polygon, subtract_no_fly_zones
from planning.coverage_planner import CoveragePlanner, optimize_angle
from planning.route_connector import combine_full_route
from planning.drone_allocator import DroneAllocator
from planning.battery_checker import check_battery
from planning.shift_scheduler import ShiftScheduler
from planning.persistent_coverage import PersistentCoverage

from visualization.map_view import create_map, add_polygon_to_map, add_marker, add_route_to_map
from exporters.geojson_exporter import polygon_to_geojson, points_to_geojson_line, create_feature_collection
from exporters.json_exporter import mission_plan_to_dict, save_mission_plan_json
from exporters.html_map_exporter import save_map_html

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_sample_area() -> Polygon:
    """
    تولید یک محدوده مستطیلی نمونه در WGS84 (اطراف تهران).
    """
    # مختصات تقریبی: طول 51.2 تا 51.25، عرض 35.1 تا 35.15
    lon_min, lat_min = 51.20, 35.10
    lon_max, lat_max = 51.25, 35.15
    return Polygon([
        (lon_min, lat_min),
        (lon_max, lat_min),
        (lon_max, lat_max),
        (lon_min, lat_max),
    ])


def main():
    logger.info("شروع سناریوی کامل...")

    # ---------- 1. محدوده عملیات ----------
    area_wgs = generate_sample_area()
    if not validate_polygon(area_wgs):
        area_wgs = repair_polygon(area_wgs)
    logger.info(f"مساحت محدوده (WGS84): {area_wgs.area:.6f} درجه مربع")

    # مختصات آشیانه (نقطه‌ای نزدیک محدوده)
    home_lat, home_lon = 35.12, 51.22
    home_point_wgs = Point(home_lon, home_lat)

    # تبدیل محدوده و آشیانه به UTM
    centroid = area_wgs.centroid
    src_crs = get_utm_crs(centroid.x, centroid.y)
    area_utm = wgs84_to_utm(area_wgs, centroid.x, centroid.y)
    home_utm = wgs84_to_utm(home_point_wgs, centroid.x, centroid.y)
    home_m = (home_utm.x, home_utm.y)
    logger.info(f"ناحیه UTM: EPSG:{src_crs.to_epsg()}")
    logger.info(f"مساحت محدوده (UTM): {area_utm.area:.2f} متر مربع")

    # ---------- 2. تعریف پهپادها ----------
    drones = [
        Drone(
            drone_id="drone_01",
            max_flight_time_min=30,
            speed_mps=8,
            altitude_m=80,
            reserve_time_min=5,
            takeoff_time_sec=30,
            landing_time_sec=30,
            status=DroneStatus.AVAILABLE,
        ),
        Drone(
            drone_id="drone_02",
            max_flight_time_min=25,
            speed_mps=7,
            altitude_m=80,
            reserve_time_min=5,
            takeoff_time_sec=30,
            landing_time_sec=30,
            status=DroneStatus.AVAILABLE,
        ),
    ]
    logger.info(f"تعداد پهپادها: {len(drones)}")

    # ---------- 3. پارامترهای مأموریت ----------
    mission_config = MissionConfig(
        track_spacing_m=50,          # فاصله خطوط 50 متر
        overlap_ratio=0.1,
        shift_duration_min=45,       # شیفت 45 دقیقه
        target_revisit_interval_min=60,
        default_altitude_m=80,
        default_speed_mps=8,
        reserve_time_min=5,
        takeoff_time_sec=30,
        landing_time_sec=30,
        camera=None,                 # بدون دوربین
    )
    spacing = mission_config.track_spacing_m
    logger.info(f"فاصله خطوط: {spacing} متر")

    # ---------- 4. تولید مسیر پوشش ----------
    # انتخاب بهترین زاویه
    best_angle, best_length = optimize_angle(
        area_utm, spacing, candidate_angles=[0, 30, 45, 60, 90, 120, 135, 150]
    )
    logger.info(f"بهترین زاویه: {best_angle} درجه، طول مسیر: {best_length:.2f} متر")

    planner = CoveragePlanner(area_utm, spacing, angle_deg=best_angle)
    coverage_path_m = planner.generate_coverage_path()
    if not coverage_path_m:
        logger.error("هیچ مسیری تولید نشد.")
        return

    logger.info(f"تعداد نقاط مسیر پوشش: {len(coverage_path_m)}")
    logger.info(f"طول مسیر پوشش: {planner.get_path_length():.2f} متر")

    # ---------- 5. تخصیص مسیر به پهپادها ----------
    allocator = DroneAllocator(coverage_path_m, drones, home_m, area_utm)
    allocations = allocator.allocate_by_length()
    for drone_id, path in allocations.items():
        if path:
            logger.info(f"{drone_id}: {len(path)} نقطه، طول تقریبی: {sum(math.hypot(path[i][0]-path[i-1][0], path[i][1]-path[i-1][1]) for i in range(1, len(path))):.2f} متر")
        else:
            logger.info(f"{drone_id}: بدون مسیر")

    # ---------- 6. بررسی باتری برای هر پهپاد ----------
    battery_results = {}
    warnings = []
    for drone in drones:
        drone_alloc = allocations.get(drone.drone_id, [])
        if not drone_alloc:
            battery_results[drone.drone_id] = None
            continue
        # مسیر کامل شامل رفت و برگشت به آشیانه
        full_route_utm = combine_full_route(home_m, drone_alloc)
        result = check_battery(full_route_utm, drone, home_m)
        battery_results[drone.drone_id] = result
        if result.can_complete:
            logger.info(f"{drone.drone_id}: مأموریت با باتری قابل انجام است. درصد باتری باقی‌مانده: {result.battery_remaining_percent:.1f}%")
        else:
            msg = f"{drone.drone_id}: مأموریت با باتری قابل انجام نیست (دلیل: {result.return_reason})"
            logger.warning(msg)
            warnings.append(msg)

    # ---------- 7. برنامه‌ریزی شیفت‌ها ----------
    scheduler = ShiftScheduler(
        drones=drones,
        mission_config=mission_config,
        home_m=home_m,
        coverage_path_m=coverage_path_m,
        allocations=allocations,
    )
    start_time = datetime.now()
    shifts = scheduler.create_shifts(start_time=start_time)
    logger.info(f"تعداد شیفت‌ها: {len(shifts)}")

    # ---------- 8. ساخت MissionPlan ----------
    mission_plan = MissionPlan(
        mission_id=f"mission_{start_time.strftime('%Y%m%d_%H%M%S')}",
        created_at=start_time.isoformat(),
        coordinate_reference_system="WGS84",
        area={
            "area_m2": area_utm.area,
            "coverage_percent": 100.0,  # فرض پوشش کامل در این سناریو
        },
        summary={
            "number_of_drones": len(drones),
            "number_of_shifts": len(shifts),
            "total_distance_m": sum(dp.distance_m for sh in shifts for dp in sh.drones),
            "maximum_revisit_interval_min": None,
            "warnings": warnings,
        },
        shifts=shifts,
        uncovered_segments=[],
        warnings=warnings,
    )

    # ---------- 9. پر کردن Waypoint ها با مختصات WGS84 ----------
    # برای هر شیفت و هر پهپاد، مسیر مأموریت (از allocation) را به WGS84 تبدیل و Waypoint بسازیم.
    # در این نسخه، نقاط مسیر هر پهپاد از allocation گرفته می‌شود.
    for shift in mission_plan.shifts:
        for drone_plan in shift.drones:
            drone_id = drone_plan.drone_id
            drone_alloc = allocations.get(drone_id, [])
            if not drone_alloc:
                continue
            # تبدیل نقاط UTM به WGS84
            from shapely.geometry import LineString
            line_utm = LineString(drone_alloc)
            line_wgs = utm_to_wgs84(line_utm, src_crs)
            wgs_points = [(lat, lon) for lon, lat in line_wgs.coords]  # (lat, lon)

            waypoints = []
            for i, (lat, lon) in enumerate(wgs_points):
                wp = Waypoint(
                    latitude=lat,
                    longitude=lon,
                    altitude_m=drones[0].altitude_m,  # از پهپاد
                    speed_mps=drones[0].speed_mps,
                    action=WaypointAction.SURVEY if i > 0 and i < len(wgs_points)-1 else (
                        WaypointAction.TAKEOFF if i == 0 else WaypointAction.LANDING
                    ),
                    sequence=i,
                )
                waypoints.append(wp)
            drone_plan.waypoints = waypoints

    # ---------- 10. تولید خروجی‌ها ----------
    output_dir = Path("F:/New folder/drone_planner/exporters/output")
    output_dir.mkdir(exist_ok=True)

    # JSON
    json_path = output_dir / "mission_plan.json"
    save_mission_plan_json(mission_plan, str(json_path))
    logger.info(f"فایل JSON ذخیره شد: {json_path}")

    # GeoJSON از مسیرها (برای نمایش)
    geojson_features = [
        polygon_to_geojson(area_wgs, properties={"type": "area"})
    ]
    # افزودن مسیر هر پهپاد
    for shift in mission_plan.shifts:
        for drone_plan in shift.drones:
            if not drone_plan.waypoints:
                continue
            pts = [(wp.latitude, wp.longitude) for wp in drone_plan.waypoints]
            geojson_features.append(
                points_to_geojson_line(
                    pts,
                    properties={"drone_id": drone_plan.drone_id, "type": "route"}
                )
            )
    geojson_collection = create_feature_collection(geojson_features)
    geojson_path = output_dir / "mission_plan.geojson"
    with open(geojson_path, 'w', encoding='utf-8') as f:
        json.dump(geojson_collection, f, indent=2, ensure_ascii=False)
    logger.info(f"فایل GeoJSON ذخیره شد: {geojson_path}")

    # نقشه HTML
    map_center = (home_lat, home_lon)
    m = create_map(center=map_center, zoom_start=13)
    # محدوده
    add_polygon_to_map(m, polygon_to_geojson(area_wgs))
    # آشیانه
    add_marker(m, home_lat, home_lon, "Home", icon_color="red")
    # مسیرها
    colors = ["blue", "green", "orange", "purple", "darkred"]
    for i, shift in enumerate(mission_plan.shifts):
        for drone_plan in shift.drones:
            if not drone_plan.waypoints:
                continue
            pts = [(wp.latitude, wp.longitude) for wp in drone_plan.waypoints]
            add_route_to_map(m, pts, color=colors[i % len(colors)], weight=3)
    html_path = output_dir / "mission_map.html"
    save_map_html(m, str(html_path))
    logger.info(f"نقشه HTML ذخیره شد: {html_path}")

    logger.info("سناریو با موفقیت به پایان رسید.")


if __name__ == "__main__":
    main()