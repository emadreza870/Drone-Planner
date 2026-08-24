"""
تست نصب و ساختار اولیه پروژه.
"""

import importlib

def test_app_main_importable():
    """بررسی اینکه ماژول app.main قابل import است."""
    module = importlib.import_module("app.main")
    assert hasattr(module, "main")

def test_models_importable():
    """بررسی import مدل‌های اصلی."""
    import models
    assert hasattr(models, "Drone")
    assert hasattr(models, "MissionConfig")
    assert hasattr(models, "Waypoint")