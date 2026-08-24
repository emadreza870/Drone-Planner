"""
توابع تبدیل سیستم مختصات بین WGS84 و UTM.
"""

from typing import Optional

from pyproj import CRS, Transformer
from shapely.geometry import base
from shapely.ops import transform


def get_utm_epsg(longitude: float, latitude: float) -> int:
    """
    محاسبه EPSG code برای ناحیه UTM بر اساس مختصات جغرافیایی.

    Args:
        longitude: طول جغرافیایی (درجه).
        latitude: عرض جغرافیایی (درجه).

    Returns:
        int: کد EPSG سیستم UTM مناسب (مثلاً 32639 برای شمال، 32739 برای جنوب).
    """
    zone = int((longitude + 180) // 6) + 1
    if latitude >= 0:
        return 32600 + zone  # WGS 84 / UTM zone N
    else:
        return 32700 + zone  # WGS 84 / UTM zone S


def get_utm_crs(longitude: float, latitude: float) -> CRS:
    """
    بازگرداندن CRS ناحیه UTM برای مختصات داده‌شده.

    Args:
        longitude: طول جغرافیایی.
        latitude: عرض جغرافیایی.

    Returns:
        CRS: شئ CRS مربوط به UTM.
    """
    epsg = get_utm_epsg(longitude, latitude)
    return CRS.from_epsg(epsg)


def transform_geometry(
    geometry: base.BaseGeometry,
    src_crs: CRS = CRS.from_epsg(4326),  # WGS84
    dst_crs: Optional[CRS] = None,
    longitude: Optional[float] = None,
    latitude: Optional[float] = None,
) -> base.BaseGeometry:
    """
    تبدیل یک هندسه از یک CRS به CRS دیگر.
    اگر dst_crs داده نشود، بر اساس مرکز هندسه (centroid) ناحیه UTM تعیین می‌شود.

    Args:
        geometry: هندسه ورودی.
        src_crs: CRS مبدأ (پیش‌فرض WGS84).
        dst_crs: CRS مقصد (اختیاری).
        longitude: طول جغرافیایی برای تعیین dst_crs (اختیاری).
        latitude: عرض جغرافیایی برای تعیین dst_crs (اختیاری).

    Returns:
        base.BaseGeometry: هندسه تبدیل‌شده.
    """
    if dst_crs is None:
        if longitude is None or latitude is None:
            # تعیین از centroid هندسه
            centroid = geometry.centroid
            longitude, latitude = centroid.x, centroid.y
        dst_crs = get_utm_crs(longitude, latitude)

    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    return transform(transformer.transform, geometry)


def wgs84_to_utm(
    geometry: base.BaseGeometry,
    longitude: Optional[float] = None,
    latitude: Optional[float] = None,
) -> base.BaseGeometry:
    """
    تبدیل هندسه از WGS84 به UTM.

    Args:
        geometry: هندسه در WGS84.
        longitude, latitude: مختصات برای تعیین ناحیه UTM (اختیاری).

    Returns:
        base.BaseGeometry: هندسه در UTM متری.
    """
    return transform_geometry(
        geometry,
        src_crs=CRS.from_epsg(4326),
        dst_crs=None,
        longitude=longitude,
        latitude=latitude,
    )


def utm_to_wgs84(
    geometry: base.BaseGeometry,
    src_crs: CRS,
) -> base.BaseGeometry:
    """
    تبدیل هندسه از UTM به WGS84.

    Args:
        geometry: هندسه در UTM.
        src_crs: CRS مبدأ (UTM).

    Returns:
        base.BaseGeometry: هندسه در WGS84.
    """
    return transform_geometry(
        geometry,
        src_crs=src_crs,
        dst_crs=CRS.from_epsg(4326),
    )