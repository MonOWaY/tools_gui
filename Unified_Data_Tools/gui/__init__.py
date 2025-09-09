# Unified_Data_Tools/gui/__init__.py
"""
GUI модуль для Unified Data Tools
"""
from .main_window import MainWindow

# Backward-compat: старое имя из монолита
UnifiedDataTools = MainWindow

__all__ = ["MainWindow", "UnifiedDataTools"]
