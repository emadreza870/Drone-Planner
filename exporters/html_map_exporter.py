"""
تولید نقشه HTML از اشیاء Folium.
"""

import folium
from typing import List, Tuple, Dict, Any


def save_map_html(m: folium.Map, file_path: str) -> None:
    """ذخیره نقشه Folium به عنوان فایل HTML."""
    m.save(file_path)


def map_to_html_string(m: folium.Map) -> str:
    """تبدیل نقشه به رشته HTML برای نمایش در Streamlit."""
    return m._repr_html_()