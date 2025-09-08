# gui/widgets/common.py
"""
Общие виджеты, переиспользуемые компоненты
"""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict


class MetricsPanel:
    """Панель с метриками (количество файлов, строк и т.д.)"""
    
    def __init__(self, parent, metrics_config: Dict[str, str]):
        """
        metrics_config: {"files": "Files: —", "lines": "Lines: —", ...}
        """
        self.frame = ttk.Frame(parent)
        self.vars = {}
        
        for i, (key, default_text) in enumerate(metrics_config.items()):
            var = tk.StringVar(value=default_text)
            self.vars[key] = var
            ttk.Label(self.frame, textvariable=var).grid(
                row=0, column=i, padx=(0, 20), sticky='w'
            )
    
    def update_metric(self, key: str, value: str):
        """Обновляет значение метрики."""
        if key in self.vars:
            self.vars[key].set(value)
    
    def grid(self, **kwargs):
        """Размещает панель в родительском контейнере."""
        self.frame.grid(**kwargs)


class LogPanel:
    """Панель логов с заголовком."""
    
    def __init__(self, parent, title: str = "Журнал операций", height: int = 12):
        self.log_frame = ttk.LabelFrame(parent, text=title)
        self.log = ScrolledText(self.log_frame, height=height, state='disabled')
        self.log.pack(fill='both', expand=True, padx=4, pady=4)
    
    def pack(self, **kwargs):
        """Размещает панель логов."""
        self.log_frame.pack(**kwargs)
    
    def get_widget(self) -> ScrolledText:
        """Возвращает виджет ScrolledText для логирования."""
        return self.log


class FileSelector:
    """Компонент для выбора файлов с кнопкой Browse."""
    
    def __init__(self, parent, label_text: str, width: int = 60, 
                 browse_callback=None, file_types=None):
        self.frame = ttk.Frame(parent)
        
        ttk.Label(self.frame, text=label_text).grid(row=0, column=0, sticky='e', padx=(0, 6))
        
        self.entry = ttk.Entry(self.frame, width=width)
        self.entry.grid(row=0, column=1, sticky='we', padx=(0, 6))
        
        self.browse_btn = ttk.Button(self.frame, text="Browse…", 
                                   command=browse_callback or self._default_browse)
        self.browse_btn.grid(row=0, column=2)
        
        self.frame.columnconfigure(1, weight=1)
        self.file_types = file_types or [("All files", "*.*")]
    
    def _default_browse(self):
        """Заглушка для browse callback."""
        pass
    
    def get_value(self) -> str:
        """Получает значение из поля ввода."""
        return self.entry.get().strip()
    
    def set_value(self, value: str):
        """Устанавливает значение в поле ввода."""
        self.entry.delete(0, 'end')
        self.entry.insert(0, value)
    
    def grid(self, **kwargs):
        """Размещает компонент."""
        self.frame.grid(**kwargs)


class SettingsFrame:
    """Фрейм с настройками (кодировки, разделители и т.д.)"""
    
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.widgets = {}
        self.row = 0
    
    def add_combobox(self, label: str, key: str, values: list, default: str = "", width: int = 15):
        """Добавляет combobox с подписью."""
        ttk.Label(self.frame, text=label).grid(row=self.row, column=len(self.widgets)*2, 
                                             sticky='w', padx=(0, 6))
        
        combo = ttk.Combobox(self.frame, width=width, values=values, state="readonly")
        if default:
            combo.set(default)
        combo.grid(row=self.row, column=len(self.widgets)*2+1, padx=(0, 16))
        
        self.widgets[key] = combo
        return combo
    
    def add_entry(self, label: str, key: str, default: str = "", width: int = 15):
        """Добавляет поле ввода с подписью."""
        ttk.Label(self.frame, text=label).grid(row=self.row, column=len(self.widgets)*2, 
                                             sticky='w', padx=(0, 6))
        
        entry = ttk.Entry(self.frame, width=width)
        if default:
            entry.insert(0, default)
        entry.grid(row=self.row, column=len(self.widgets)*2+1, padx=(0, 16))
        
        self.widgets[key] = entry
        return entry
    
    def add_checkbox(self, label: str, key: str, default: bool = False):
        """Добавляет checkbox."""
        var = tk.BooleanVar(value=default)
        checkbox = ttk.Checkbutton(self.frame, text=label, variable=var)
        checkbox.grid(row=self.row, column=len(self.widgets)*2, padx=(0, 16))
        
        self.widgets[key] = var
        return var
    
    def new_row(self):
        """Переходит на новую строку."""
        self.row += 1
    
    def get_value(self, key: str):
        """Получает значение виджета."""
        widget = self.widgets.get(key)
        if isinstance(widget, tk.BooleanVar):
            return widget.get()
        elif hasattr(widget, 'get'):
            return widget.get()
        return None
    
    def grid(self, **kwargs):
        """Размещает фрейм настроек."""
        self.frame.grid(**kwargs)