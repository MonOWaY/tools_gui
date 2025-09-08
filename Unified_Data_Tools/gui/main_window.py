# gui/main_window.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

# Внутренние вкладки
from gui.tabs.main_tabs import add_main_tabs    # уже реализовано у тебя
from gui.tabs.helper_tabs import add_helper_tabs

class MainWindow(tk.Tk):
    """Главное окно приложения Unified Data Tools (модульная версия)."""

    def __init__(self, *, title: str = "Unified Data Tools", geometry: str = "1200x900"):
        super().__init__()
        self.title(title)
        self.geometry(geometry)

        # Строковые метрики, чтобы вкладки могли их обновлять
        self._init_metrics()

        # Общий Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        # Основные вкладки (TXT→Table, Find/Remove Duplicates, Email Scanner)
        add_main_tabs(self)

        # Вспомогательные вкладки (Replace, Split, Join, CSV→TXT, Delete by List, Separator, Copy Files)
        add_helper_tabs(self)

        # Общий лог внизу
        self._create_log_section()

        # Немного аккуратной темы, если доступна
        try:
            style = ttk.Style()
            style.theme_use("clam")
        except Exception:
            pass

    # ------------------------------ Метрики -----------------------------------

    def _init_metrics(self):
        # TXT → Table
        self.txt_files_var = tk.StringVar(value="Files: —")
        self.txt_lines_var = tk.StringVar(value="Lines: —")

        # Find Duplicates
        self.dup_files_var = tk.StringVar(value="Files: —")
        self.dup_lines_var = tk.StringVar(value="Lines: —")
        self.dup_found_var = tk.StringVar(value="Duplicates found: —")

        # Remove Duplicates
        self.dd_files_var = tk.StringVar(value="Files: —")
        self.dd_lines_var = tk.StringVar(value="Lines: —")
        self.dd_before_var = tk.StringVar(value="Lines Before: —")
        self.dd_after_var = tk.StringVar(value="Lines After: —")
        self.dd_dups_lines_var = tk.StringVar(value="Duplicates Lines: —")
        self.dd_removed_var = tk.StringVar(value="Duplicates removed: —")

        # Email Duplicates
        self.ed_files_var = tk.StringVar(value="Files: —")
        self.ed_lines_var = tk.StringVar(value="Lines: —")
        self.ed_found_var = tk.StringVar(value="Duplicate emails: —")

        # File Separator
        self.sep_files_var = tk.StringVar(value="Files: —")
        self.sep_lines_var = tk.StringVar(value="Lines: —")
        self.sep_parts_var = tk.StringVar(value="Parts created: —")

        # Copy Files
        self.copy_files_var = tk.StringVar(value="Files: —")
        self.copy_lines_var = tk.StringVar(value="Lines: —")
        self.copy_total_var = tk.StringVar(value="Total lines: —")

    # -------------------------- Секция общего лога -----------------------------

    def _create_log_section(self):
        log_frame = ttk.LabelFrame(self, text="Журнал операций")
        log_frame.pack(fill='both', expand=False, padx=8, pady=(0, 8))

        # Делай public — вкладки будут писать сюда
        self.log = ScrolledText(log_frame, height=12, state='disabled')
        self.log.pack(fill='both', expand=True, padx=4, pady=4)


def run():
    app = MainWindow(title="Unified Data Tools - Полный набор инструментов для работы с данными")
    app.mainloop()


if __name__ == "__main__":
    run()
