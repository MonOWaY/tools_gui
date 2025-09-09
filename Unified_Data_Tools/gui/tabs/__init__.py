# Unified_Data_Tools/gui/tabs/__init__.py
"""
Модули вкладок GUI
"""
from .main_tabs import MainTabs
from .helper_tabs import add_helper_tabs  # в helper_tabs.py функция, а не класс

# Шим для совместимости со старым импортом:
class HelperTabs:
    def __init__(self, app):
        add_helper_tabs(app)

__all__ = ["MainTabs", "add_helper_tabs", "HelperTabs"]
