"""
رابط کاربری Streamlit برای برنامه‌ریزی مأموریت.
"""
import sys
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from datetime import datetime
from pathlib import Path
import tempfile

sys.path.append(str(Path(__file__).parent.parent))

# Import های داخلی
from models.drone import Drone, DroneStatus
from models.mission import MissionConfig, CameraConfig
from models.waypoint import Waypoint, WaypointAction
from models.schedule import MissionPlan, Shift, DronePlan, CellStatus
from geo.io import read_area_polygon, read_no_fly_zones
from geo.projection import (
    wgs84_to_utm,
    utm_to_wgs84,
    get_utm_crs,
    transform_geometry,
)
from geo.polygon_ops import validate_polygon, repair_polygon, subtract_no_fly_zones
from planning.coverage_planner import CoveragePlanner, optimize_angle
from planning.route_connector import combine_full_route
from planning.drone_allocator import DroneAllocator
from planning.battery_checker import check_battery
from planning.shift_scheduler import ShiftScheduler
from planning.persistent_coverage import PersistentCoverage
from visualization.map_view import create_map, add_polygon_to_map, add_marker, add_route_to_map
from exporters.geojson_exporter import polygon_to_geojson, points_to_geojson_line, create_feature_collection
from exporters.json_exporter import mission_plan_to_dict
from exporters.html_map_exporter import map_to_html_string

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- توابع کمکی ----------

def generate_unique_colors(n: int) -> list[str]:
    """تولید n رنگ مجزا."""
    # استفاده از پالت های از پیش تعیین شده
    base_colors = [
        "#e6194B", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
        "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
        "#469990", "#dcbeff", "#9A6324", "#fffac8", "#800000",
        "#aaffc3", "#808000", "#ffd8b1", "#000075", "#a9a9a9",
    ]
    if n <= len(base_colors):
        return base_colors[:n]
    # اگر بیشتر بود، رنگ‌های تصادفی تولید کنیم
    import random
    random.seed(42)
    extra = ["#%06x" % random.randint(0, 0xFFFFFF) for _ in range(n - len(base_colors))]
    return base_colors + extra


def convert_points_to_wgs84(points_m, src_crs):
    """تبدیل لیست نقاط متری (x,y) به لیست (lat, lon)."""
    if not points_m:
        return []
    from shapely.geometry import LineString
    line = LineString(points_m)
    line_wgs = utm_to_wgs84(line, src_crs)
    return [(lat, lon) for lon, lat in line_wgs.coords]


def main():
    # --- تغییر اول: تعریف متغیر وضعیت در حافظه استریم‌لیت ---
    if 'mission_generated' not in st.session_state:
        st.session_state.mission_generated = False

    st.set_page_config(page_title="Drone Mission Planner", layout="wide")
    st.title("Drone Mission Planner - Phase 1")
    st.markdown("برنامه‌ریزی مأموریت چندپهپادی برای پایش مناطق")

    # ---------- سایدبار برای ورودی‌ها ----------
    with st.sidebar:
        st.header("ورودی‌ها")

        # آپلود GeoJSON محدوده
        area_file = st.file_uploader("آپلود فایل GeoJSON محدوده", type=["geojson", "json"])
        
        # ورود مختصات آشیانه
        st.subheader("موقعیت آشیانه")
        home_lat = st.number_input("عرض جغرافیایی (latitude)", value=35.0, format="%.6f")
        home_lon = st.number_input("طول جغرافیایی (longitude)", value=51.0, format="%.6f")

        # تعداد پهپادها
        n_drones = st.number_input("تعداد پهپادها", min_value=1, max_value=10, value=1, step=1)

        # مشخصات هر پهپاد
        st.subheader("مشخصات پهپادها")
        drones = []
        for i in range(int(n_drones)):
            st.markdown(f"**پهپاد {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                drone_id = st.text_input(f"شناسه", value=f"drone_{i+1:02d}", key=f"id_{i}")
                max_flight = st.number_input(f"حداکثر زمان پرواز (دقیقه)", min_value=1.0, value=30.0, key=f"max_{i}")
                speed = st.number_input(f"سرعت (m/s)", min_value=0.1, value=8.0, key=f"speed_{i}")
            with col2:
                altitude = st.number_input(f"ارتفاع (m)", min_value=1.0, value=80.0, key=f"alt_{i}")
                reserve = st.number_input(f"ذخیره (دقیقه)", min_value=0.0, value=5.0, key=f"res_{i}")
                status = st.selectbox(f"وضعیت", ["available", "maintenance", "charging"], key=f"status_{i}")
            drones.append(Drone(
                drone_id=drone_id,
                max_flight_time_min=max_flight,
                speed_mps=speed,
                altitude_m=altitude,
                reserve_time_min=reserve,
                takeoff_time_sec=30,
                landing_time_sec=30,
                status=DroneStatus(status),
            ))

        # پارامترهای مأموریت
        st.subheader("پارامترهای مأموریت")
        use_camera = st.checkbox("استفاده از دوربین", value=False)
        if use_camera:
            fov = st.number_input("زاویه دید دوربین (درجه)", min_value=1.0, max_value=180.0, value=60.0)
            overlap = st.number_input("هم‌پوشانی (0-1)", min_value=0.0, max_value=0.99, value=0.2)
            camera = CameraConfig(fov_deg=fov, overlap_ratio=overlap)
            track_spacing = None
        else:
            track_spacing = st.number_input("فاصله خطوط پرواز (متر)", min_value=1.0, value=40.0)
            camera = None

        shift_duration = st.number_input("مدت شیفت (دقیقه)", min_value=1.0, value=45.0)
        revisit_interval = st.number_input("زمان بازدید مجدد هدف (دقیقه)", min_value=1.0, value=60.0)

        # --- تغییر دوم: دکمه فقط حافظه را آپدیت می‌کند ---
        if st.button("تولید برنامه پروازی"):
            st.session_state.mission_generated = True

    # ---------- بخش اصلی ----------
    
    # --- تغییر سوم: تمام کدهای پردازش بر اساس متغیر حافظه اجرا می‌شوند ---
    if st.session_state.mission_generated:
        if area_file is None:
            st.error("لطفاً فایل GeoJSON محدوده را آپلود کنید.")
        else:
            # خواندن محدوده از فایل
            try:
                # ذخیره موقت فایل
                with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmp:
                    tmp.write(area_file.getvalue())
                    tmp_path = tmp.name
                area_polygon_wgs = read_area_polygon(tmp_path)
            except Exception as e:
                st.error(f"خطا در خواندن محدوده: {e}")
                return

            # اعتبارسنجی و اصلاح
            if not validate_polygon(area_polygon_wgs):
                area_polygon_wgs = repair_polygon(area_polygon_wgs)

            # خواندن مناطق ممنوعه (اختیاری) - در این نسخه ساده از ورودی صرف نظر می‌کنیم
            no_fly_zones_wgs = []  # می‌توان بعداً اضافه کرد

            # حذف مناطق ممنوعه
            if no_fly_zones_wgs:
                area_polygon_wgs = subtract_no_fly_zones(area_polygon_wgs, no_fly_zones_wgs)

            # تبدیل محدوده به UTM
            # تعیین CRS بر اساس مرکز محدوده
            centroid = area_polygon_wgs.centroid
            src_crs = get_utm_crs(centroid.x, centroid.y)
            area_polygon_utm = wgs84_to_utm(area_polygon_wgs, centroid.x, centroid.y)
            
            # همچنین مختصات آشیانه به UTM
            from shapely.geometry import Point
            home_point_wgs = Point(home_lon, home_lat)
            home_point_utm = wgs84_to_utm(home_point_wgs, centroid.x, centroid.y)
            home_m = (home_point_utm.x, home_point_utm.y)

            # ساخت MissionConfig
            mission_config = MissionConfig(
                track_spacing_m=track_spacing if not use_camera else None,
                overlap_ratio=overlap if use_camera else 0.2,
                shift_duration_min=shift_duration,
                target_revisit_interval_min=revisit_interval,
                default_altitude_m=drones[0].altitude_m,
                default_speed_mps=drones[0].speed_mps,
                reserve_time_min=drones[0].reserve_time_min,
                takeoff_time_sec=30,
                landing_time_sec=30,
                camera=camera,
            )

            # تعیین فاصله خطوط (اگر دوربین داریم)
            if use_camera:
                # W = 2 * h * tan(FOV/2)
                import math
                h = drones[0].altitude_m
                fov_rad = math.radians(camera.fov_deg)
                W = 2 * h * math.tan(fov_rad / 2)
                spacing = W * (1 - camera.overlap_ratio)
            else:
                spacing = mission_config.track_spacing_m

            # تولید مسیر پوشش
            planner = CoveragePlanner(area_polygon_utm, spacing, angle_deg=0)  # زاویه 0 درجه
            coverage_path_m = planner.generate_coverage_path()
            
            if not coverage_path_m:
                st.error("هیچ مسیری تولید نشد.")
            else:
                # بهینه‌سازی زاویه (اختیاری) - می‌توانیم فعال کنیم
                # best_angle, _ = optimize_angle(area_polygon_utm, spacing)
                # planner = CoveragePlanner(area_polygon_utm, spacing, best_angle)
                # coverage_path_m = planner.generate_coverage_path()

                # تخصیص مسیر به پهپادها
                allocator = DroneAllocator(coverage_path_m, drones, home_m, area_polygon_utm)
                allocations = allocator.allocate_by_length()  # یا allocate_by_grid

                # برنامه‌ریزی شیفت‌ها
                scheduler = ShiftScheduler(
                    drones=drones,
                    mission_config=mission_config,
                    home_m=home_m,
                    coverage_path_m=coverage_path_m,
                    allocations=allocations,
                )
                shifts = scheduler.create_shifts(start_time=datetime.now())

                # ساخت MissionPlan
                mission_plan = MissionPlan(
                    mission_id=f"mission_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    created_at=datetime.now().isoformat(),
                    coordinate_reference_system="WGS84",
                    area={
                        "area_m2": area_polygon_utm.area,
                        "coverage_percent": 100.0,  # فرض پوشش کامل (بعداً بهبود)
                    },
                    summary={
                        "number_of_drones": len(drones),
                        "number_of_shifts": len(shifts),
                        "total_distance_m": sum(dp.distance_m for sh in shifts for dp in sh.drones),
                        "maximum_revisit_interval_min": None,  # بعداً
                        "warnings": [],
                    },
                    shifts=shifts,
                    uncovered_segments=[],
                    warnings=[],
                )

                # ساخت خروجی‌ها
                # GeoJSON
                features = []
                # محدوده مجاز
                features.append(polygon_to_geojson(area_polygon_wgs, properties={"type": "area"}))
                # مسیرها
                for shift in shifts:
                    for drone_plan in shift.drones:
                        # در این نسخه، drone_plan.waypoints خالی است. باید پر کنیم.
                        pass  # در ادامه

                # نمایش نقشه
                st.subheader("نقشه مأموریت")
                # ساخت نقشه با مرکز آشیانه
                m = create_map(center=(home_lat, home_lon), zoom_start=12)
                # افزودن محدوده
                add_polygon_to_map(m, polygon_to_geojson(area_polygon_wgs))
                # افزودن آشیانه
                add_marker(m, home_lat, home_lon, "Home", icon_color="red")
                
                # افزودن مسیرها (فقط مسیر اصلی برای نمایش)
                # تبدیل مسیر کامل به WGS84
                full_path_wgs = convert_points_to_wgs84(coverage_path_m, src_crs)
                add_route_to_map(m, full_path_wgs, color="blue", weight=3)

                # نمایش نقشه (اکنون با رفرش شدن ناپدید نمی‌شود)
                st_folium(m, width=1000, height=600)

                # نمایش جدول گزارش
                st.subheader("گزارش پهپادها")
                report_data = []
                for shift in shifts:
                    for dp in shift.drones:
                        report_data.append({
                            "شناسه": dp.drone_id,
                            "وضعیت": dp.status,
                            "مسافت (m)": round(dp.distance_m, 2),
                            "مدت (min)": round(dp.duration_min, 2),
                            "باتری باقی‌مانده (%)": round(dp.estimated_battery_remaining_percent, 1),
                            "دلیل بازگشت": dp.return_reason or "-",
                        })
                if report_data:
                    import pandas as pd
                    st.table(pd.DataFrame(report_data))

                # هشدارها
                if mission_plan.warnings:
                    st.warning("هشدارها:")
                    for w in mission_plan.warnings:
                        st.write(f"- {w}")

                # دکمه‌های دانلود
                st.subheader("دانلود خروجی‌ها")
                # JSON
                json_str = json.dumps(mission_plan_to_dict(mission_plan), indent=2, ensure_ascii=False)
                st.download_button(
                    label="دانلود JSON برنامه",
                    data=json_str,
                    file_name="mission_plan.json",
                    mime="application/json",
                )
                # GeoJSON
                # ساخت GeoJSON از مسیرها (ساده)
                geojson_features = [polygon_to_geojson(area_polygon_wgs, properties={"type": "area"})]
                # مسیر کامل
                geojson_features.append(points_to_geojson_line(full_path_wgs, properties={"type": "coverage_path"}))
                geojson_obj = create_feature_collection(geojson_features)
                geojson_str = json.dumps(geojson_obj, indent=2)
                st.download_button(
                    label="دانلود GeoJSON",
                    data=geojson_str,
                    file_name="coverage.geojson",
                    mime="application/geo+json",
                )
                # HTML نقشه
                html_str = map_to_html_string(m)
                st.download_button(
                    label="دانلود نقشه HTML",
                    data=html_str,
                    file_name="map.html",
                    mime="text/html",
                )


if __name__ == "__main__":
    main()
